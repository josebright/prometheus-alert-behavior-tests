"""Offline-testable transport, lossless extraction, usage and dispatch recording."""
import copy
import datetime
from decimal import Decimal
import hashlib
import http.client
import json
import os
from pathlib import Path
import ssl
import time
import uuid

MODEL='gpt-6.1-sol'
ALLOWED_PATHS={'/v1/models/'+MODEL, '/v1/responses/input_tokens', '/v1/responses'}
SAFE_RESPONSE_HEADERS={'x-request-id','content-type','date','openai-version','openai-processing-ms'}

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def encode(obj): return (json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def save_new(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    path.chmod(0o444)
def save_json(path,obj): save_new(path,encode(obj))
def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def invalid_constant(value): raise ValueError('nonstandard JSON constant')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid_constant)

class Transport:
    """One HTTPS send. No SDK, retries, redirects, proxies or env-derived URL."""
    def __init__(self,key,timeout=180,connection_factory=None):
        if not key or '\n' in key or '\r' in key: raise ValueError('Missing or malformed environment credential')
        self._key=key; self.timeout=timeout
        self.factory=connection_factory or (lambda: http.client.HTTPSConnection('api.openai.com',timeout=timeout,context=ssl.create_default_context()))
    def exchange(self,method,path,body,correlation):
        if path not in ALLOWED_PATHS: raise ValueError('Endpoint is not allowlisted')
        if (path.startswith('/v1/models/') and method!='GET') or (not path.startswith('/v1/models/') and method!='POST'):
            raise ValueError('HTTP method is not allowlisted')
        start=now(); tick=time.monotonic(); chunks=[]; status=None; headers={}; connection=None; error=None
        try:
            connection=self.factory()
            connection.request(method,path,body=body if method=='POST' else None,headers={
                'Authorization':'Bearer '+self._key,'Content-Type':'application/json',
                'Accept':'application/json','Accept-Encoding':'identity','X-Client-Request-Id':correlation})
            response=connection.getresponse(); status=response.status
            headers={k.lower():v for k,v in response.getheaders() if k.lower() in SAFE_RESPONSE_HEADERS}
            while True:
                if time.monotonic()-tick > self.timeout: raise TimeoutError()
                chunk=response.read(65536)
                if not chunk: break
                chunks.append(chunk)
        except http.client.IncompleteRead as e:
            chunks.append(e.partial); error=type(e).__name__
        except Exception as e:
            # Never log exception messages, request objects or auth-bearing headers.
            error=type(e).__name__
        finally:
            if connection is not None: connection.close()
        raw=b''.join(chunks)
        return {'http_status':status,'headers':headers,'body':raw,'error_type':error,
                'completion_uncertain':error is not None,'started_utc':start,'finished_utc':now(),
                'elapsed_seconds':time.monotonic()-tick}
    def contains_credential(self,body): return self._key.encode() in body

def request_body(prompt,settings):
    # String decoding only, no whitespace or newline normalization.
    text=prompt.decode('utf-8'); assert text.encode('utf-8')==prompt
    obj=copy.deepcopy(settings['request_fields'])
    obj['input']=[{'role':'user','content':[{'type':'input_text','text':text}]}]
    return obj

def count_body(request):
    # Documented count-endpoint fields affecting model input, including reasoning/text.
    return {k:copy.deepcopy(v) for k,v in request.items() if k in {'model','input','reasoning','text','tools','tool_choice','truncation','parallel_tool_calls'}}

def recorded_exchange(directory,transport,method,path,body,kind,backup):
    """Durably record attempt before dispatch; existing directories cannot resend."""
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=False)
    raw=encode(body) if body is not None else b''
    save_new(directory/'request.body.json',raw)
    correlation=str(uuid.uuid4())
    event={'kind':kind,'method':method,'origin':'https://api.openai.com','path':path,
           'client_request_id':correlation,'attempt_recorded_utc':now(),'request_sha256':sha(raw),
           'request_bytes':len(raw),'automatic_retries':0,'dispatch_status':'attempted_before_dispatch'}
    save_json(directory/'attempt.json',event)
    # A backup failure here stops before the send. No automatic resend on rerun.
    backup()
    result=transport.exchange(method,path,raw,correlation)
    payload=result.pop('body')
    result.update(response_body_sha256=sha(payload),response_body_bytes=len(payload),client_request_id=correlation)
    if transport.contains_credential(payload):
        # Secret exclusion outranks retaining a credential-echoing error verbatim.
        result.update(credential_echo_withheld=True,completion_uncertain=True,error_type='CredentialEcho')
        save_json(directory/'response.json',result); backup()
        return result,None
    save_new(directory/'response.body.raw',payload)
    save_json(directory/'response.json',result); backup()
    return result,payload

def extract(payload):
    """One assistant message; concatenate its visible text blocks without separators."""
    result={'text_available':False,'refusal':False,'text':None,'blocks':[], 'status':'missing_text'}
    if not isinstance(payload,dict) or not isinstance(payload.get('output'),list):
        result['status']='unrecognized_response_schema'; return result
    messages=[]
    for i,item in enumerate(payload['output']):
        if not isinstance(item,dict): result['status']='unrecognized_output_item'; return result
        if item.get('type')=='reasoning': continue
        if item.get('type')!='message' or item.get('role')!='assistant':
            result['status']='unexpected_output_item'; return result
        messages.append((i,item))
    if len(messages)>1: result['status']='ambiguous_multiple_messages'; return result
    if not messages: return result
    index,message=messages[0]; content=message.get('content')
    if not isinstance(content,list): result['status']='unrecognized_message_content'; return result
    texts=[]
    for j,block in enumerate(content):
        if not isinstance(block,dict): result['status']='unrecognized_content_block'; return result
        if block.get('type')=='refusal':
            result['refusal']=True
            result['blocks'].append({'path':f'output[{index}].content[{j}].refusal','kind':'refusal','value':block.get('refusal')})
        elif block.get('type')=='output_text':
            value=block.get('text')
            if not isinstance(value,str): result['status']='missing_or_nontext_text_field'; return result
            try: value.encode('utf-8')
            except UnicodeEncodeError: result['status']='invalid_unicode_text'; return result
            texts.append(value)
            result['blocks'].append({'path':f'output[{index}].content[{j}].text','kind':'output_text','value':value})
        else: result['status']='unrecognized_content_block'; return result
    if texts:
        result.update(text_available=True,text=''.join(texts),status='empty_text' if ''.join(texts)=='' else 'available')
    elif result['refusal']: result['status']='refusal_without_text'
    return result

