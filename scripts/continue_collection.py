#!/usr/bin/env python3
"""Explicit continuation-v1: nine previously unattempted slots, never a lock bypass."""
import argparse
import datetime
from decimal import Decimal
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from collection_adapter.core import (MODEL, Transport, budget_bound, count_body, encode,
    now, recorded_exchange, save_json, save_new, sha, strict_json)
from collection_adapter.workflow import ROOT, atomic_json, command, inventory, mirror
from collection_adapter.continuation import (ALLOWED, UNKNOWN, Stop, process_lock, eligible,
    claim, exposure, verify_files, verify_frozen, mark_uncertain, dispatch_slot, reject_prior_continuation)
from run_collection import check_configuration, actual_model_access, Halt

SOURCES=['scripts/continue_collection.py','scripts/package_continuation.py',
         'scripts/collection_adapter/continuation.py','tests/test_continuation.py',
         'collection/CONTINUATION_AMENDMENT.md','collection/continuation-v1.json',
         'collection/continuation-api-review.json','scripts/run_collection.py']

def execute(collect):
    cfg=json.loads((ROOT/'collection/continuation-v1.json').read_text())
    original=ROOT/cfg['original_run']; audit=ROOT/cfg['audit_run']
    control=ROOT/'results/continuation/control'
    with process_lock(control/'process.lock'):
        reject_prior_continuation(control)
        if tuple(cfg['allowed_slots'])!=ALLOWED: raise Stop('Amended slot list changed')
        freeze=json.loads((original/'freeze-manifest.json').read_text())
        verify_files(ROOT,{cfg['original_run']+'/freeze-manifest.json':cfg['original_freeze_sha256'],
                           'results/collection/generation-dispatch.lock':cfg['original_lock_sha256']})
        prior=json.loads((original/'summary.json').read_text())
        eligible(original,prior['slots'],ALLOWED)
        selected=verify_frozen(ROOT,original,freeze)
        preserved=json.loads((ROOT/cfg['preservation_inventory']).read_text()); verify_files(ROOT,preserved)
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        run=ROOT/'results/continuation'/stamp; run.mkdir(parents=True,exist_ok=False)
        backup=ROOT/'.collection-backups'/('continuation-'+stamp)
        summary={'kind':'continuation-v1','status':'preflight','started_utc':now(),
                 'original_run':cfg['original_run'],'audit_run':cfg['audit_run'],
                 'generation_requests_attempted':0,'metadata_requests_attempted':0,
                 'estimated_known_api_cost_usd':'0','unknown_cost_slots':[],
                 'original_unknown_slots':[UNKNOWN],'errors':[],'frozen':False,
                 'run_directory':str(run),'backup_directory':str(backup),
                 'slots':[{'slot_id':sid,'task':sid[:3],'status':'not_attempted','analysis':None,'score':None} for sid in ALLOWED]}
        def persist(): atomic_json(run/'summary.json',summary)
        def backup_now(): mirror(run,backup)
        per=Decimal('0.09392'); known=Decimal('0'); new_hashes={}
        try:
            # Immutable old inputs and new continuation code are separate namespaces.
            for name,h in freeze['input_sha256'].items(): save_new(run/'inputs'/name,(original/'inputs'/name).read_bytes())
            for name in SOURCES:
                data=(ROOT/name).read_bytes(); new_hashes[name]=sha(data); save_new(run/'continuation-code'/name,data)
            save_json(run/'original-freeze.json',freeze); save_json(run/'preservation-before.json',preserved)
            save_json(run/'frozen-input-verification.json',{'matched_current_files':selected,'original_inputs_matched':freeze['input_sha256']})
            summary['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            summary['uncommitted_files']=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,text=True).splitlines()
            summary['python_version']=sys.version
            summary['dependencies']={n:importlib.metadata.version(n) for n in freeze['dependencies']}
            if sys.version!=freeze['python_version'] or summary['dependencies']!=freeze['dependencies']:
                raise Stop('Python or dependency versions differ from original freeze')
            settings=freeze['settings']; pricing=json.loads((ROOT/'collection/continuation-api-review.json').read_text())
            per,_=check_configuration(settings,pricing)
            if pricing['rates_per_million']!=freeze['pricing']['rates_per_million']: raise Stop('Pricing changed; a new reviewed bound is required')
            # Derive the original known cost from all saved usage, never from a zero default.
            for slot in prior['slots']:
                if slot['status']=='response_recorded':
                    cost=slot['analysis']['accounting']['estimated_api_cost_usd']
                    if cost is None: raise Stop('Original known response has unaccounted usage')
                    known+=Decimal(cost)
                elif slot['status']!='not_attempted' and slot['slot_id']!=UNKNOWN:
                    raise Stop('Unexpected original attempted slot')
            summary.update(original_known_cost_usd=str(known),original_unknown_reserve_usd=str(per),
                           operational_ceiling_usd='5.00',approved_budget_usd='10.00',
                           planned_combined_exposure_usd=str(exposure(known,1,9,per)))
            missing=original/'slots'/UNKNOWN
            # There is no provider response ID in this exact non-streaming attempt.
            if (missing/'response.json').exists() or (missing/'response.body.raw').exists():
                raise Stop('R03-G02 response evidence changed; perform a separate exact-response recovery review')
            save_json(run/'recovery-assessment.json',{'slot_id':UNKNOWN,'status':'completion_unknown',
                'saved_files':sorted(p.name for p in missing.iterdir()),'response_id':None,
                'store':settings['request_fields']['store'],'read_only_retrieval_attempted':False,
                'reason':'No response ID was saved. Documented GET /responses/{response_id} needs that exact ID. Client-request IDs are not response IDs; no speculative lookup or generation.',
                'source':pricing['continuation_recovery_source']})
            code,_,_=command(run,'offline-continuation-tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_continuation.py','-v'])
            if code!=0: raise Stop('Continuation offline validation failed')
            code,_,_=command(run,'original-adapter-tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_collection_adapter.py','-v'])
            if code!=0: raise Stop('Existing adapter validation failed')
            code,_,_=command(run,'protocol-integrity',[sys.executable,'scripts/check_collection_protocol.py'])
            if code!=0: raise Stop('Prompt/readiness integrity validation failed')
            # The original scorer records Docker/promtool versions and image platform.
            code,_,_=command(run,'frozen-scorer-control',[sys.executable,'-B',str(run/'inputs/scripts/score_candidate.py'),
                'R01',str(run/'inputs/controls/stage3a/R01_reference.yml'),'--output-parent',str(run/'control-scoring')])
            if code!=0: raise Stop('Frozen scorer or pinned Docker preflight failed')
            summary['offline_preflight_pass']=True
            key=os.environ.get('OPENAI_API_KEY'); summary['credential_configured']=bool(key)
            if not collect: raise Stop('Preflight only; --collect not supplied')
            if not key: raise Stop('OPENAI_API_KEY absent in this process; no continuation API requests made')
            transport=Transport(key,timeout=settings['request_timeout_seconds'])
            summary['metadata_requests_attempted']+=1; persist()
            meta,raw=recorded_exchange(run/'preflight/model-access',transport,'GET','/v1/models/'+MODEL,None,'continuation_model_access',backup_now)
            summary['model_access']=actual_model_access(meta,raw)
            prepared={}; counts={}
            for task in ('R01','R02','R03','R04','R05','R06'):
                raw_request=(original/'prepared-requests'/(task+'.json')).read_bytes()
                req=strict_json(raw_request)
                if sha(encode(req))!=freeze['prepared_request_sha256'][task]: raise Stop('Request re-encoding differs from original')
                prepared[task]=req; save_new(run/'prepared-requests'/(task+'.json'),raw_request)
                summary['metadata_requests_attempted']+=1; persist()
                meta,raw=recorded_exchange(run/'preflight'/('count-'+task),transport,'POST','/v1/responses/input_tokens',count_body(req),'continuation_token_count',backup_now)
                if meta['completion_uncertain'] or meta['http_status']!=200 or raw is None: raise Stop('Token counting failed for '+task)
                result=strict_json(raw)
                count=result.get('input_tokens') if isinstance(result,dict) else None
                if not isinstance(result,dict) or result.get('object')!='response.input_tokens' or type(count) is not int or not 0<=count<=6000:
                    raise Stop('Invalid token count for '+task)
                counts[task]=count
            verify_files(ROOT,preserved); verify_files(ROOT,new_hashes); verify_frozen(ROOT,original,freeze)
            manifest={'frozen':True,'created_utc':now(),'original_freeze_sha256':cfg['original_freeze_sha256'],
                      'original_lock_sha256':cfg['original_lock_sha256'],'amendment':cfg,
                      'continuation_code_sha256':new_hashes,'unchanged_inputs_sha256':selected,
                      'prepared_request_sha256':freeze['prepared_request_sha256'],'settings':settings,
                      'pricing':pricing,'git_commit':summary['git_commit'],'uncommitted_files':summary['uncommitted_files'],
                      'dependencies':summary['dependencies'],'python_version':sys.version,'input_token_counts':counts,
                      'model_identifier_kind':'alias','unknown_reserve_usd':str(per),'combined_bound_usd':summary['planned_combined_exposure_usd']}
            save_json(run/'continuation-freeze.json',manifest); backup_now()
            # Persistent claim forbids any subsequent dispatch session, even after SIGKILL.
            dispatch_claim={'run_directory':str(run),'created_utc':now(),'slots':list(ALLOWED),
                 'original_lock_sha256':cfg['original_lock_sha256'],'continuation_freeze_sha256':sha((run/'continuation-freeze.json').read_bytes())}
            claim(control/'dispatch-v1.json',dispatch_claim)
            save_json(run/'continuation-dispatch-claim.json',dispatch_claim)
            summary['frozen']=True; summary['status']='collecting'; persist(); backup_now()
            for index,slot in enumerate(summary['slots']):
                verify_files(ROOT,new_hashes); verify_files(ROOT,selected)
                exposure(known+Decimal(summary['estimated_known_api_cost_usd']),1+len(summary['unknown_cost_slots']),9-index,per)
                dispatch_slot(run,control,slot,summary,transport,prepared[slot['task']],settings,pricing,persist,backup_now)
                if index<8: time.sleep(settings['pacing_seconds'])
            summary['status']='continuation_complete'
        except (Stop,Halt) as e:
            summary['status']='halted' if summary['generation_requests_attempted'] else 'preflight_blocked'; summary['errors'].append(str(e))
        except (KeyboardInterrupt,SystemExit):
            summary['status']='interrupted'; summary['errors'].append('Local interruption; active attempt is uncertain and must not be resent')
        except Exception as e:
            summary['status']='execution_error'; summary['errors'].append(type(e).__name__+'; no automatic retry')
        finally:
            mark_uncertain(summary)
            # Score only after collection stops; original frozen scorer, unchanged bytes.
            seen={s['candidate_sha256']:s['slot_id'] for s in prior['slots'] if s.get('candidate_sha256')}
            for slot in summary['slots']:
                candidate=run/'slots'/slot['slot_id']/'candidate.txt'
                if candidate.exists():
                    h=sha(candidate.read_bytes()); slot['duplicate_of']=seen.get(h); seen.setdefault(h,slot['slot_id'])
                    try:
                        code,_,_=command(run,'score-'+slot['slot_id'],[sys.executable,'-B',str(run/'inputs/scripts/score_candidate.py'),
                            slot['task'],str(candidate),'--output-parent',str(run/'scoring'/slot['slot_id'])])
                        records=list((run/'scoring'/slot['slot_id']).glob('*/summary.json'))
                        slot['score']={'exit_code':code,'record':str(records[0].relative_to(run)) if len(records)==1 else None,
                                      'outcomes':json.loads(records[0].read_text())['outcomes'] if len(records)==1 else None}
                    except (Exception,KeyboardInterrupt) as e:
                        slot['score']={'outcomes':None,'error':type(e).__name__}
                if slot['status']=='not_attempted': slot['not_attempted_reason']=summary['status']
            summary['finished_utc']=now()
            summary['combined_known_cost_usd']=str(known+Decimal(summary['estimated_known_api_cost_usd']))
            summary['combined_unknown_reserve_usd']=str(per*(1+len(summary['unknown_cost_slots'])))
            summary['billing_amount_usd']=None
            try: verify_files(ROOT,preserved); summary['originals_unchanged']=True
            except Stop as e: summary['originals_unchanged']=False; summary['errors'].append(str(e))
            if not summary['frozen']: save_json(run/'preflight-manifest.json',{'frozen':False,'original_freeze_sha256':cfg['original_freeze_sha256'],'continuation_code_sha256':new_hashes,'status':summary['status']})
            persist(); inventory(run); backup_now()
            print(json.dumps({k:summary[k] for k in ('run_directory','status','generation_requests_attempted','metadata_requests_attempted','errors','originals_unchanged')},indent=2),flush=True)
        return run,summary['status']=='continuation_complete'

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--collect',action='store_true'); args=parser.parse_args()
    def interrupted(signum,frame): raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted)
    try: run,complete=execute(args.collect)
    except (Stop,Halt) as e:
        print(json.dumps({'status':'continuation_refused','error':str(e),'new_generations':0})); return 2
    # Packaging is local and cannot dispatch. Every run receives a new archive name.
    packaged=subprocess.run([sys.executable,str(ROOT/'scripts/package_continuation.py'),str(run)],cwd=ROOT)
    return 0 if complete and packaged.returncode==0 else 2

if __name__=='__main__': sys.exit(main())
