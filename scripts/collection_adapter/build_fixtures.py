"""Create labelled offline transport fixtures; no network or model output sampling."""
import copy
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'controls/collection-adapter'

def main():
    text=(ROOT/'rules/reference.yml').read_text()
    base={'object':'response','id':'fixture-response','model':'gpt-6.1-sol','status':'completed',
          'service_tier':'default','max_output_tokens':8192,'store':False,
          'reasoning':{'effort':'medium','mode':'standard'},'tools':[],
          'output':[{'type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':text}]}],
          'usage':{'input_tokens':1200,'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':0},'output_tokens':100,'output_tokens_details':{'reasoning_tokens':40},'total_tokens':1300}}
    controls=[]
    def add(name,payload,expected,code=200,error=None):
        raw=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(payload,bytes) else payload
        target=DEST/(name+'.body'); target.write_bytes(raw)
        controls.append({'id':name,'kind':'synthetic_transport_fixture','body':str(target.relative_to(ROOT)),'http_status':code,'transport_error':error,'expected':expected})
    add('success',base,{'text_status':'available','halt':False,'cost':'0.0034'})
    d=copy.deepcopy(base); d['output'][0]['content']=[{'type':'refusal','refusal':'Synthetic refusal fixture.'}]
    add('refusal',d,{'text_status':'refusal_without_text','halt':False,'cost':'0.0034'})
    d=copy.deepcopy(base); d['status']='incomplete'; d['incomplete_details']={'reason':'max_output_tokens'}; d['output'][0]['content'][0]['text']='groups:\n - name:'
    d['usage'].update(output_tokens=8192,total_tokens=9392); d['usage']['output_tokens_details']['reasoning_tokens']=8000
    add('truncation',d,{'text_status':'available','halt':False,'cost':'0.08432'})
    d=copy.deepcopy(base); d['output'][0]['content'][0]['text']=''
    add('empty_text',d,{'text_status':'empty_text','halt':False,'cost':'0.0034'})
    d=copy.deepcopy(base); d['output']=[]
    add('missing_text',d,{'text_status':'missing_text','halt':False,'cost':'0.0034'})
    d=copy.deepcopy(base); d['output'][0]['content'][0].pop('text')
    add('absent_text_field',d,{'text_status':'missing_or_nontext_text_field','halt':False,'cost':'0.0034'})
    d=copy.deepcopy(base); d['output'][0]['content']=[{'type':'output_text','text':'\ufeffα\r\n  "{x}"\\'}, {'type':'output_text','text':'\nfinal\n'}]
    add('unicode_multiblock',d,{'text_status':'available','halt':False,'cost':'0.0034','exact_text':'\ufeffα\r\n  "{x}"\\\nfinal\n'})
    d=copy.deepcopy(base); d['output'].insert(0,{'type':'reasoning','summary':[{'type':'summary_text','text':'Do not extract this fixture summary.'}]})
    add('reasoning_item_first',d,{'text_status':'available','halt':False,'cost':'0.0034','exact_text':text})
    d=copy.deepcopy(base); d['output'].append(copy.deepcopy(d['output'][0]))
    add('ambiguous_messages',d,{'text_status':'ambiguous_multiple_messages','halt':False,'cost':'0.0034'})
    d=copy.deepcopy(base); d['model']='fixture-wrong-model'
    add('model_mismatch',d,{'text_status':'available','halt':True,'cost':'0.0034'})
    d=copy.deepcopy(base); d['service_tier']='priority'
    add('tier_mismatch',d,{'text_status':'available','halt':True,'cost':'0.0034'})
    d=copy.deepcopy(base); d['usage']=None
    add('missing_usage',d,{'text_status':'available','halt':True,'cost':None})
    d=copy.deepcopy(base); del d['usage']['input_tokens_details']['cache_write_tokens']
    add('unknown_cache_usage',d,{'text_status':'available','halt':True,'cost':None})
    d=copy.deepcopy(base); d['usage']['input_tokens']=6001; d['usage']['total_tokens']=6101
    add('over_input_allowance',d,{'text_status':'available','halt':True,'cost':None})
    d=copy.deepcopy(base); d['output'][0]['content'][0]['text']='```yaml\n'+text+'```\n'
    add('markdown_unchanged',d,{'text_status':'available','halt':False,'cost':'0.0034','exact_text':d['output'][0]['content'][0]['text']})
    add('duplicate_success',base,{'text_status':'available','halt':False,'cost':'0.0034','exact_text':text})
    for name,code in [('authentication_error',401),('rate_limit',429),('server_error',500)]:
        add(name,{'error':{'type':'synthetic_fixture_error','message':'Synthetic error; not a real API response.'}}, {'text_status':None,'halt':True,'cost':None},code=code)
    add('uncertain_partial',b'{"object":"response",',{'text_status':None,'halt':True,'cost':None},error='TimeoutError')
    add('uncertain_complete_body',base,{'text_status':'available','halt':True,'cost':'0.0034'},error='IncompleteRead')
    add('invalid_json',b'{not json}',{'text_status':None,'halt':True,'cost':None})
    add('duplicate_json_keys',b'{"output":[],"output":[]}',{'text_status':None,'halt':True,'cost':None})
    (DEST/'manifest.json').write_text(json.dumps({'notice':'OFFLINE SYNTHETIC TRANSPORT FIXTURES. Not API calls, provider measurements, or experimental outputs. Synthetic usage values test accounting only.','controls':controls},indent=2)+'\n')
    print('Created',len(controls),'labelled synthetic fixtures')
if __name__=='__main__': main()
