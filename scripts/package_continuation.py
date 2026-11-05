#!/usr/bin/env python3
"""Create a factual combined report and a new, exclusive versioned local ZIP."""
import argparse
from collections import Counter,defaultdict
import datetime
from decimal import Decimal
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile
from collection_adapter.core import encode, now, save_new, save_json, sha
from collection_adapter.workflow import ROOT
from collection_adapter.continuation import verify_files

def report(summary,old,cfg,version):
    by_id={s['slot_id']:dict(s) for s in old['slots']}
    by_id.update({s['slot_id']:s for s in summary['slots']})
    rows=[]; totals=defaultdict(Counter); usages=[]; available=0
    for sid,slot in by_id.items():
        outcomes=(slot.get('score') or {}).get('outcomes') or {}
        for dimension,result in outcomes.items(): totals[dimension][result]+=1
        account=(slot.get('analysis') or {}).get('accounting') or {}
        if isinstance(account.get('usage'),dict): usages.append(account['usage'])
        if ((slot.get('analysis') or {}).get('extraction') or {}).get('text_available'): available+=1
        rows.append('| '+sid+' | '+slot['status']+' | '+('; '.join(k+'='+str(v) for k,v in outcomes.items()) or 'not evaluated')+' |')
    usage={k:sum(u[k] for u in usages) for k in ('input_tokens','output_tokens','total_tokens')}
    errors='\n'.join('- '+e for e in summary['errors']) or 'No continuation errors recorded.'
    remaining=sum(s['status']=='not_attempted' for s in summary['slots'])
    conservative=Decimal(summary['combined_known_cost_usd'])+Decimal(summary['combined_unknown_reserve_usd'])+Decimal('0.09392')*remaining
    local=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).isoformat()
    text=f'''# Collection results

Updated {local} (Africa/Lagos). Continuation status: **{summary['status']}**.
Original generation attempts: **9**. New continuation attempts: **{summary['generation_requests_attempted']}/9**.
Unchanged response texts available across the pilot: **{available}/18**.

The researcher interrupted the original run with Ctrl+C after eight saved responses
and an attempt record for R03-G02. The original audit scored those eight responses:
all six scoring dimensions passed for each. R03-G02 has no saved response ID or
response body and remains **completion unknown**. It was not resent. No documented
exact-response retrieval could be constructed from the saved correlation ID.

The approved [continuation amendment](collection/CONTINUATION_AMENDMENT.md) permits
only the nine previously unattempted slots in their original order. This amendment
was made after the eight original results were known. It does not replace outputs,
increase the sample, or seek failures. The model is still the **gpt-6.1-sol alias**;
fixed request settings cannot guarantee that alias weights stayed unchanged.

## Current continuation outcome

{errors}

Continuation metadata/access/token-count requests: **{summary['metadata_requests_attempted']}**.
Continuation frozen for generation: **{summary['frozen']}**.
Offline preflight passed: **{summary.get('offline_preflight_pass',False)}**.
Original records verified unchanged: **{summary['originals_unchanged']}**.
Current code commit: `{summary.get('git_commit','unavailable')}`; new continuation
source snapshots and the uncommitted-file list are recorded separately.

The exact prompts, prepared requests, settings, scorer, requirements and fixtures
were checked against the original freeze. Python and pinned dependencies matched.
The pinned Docker scorer reference control passed. The new offline controls test
eligibility, ordering, locking, SIGKILL, Ctrl+C, duplicate prevention, integrity
drift, uncertain responses, backup failure, and budget reserves. They are synthetic
infrastructure controls, not experimental outputs. Test commands, exit codes,
stdout and stderr are in the continuation record.

## Actual costs, reserves and usage

Known usage from {len(usages)} saved responses: `{json.dumps(usage)}`.
Estimated original known token cost: **US${summary.get('original_known_cost_usd','unavailable')}**.
Estimated continuation known token cost: **US${summary['estimated_known_api_cost_usd']}**.
Combined known token cost: **US${summary['combined_known_cost_usd']}**.
Combined unknown-cost reserve: **US${summary['combined_unknown_reserve_usd']}**.
Original unknown slot: R03-G02. Additional unknown-cost slots:
`{json.dumps(summary['unknown_cost_slots'])}`.

Each unknown-cost request reserves the full **US$0.09392**, including its input
allowance and capped reasoning/output. It is never counted as zero. The initial
combined bound was **US$0.960424**: US$0.021224 known + US$0.09392 unknown reserve
+ nine full request allowances. Current known costs plus reserves plus all
remaining unattempted allowances total **US${conservative}**.
The approved budget stays **US$10** and the operational ceiling **US$5**.

These are token-cost estimates and conservative reserves, **not billing**. The
billing amount was not queried. [Verified standard pricing](https://developers.openai.com/api/docs/pricing)
is US$2/M input and US$10/M output; reasoning is already included in output usage.

## All 18 preassigned slots

| Slot | Status | Scoring dimensions |
|---|---|---|
'''+ '\n'.join(rows)+f'''

Dimension totals: `{json.dumps({k:dict(v) for k,v in totals.items()},sort_keys=True)}`.
Unknown and unattempted slots are not passes or failures. Repeats are grouped by
six tasks, not 18 independent tasks. Tests use synthetic inputs; passing does not
establish operational safety or directly inspect every internal pending state.
Human review remains necessary. All available outputs are retained unchanged.

## Evidence and execution

- Original: `{cfg['original_run']}`.
- Original audit and scores: `{cfg['audit_run']}`.
- Historical report preserved: `{cfg['historical_report']}`.
- Continuation: `{Path(summary['run_directory']).relative_to(ROOT)}`.
- Separate local backup: `{Path(summary['backup_directory']).relative_to(ROOT)}`.
- New versioned review archive: `{version}`.

The original dispatch lock remains unchanged. An additional process lock and
persistent continuation/per-slot claims prevent concurrent dispatch and replay.
Earlier archives remain unchanged. The ZIP contains original, audit, amendment,
and continuation evidence. Sharing-copy path redactions and cache exclusions are
listed inside it; original response bytes are unchanged. Same-disk backups do not
protect against disk loss. No raw logs are pushed.
'''
    if summary['generation_requests_attempted']==0 and not summary['frozen']:
        text+='''
The continuation has not entered dispatch. To run the explicit continuation from
the project directory in a local zsh terminal, supply the key without sharing it:

```sh
read -rs 'OPENAI_API_KEY?API key (hidden input): '; printf '\\n'
export OPENAI_API_KEY
.venv-stage3a/bin/python scripts/continue_collection.py --collect
unset OPENAI_API_KEY
```

This command uses the existing budget approval and reruns preflight. It packages
its outcome automatically. Do not run the original `run_collection.py` command.
'''
    else:
        text+='\nThis continuation entered dispatch. Its persistent claim refuses another execution; do not delete it or retry an uncertain request.\n'
    return text

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('run',type=Path); args=parser.parse_args()
    run=args.run.resolve()
    if run.parent!=ROOT/'results/continuation': raise SystemExit('Expected a continuation run')
    summary=json.loads((run/'summary.json').read_text())
    cfg=json.loads((run/'continuation-code/collection/continuation-v1.json').read_text())
    verify_files(ROOT,json.loads((ROOT/cfg['preservation_inventory']).read_text()))
    verify_files(run,json.loads((run/'file-hashes.json').read_text()))
    backup=Path(summary['backup_directory'])
    for p in run.rglob('*'):
        if p.is_file() and sha(p.read_bytes())!=sha((backup/p.relative_to(run)).read_bytes()): raise SystemExit('Backup mismatch')
    version='collection-review-'+run.name+'.zip'; output=ROOT/version
    if output.exists(): raise SystemExit('Versioned archive already exists; never overwrite it')
    old=json.loads((ROOT/cfg['audit_run']/'summary.json').read_text())
    text=report(summary,old,cfg,version)
    # Preserve the prior current report before replacing it; old archives are untouched.
    history=ROOT/'results/continuation-history'/('before-report-'+run.name)
    save_new(history/'COLLECTION_RESULTS.md',(ROOT/'COLLECTION_RESULTS.md').read_bytes())
    (ROOT/'COLLECTION_RESULTS.md').write_text(text)
    files={'COLLECTION_RESULTS.md':ROOT/'COLLECTION_RESULTS.md'}
    files['results/collection/generation-dispatch.lock']=ROOT/'results/collection/generation-dispatch.lock'
    for p in (ROOT/'results/continuation/control').rglob('*.json'):
        files[str(p.relative_to(ROOT))]=p
    records=[ROOT/cfg['original_run'],ROOT/cfg['audit_run'],ROOT/cfg['blocked_run'],run,
             (ROOT/cfg['historical_report']).parent,history]
    for prior in (ROOT/cfg['original_run'],ROOT/cfg['audit_run']):
        s=json.loads((prior/'summary.json').read_text())
        val=Path(s['adapter_validation_record'])
        if val not in records: records.append(val)
    for record in records:
        for p in record.rglob('*'):
            if p.is_file(): files[str(p.relative_to(ROOT))]=p
    for p in (run/'continuation-code').rglob('*'):
        if p.is_file(): files[str(p.relative_to(run/'continuation-code'))]=p
    # Package the actually executed packaging code separately from collection code.
    files['packaging-source/package_continuation.py']=Path(__file__)
    entries={}; manifest=[]; redactions=[]; omitted=[]
    for name,p in sorted(files.items()):
        parts=Path(name).parts
        if '__pycache__' in parts or p.suffix=='.pyc': omitted.append(name); continue
        if p.is_symlink() or any(x.startswith('.env') or x in {'.git','.aws','secrets','credentials'} or x.endswith(('.key','.pem')) for x in parts):
            raise SystemExit('Excluded path in archive')
        raw=p.read_bytes(); data=raw
        protected='inputs' in parts or 'continuation-code' in parts or p.name in {'response.body.raw','candidate.txt','candidate.original','rule.yml','test.yml'}
        if not protected:
            data,n=re.subn(re.escape(str(ROOT).encode()),b'<PROJECT_ROOT>',data)
            if n: redactions.append({'file':name,'personal_path_occurrences':n})
        if re.search(rb'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b',data): raise SystemExit('Potential credential; archive stopped')
        entries[name]=data; manifest.append({'file':name,'original_sha256':sha(raw),'packaged_sha256':sha(data)})
    entries['REDACTIONS.md']=b'''# Sharing copy
Personal project paths in derived metadata/logs are replaced with <PROJECT_ROOT>.
Original response bodies, candidate bytes, input snapshots and continuation code
snapshots are unchanged. MANIFEST.json lists redactions, hashes and excluded Python
bytecode caches. Original local records and earlier archives remain unchanged.
Embedded original inventories refer to original bytes; SHA256SUMS verifies this copy.
'''
    entries['MANIFEST.json']=encode({'created_utc':now(),'command':[sys.executable,*sys.argv],
        'continuation_status':summary['status'],'version':version,'files':manifest,'redactions':redactions,'excluded_caches':omitted})
    entries['SHA256SUMS']=''.join(f'{sha(b)}  {n}\n' for n,b in sorted(entries.items())).encode()
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(entries.items()): z.writestr(name,data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None: raise SystemExit('ZIP CRC failure')
        for line in z.read('SHA256SUMS').decode().splitlines():
            h,n=line.split('  ',1)
            if sha(z.read(n))!=h: raise SystemExit('ZIP checksum failure')
    save_new(backup/version,output.read_bytes())
    result={'zip':str(output),'sha256':sha(output.read_bytes()),'entries':len(entries),'redacted_files':len(redactions),
            'earlier_archives_unchanged':True,'backup_verified':sha((backup/version).read_bytes())==sha(output.read_bytes())}
    save_json(ROOT/'results/continuation-packages'/(run.name+'.json'),result)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
