#!/usr/bin/env python3
"""Package one Stage 2 record and its exact inputs, with documented path redaction."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    if len(sys.argv)<2: raise SystemExit('Usage: python3 scripts/package_stage2.py FINAL_RUN [EARLIER_ATTEMPT ...]')
    run=Path(sys.argv[1]).resolve()
    records=[Path(arg).resolve() for arg in sys.argv[1:]]
    if any(record.parent!=ROOT/'results/stage2' for record in records): raise SystemExit('Expected direct Stage 2 run directories')
    summary=json.loads((run/'summary.json').read_text())
    output=ROOT/'stage2-review.zip'
    if output.exists(): raise SystemExit('Refusing to overwrite an existing stage2-review.zip')
    files={}
    # Use the executed snapshots, not possibly changed current implementation.
    for relative,digest in summary['sha256'].items():
        source=run/'inputs'/relative
        if sha(source.read_bytes())!=digest: raise SystemExit('Snapshot mismatch: '+relative)
        files[relative]=source
    files['STAGE2_VALIDATION.md']=ROOT/'STAGE2_VALIDATION.md'
    # Preserve the recorded packager snapshot, and ship the current packaging
    # utility at top level when a packaging-only fix followed validation.
    files['scripts/package_stage2.py']=Path(__file__).resolve()
    for record in records:
        for p in sorted(record.rglob('*')):
            if p.is_file(): files[str(p.relative_to(ROOT))]=p
    entries={}; manifest=[]; redactions=[]
    original_hashes={str(p):sha(p.read_bytes()) for p in files.values()}
    for name,source in files.items():
        if source.is_symlink(): raise SystemExit('Symlinks are not allowed')
        parts=Path(name).parts
        if any(part=='.env' or part.startswith('.env.') or part in {'credentials','secrets','.git','.aws'} or part.endswith(('.pem','.key')) for part in parts):
            raise SystemExit('Excluded file type: '+name)
        raw=source.read_bytes(); data=raw
        # Only redact execution artifacts, never code, specifications or inputs.
        if any(source.is_relative_to(record) and not source.is_relative_to(record/'inputs') for record in records):
            data,project_count=re.subn(re.escape(str(ROOT).encode()),b'<PROJECT_ROOT>',data)
            data,temp_count=re.subn(rb'(?<=src=)/(?:private/)?var/folders/[^,\"\s]+',b'<REDACTED_TEMP_WORKDIR>',data)
            if project_count or temp_count:
                redactions.append({'file':name,'project_path_occurrences':project_count,'temporary_path_occurrences':temp_count})
        if re.search(rb'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/]',data) or re.search(rb'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b',data):
            raise SystemExit('Potential credential marker in '+name)
        entries[name]=data
        manifest.append({'file':name,'original_sha256':sha(raw),'packaged_sha256':sha(data),'redacted':raw!=data})
    entries['REDACTIONS.md']=('''# Sharing copy

Original records were not modified. Personal absolute project paths in execution
artifacts are replaced with `<PROJECT_ROOT>`; temporary Docker bind-mount source
paths are replaced with `<REDACTED_TEMP_WORKDIR>`. These placeholders are not
literal replay paths. Candidate files, specifications and input snapshots are
unchanged. Public upstream tool/build metadata is retained. The manifest lists
every changed file and occurrence counts; original and packaged hashes are kept.
No credential files, .env files, chat transcripts or unrelated files are included.

This ZIP contains infrastructure-validation evidence, not sampled model outputs.
See STAGE2_VALIDATION.md for actual outcomes and classification limitations.
''').encode()
    entries['MANIFEST.json']=(json.dumps({'packaged_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':str(run.relative_to(ROOT)),'included_records':[str(record.relative_to(ROOT)) for record in records],'files':manifest,'redactions':redactions},indent=2)+'\n').encode()
    entries['SHA256SUMS']=''.join(f'{sha(data)}  {name}\n' for name,data in sorted(entries.items())).encode()
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(entries.items()): z.writestr(name,data)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS').decode().splitlines():
            digest,name=line.split('  ',1); assert sha(z.read(name))==digest
        for relative,digest in summary['sha256'].items():
            assert sha(z.read(str(run.relative_to(ROOT)/'inputs'/relative)))==digest
            if relative!='scripts/package_stage2.py':
                assert sha(z.read(relative))==digest
        assert z.read('scripts/package_stage2.py')==Path(__file__).read_bytes()
    assert all(sha(Path(p).read_bytes())==digest for p,digest in original_hashes.items())
    print(json.dumps({'zip':str(output),'bytes':output.stat().st_size,'sha256':sha(output.read_bytes()),'files':len(entries),'redacted_files':len(redactions),'verified':True},indent=2))

if __name__=='__main__': main()
