#!/usr/bin/env python3
"""Run Stage 2 infrastructure validation. Exit 0 expected outcomes; 2 otherwise."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import traceback
from classify_stage2 import EvidenceError, analyze

ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,obj): path.write_text(json.dumps(obj,indent=2)+'\n')

def main():
    run=ROOT/'results/stage2'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run.mkdir(parents=True)
    records=[]
    (run/'runner.stdout').write_text(''); (run/'runner.stderr').write_text('')
    def emit(message):
        print(message,flush=True)
        with (run/'runner.stdout').open('a') as f: f.write(message+'\n')
    def command(name,args):
        begin=now(); error=None
        try:
            result=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=240)
            out,err,code=result.stdout,result.stderr,result.returncode
        except subprocess.TimeoutExpired as e:
            out,err,code=e.stdout or b'',e.stderr or b'',None
            error='timeout after 240 seconds'
        except OSError as e:
            out,err,code=b'',str(e).encode(),None
            error=type(e).__name__
        (run/f'{name}.stdout').write_bytes(out); (run/f'{name}.stderr').write_bytes(err)
        records.append({'name':name,'argv':args,'start_utc':begin,'end_utc':now(),'exit_code':code,'execution_error':error})
        write(run/'commands.json',records)
        return code,out.decode(errors='replace'),err.decode(errors='replace')
    def require(name,args):
        code,out,err=command(name,args)
        if code!=0: raise RuntimeError(f'{name}: exit {code}, see raw logs')
        return out
    summary={'started_utc':now(),'invocation':[sys.executable,*sys.argv],'host_machine':platform.machine(),'python_version':sys.version,'candidates':{},'errors':[]}
    emit('Run directory: '+str(run))
    try:
        files=[ROOT/'STUDY_PLAN.md',ROOT/'prometheus-image.txt',ROOT/'.gitignore',ROOT/'rules/reference.yml',ROOT/'tests/R01.test.yml',ROOT/'scripts/check_stage1.py']
        files+=sorted((ROOT/'requirements').glob('*.md'))
        files+=sorted((ROOT/'rules/mutations').glob('*.yml'))
        files+=sorted((ROOT/'rules/stage2').rglob('*.yml'))
        files+=sorted((ROOT/'tests/stage2').glob('*'))
        files += [ROOT/'scripts'/name for name in ['build_stage2.py','classify_stage2.py','check_stage2.py','package_stage2.py']]
        files += [ROOT/'tests/test_stage2_classifier.py']
        snapshot=run/'inputs'
        for source in files:
            dest=snapshot/source.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dest)
        summary['sha256']={str(p.relative_to(ROOT)):sha(snapshot/p.relative_to(ROOT)) for p in files}
        catalog=json.loads((snapshot/'tests/stage2/catalog.json').read_text())
        summary['task_coverage']={k:{'scenarios':v['scenarios'],'assertions':v['assertions']} for k,v in catalog['tasks'].items()}
        # Assert executable inputs still exactly compile from the reviewed tables.
        from build_stage2 import compile_suite
        for task in catalog['tasks']:
            suite,rows=compile_suite(task)
            if suite!=json.loads((snapshot/f'tests/stage2/{task}.test.yml').read_text()) or rows!=catalog['tasks'][task]['scenario_rows']:
                raise RuntimeError(f'{task}: compiled fixture drift from specification')
        require('classifier-tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_stage2_classifier.py','-v'])
        require('docker-version',['docker','version'])
        image=(snapshot/'prometheus-image.txt').read_text().strip()
        if not image.startswith('prom/prometheus@sha256:'): raise RuntimeError('An immutable image pin is required')
        require('pull',['docker','pull','--platform','linux/arm64',image])
        info=json.loads(require('image-inspect',['docker','image','inspect',image]))[0]
        if (info['Os'],info['Architecture'])!=('linux','arm64'): raise RuntimeError('Wrong image platform')
        summary.update(image_digest=image,image_id=info['Id'],image_platform='linux/arm64')
        def docker(work,*args,entrypoint='/bin/promtool'):
            return ['docker','run','--rm','--network','none','--platform','linux/arm64','--mount',f'type=bind,src={work},dst=/work,readonly','--workdir','/work','--entrypoint',entrypoint,image,*args]
        with tempfile.TemporaryDirectory(prefix='stage2-') as tmp:
            work=Path(tmp)
            summary['promtool_version']=require('promtool-version',docker(work,'--version'))
            if 'promtool, version 3.15.1 ' not in summary['promtool_version']: raise RuntimeError('Unexpected promtool version')
            for candidate in catalog['candidates']:
                cid=candidate['id']; task=candidate['task']
                result={'task':task,'kind':candidate['kind'],'description':candidate['description'],'targeted_obligations':candidate['targeted_obligations']}
                summary['candidates'][cid]=result
                try:
                    # A distinct, never-overwritten mount for every candidate.
                    work=Path(tmp)/cid
                    work.mkdir()
                    source=snapshot/candidate['path']
                    shutil.copyfile(source,work/'rule.yml')
                    shutil.copyfile(snapshot/f'tests/stage2/{task}.test.yml',work/'test.yml')
                    if sha(source)!=sha(work/'rule.yml'): raise RuntimeError('Candidate bytes changed in staging')
                    (work/'rule.yml').chmod(0o444)
                    (work/'test.yml').chmod(0o444)
                    hashes=require(cid+'-container-input-hashes',docker(work,'sha256sum','rule.yml','test.yml',entrypoint='/bin/busybox'))
                    observed={line.split()[1]:line.split()[0] for line in hashes.splitlines()}
                    expected={'rule.yml':sha(source),'test.yml':sha(work/'test.yml')}
                    if observed!=expected: raise RuntimeError('Container-visible input hashes differ from snapshots')
                    result['container_input_sha256']=observed
                    rule=json.loads(source.read_text())['groups'][0]['rules'][0]
                    result['declared_annotations']=rule.get('annotations',{})
                    syntax,_,_=command(cid+'-syntax',docker(work,'check','rules','rule.yml'))
                    code,out,err=command(cid+'-behavior',docker(work,'test','rules','test.yml'))
                    result.update(syntax_exit=syntax,behavior_exit=code,candidate_sha256=sha(source),executed_candidate_sha256=sha(work/'rule.yml'))
                    if syntax!=0:
                        raise EvidenceError('Syntax check failed; not a behavioural mutation detection')
                    suite=json.loads((work/'test.yml').read_text())
                    analyzed=analyze(suite,candidate,catalog['tasks'][task],code,out,err)
                    write(run/(cid+'-scenarios.json'),analyzed)
                    result.update({k:v for k,v in analyzed.items() if k!='scenarios'})
                    if candidate['kind']=='reference':
                        result['expected_outcome']=code==0
                    elif candidate['kind']=='metadata_control':
                        result['expected_outcome']=code==1 and analyzed['metadata_only_failure'] and analyzed['detection_and_timing_pass'] and analyzed['required_identity_pass'] and not analyzed['targeted_obligation_counts']
                    else:
                        result['expected_outcome']=code==1 and analyzed['failed_assertions']>0 and not analyzed['metadata_only_failure']
                    result['status']='reference_pass' if code==0 and candidate['kind']=='reference' else 'survived' if code==0 else 'metadata_contract_failure' if analyzed['metadata_only_failure'] else 'assertion_failure'
                except Exception as e:
                    result.update(status='validation_or_execution_error',error=str(e),expected_outcome=False)
                    summary['errors'].append(cid+': '+str(e))
                emit(cid+': '+result['status'])
                write(run/'summary.json',summary)
        summary['surviving_mutations']=[cid for cid,r in summary['candidates'].items() if r['kind']=='mutation' and r['status']=='survived']
        summary['success']=len(summary['candidates'])==len(catalog['candidates']) and all(r['expected_outcome'] for r in summary['candidates'].values())
        changed=[str(p.relative_to(ROOT)) for p in files if sha(p)!=summary['sha256'][str(p.relative_to(ROOT))]]
        summary['inputs_unchanged_after_execution']=not changed
        if changed: raise RuntimeError('Inputs changed during run: '+repr(changed))
    except Exception as e:
        summary['success']=False; summary['errors'].append(str(e))
        (run/'runner.stderr').write_text(traceback.format_exc())
    summary['finished_utc']=now(); summary['runner_exit_code']=0 if summary.get('success') else 2
    write(run/'summary.json',summary)
    emit('Overall success: '+str(summary.get('success')))
    emit('Summary: '+str(run/'summary.json'))
    return summary['runner_exit_code']

if __name__=='__main__': sys.exit(main())
