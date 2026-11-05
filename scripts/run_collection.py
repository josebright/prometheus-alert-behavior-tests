#!/usr/bin/env python3
"""Run preflight, then the one authorized 18-slot pilot. Never resume/resend automatically."""
import argparse
import datetime
from decimal import Decimal
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from collection_adapter.core import (MODEL,Transport,budget_bound,count_body,encode,inspect_response,now,
    recorded_exchange,request_body,save_json,save_new,sha,strict_json)
from collection_adapter.workflow import ROOT,assert_inputs,atomic_json,command,inventory,mirror,snapshot

class Halt(RuntimeError): pass

def reject_existing_dispatch(root):
    guard=Path(root)/'results/collection/generation-dispatch.lock'
    if guard.exists():
        raise Halt('A pilot has already acquired the generation-dispatch lock. '
                   'No API calls were made by this invocation. Inspect the original run; '
                   'do not delete the lock or resend uncertain requests.')

def check_configuration(settings,pricing):
    expected={'model':MODEL,'reasoning':{'effort':'medium','mode':'standard'},'max_output_tokens':8192,
              'stream':False,'background':False,'service_tier':'default','store':False,'tools':[],
              'tool_choice':'none','text':{'format':{'type':'text'},'verbosity':'medium'},
              'truncation':'disabled','prompt_cache_options':{'mode':'explicit'}}
    if settings['request_fields']!=expected or settings['model']!=MODEL: raise Halt('Selected request settings differ from reviewed configuration')
    if settings['max_input_tokens_including_overhead']!=6000 or settings['planned_slots']!=18 or settings['retries']!=0:
        raise Halt('Input/slot/retry policy mismatch')
    if settings['api_origin']!='https://api.openai.com' or settings['generation_path']!='/v1/responses': raise Halt('Endpoint mismatch')
    if Decimal(settings['operational_ceiling_usd'])!=Decimal('5') or Decimal(settings['approved_budget_usd'])!=Decimal('10'): raise Halt('Approved budget mismatch')
    reviewed=datetime.datetime.fromisoformat(pricing['reviewed_at'])
    age=(datetime.datetime.now(datetime.timezone.utc)-reviewed).total_seconds()
    if not 0<=age<=24*3600: raise Halt('Official pricing/settings review is stale; reverify before collection')
    if pricing['review_status']!='official_sources_verified' or not pricing['output_cap_includes_reasoning_and_nonvisible_tokens']:
        raise Halt('Pricing/output-cap semantics not established')
    if pricing['rates_per_million']['uncached_input']!='2.00' or pricing['rates_per_million']['output_including_reasoning']!='10.00':
        raise Halt('Reviewed pricing changed; requires a new documented bound')
    per,total=budget_bound(settings,pricing)
    if total>Decimal(settings['operational_ceiling_usd']): raise Halt('Conservative bound exceeds operational ceiling')
    return per,total

