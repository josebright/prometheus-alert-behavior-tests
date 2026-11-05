#!/usr/bin/env python3
"""Offline audit of an interrupted pilot; never dispatch or resume requests.

Run only after confirming the collector has stopped. Originals are copied, hashed,
and left untouched. The audit's summary is derived evidence, not a new pilot.
"""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import sys
from collection_adapter.core import save_json, save_new, sha, now
from collection_adapter.workflow import ROOT, atomic_json, command, inventory, mirror

def hashes(path):
    return {str(p.relative_to(path)):sha(p.read_bytes()) for p in sorted(path.rglob('*')) if p.is_file()}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original',type=Path)
    parser.add_argument('--blocked-run',type=Path,required=True)
    args=parser.parse_args()
    original=args.original.resolve(); blocked=args.blocked_run.resolve()
    if original.parent!=ROOT/'results/collection' or blocked.parent!=original.parent:
        raise SystemExit('Expected existing collection records')
    before=hashes(original); blocked_before=hashes(blocked)
    summary=json.loads((original/'summary.json').read_text())
    if summary['status']!='collecting' or not summary['frozen'] or summary.get('finished_utc'):
        raise SystemExit('Expected an interrupted collecting record without finalization')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-audit'
    run=ROOT/'results/collection'/stamp
    shutil.copytree(original,run)
    shutil.copytree(blocked,run/'related-blocked-run')
    backup=ROOT/'.collection-backups'/stamp
    summary.update(status='halted_uncertain_completion',run_directory=str(run),backup_directory=str(backup),
                   derived_audit=True,original_run_directory=str(original),
                   unknown_cost_slots=[],errors=['User reported Ctrl+C followed by a second invocation. '
                   'The original process was confirmed absent; an attempted request has no saved response. '
                   'No request is resent. The second invocation was blocked by the original dispatch lock.'])
    for slot in summary['slots']:
        folder=run/'slots'/slot['slot_id']
        if slot['status']=='attempted_before_dispatch':
            if (folder/'response.json').exists():
                raise SystemExit('Saved response requires separate review; do not infer uncertainty blindly')
            slot['status']='completion_unknown_after_interruption'
            summary['unknown_cost_slots'].append(slot['slot_id'])
        if slot['status']=='not_attempted': slot['not_attempted_reason']='halted_uncertain_completion'
        candidate=folder/'candidate.txt'
        if not candidate.exists(): continue
        code,_,_=command(run,'audit-score-'+slot['slot_id'],[
            sys.executable,str(run/'inputs/scripts/score_candidate.py'),slot['task'],str(candidate),
            '--output-parent',str(run/'scoring'/slot['slot_id'])])
        records=list((run/'scoring'/slot['slot_id']).glob('*/summary.json'))
        slot['score']={'exit_code':code,'record':str(records[0].relative_to(run)) if len(records)==1 else None,
                       'outcomes':json.loads(records[0].read_text())['outcomes'] if len(records)==1 else None}
    summary['finished_utc']=now()
    atomic_json(run/'summary.json',summary)
    save_json(run/'audit.json',{'kind':'offline_interruption_audit','original_run':str(original),
        'blocked_run':str(blocked),'new_api_requests':0,'new_generations':0,
        'reason':'User confirmed Ctrl+C, then rerun; process inspection found no active collector.',
        'original_file_sha256':before,'blocked_run_file_sha256':blocked_before,
        'command':[sys.executable,*sys.argv],'created_utc':now(),
        'freeze_note':'Copied original freeze describes original collection code; later guard fix does not change it.'})
    for relative in ['scripts/audit_interrupted_collection.py','scripts/run_collection.py','tests/test_collection_adapter.py']:
        save_new(run/'audit-support'/relative,(ROOT/relative).read_bytes())
    if hashes(original)!=before or hashes(blocked)!=blocked_before:
        raise SystemExit('Original record changed during audit; do not treat audit as final')
    inventory(run); mirror(run,backup)
    print(json.dumps({'audit_directory':str(run),'originals_unchanged':True,
        'attempted_generations_in_original':summary['generation_requests_attempted'],
        'unknown_cost_slots':summary['unknown_cost_slots'],'new_api_requests':0,'backup_verified':True},indent=2))

if __name__=='__main__': main()
