"""Offline transport edge cases. Network access is neither needed nor performed."""
import copy
from decimal import Decimal
import http.client
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collection_adapter.core import Transport,encode,recorded_exchange,inspect_response,budget_bound,request_body,count_body
ROOT=Path(__file__).resolve().parents[1]
SETTINGS=json.loads((ROOT/'collection/settings.selected.json').read_text())
PRICING=json.loads((ROOT/'collection/api-review.json').read_text())

class FakeResponse:
    status=200
    def __init__(self,chunks,error=None): self.chunks=list(chunks); self.error=error
    def getheaders(self): return [('x-request-id','fixture-request-id'),('Set-Cookie','private-cookie')]
    def read(self,size):
        if self.chunks: return self.chunks.pop(0)
        if self.error: raise self.error
        return b''
class FakeConnection:
    def __init__(self,response,error=None): self.response=response; self.error=error; self.sends=0; self.closed=False
    def request(self,*args,**kwargs):
        self.sends+=1
        if self.error: raise self.error
    def getresponse(self): return self.response
    def close(self): self.closed=True
class Tests(unittest.TestCase):
    def test_existing_pilot_stops_before_preflight(self):
        from unittest.mock import patch
        import run_collection
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); guard=root/'results/collection/generation-dispatch.lock'
            guard.parent.mkdir(parents=True); guard.write_text('{"original":"untouched"}')
            before=guard.read_bytes()
            with patch.object(run_collection,'ROOT',root), patch.object(sys,'argv',['run_collection.py','--collect']), patch.object(run_collection,'Transport') as transport, patch.object(run_collection,'snapshot') as snapshot, patch('builtins.print'):
                self.assertEqual(run_collection.main(),2)
                transport.assert_not_called(); snapshot.assert_not_called()
            self.assertEqual(guard.read_bytes(),before)
            self.assertEqual(list(guard.parent.iterdir()),[guard])

    def test_all_labelled_fixtures(self):
        manifest=json.loads((ROOT/'controls/collection-adapter/manifest.json').read_text())
        for c in manifest['controls']:
            with self.subTest(c['id']):
                raw=(ROOT/c['body']).read_bytes()
                meta={'http_status':c['http_status'],'completion_uncertain':c['transport_error'] is not None}
                r=inspect_response(meta,raw,SETTINGS,PRICING); expected=c['expected']
                self.assertEqual(bool(r['halt_reasons']),expected['halt'])
                self.assertEqual((r['extraction'] or {}).get('status'),expected['text_status'])
                self.assertEqual((r['accounting'] or {}).get('estimated_api_cost_usd'),expected['cost'])
                if 'exact_text' in expected: self.assertEqual(r['extraction']['text'],expected['exact_text'])
    def test_lossless_raw_and_attempt_precedes_send(self):
        raw=b'{  "not_normalized": "\\u03b1" }\r\n'
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'slot'; backups=[]
            conn=FakeConnection(FakeResponse([raw]))
            original_request=conn.request
            def request(*args,**kwargs):
                self.assertTrue((folder/'attempt.json').exists()); self.assertTrue(backups)
                return original_request(*args,**kwargs)
            conn.request=request
            t=Transport('fixture-secret-value',connection_factory=lambda:conn)
            meta,body=recorded_exchange(folder,t,'POST','/v1/responses',{'input':'x'},'synthetic_fixture',lambda:backups.append(True))
            self.assertEqual((folder/'response.body.raw').read_bytes(),raw)
            self.assertEqual(body,raw); self.assertEqual(conn.sends,1)
            self.assertNotIn('set-cookie',meta['headers'])
            self.assertNotIn(b'fixture-secret-value',b''.join(p.read_bytes() for p in folder.iterdir()))
            with self.assertRaises(FileExistsError): recorded_exchange(folder,t,'POST','/v1/responses',{},'synthetic_fixture',lambda:None)
            self.assertEqual(conn.sends,1)
    def test_timeout_never_retries(self):
        conn=FakeConnection(FakeResponse([]),TimeoutError('sensitive exception must not be logged'))
        result=Transport('fixture-secret-value',connection_factory=lambda:conn).exchange('POST','/v1/responses',b'{}','fixture')
        self.assertEqual(conn.sends,1); self.assertTrue(result['completion_uncertain'])
        self.assertNotIn('sensitive',str(result)); self.assertEqual(result['error_type'],'TimeoutError')
    def test_partial_body_preserved(self):
        conn=FakeConnection(FakeResponse([b'first'],http.client.IncompleteRead(b'last')))
        r=Transport('fixture-secret-value',connection_factory=lambda:conn).exchange('POST','/v1/responses',b'{}','fixture')
        self.assertEqual(r['body'],b'firstlast'); self.assertTrue(r['completion_uncertain'])
    def test_credential_echo_withheld(self):
        with tempfile.TemporaryDirectory() as d:
            conn=FakeConnection(FakeResponse([b'error: fixture-secret-value']))
            t=Transport('fixture-secret-value',connection_factory=lambda:conn)
            meta,body=recorded_exchange(Path(d)/'slot',t,'POST','/v1/responses',{},'synthetic_fixture',lambda:None)
            self.assertIsNone(body); self.assertTrue(meta['credential_echo_withheld'])
            observed=inspect_response(meta,body,SETTINGS,PRICING)
            self.assertIn('uncertain_completion',observed['halt_reasons'])
            self.assertNotIn(b'fixture-secret-value',b''.join(p.read_bytes() for p in (Path(d)/'slot').iterdir()))
    def test_backup_failure_prevents_send(self):
        conn=FakeConnection(FakeResponse([])); t=Transport('fixture-secret-value',connection_factory=lambda:conn)
        def failed_backup(): raise OSError('fixture backup failure')
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError): recorded_exchange(Path(d)/'slot',t,'POST','/v1/responses',{},'synthetic_fixture',failed_backup)
        self.assertEqual(conn.sends,0)
    def test_cost_and_no_reasoning_double_count(self):
        per,total=budget_bound(SETTINGS,PRICING)
        self.assertEqual(per,Decimal('0.09392')); self.assertEqual(total,Decimal('1.69056'))
        self.assertLess(total,Decimal(SETTINGS['operational_ceiling_usd']))
    def test_request_is_one_fresh_user_message(self):
        raw=b' \r\nYAML\n'; req=request_body(raw,SETTINGS)
        self.assertEqual(req['input'],[{'role':'user','content':[{'type':'input_text','text':raw.decode()}]}])
        for k in ('temperature','top_p','seed','instructions','conversation','previous_response_id'): self.assertNotIn(k,req)
        self.assertEqual(req['tools'],[]); self.assertEqual(req['tool_choice'],'none')
        self.assertEqual(req['service_tier'],'default'); self.assertFalse(req['stream'])
        self.assertEqual(count_body(req)['reasoning'],req['reasoning'])
        self.assertEqual(count_body(req)['input'],req['input'])
    def test_selected_config_and_budget_guards(self):
        from run_collection import check_configuration, Halt
        self.assertEqual(check_configuration(SETTINGS,PRICING)[1],Decimal('1.69056'))
        for field,value in [('temperature',1),('max_output_tokens',8193),('model','other-model'),('service_tier','auto')]:
            altered=copy.deepcopy(SETTINGS); altered['request_fields'][field]=value
            with self.assertRaises(Halt): check_configuration(altered,PRICING)
    def test_access_identity_without_generation(self):
        from run_collection import actual_model_access, Halt
        meta={'http_status':200,'completion_uncertain':False}
        self.assertTrue(actual_model_access(meta,encode({'id':'gpt-6.1-sol','object':'model'}))['verified'])
        with self.assertRaises(Halt): actual_model_access(meta,encode({'id':'other','object':'model'}))
        with self.assertRaises(Halt): actual_model_access({'http_status':403,'completion_uncertain':False},b'{}')
    def test_backup_copy_hashes(self):
        from collection_adapter.workflow import mirror
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a'; b=Path(d)/'b'; a.mkdir(); (a/'original').write_bytes(b'body\r\n')
            mirror(a,b); self.assertEqual((a/'original').read_bytes(),(b/'original').read_bytes())
            with self.assertRaises(ValueError): mirror(a,a/'nested')
    def test_no_redirect_or_alt_host(self):
        conn=FakeConnection(FakeResponse([])); conn.response.status=307
        t=Transport('fixture-secret-value',connection_factory=lambda:conn)
        r=t.exchange('POST','/v1/responses',b'{}','fixture')
        self.assertEqual(r['http_status'],307); self.assertEqual(conn.sends,1)
        with self.assertRaises(ValueError): t.exchange('POST','https://other.invalid',b'{}','fixture')
if __name__=='__main__': unittest.main()