def actual_model_access(meta,raw):
    if meta['completion_uncertain'] or meta['http_status']!=200 or raw is None: raise Halt('Model-access verification failed; no substitution permitted')
    try: doc=strict_json(raw)
    except (ValueError,UnicodeError): raise Halt('Unrecognized model-access response')
    if not isinstance(doc,dict) or doc.get('id')!=MODEL or doc.get('object')!='model': raise Halt('Model-access identifier mismatch')
    return {'verified':True,'method':'GET /v1/models/'+MODEL,'model_id':doc['id'],
            'limitation':'Metadata visibility is not a guarantee of quota or generation permission; any generation error halts without retry.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect',action='store_true',help='Perform authorized live preflight and collect only if all checks pass')
    args=parser.parse_args()
    # Check before creating records, validating, or making metadata requests.
    # The exclusive creation below still guards concurrent starts at dispatch.
    try:
        reject_existing_dispatch(ROOT)
    except Halt as e:
        print(json.dumps({'status':'existing_pilot_blocked','attempted_generations':0,
                          'metadata_requests_attempted':0,'errors':[str(e)]},indent=2))
        return 2
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run=ROOT/'results/collection'/stamp; run.mkdir(parents=True)
    backup=ROOT/'.collection-backups'/stamp
    summary={'started_utc':now(),'status':'preflight','frozen':False,'generation_requests_attempted':0,
             'metadata_requests_attempted':0,'errors':[],'slots':[], 'billing_amount_usd':None,
             'estimated_known_api_cost_usd':'0','unknown_cost_slots':[],'run_directory':str(run),
             'backup_directory':str(backup),'backup_scope':'separate local directory on same filesystem, not offsite'}
    def persist(): atomic_json(run/'summary.json',summary)
    def backup_now(): mirror(run,backup)
    hashes={}; settings=None; guard=None
    try:
        hashes=snapshot(run); summary['input_sha256']=hashes
        summary['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        summary['uncommitted_status']=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,text=True).splitlines()
        summary['python_version']=sys.version; summary['host_machine']=platform.machine()
        summary['dependencies']={p:importlib.metadata.version(p) for p in ('PyYAML','promql-parser')}
        settings=json.loads((run/'inputs/collection/settings.selected.json').read_text())
        pricing=json.loads((run/'inputs/collection/api-review.json').read_text())
        per,total=check_configuration(settings,pricing)
        summary.update(approved_budget_usd='10.00',operational_ceiling_usd='5.00',per_slot_bound_usd=str(per),total_planned_bound_usd=str(total))
        slots=json.loads((run/'inputs/collection/slots.json').read_text())['slots']
        expected=[f'R{task:02d}-G{rnd:02d}' for rnd in range(1,4) for task in range(1,7)]
        if [s['slot_id'] for s in slots]!=expected: raise Halt('Slot order/count differs from authorized 18 slots')
        summary['slots']=[{**s,'status':'not_attempted','score':None,'analysis':None} for s in slots]
        persist()
        code,_,_=command(run,'protocol-integrity',[sys.executable,'scripts/check_collection_protocol.py'])
        if code!=0: raise Halt('Prompt/baseline integrity check failed')
        code,out,_=command(run,'offline-adapter-validation',[sys.executable,'scripts/validate_collection_adapter.py','--with-scorer'],timeout=300)
        if code!=0: raise Halt('Offline adapter/scorer validation failed')
        validation=json.loads(out); summary['adapter_validation_record']=validation['run_directory']
        validation_path=Path(validation['run_directory'])
        save_json(run/'adapter-validation-reference.json',{'path':str(validation_path),'summary_sha256':sha((validation_path/'summary.json').read_bytes())})
        summary['offline_validation_pass']=True
        assert_inputs(hashes); backup_now()
        if not args.collect: raise Halt('Preflight-only invocation: --collect was not supplied')
        # Inspect only this environment variable; never search files or display its value.
        key=os.environ.get('OPENAI_API_KEY')
        summary['credential_configured']=bool(key)
        if not key: raise Halt('OPENAI_API_KEY is not configured in this process; live preflight and collection were not attempted')
        transport=Transport(key,timeout=settings['request_timeout_seconds'])
        summary['metadata_requests_attempted']+=1; persist()
        meta,raw=recorded_exchange(run/'preflight/model-access',transport,'GET','/v1/models/'+MODEL,None,'model_access_no_generation',backup_now)
        summary['model_access']=actual_model_access(meta,raw)
        summary['input_token_counts']={}; prepared={}
        for task in ('R01','R02','R03','R04','R05','R06'):
            prompt=(run/f'inputs/prompts/collection-draft/{task}.txt').read_bytes()
            req=request_body(prompt,settings); prepared[task]=req
            summary['metadata_requests_attempted']+=1; persist()
            meta,raw=recorded_exchange(run/'preflight'/('token-count-'+task),transport,'POST','/v1/responses/input_tokens',count_body(req),'input_count_no_generation',backup_now)
            if meta['completion_uncertain'] or meta['http_status']!=200 or raw is None: raise Halt('Input token count preflight failed for '+task)
            doc=strict_json(raw); count=doc.get('input_tokens') if isinstance(doc,dict) else None
            if doc.get('object')!='response.input_tokens' or type(count) is not int or count<0 or count>6000: raise Halt('Input allowance/count response invalid for '+task)
            summary['input_token_counts'][task]=count
            save_json(run/'prepared-requests'/(task+'.json'),req)
        assert_inputs(hashes)
        # Refuse any automatic restart once an authorized pilot has begun.
        guard=ROOT/'results/collection/generation-dispatch.lock'
        try:
            save_json(guard,{'run_directory':str(run),'created_utc':now(),'authorization':'existing 18 slots; US$5 operational / US$10 approved','automatic_resume':False})
        except FileExistsError:
            raise Halt('Another pilot acquired the generation-dispatch lock; this run cannot generate or resume.')
        freeze={'frozen':True,'frozen_utc':now(),'git_commit':summary['git_commit'],'uncommitted_relevant_files_archived':summary['uncommitted_status'],
                'input_sha256':hashes,'prepared_request_sha256':{t:sha(encode(req)) for t,req in prepared.items()},
                'settings':settings,'pricing':pricing,'model_identifier_kind':'alias','immutable_snapshot_verified':False,
                'python_version':sys.version,'dependencies':summary['dependencies'],
                'validated_scorer_manifest':json.loads((run/'inputs/collection/protocol-manifest.json').read_text())['validated_baseline'],
                'input_token_counts_including_overhead':summary['input_token_counts'],'model_access':summary['model_access'],
                'adapter_validation_summary_sha256':sha((validation_path/'summary.json').read_bytes()),
                'extraction_policy_sha256':hashes['collection/ADAPTER_PROTOCOL.md'],'budget_authorization_reconfirmed':False}
        save_json(run/'freeze-manifest.json',freeze); summary['frozen']=True; summary['status']='collecting'; persist(); backup_now()
        known_cost=Decimal('0'); seen={}
        for index,slot in enumerate(summary['slots']):
            assert_inputs(hashes)
            if known_cost+per*(18-index)>Decimal('5'): raise Halt('Budget risk before dispatch')
            directory=run/'slots'/slot['slot_id']; slot['status']='attempted_before_dispatch'; summary['generation_requests_attempted']+=1
            persist(); backup_now()
            meta,raw=recorded_exchange(directory,transport,'POST','/v1/responses',prepared[slot['task']],'experimental_generation',backup_now)
            analysis=inspect_response(meta,raw,settings,pricing)
            extracted=analysis.get('extraction') or {}
            if extracted.get('text_available'):
                data=extracted['text'].encode('utf-8'); save_new(directory/'candidate.txt',data)
                h=sha(data); slot['candidate_sha256']=h; slot['duplicate_of']=seen.get(h); seen.setdefault(h,slot['slot_id'])
            save_json(directory/'analysis.json',analysis)
            slot['analysis']=analysis; slot['status']='halted_after_response' if analysis['halt_reasons'] else 'response_recorded'
            cost=(analysis.get('accounting') or {}).get('estimated_api_cost_usd')
            if cost is None: summary['unknown_cost_slots'].append(slot['slot_id'])
            else: known_cost+=Decimal(cost)
            summary['estimated_known_api_cost_usd']=str(known_cost)
            persist(); backup_now()
            if analysis['halt_reasons']: raise Halt('Slot '+slot['slot_id']+': '+', '.join(analysis['halt_reasons']))
            if index<17: time.sleep(settings['pacing_seconds'])
        summary['status']='collection_complete'
    except Halt as e:
        summary['status']='halted' if summary['generation_requests_attempted'] else 'preflight_blocked'
        summary['errors'].append(str(e))
    except Exception as e:
        summary['status']='execution_error'
        # No exception message is logged from an unexpected network/library failure.
        summary['errors'].append(type(e).__name__+'; inspect local stage records; no automatic retry')
    finally:
        if not summary.get('frozen'):
            save_json(run/'preflight-manifest.json',{'frozen':False,'status':'blocked_or_preflight_only','created_utc':now(),
                'input_sha256':hashes,'settings':settings,'current_commit':summary.get('git_commit'),'errors':summary['errors'],
                'note':'Not a completed freeze: no model-access/token-count success or generation is claimed.'})
        # Score after collection completes or halts, never feed scores into generation.
        for slot in summary['slots']:
            candidate=run/'slots'/slot['slot_id']/'candidate.txt'
            if not candidate.exists(): continue
            try:
                code,out,err=command(run,'score-'+slot['slot_id'],[sys.executable,str(run/'inputs/scripts/score_candidate.py'),slot['task'],str(candidate),'--output-parent',str(run/'scoring'/slot['slot_id'])])
                records=list((run/'scoring'/slot['slot_id']).glob('*/summary.json'))
                slot['score']={'exit_code':code,'record':str(records[0].relative_to(run)) if len(records)==1 else None,
                               'outcomes':json.loads(records[0].read_text())['outcomes'] if len(records)==1 else None}
            except Exception as e:
                slot['score']={'exit_code':None,'error':type(e).__name__,'outcomes':None}
        for slot in summary['slots']:
            if slot['status']=='not_attempted': slot['not_attempted_reason']=summary['status']
            elif slot['status']=='attempted_before_dispatch':
                slot['status']='completion_unknown_after_interruption'
                if slot['slot_id'] not in summary['unknown_cost_slots']: summary['unknown_cost_slots'].append(slot['slot_id'])
        summary['finished_utc']=now(); persist(); inventory(run)
        try: backup_now(); backup_ok=True
        except Exception: backup_ok=False
        # Store backup audit outside the immutable run inventory; both copies can verify it.
        audit={'run':str(run),'backup':str(backup),'backup_verified':backup_ok,'checked_utc':now()}
        auditpath=ROOT/'results/collection'/(stamp+'.backup.json'); save_json(auditpath,audit)
        print(json.dumps({'run_directory':str(run),'status':summary['status'],'attempted_generations':summary['generation_requests_attempted'],'errors':summary['errors'],'backup_verified':backup_ok},indent=2),flush=True)
    return 0 if summary['status']=='collection_complete' and backup_ok else 2
if __name__=='__main__': sys.exit(main())
