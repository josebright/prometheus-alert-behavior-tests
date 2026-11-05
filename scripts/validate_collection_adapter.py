#!/usr/bin/env python3
"""Validate synthetic transport fixtures offline; optionally include real pinned scorer."""
import argparse
import datetime
import json
from pathlib import Path
import sys
from collection_adapter.core import encode, inspect_response, request_body, save_json, save_new, sha
from collection_adapter.workflow import ROOT, command, snapshot, inventory

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--with-scorer',action='store_true'); args=parser.parse_args()
    run=ROOT/'results/collection-adapter'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'); run.mkdir(parents=True)
    hashes=snapshot(run)
    result={'kind':'offline_synthetic_transport_validation','input_sha256':hashes,'controls':{},'network_calls':0,'model_generations':0}
    code,_,_=command(run,'unit-tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_collection_adapter.py','-v'])
    result['unit_tests_exit']=code
    settings=json.loads((ROOT/'collection/settings.selected.json').read_text()); pricing=json.loads((ROOT/'collection/api-review.json').read_text())
    controls=json.loads((ROOT/'controls/collection-adapter/manifest.json').read_text())['controls']
    for c in controls:
        folder=run/'fixtures'/c['id']; raw=(ROOT/c['body']).read_bytes()
        save_new(folder/'response.body.raw',raw)
        meta={'http_status':c['http_status'],'completion_uncertain':c['transport_error'] is not None}
        observed=inspect_response(meta,raw,settings,pricing); expected=c['expected']
        actual={'text_status':(observed['extraction'] or {}).get('status'),'halt':bool(observed['halt_reasons']),'cost':(observed['accounting'] or {}).get('estimated_api_cost_usd')}
        if 'exact_text' in expected: actual['exact_text']=(observed['extraction'] or {}).get('text')
        mismatches={k:{'expected':v,'actual':actual.get(k)} for k,v in expected.items() if actual.get(k)!=v}
        extracted=observed.get('extraction') or {}
        if extracted.get('text_available'):
            data=extracted['text'].encode('utf-8'); save_new(folder/'candidate.txt',data)
            observed['candidate_sha256']=sha(data)
        save_json(folder/'observed.json',observed)
        result['controls'][c['id']]={'expected_outcome':not mismatches,'mismatches':mismatches,'body_sha256':sha(raw),'actual':actual}
    result['scorer_integration']='not_run'
    if args.with_scorer:
        # Valid reference text extracted from a synthetic payload, never a model answer.
        candidate=run/'fixtures/success/candidate.txt'
        code,out,err=command(run,'frozen-scorer',[sys.executable,str(ROOT/'scripts/score_candidate.py'),'R01',str(candidate),'--output-parent',str(run/'scoring')])
        result['scorer_integration']='pass' if code==0 else 'fail'
        result['scorer_exit']=code
    result['success']=code==0 and result['unit_tests_exit']==0 and all(c['expected_outcome'] for c in result['controls'].values()) and result['scorer_integration']!='fail'
    save_json(run/'summary.json',result); inventory(run)
    print(json.dumps({'run_directory':str(run),'controls':len(controls),'success':result['success'],'scorer_integration':result['scorer_integration']},indent=2))
    return 0 if result['success'] else 2
if __name__=='__main__': sys.exit(main())