def usage_cost(payload,settings,pricing):
    usage=payload.get('usage')
    out={'usage':usage,'estimated_api_cost_usd':None,'billing_amount_usd':None,'errors':[]}
    if not isinstance(usage,dict): out['errors']=['missing_usage']; return out
    def integer(value): return type(value) is int and value>=0
    names=['input_tokens','output_tokens','total_tokens']
    if not all(integer(usage.get(k)) for k in names): out['errors']=['invalid_usage_totals']; return out
    inp,output,total=(usage[k] for k in names)
    if inp+output!=total: out['errors'].append('inconsistent_usage_totals')
    if inp>settings['max_input_tokens_including_overhead']: out['errors'].append('input_allowance_exceeded')
    if output>settings['request_fields']['max_output_tokens']: out['errors'].append('output_cap_exceeded')
    detail=usage.get('input_tokens_details')
    if not isinstance(detail,dict): out['errors'].append('missing_cache_usage_details'); return out
    cached=detail.get('cached_tokens'); writes=detail.get('cache_write_tokens')
    if not integer(cached) or not integer(writes): out['errors'].append('unknown_cache_usage'); return out
    if cached or writes: out['errors'].append('unexpected_cache_usage')
    reasoning=usage.get('output_tokens_details',{}).get('reasoning_tokens') if isinstance(usage.get('output_tokens_details',{}),dict) else None
    if reasoning is not None and (not integer(reasoning) or reasoning>output): out['errors'].append('invalid_reasoning_usage')
    # Reasoning is already inside output_tokens: never charge it a second time.
    if not out['errors']:
        rates=pricing['rates_per_million']
        out['estimated_api_cost_usd']=str((Decimal(inp)*Decimal(rates['uncached_input'])+Decimal(output)*Decimal(rates['output_including_reasoning']))/Decimal(1000000))
    return out

def inspect_response(meta,raw,settings,pricing):
    result={'http_status':meta['http_status'],'halt_reasons':[],'completion_status':None,
            'extraction':None,'accounting':None,'response_id':None,'returned_model':None}
    if meta['completion_uncertain']:
        result['halt_reasons'].append('uncertain_completion')
    if raw is None:
        if not result['halt_reasons']: result['halt_reasons'].append('response_body_unavailable')
        return result
    if meta['http_status']!=200:
        result['halt_reasons'].append('http_or_provider_error'); return result
    try: payload=strict_json(raw)
    except (ValueError,UnicodeError):
        result['halt_reasons'].append('unparseable_response_body'); return result
    if not isinstance(payload,dict): result['halt_reasons'].append('unrecognized_response_schema'); return result
    result.update(completion_status=payload.get('status'),response_id=payload.get('id'),returned_model=payload.get('model'),
                  created_at=payload.get('created_at'),incomplete_details=payload.get('incomplete_details'),provider_error=payload.get('error'))
    if payload.get('object')!='response' or not isinstance(payload.get('id'),str): result['halt_reasons'].append('unrecognized_response_schema')
    if payload.get('model')!=settings['model']: result['halt_reasons'].append('model_mismatch')
    if payload.get('service_tier')!='default': result['halt_reasons'].append('service_tier_mismatch')
    if payload.get('status') not in {'completed','incomplete'}: result['halt_reasons'].append('nonterminal_or_failed_response')
    if payload.get('error') is not None: result['halt_reasons'].append('provider_error')
    for field,wanted in [('max_output_tokens',8192),('store',False)]:
        if field in payload and payload[field]!=wanted: result['halt_reasons'].append('request_setting_mismatch:'+field)
    reasoning=payload.get('reasoning')
    if not isinstance(reasoning,dict) or reasoning.get('effort')!='medium' or reasoning.get('mode','standard')!='standard': result['halt_reasons'].append('reasoning_setting_mismatch')
    if payload.get('tools',[]) or payload.get('previous_response_id') is not None or payload.get('conversation') is not None:
        result['halt_reasons'].append('unexpected_tools_or_history')
    result['extraction']=extract(payload)
    if result['extraction']['status'] in {'unrecognized_response_schema','unrecognized_output_item','unexpected_output_item','unrecognized_message_content','unrecognized_content_block','invalid_unicode_text'}:
        result['halt_reasons'].append('extraction_limitation')
    result['accounting']=usage_cost(payload,settings,pricing)
    result['halt_reasons'].extend(result['accounting']['errors'])
    return result

def budget_bound(settings,pricing,slots=18):
    rates=pricing['rates_per_million']
    per=(Decimal(settings['max_input_tokens_including_overhead'])*Decimal(rates['uncached_input'])+Decimal(settings['request_fields']['max_output_tokens'])*Decimal(rates['output_including_reasoning']))/Decimal(1000000)
    return per,per*slots
