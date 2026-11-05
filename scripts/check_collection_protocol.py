#!/usr/bin/env python3
"""Offline draft protocol integrity checks. No API/network/credential access."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    m=json.loads((ROOT/'collection/protocol-manifest.json').read_text())
    settings=json.loads((ROOT/'collection/settings.pending.json').read_text())
    slots=json.loads((ROOT/'collection/slots.json').read_text())['slots']
    assert m['frozen'] is False and settings['frozen'] is False
    assert m['collection_authorized'] is False and settings['collection_authorized'] is False
    assert all(v is None for v in settings['pending_selection'].values())
    current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for section in ('baseline_additional_sha256','draft_artifact_sha256'):
        for relative,h in m[section].items(): assert sha(ROOT/relative)==h,relative
    baseline=m['validated_baseline']
    for relative,h in baseline['input_sha256'].items(): assert sha(ROOT/relative)==h,relative
    assert sha(ROOT/baseline['record']/'summary.json')==baseline['summary_sha256']
    common=(ROOT/'collection/COMMON_OUTPUT_CONTRACT.txt').read_text()
    # Disclosed field/support names reflect the unchanged inspector source policy.
    for value in ('groups','name','interval','rules','labels','alert','expr','for','keep_firing_for','annotations','200,000','20,000','60','__name__','_over_time','histogram_'):
        assert value in common,value
    for value in ('abs','ceil','floor','round','clamp','clamp_min','clamp_max','exp','ln','log2','log10','sqrt','sgn','scalar','vector','label_replace','label_join','sort','sort_desc','rate','irate','increase','delta','idelta','deriv','predict_linear','double_exponential_smoothing','holt_winters','changes','resets','timestamp','time','absent','absent_over_time'):
        assert re.search(r'\b'+value+r'\b',common),value
    report=(ROOT/'COLLECTION_READINESS.md').read_text()
    forbidden=('input_series','exp_alerts','exp_labels','rule_files','Review-only scenarios','service="api"','service="web"','instance="a"','instance="b"','targeted_obligations')
    for task,entry in m['prompts'].items():
        p=ROOT/entry['path']; raw=p.read_bytes(); text=raw.decode('utf-8')
        assert sha(p)==entry['sha256'] and len(raw)==entry['bytes'],task
        assert text.endswith(common),task
        assert all(value not in text for value in forbidden),task
        assert not re.search(r'\b\d+m\b|t\+[123]m',text),task
        assert f'```text\n{text}```' in report,task+' exact readiness copy missing'
        if task=='R01':
            expression=next(line.split('expr:',1)[1].strip() for line in (ROOT/'rules/reference.yml').read_text().splitlines() if line.strip().startswith('expr:'))
        else:
            reference=json.loads((ROOT/f'rules/stage2/{task}/reference.yml').read_text())
            expression=reference['groups'][0]['rules'][0]['expr']
        assert expression not in text,task+' reference expression leaked'
    expected=[(r,t) for r in range(1,4) for t in m['prompts']]
    assert len(slots)==18 and len({s['slot_id'] for s in slots})==18
    for i,(slot,(r,t)) in enumerate(zip(slots,expected),1):
        assert (slot['order'],slot['round'],slot['task'],slot['slot_id'])==(i,r,t,f'{t}-G{r:02d}')
        assert slot['status']=='not_attempted' and slot['provider_request_id'] is None and slot['response_id'] is None
        assert slot['prompt_sha256']==m['prompts'][t]['sha256']
    print(json.dumps({'status':'draft_not_frozen','prompts_verified':6,'slots_verified':18,'validated_input_hashes_verified':len(baseline['input_sha256']),'model_api_calls':0,'recorded_baseline_commit':m['current_commit'],'current_commit':current_head,'snapshot_commit_matches_current_head':current_head==m['current_commit'],'success':True},indent=2))
if __name__=='__main__': main()
