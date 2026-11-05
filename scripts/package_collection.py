#!/usr/bin/env python3
"""Write an actual-results report and local review ZIP; never push raw evidence."""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
from collection_adapter.workflow import ROOT

def sha(data): return hashlib.sha256(data).hexdigest()
def verify_inventory(record):
    inventory=json.loads((record/'file-hashes.json').read_text())
    for relative,h in inventory.items():
        if sha((record/relative).read_bytes())!=h: raise ValueError('Evidence hash mismatch: '+relative)

def render_report(run,summary,validation):
    attempted=summary['generation_requests_attempted']; rows=[]; counts=collections.defaultdict(collections.Counter)
    for slot in summary['slots']:
        outcomes=(slot.get('score') or {}).get('outcomes') or {}
        for dimension,status in outcomes.items(): counts[dimension][status]+=1
        rows.append('| '+slot['slot_id']+' | '+slot['status']+' | '+(', '.join(k+'='+v for k,v in outcomes.items()) if outcomes else 'not evaluated')+' |')
    known_usage=[s['analysis']['accounting']['usage'] for s in summary['slots'] if s.get('analysis') and s['analysis'].get('accounting') and isinstance(s['analysis']['accounting'].get('usage'),dict)]
    totals={k:sum(u[k] for u in known_usage if type(u.get(k)) is int) for k in ('input_tokens','output_tokens','total_tokens')} if known_usage else None
    pricing=json.loads((run/'inputs/collection/api-review.json').read_text())
    doc=f'''# Collection results

Status: **{summary['status']}**. Generation requests attempted: **{attempted}/18**.
Protocol frozen: **{summary['frozen']}**. Model: `gpt-6.1-sol` (alias; no immutable
snapshot verified). Current source commit: `{summary.get('git_commit','unavailable')}`.

'''
    if not attempted:
        doc+='''**No experimental model outputs were collected.** No refusals, successful
answers, failures, duplicate outputs or behavioural results can be claimed from
this run. The adapter and offline fixtures are implementation-validation material.

'''
    if summary.get('derived_audit'):
        doc+=f'''This is an **offline interruption audit**, not a new collection run.
Original record: `{Path(summary['original_run_directory']).relative_to(ROOT)}`.
The user confirmed Ctrl+C followed by a rerun. The collector process was no longer
running. Original files, response bytes, and the dispatch lock are preserved.
The copied freeze describes the original collection implementation. No request
was retried and no API calls were made for this audit. The separate blocked rerun
made seven metadata/access/token-count calls and zero generation calls.

The runner now detects the existing dispatch lock before preflight and reports
`existing_pilot_blocked` clearly. This post-collection correction does not alter
the frozen code, response extraction, scorer, expected outcomes, or requirements.

'''
    doc+='\n'.join('- '+e for e in summary['errors'])+'\n\n'
    doc+=f'''Selected settings: medium reasoning, Responses API, non-streaming, standard
processing, 8192 capped output tokens including reasoning, 6000 input-token
allowance including overhead, one fresh user message, no tools/history/feedback,
zero retries. The approved budget remains **US$10**; the operational ceiling is
**US$5**. No repeat budget approval is required.

## Actual validation and preflight

Offline unit-test exit: `{validation.get('unit_tests_exit','not run')}`.
Synthetic transport fixture outcomes matched:
**{sum(c['expected_outcome'] for c in validation.get('controls',{}).values())}/{len(validation.get('controls',{}))}**.
Extracted reference text through pinned scorer: **{validation.get('scorer_integration','not run')}**.
Fixtures cover success, refusal, truncation, empty/missing text, duplicates,
Unicode/CRLF/BOM preservation, multipart text, reasoning-item exclusion, ambiguous
messages, HTTP failures, uncertain completion, and usage/configuration problems.
They are not provider responses or model-performance measurements.

The six prompt files were checked byte-for-byte against the readiness report and
their hashes. The validated requirements/scorer/fixtures remain unchanged. Raw
commands, stdout, stderr, exit codes, input snapshots and hashes are retained.
Metadata/access/token-count requests attempted: **{summary['metadata_requests_attempted']}**.
Account/model access: **{'verified by metadata retrieval' if summary.get('model_access') else 'not verified'}**.
Live input-token counts: **{'recorded per task' if summary.get('input_token_counts') else 'not obtained'}**.
A blocked preflight manifest is not a completed freeze; the runner creates a true
immutable freeze only after every live check passes.

## Usage and cost

Reported usage objects: **{len(known_usage)}**.
Aggregate known usage: `{json.dumps(totals)}`; null means no API usage was returned.
Estimated known API token cost: **US${summary['estimated_known_api_cost_usd']}**.
Unknown-cost slots: `{json.dumps(summary['unknown_cost_slots'])}`.
Actual billing amount: **not queried / unknown**. Estimates are not billing.
For zero generation requests, US$0 is the adapter's generation-cost estimate,
not a measured account balance or invoice.

At verified standard short-context rates of US$2/M uncached input and US$10/M
output, with caching disabled, the conservative 18-slot token-cost bound is:

`18 × ((6000 × 2 + 8192 × 10) / 1,000,000) = US$1.69056`.

This includes reasoning and non-visible output inside the cap, without double
counting. It excludes unrelated account activity, credit purchases and tax.
See [official pricing]({pricing['sources']['pricing']}) and the
[output-cap semantics]({pricing['sources']['reasoning']}). Documentation review
must be refreshed after 24 hours before a later collection attempt.

## Slot outcomes

| Slot | Delivery/attempt status | Scoring outcomes |
|---|---|---|
'''+ '\n'.join(rows)+f'''

Scoring dimension totals: `{json.dumps({k:dict(v) for k,v in counts.items()},sort_keys=True)}`.
No result is fabricated for unavailable text. Response format, syntax, structure,
metadata, identity, behaviour and unevaluable outcomes stay separate. Report all,
some or no failures without extending the sample. Repeats are grouped by six tasks,
not 18 independent tasks. Finite synthetic tests do not establish operational safety.

## Files, backup and continuation

Primary record: `{run.relative_to(ROOT)}`.
Separate local backup: `{Path(summary['backup_directory']).relative_to(ROOT)}`.
The backup is hash-verified and on the same local filesystem, not offsite.
The review archive is `collection-review.zip`; raw evidence is not pushed.
The archive contains original available payloads/text (none if no generation was
attempted), preflight/freeze status, usage/scoring records, selected protocol,
source snapshots and labelled offline validation evidence. Sharing-copy path
redactions and original/packaged hashes are documented inside the ZIP.

The adapter uses only the local environment variable. In the same zsh terminal:

```sh
read -rs 'OPENAI_API_KEY?API key (hidden input): '; printf '\\n'
export OPENAI_API_KEY
.venv-stage3a/bin/python scripts/run_collection.py --collect
unset OPENAI_API_KEY
```

Do not paste the key into chat, print it, or put it in a command history entry.
A sibling terminal/process does not automatically inherit a newly exported key.
The command uses the existing budget authorization, but must pass fresh preflight.
Do not bypass a persistent generation-dispatch lock after an attempted pilot.

## Limits

Live transport/account behaviour remains unverified if the key is absent. Model
metadata visibility does not guarantee generation quota/permission. A moving alias
limits reproducibility. Unknown usage/schema or missing optional cache counts
halts conservatively. Offline fixtures cannot establish provider compliance with
caps. Same-volume backups do not protect against disk failure. Original local
records are preserved; sharing copies may redact personal paths. If a credential
is echoed by the provider, its raw body is withheld and the exception is recorded.
Human review remains necessary. No model or setting is silently substituted.

The credential-body handling correction and its revalidation are documented in
`collection/ADAPTER_PROTOCOL.md` under Implementation correction record. Earlier
preflight records remain preserved; no expected experimental outcome was changed.
'''
    return doc

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('run',type=Path)
    parser.add_argument('--additional-validation',type=Path,help='Include a separately recorded post-collection correction validation')
    args=parser.parse_args()
    run=args.run.resolve()
    if run.parent!=ROOT/'results/collection': raise SystemExit('Expected a collection run directory')
    summary=json.loads((run/'summary.json').read_text()); verify_inventory(run)
    validation_path=Path(summary['adapter_validation_record']) if summary.get('adapter_validation_record') else None
    validation=json.loads((validation_path/'summary.json').read_text()) if validation_path else {}
    if validation_path: verify_inventory(validation_path)
    # Verify every primary original also exists byte-identically in the separate backup.
    backup=Path(summary['backup_directory'])
    for p in run.rglob('*'):
        if p.is_file() and sha(p.read_bytes())!=sha((backup/p.relative_to(run)).read_bytes()): raise SystemExit('Backup mismatch')
    report=render_report(run,summary,validation)
    additional=args.additional_validation.resolve() if args.additional_validation else None
    if additional:
        if additional.parent!=ROOT/'results/collection-adapter': raise SystemExit('Expected an adapter validation record')
        verify_inventory(additional)
        correction=json.loads((additional/'summary.json').read_text())
        report+=f'''\n## Post-collection guard validation\n\nRecord: `{additional.relative_to(ROOT)}`.
Overall success: `{correction['success']}`; unit-test exit: `{correction['unit_tests_exit']}`;
synthetic controls matched: {sum(c['expected_outcome'] for c in correction['controls'].values())}/{len(correction['controls'])};
scorer integration: `{correction['scorer_integration']}`. This validation includes
the regression test that an existing lock stops before transport or snapshots.
It made no model API calls. The original frozen implementation is retained.
'''
    (ROOT/'COLLECTION_RESULTS.md').write_text(report)
    files={relative:run/'inputs'/relative for relative in summary['input_sha256']}
    files['COLLECTION_RESULTS.md']=ROOT/'COLLECTION_RESULTS.md'
    files['audit-support/package_collection.py']=Path(__file__)
    records=[run]+([validation_path] if validation_path else [])+([additional] if additional else [])
    for record in records:
        for p in sorted(record.rglob('*')):
            if p.is_file(): files[str(p.relative_to(ROOT))]=p
    entries={}; manifest=[]; redactions=[]; excluded_caches=[]
    for name,p in files.items():
        if p.is_symlink(): raise SystemExit('No symlinks in archive')
        parts=Path(name).parts
        if '__pycache__' in parts or p.suffix=='.pyc':
            excluded_caches.append(name)
            continue
        if any(x.startswith('.env') or x in {'.git','.aws','secrets','credentials','__pycache__'} or x.endswith(('.key','.pem','.pyc')) for x in parts):
            raise SystemExit('Excluded path type')
        raw=p.read_bytes(); data=raw
        protected='inputs' in parts or p.name in {'response.body.raw','candidate.txt','candidate.original','rule.yml','test.yml'}
        if any(p.is_relative_to(r) for r in records) and not protected:
            data,n=re.subn(re.escape(str(ROOT).encode()),b'<PROJECT_ROOT>',data)
            if n: redactions.append({'file':name,'personal_project_path_occurrences':n})
        if re.search(rb'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b',data): raise SystemExit('Potential credential marker; archive stopped')
        entries[name]=data; manifest.append({'file':name,'original_sha256':sha(raw),'packaged_sha256':sha(data),'redacted':raw!=data})
    entries['REDACTIONS.md']=b'''# Sharing copy

Personal absolute project paths in derived execution metadata/logs are replaced
with <PROJECT_ROOT>. Input snapshots and original response/candidate bytes are
unchanged. Original local records and backup are unchanged. MANIFEST.json records
original and packaged hashes for every file. Original file-hashes.json inventories
refer to original records; SHA256SUMS verifies this sharing copy. Synthetic fixture
usage is not experimental usage. Missing experimental payloads are not invented.
Derived Python bytecode caches are excluded and listed in MANIFEST.json; they
remain in the original local records. No source or response bytes are excluded
as caches.
'''
    encode_manifest={'status':summary['status'],'frozen':summary['frozen'],'run':str(run.relative_to(ROOT)),'files':manifest,'redactions':redactions,'excluded_derived_cache_files':excluded_caches}
    entries['MANIFEST.json']=(json.dumps(encode_manifest,indent=2)+'\n').encode()
    entries['SHA256SUMS']=''.join(f'{sha(data)}  {name}\n' for name,data in sorted(entries.items())).encode()
    output=ROOT/'collection-review.zip'; temporary=ROOT/'.collection-review.zip.tmp'
    with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(entries.items()): z.writestr(name,data)
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS').decode().splitlines():
            h,name=line.split('  ',1); assert sha(z.read(name))==h
    # Preserve any previous collection archive in its original backup before replacement.
    if output.exists():
        previous=ROOT/'.collection-backups'/'superseded-archives'/('collection-review-'+sha(output.read_bytes())+'.zip')
        previous.parent.mkdir(parents=True,exist_ok=True)
        if not previous.exists(): shutil.copyfile(output,previous)
        output.unlink()
    temporary.replace(output); shutil.copyfile(output,backup/'collection-review.zip')
    assert sha(output.read_bytes())==sha((backup/'collection-review.zip').read_bytes())
    # User requested deleting older review ZIPs; original execution directories stay intact.
    deleted=[]
    for older in ROOT.glob('stage*-review.zip'):
        if older.is_file() and not older.is_symlink(): older.unlink(); deleted.append(older.name)
    print(json.dumps({'zip':str(output),'sha256':sha(output.read_bytes()),'bytes':output.stat().st_size,'entries':len(entries),'redacted_files':len(redactions),'older_review_zips_deleted':deleted,'backup_verified':True},indent=2))
if __name__=='__main__': main()
