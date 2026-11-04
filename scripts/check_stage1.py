#!/usr/bin/env python3
"""Exit 0: expected validation outcomes; exit 2: unexpected/infrastructure error."""
import datetime, hashlib, json, pathlib, shutil, subprocess, sys, tempfile, platform
ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMETHEUS_VERSION = '3.15.1'
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
run = ROOT / 'results/stage1' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
run.mkdir(parents=True)
records=[]
def command(name, args):
    start=now()
    try:
        r=subprocess.run(args,cwd=ROOT,capture_output=True)
        out,err,code=r.stdout,r.stderr,r.returncode
    except OSError as e:
        out,err,code=b'',str(e).encode(),127
    (run/f'{name}.stdout').write_bytes(out)
    (run/f'{name}.stderr').write_bytes(err)
    records.append(dict(name=name,argv=args,start_utc=start,end_utc=now(),exit_code=code))
    (run/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
    return code,out.decode(errors='replace'),err.decode(errors='replace')
def require(name,args):
    code,out,err=command(name,args)
    if code: raise RuntimeError(f'{name}: exit {code}; see raw logs')
    return out
summary={'started_utc':now(),'host_machine':platform.machine(),'python_version':sys.version,'expected_prometheus_version':PROMETHEUS_VERSION,'outcomes':{}}
try:
    files=[ROOT/'requirements/R01.md',ROOT/'rules/reference.yml',ROOT/'tests/R01.test.yml',ROOT/'scripts/check_stage1.py',ROOT/'.gitignore',*sorted((ROOT/'rules/mutations').glob('*.yml'))]
    lock=ROOT/'prometheus-image.txt'
    if lock.exists(): files.append(lock)
    snapshot=run/'inputs'; snapshot.mkdir()
    for f in files:
        dest=snapshot/f.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(f,dest)
    summary['sha256']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    require('docker-version',['docker','version'])
    image=lock.read_text().strip() if lock.exists() else f'prom/prometheus:v{PROMETHEUS_VERSION}'
    require('pull',['docker','pull','--platform','linux/arm64',image])
    info=json.loads(require('image-inspect',['docker','image','inspect',image]))[0]
    if info['Architecture']!='arm64' or info['Os']!='linux': raise RuntimeError('Expected native linux/arm64 image')
    digest=next(x for x in info['RepoDigests'] if x.startswith('prom/prometheus@sha256:'))
    summary.update(image_requested=image,image_digest=digest,image_id=info['Id'],image_platform=info['Os']+'/'+info['Architecture'])
    if not lock.exists():
        lock.write_text(digest+'\n')
        shutil.copyfile(lock,snapshot/lock.name)
        summary['sha256'][lock.name]=hashlib.sha256(lock.read_bytes()).hexdigest()
    def docker(work,*args):
        return ['docker','run','--rm','--network','none','--platform','linux/arm64','--mount',f'type=bind,src={work},dst=/work,readonly','--workdir','/work','--entrypoint','/bin/promtool',digest,*args]
    with tempfile.TemporaryDirectory(prefix='r01-') as tmp:
        work=pathlib.Path(tmp)
        shutil.copyfile(snapshot/'tests/R01.test.yml',work/'test.yml')
        summary['promtool_version']=require('promtool-version',docker(work,'--version'))
        if f'promtool, version {PROMETHEUS_VERSION} ' not in summary['promtool_version']:
            raise RuntimeError('Pinned image does not match the expected Prometheus version')
        for name,relative in [('reference','rules/reference.yml'),('no_for','rules/mutations/no_for.yml'),('inclusive','rules/mutations/inclusive.yml'),('no_service','rules/mutations/no_service.yml')]:
            shutil.copyfile(snapshot/relative,work/'rule.yml')
            syntax,_,_=command(name+'-syntax',docker(work,'check','rules','rule.yml'))
            behavior,out,err=command(name+'-behavior',docker(work,'test','rules','test.yml'))
            # Assertion mismatch text distinguishes expected failures from loader/runtime errors.
            mismatch=('FAILED' in out+err and 'exp:' in out+err and 'got:' in out+err)
            expected=syntax==0 and (behavior==0 if name=='reference' else behavior==1 and mismatch)
            summary['outcomes'][name]=dict(syntax_exit=syntax,behavior_exit=behavior,assertion_mismatch=mismatch,expected_outcome=expected)
    summary['success']=all(x['expected_outcome'] for x in summary['outcomes'].values())
except Exception as e:
    summary.update(success=False,error=str(e))
summary['finished_utc']=now()
(run/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2)); print('Run directory:',run)
sys.exit(0 if summary['success'] else 2)
