"""Synthetic continuation controls. No provider API calls or experimental outputs."""
import copy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collection_adapter.continuation import (ALLOWED, Stop, claim, dispatch_slot, eligible,
    exposure, mark_uncertain, process_lock, verify_files, verify_frozen, reject_prior_continuation)
from collection_adapter.core import sha
ROOT=Path(__file__).resolve().parents[1]
SETTINGS=json.loads((ROOT/'collection/settings.selected.json').read_text())
PRICING=json.loads((ROOT/'collection/continuation-api-review.json').read_text())

class FakeTransport:
    def __init__(self,interrupt=False,uncertain=False): self.sends=0; self.interrupt=interrupt; self.uncertain=uncertain
    def contains_credential(self,body): return False
    def exchange(self,*args):
        self.sends+=1
        if self.interrupt: raise KeyboardInterrupt()
        return {'http_status':200,'headers':{},'completion_uncertain':self.uncertain,
                'body':(ROOT/'controls/collection-adapter/success.body').read_bytes()}

class ContinuationTests(unittest.TestCase):
    def test_prior_slot_claim_blocks_even_without_session_claim(self):
        with tempfile.TemporaryDirectory() as d:
            control=Path(d); reject_prior_continuation(control)
            claim(control/'attempts'/f'{ALLOWED[2]}.json',{'attempted':True})
            with self.assertRaises(Stop): reject_prior_continuation(control)

    def slots(self): return [{'slot_id':s,'status':'not_attempted'} for s in ALLOWED]
    def state(self): return {'slots':self.slots(),'generation_requests_attempted':0,'estimated_known_api_cost_usd':'0','unknown_cost_slots':[]}
    def test_exact_order_and_unknown_exclusion(self):
        with tempfile.TemporaryDirectory() as d:
            eligible(d,self.slots(),ALLOWED)
            for ids in [ALLOWED[::-1],('R03-G02',)+ALLOWED[1:],ALLOWED[:-1]]:
                with self.assertRaises(Stop): eligible(d,self.slots(),ids)
    def test_refuses_completed_and_attempted(self):
        with tempfile.TemporaryDirectory() as d:
            for status in ['response_recorded','attempted_before_dispatch','completion_unknown_after_interruption']:
                slots=self.slots(); slots[0]['status']=status
                with self.assertRaises(Stop): eligible(d,slots,ALLOWED)
            (Path(d)/'slots'/ALLOWED[0]).mkdir(parents=True)
            with self.assertRaises(Stop): eligible(d,self.slots(),ALLOWED)
    def test_exclusive_claim_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'claim.json'; claim(p,{'first':True}); before=p.read_bytes()
            with self.assertRaises(Stop): claim(p,{'second':True})
            self.assertEqual(p.read_bytes(),before)
    def test_concurrent_process_and_sigkill(self):
        with tempfile.TemporaryDirectory() as d:
            lock=Path(d)/'process.lock'; marker=Path(d)/'claim.json'
            code="import sys,time; from pathlib import Path; from collection_adapter.continuation import process_lock,claim\nwith process_lock(sys.argv[1]):\n claim(Path(sys.argv[2]), {'attempted':True}); print('locked',flush=True); time.sleep(30)"
            child=subprocess.Popen([sys.executable,'-B','-c',code,str(lock),str(marker)],cwd=ROOT/'scripts',stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(),'locked')
                with self.assertRaises(Stop):
                    with process_lock(lock): self.fail('Concurrent process acquired lock')
            finally:
                child.kill(); child.wait(timeout=5); child.stdout.close()
            with process_lock(lock):
                with self.assertRaises(Stop): claim(marker,{'retry':True})
    def test_unknown_cost_is_reserved(self):
        per=Decimal('0.09392')
        self.assertEqual(exposure('0.021224',1,9,per),Decimal('0.960424'))
        self.assertEqual(exposure('0.021224',2,8,per),Decimal('0.960424'))
        with self.assertRaises(Stop): exposure('4.9',1,9,per)
    def test_changed_frozen_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prompt'; p.write_bytes(b'exact\r\n'); h={'prompt':sha(p.read_bytes())}
            verify_files(d,h); p.write_bytes(b'exact\n')
            with self.assertRaises(Stop): verify_files(d,h)
    def test_frozen_request_bytes_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); original=root/'old'; p=original/'prepared-requests/R01.json'; p.parent.mkdir(parents=True)
            p.write_bytes(b'{"input":"same"}\n')
            freeze={'input_sha256':{},'prepared_request_sha256':{'R01':sha(p.read_bytes())}}
            verify_frozen(root,original,freeze); p.write_bytes(b'{"input":"different"}\n')
            with self.assertRaises(Stop): verify_frozen(root,original,freeze)
    def test_success_bytes_preserved_and_no_second_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); state=self.state(); t=FakeTransport(); events=[]
            dispatch_slot(root/'run',root/'control',state['slots'][0],state,t,{},SETTINGS,PRICING,lambda:events.append('persist'),lambda:events.append('backup'))
            folder=root/'run/slots'/ALLOWED[0]
            self.assertEqual((folder/'response.body.raw').read_bytes(),(ROOT/'controls/collection-adapter/success.body').read_bytes())
            self.assertEqual(t.sends,1); self.assertEqual(state['generation_requests_attempted'],1)
            # Even a fabricated fresh in-memory state cannot bypass the persistent claim.
            fresh=self.state()
            with self.assertRaises(Stop): dispatch_slot(root/'other',root/'control',fresh['slots'][0],fresh,t,{},SETTINGS,PRICING,lambda:None,lambda:None)
            self.assertEqual(t.sends,1)
    def test_ctrl_c_marks_unknown_and_forbids_resend(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); state=self.state(); t=FakeTransport(interrupt=True)
            with self.assertRaises(KeyboardInterrupt): dispatch_slot(root/'run',root/'control',state['slots'][0],state,t,{},SETTINGS,PRICING,lambda:None,lambda:None)
            mark_uncertain(state); self.assertEqual(state['unknown_cost_slots'],[ALLOWED[0]])
            self.assertEqual(state['slots'][1]['status'],'not_attempted')
            with self.assertRaises(Stop): dispatch_slot(root/'run',root/'control',state['slots'][0],state,t,{},SETTINGS,PRICING,lambda:None,lambda:None)
            self.assertEqual(t.sends,1)
    def test_uncertain_response_halts_and_preserves_text(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); state=self.state(); t=FakeTransport(uncertain=True)
            with self.assertRaises(Stop):
                for slot in state['slots']:
                    dispatch_slot(root/'run',root/'control',slot,state,t,{},SETTINGS,PRICING,lambda:None,lambda:None)
            self.assertEqual(t.sends,1)
            self.assertTrue((root/'run/slots'/ALLOWED[0]/'candidate.txt').exists())
    def test_backup_failure_prevents_send(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); state=self.state(); t=FakeTransport()
            def failed(): raise OSError('labelled fixture backup failure')
            with self.assertRaises(OSError): dispatch_slot(root/'run',root/'control',state['slots'][0],state,t,{},SETTINGS,PRICING,lambda:None,failed)
            self.assertEqual(t.sends,0); self.assertTrue((root/'control/attempts'/f'{ALLOWED[0]}.json').exists())
    def test_ineligible_dispatch_never_calls_transport(self):
        with tempfile.TemporaryDirectory() as d:
            state=self.state(); t=FakeTransport(); slot={'slot_id':'R03-G02','status':'not_attempted'}
            with self.assertRaises(Stop): dispatch_slot(Path(d),Path(d)/'control',slot,state,t,{},SETTINGS,PRICING,lambda:None,lambda:None)
            self.assertEqual(t.sends,0)

if __name__=='__main__': unittest.main()
