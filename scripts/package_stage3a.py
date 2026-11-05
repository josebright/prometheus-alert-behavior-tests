#!/usr/bin/env python3
"""Package explicit Stage 3A runs; preserve originals and document path redactions."""
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
    if len(sys.argv)<2: raise SystemExit('Usage: python3 scripts/package_stage3a.py FINAL_RUN [EARLIER_RUN ...]')
    records=[Path(p).resolve() for p in sys.argv[1:]]
    if any(p.parent!=ROOT/'results/stage3a' for p in records): raise SystemExit('Expected direct Stage 3A validation directories')
    final=records[0]; summary=json.loads((final/'summary.json').read_text())
    if not summary['success']: raise SystemExit('Final validation did not succeed')
    files={}
    for relative,h in summary['input_sha256'].items():
        p=final/'inputs'/relative
        if sha(p.read_bytes())!=h: raise SystemExit('Snapshot hash mismatch: '+relative)
        files[relative]=p
    for relative in ('STAGE3A_VALIDATION.md','scripts/package_stage3a.py','controls/stage3a/README.md','.gitignore'):
        files[relative]=ROOT/relative
    for record in records:
        # Verify every original hashed record before packaging. No redaction here.
        inventory=json.loads((record/'file-hashes.json').read_text())
        for relative,h in inventory.items():
            if sha((record/relative).read_bytes())!=h: raise SystemExit('Execution evidence changed: '+relative)
        for p in sorted(record.rglob('*')):
            if p.is_file(): files[str(p.relative_to(ROOT))]=p
    entries={}; manifest=[]; redactions=[]; originals={}
    for name,p in files.items():
        if p.is_symlink(): raise SystemExit('No symlinks in package')
        if any(part.startswith('.env') or part in {'.git','.aws','credentials','secrets','responses','prompts','__pycache__'} or part.endswith(('.pem','.key','.pyc')) for part in Path(name).parts):
            raise SystemExit('Excluded path: '+name)
        raw=p.read_bytes(); data=raw; originals[str(p)]=sha(raw)
        is_record=any(p.is_relative_to(r) for r in records)
        # Original candidates, mount files, and input snapshots are byte-identical.
        protected='inputs' in Path(name).parts or 'mount' in Path(name).parts or p.name=='candidate.original'
        if is_record and not protected:
            data,n=re.subn(re.escape(str(ROOT).encode()),b'<PROJECT_ROOT>',data)
            if n: redactions.append({'file':name,'project_path_occurrences':n})
        if re.search(rb'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/]',data) or re.search(rb'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b',data):
            raise SystemExit('Potential credential marker: '+name)
        entries[name]=data; manifest.append({'file':name,'original_sha256':sha(raw),'packaged_sha256':sha(data),'redacted':raw!=data})
    entries['REDACTIONS.md']=b'''# Sharing-copy redactions

Original execution records are unchanged. Absolute personal project paths in
execution metadata/stdout/stderr are replaced by <PROJECT_ROOT> in this ZIP.
These placeholders are not literal replay commands. Candidate originals, mounted
candidate/fixture copies and input snapshots remain byte-identical. MANIFEST.json
lists redacted files and both original and packaged hashes. Original evidence
inventories describe originals; SHA256SUMS verifies the sharing copy. Public tool
build metadata is retained. No credentials, .env files, transcripts, earlier-stage
archives or future experimental responses are included.
'''
    entries['MANIFEST.json']=(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'final_record':str(final.relative_to(ROOT)),'records':[str(p.relative_to(ROOT)) for p in records],'files':manifest,'redactions':redactions},indent=2)+'\n').encode()
    entries['SHA256SUMS']=''.join(f'{sha(data)}  {name}\n' for name,data in sorted(entries.items())).encode()
    output=ROOT/'stage3a-review.zip'
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(entries.items()): z.writestr(name,data)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS').decode().splitlines():
            h,name=line.split('  ',1); assert sha(z.read(name))==h
        for relative,h in summary['input_sha256'].items(): assert sha(z.read(relative))==h
    assert all(sha(Path(p).read_bytes())==h for p,h in originals.items())
    print(json.dumps({'zip':str(output),'sha256':sha(output.read_bytes()),'bytes':output.stat().st_size,'entries':len(entries),'redacted_files':len(redactions),'verified':True},indent=2))
if __name__=='__main__': main()
