#!/usr/bin/env python3
"""Run predeclared infrastructure controls, not experimental model candidates."""
import datetime
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from score_candidate import ROOT, sources, write

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=int,choices=(1,2,3),default=1)
    args=parser.parse_args(); command_lock=threading.Lock()
    run=ROOT/'results/stage3a'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run.mkdir(parents=True); summary={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'notice':'Infrastructure controls only; no model API calls.','controls':{},'commands':[],'invocation':[sys.executable,*sys.argv],'jobs':args.jobs}
    snapshot=run/'inputs'
    files=sources()+list((ROOT/'controls/stage3a').glob('*'))+[ROOT/'scripts/validate_stage3a.py',ROOT/'tests/test_stage3a.py']
    for path in files:
        dest=snapshot/path.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,dest)
    summary['input_sha256']={str(p.relative_to(ROOT)):sha(p) for p in files}
    manifest=json.loads((snapshot/'controls/stage3a/manifest.json').read_text())
    def execute(name,args):
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        p=subprocess.run(args,cwd=ROOT,capture_output=True)
        (run/(name+'.stdout')).write_bytes(p.stdout); (run/(name+'.stderr')).write_bytes(p.stderr)
        with command_lock:
            summary['commands'].append(dict(name=name,argv=args,start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=p.returncode))
        return p
    unit=execute('unit-tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_stage3a.py','-v'])
    summary['unit_tests_pass']=unit.returncode==0
    print('Run directory:',run,flush=True)
    def check_control(control):
        cid=control['id']; parent=run/'candidates'/cid
        p=execute(cid,[sys.executable,str(ROOT/'scripts/score_candidate.py'),control['task'],str(snapshot/control['path']),'--output-parent',str(parent)])
        records=list(parent.glob('*/summary.json'))
        if len(records)!=1:
            outcome={'expected_outcome':False,'error':'Missing/ambiguous scorer record','exit_code':p.returncode}
        else:
            result=json.loads(records[0].read_text()); actual={**result,**result['outcomes']}
            actual['only_symptoms']=sorted(result.get('analysis',{}).get('observed_symptom_counts',{}))
            discrepancies={k:{'expected':v,'actual':actual.get(k)} for k,v in control['expected'].items() if actual.get(k)!=v}
            if result['exit_code']!=p.returncode: discrepancies['process_exit']='Mismatch between summary and actual subprocess exit'
            outcome={'expected_outcome':not discrepancies,'discrepancies':discrepancies,'record':str(records[0].parent.relative_to(run)),'exit_code':p.returncode,'outcomes':result['outcomes'],'behavior_execution':result.get('behavior_execution'),'analysis':result.get('analysis'),'errors':result['errors'],'limitations':result['limitations']}
        return cid,outcome
    if unit.returncode==0:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures=[pool.submit(check_control,c) for c in manifest['controls']]
            for future in as_completed(futures):
                cid,outcome=future.result(); summary['controls'][cid]=outcome
                print(cid+': '+('expected' if outcome['expected_outcome'] else 'UNEXPECTED'),flush=True)
                write(run/'summary.json',summary)
    summary['sources_unchanged']=all(sha(ROOT/p)==h for p,h in summary['input_sha256'].items())
    summary['success']=summary['unit_tests_pass'] and summary['sources_unchanged'] and len(summary['controls'])==len(manifest['controls']) and all(c['expected_outcome'] for c in summary['controls'].values())
    summary['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat(); summary['exit_code']=0 if summary['success'] else 2
    write(run/'summary.json',summary)
    write(run/'file-hashes.json',{str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()})
    print('Success:',summary['success'],flush=True)
    return summary['exit_code']
if __name__=='__main__': sys.exit(main())
