"""Persistence helpers shared by offline validation and the live preflight runner."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from .core import encode, now, save_json, save_new, sha
ROOT=Path(__file__).resolve().parents[2]

def atomic_json(path,value):
    path=Path(path); temp=path.with_name(path.name+'.tmp')
    with temp.open('wb') as f: f.write(encode(value)); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)

def mirror(source,destination):
    source=Path(source); destination=Path(destination)
    if source.resolve()==destination.resolve() or destination.resolve().is_relative_to(source.resolve()): raise ValueError('Backup must be separate from primary run')
    for p in sorted(source.rglob('*')):
        if not p.is_file() or p.name.endswith('.tmp'): continue
        if p.is_symlink(): raise ValueError('Symlinks cannot enter evidence backup')
        relative=p.relative_to(source); out=destination/relative
        if out.exists() and sha(out.read_bytes())==sha(p.read_bytes()): continue
        out.parent.mkdir(parents=True,exist_ok=True); tmp=out.with_name(out.name+'.tmp')
        with tmp.open('wb') as f: f.write(p.read_bytes()); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,out); out.chmod(0o444)
    for p in source.rglob('*'):
        if p.is_file() and not p.name.endswith('.tmp'):
            if sha(p.read_bytes())!=sha((destination/p.relative_to(source)).read_bytes()): raise ValueError('Backup verification mismatch')

def command(run,name,args,timeout=240,cwd=ROOT):
    start=now(); error=None
    try:
        p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=timeout)
        code,out,err=p.returncode,p.stdout,p.stderr
    except (OSError,subprocess.TimeoutExpired) as e:
        code=None; out=getattr(e,'stdout',None) or b''; err=getattr(e,'stderr',None) or b''; error=type(e).__name__
    folder=Path(run)/'commands'/name; folder.mkdir(parents=True,exist_ok=False)
    save_new(folder/'stdout',out); save_new(folder/'stderr',err)
    save_json(folder/'command.json',{'argv':args,'cwd':str(cwd),'started_utc':start,'finished_utc':now(),'exit_code':code,'execution_error':error})
    return code,out,err

def code_sources():
    paths=[ROOT/'scripts/run_collection.py',ROOT/'scripts/validate_collection_adapter.py',ROOT/'scripts/package_collection.py',ROOT/'tests/test_collection_adapter.py',ROOT/'collection/settings.selected.json',ROOT/'collection/api-review.json',ROOT/'collection/ADAPTER_PROTOCOL.md']
    paths+=sorted((ROOT/'scripts/collection_adapter').glob('*.py'))
    paths+=sorted(p for p in (ROOT/'controls/collection-adapter').glob('*') if p.is_file())
    return [p for p in paths if p.exists()]

def snapshot(run):
    baseline=json.loads((ROOT/'collection/protocol-manifest.json').read_text())
    paths=set(baseline['validated_baseline']['input_sha256'])|set(baseline['baseline_additional_sha256'])|set(baseline['draft_artifact_sha256'])|{'collection/protocol-manifest.json','.gitignore'}
    paths.update(str(p.relative_to(ROOT)) for p in code_sources())
    hashes={}
    for relative in sorted(paths):
        data=(ROOT/relative).read_bytes(); hashes[relative]=sha(data)
        save_new(Path(run)/'inputs'/relative,data)
    return hashes

def assert_inputs(hashes):
    bad=[p for p,h in hashes.items() if sha((ROOT/p).read_bytes())!=h]
    if bad: raise ValueError('Relevant source/input changed: '+', '.join(bad))

def inventory(run):
    paths={str(p.relative_to(run)):sha(p.read_bytes()) for p in sorted(Path(run).rglob('*')) if p.is_file() and p.name!='file-hashes.json'}
    atomic_json(Path(run)/'file-hashes.json',paths)
    return paths
