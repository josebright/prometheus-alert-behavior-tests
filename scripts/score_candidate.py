#!/usr/bin/env python3
"""Offline unchanged-response scoring: exit 0 pass, 1 candidate failure, 2 incomplete scoring."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from stage3a.contracts import TASKS, FormatError, LimitError, load, inspect
from stage3a.diagnostics import DiagnosticError, analyze

ROOT = Path(__file__).resolve().parents[1]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def sources():
    paths = [ROOT/'STUDY_PLAN.md', ROOT/'prometheus-image.txt', ROOT/'requirements-stage3a.txt',ROOT/'scripts/score_candidate.py']
    paths += sorted((ROOT/'requirements').glob('*.md'))
    paths += sorted((ROOT/'scripts/stage3a').glob('*.py'))
    paths += [ROOT/'tests/R01.test.yml']+sorted((ROOT/'tests/stage2').glob('R*.test.yml'))
    return paths

class InfrastructureError(RuntimeError): pass

def score(task, candidate, parent):
    run = parent/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run.mkdir(parents=True,exist_ok=False)
    summary = dict(started_utc=now(),task=task,invocation=[sys.executable,*sys.argv],
        host_machine=platform.machine(),python_version=sys.version,errors=[],limitations=[],
        outcomes={k:'not_evaluated' for k in ('response_format','syntax','structural_contract','metadata','required_identity','behavioral')})
    records=[]; work=run/'mount'; work.mkdir(); inputs=run/'inputs'; hashes={}
    def command(name,argv):
        start=now(); error=None
        try:
            proc=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120)
            code,out,err=proc.returncode,proc.stdout,proc.stderr
        except (OSError,subprocess.TimeoutExpired) as e:
            code=None; out=getattr(e,'stdout',None) or b''; err=getattr(e,'stderr',None) or str(e).encode(); error=type(e).__name__
        (run/(name+'.stdout')).write_bytes(out); (run/(name+'.stderr')).write_bytes(err)
        records.append(dict(name=name,argv=argv,start_utc=start,end_utc=now(),exit_code=code,execution_error=error))
        write(run/'commands.json',records)
        return code,out.decode('utf-8',errors='replace'),err.decode('utf-8',errors='replace')
    def require(name,argv):
        code,out,err=command(name,argv)
        if code!=0: raise InfrastructureError(name+': command failed; see raw evidence')
        return out
    try:
        raw=candidate.read_bytes()
        (run/'candidate.original').write_bytes(raw); (run/'candidate.original').chmod(0o444)
        summary['candidate_sha256']=digest(raw); summary['candidate_bytes']=len(raw)
        for source in sources():
            relative=source.relative_to(ROOT); target=inputs/relative
            target.parent.mkdir(parents=True,exist_ok=True); data=source.read_bytes(); target.write_bytes(data); target.chmod(0o444)
            hashes[str(relative)]=digest(data)
        summary['input_sha256']=hashes
        summary['dependencies']={name:importlib.metadata.version(name) for name in ('PyYAML','promql-parser')}
        if summary['dependencies']!={'PyYAML':'6.0.3','promql-parser':'0.11.0'}: raise InfrastructureError('Dependency versions differ from lock')
        doc=None
        try:
            doc=load(raw); summary['outcomes']['response_format']='pass'
            contract=inspect(doc,task); summary['contract']=contract
            summary['outcomes']['structural_contract']='fail' if contract['structural'] else 'unevaluable' if contract['limitations'] else 'pass'
            summary['outcomes']['metadata']='fail' if contract['metadata'] else 'not_evaluated'
            summary['outcomes']['required_identity']='fail' if contract['identity'] else 'not_evaluated'
        except FormatError as e:
            summary['outcomes']['response_format']='fail'; summary['format_error']=str(e)
        except LimitError as e:
            summary['outcomes']['response_format']='unevaluable'; summary['limitations'].append(str(e))
        fixture='tests/R01.test.yml' if task=='R01' else f'tests/stage2/{task}.test.yml'
        fixture_raw=(inputs/fixture).read_bytes(); suite=load(fixture_raw)
        (work/'rule.yml').write_bytes(raw); (work/'test.yml').write_bytes(fixture_raw)
        for path in work.iterdir(): path.chmod(0o444)
        work.chmod(0o555)
        image=(inputs/'prometheus-image.txt').read_text().strip()
        if not re.fullmatch(r'prom/prometheus@sha256:[a-f0-9]{64}',image): raise InfrastructureError('Immutable image pin required')
        def docker(*args,entrypoint='/bin/promtool'):
            return ['docker','run','--rm','--network','none','--platform','linux/arm64','--mount',f'type=bind,src={work.resolve()},dst=/work,readonly','--workdir','/work','--entrypoint',entrypoint,image,*args]
        summary['docker_version']=require('docker-version',['docker','version','--format','{{json .}}'])
        info=json.loads(require('image-inspect',['docker','image','inspect',image]))[0]
        if (info['Os'],info['Architecture'])!=('linux','arm64') or image not in info['RepoDigests']: raise InfrastructureError('Image platform/digest mismatch')
        summary.update(image_digest=image,image_id=info['Id'],image_platform='linux/arm64')
        summary['promtool_version']=require('promtool-version',docker('--version'))
        if 'promtool, version 3.15.1 ' not in summary['promtool_version']: raise InfrastructureError('Wrong promtool version')
        expected_hashes={'rule.yml':digest(raw),'test.yml':digest(fixture_raw)}
        def check_hashes(name):
            out=require(name,docker('sha256sum','rule.yml','test.yml',entrypoint='/bin/busybox'))
            actual={line.split()[1]:line.split()[0] for line in out.splitlines()}
            if actual!=expected_hashes: raise InfrastructureError('Container input hash mismatch')
            summary[name]=actual
        check_hashes('container-hashes-before')
        code,out,err=command('syntax',docker('check','rules','rule.yml'))
        summary['syntax_exit_code']=code
        if code is None or code in (125,126,127,137): raise InfrastructureError('Docker/process failure during syntax check')
        if code==0 and re.fullmatch(r'Checking rule.yml\s+SUCCESS: \d+ rules found\s*',out) and not err.strip():
            summary['outcomes']['syntax']='pass'
        elif code==1:
            summary['outcomes']['syntax']='fail'
        else:
            summary['outcomes']['syntax']='unevaluable'; summary['limitations'].append('Unrecognized syntax diagnostics or lint exit; see raw output')
        if summary['outcomes']['syntax']=='pass' and summary['outcomes']['response_format']=='pass':
            # Inspection-library disagreement is never substituted for promtool syntax.
            summary['limitations'].extend(summary['contract']['limitations'])
            code,out,err=command('behavior',docker('test','rules','test.yml'))
            summary['behavior_exit_code']=code
            if code is None or code in (125,126,127,137): raise InfrastructureError('Docker/process failure during behaviour execution')
            try:
                analysis=analyze(suite,task,TASKS[task][0],code,out,err)
                write(run/'scenarios.json',analysis)
                summary['behavior_execution']='candidate_evaluation_failure' if analysis['evaluation_errors'] else 'assertion_failure' if analysis['failed_assertions'] else 'pass'
                summary['analysis']={k:v for k,v in analysis.items() if k!='scenarios'}
                for dim in ('metadata','required_identity','behavioral'):
                    if summary['outcomes'][dim]!='fail': summary['outcomes'][dim]=analysis[dim]
                if analysis['evaluation_errors']:
                    summary['errors'].append({'kind':'candidate_evaluation_failure','details':analysis['evaluation_errors']})
            except DiagnosticError as e:
                summary['behavior_execution']='diagnostic_parser_limitation'; summary['outcomes']['behavioral']='unevaluable'
                summary['limitations'].append(str(e))
        else: summary['behavior_execution']='not_run_response_or_syntax_not_accepted'
        check_hashes('container-hashes-after')
        if candidate.read_bytes()!=raw: raise InfrastructureError('Caller candidate changed during execution')
        if (run/'candidate.original').read_bytes()!=raw: raise InfrastructureError('Preserved candidate changed')
        if any(digest((ROOT/path).read_bytes())!=h for path,h in hashes.items()): raise InfrastructureError('Frozen input/source changed during execution')
        summary['inputs_unchanged']=True
    except InfrastructureError as e:
        summary['errors'].append({'kind':'infrastructure_failure','details':str(e)})
    except Exception as e:
        summary['errors'].append({'kind':'scorer_error','details':type(e).__name__+': '+str(e)})
    if not (run/'scenarios.json').exists():
        # No invented passes when the candidate could not be evaluated.
        try:
            write(run/'scenarios.json',{'scenarios':[{'name':t['name'],'assertions':[{'eval_time':c['eval_time'],'status':'not_evaluated'} for c in t['alert_rule_test']]} for t in suite['tests']]})
        except (NameError,KeyError): pass
    incomplete=bool(summary['limitations']) or any(e['kind']!='candidate_evaluation_failure' for e in summary['errors'])
    candidate_failed=any(v=='fail' for v in summary['outcomes'].values()) or any(e['kind']=='candidate_evaluation_failure' for e in summary['errors'])
    summary['exit_code']=2 if incomplete else 1 if candidate_failed else 0 if all(v=='pass' for v in summary['outcomes'].values()) else 2
    summary['overall']='incomplete_scoring' if summary['exit_code']==2 else 'candidate_failure' if summary['exit_code']==1 else 'pass'
    summary['finished_utc']=now()
    write(run/'summary.json',summary)
    # Non-self-referential inventory covers all raw evidence, input bytes and summary.
    write(run/'file-hashes.json',{str(p.relative_to(run)):digest(p.read_bytes()) for p in sorted(run.rglob('*')) if p.is_file()})
    return run,summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task',choices=TASKS); parser.add_argument('candidate',type=Path)
    parser.add_argument('--output-parent',type=Path,default=ROOT/'results/stage3a/candidates')
    args=parser.parse_args(); run,result=score(args.task,args.candidate,args.output_parent)
    print(json.dumps({'run_directory':str(run),'overall':result['overall'],'outcomes':result['outcomes'],'exit_code':result['exit_code']},indent=2))
    return result['exit_code']
if __name__=='__main__': sys.exit(main())
