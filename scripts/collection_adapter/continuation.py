"""Continuation-only policy; original collection/extraction/scoring code is unchanged."""
from contextlib import contextmanager
from decimal import Decimal
import fcntl
import json
from pathlib import Path
from .core import save_json, sha, now

ALLOWED=('R04-G02','R05-G02','R06-G02','R01-G03','R02-G03','R03-G03','R04-G03','R05-G03','R06-G03')
UNKNOWN='R03-G02'

class Stop(RuntimeError): pass

def reject_prior_continuation(control):
    control=Path(control)
    if (control/'dispatch-v1.json').exists() or any((control/'attempts').glob('*.json')):
        raise Stop('Continuation dispatch history exists; no automatic resend or second continuation')

@contextmanager
def process_lock(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        try: fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise Stop('Another continuation process holds the process lock')
        try: yield
        finally: fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def eligible(original,slots,requested):
    if tuple(requested)!=ALLOWED: raise Stop('Only the nine amended slots in their exact order are authorized')
    by_id={s['slot_id']:s for s in slots}
    for sid in requested:
        s=by_id.get(sid)
        if s is None or s['status']!='not_attempted' or (Path(original)/'slots'/sid).exists():
            raise Stop('Completed or previously attempted slot refused: '+sid)

def claim(path,value):
    try: save_json(path,value)
    except FileExistsError: raise Stop('A previous continuation dispatch claim exists; no automatic resend or resume')

def exposure(known,unknown_count,remaining,per_slot):
    # Unknown requests consume the entire allowance until exact usage is known.
    total=Decimal(known)+per_slot*(unknown_count+remaining)
    if total>Decimal('5'): raise Stop('Combined pilot exposure exceeds the US$5 operational ceiling')
    return total

def verify_files(root,hashes):
    for name,h in hashes.items():
        p=Path(root)/name
        if not p.is_file() or p.is_symlink() or sha(p.read_bytes())!=h:
            raise Stop('Preserved or frozen file mismatch: '+name)

def verify_frozen(root,original,freeze):
    verify_files(Path(original)/'inputs',freeze['input_sha256'])
    selected={n:h for n,h in freeze['input_sha256'].items() if
        n.startswith(('requirements/','tests/stage2/','scripts/stage3a/','prompts/collection-draft/')) or
        n in {'STUDY_PLAN.md','requirements-stage3a.txt','prometheus-image.txt','tests/R01.test.yml',
              'scripts/score_candidate.py','scripts/collection_adapter/core.py','scripts/collection_adapter/workflow.py',
              'collection/settings.selected.json','collection/slots.json','COLLECTION_READINESS.md',
              'collection/COMMON_OUTPUT_CONTRACT.txt'}}
    verify_files(root,selected)
    for task,h in freeze['prepared_request_sha256'].items():
        if sha((Path(original)/'prepared-requests'/(task+'.json')).read_bytes())!=h:
            raise Stop('Original prepared request mismatch: '+task)
    return selected

def mark_uncertain(summary):
    for slot in summary['slots']:
        if slot['status']=='attempted_before_dispatch':
            slot['status']='completion_unknown_after_interruption'
            if slot['slot_id'] not in summary['unknown_cost_slots']:
                summary['unknown_cost_slots'].append(slot['slot_id'])

def dispatch_slot(run,control,slot,summary,transport,request,settings,pricing,persist,backup):
    # Per-slot exclusive claim and journal survive SIGKILL and forbid replay.
    from .core import recorded_exchange, inspect_response, save_new
    sid=slot['slot_id']
    if sid not in ALLOWED or slot['status']!='not_attempted': raise Stop('Ineligible dispatch: '+sid)
    event={'slot_id':sid,'run':str(run),'attempt_recorded_utc':now(),'no_resend':True}
    claim(Path(control)/'attempts'/(sid+'.json'),event)
    slot['status']='attempted_before_dispatch'; summary['generation_requests_attempted']+=1
    persist(); save_json(Path(run)/'dispatch-intents'/(sid+'.json'),event); backup()
    folder=Path(run)/'slots'/sid
    meta,raw=recorded_exchange(folder,transport,'POST','/v1/responses',request,'amended_continuation_generation',backup)
    analysis=inspect_response(meta,raw,settings,pricing)
    extracted=analysis.get('extraction') or {}
    if extracted.get('text_available'):
        data=extracted['text'].encode('utf-8'); save_new(folder/'candidate.txt',data)
        slot['candidate_sha256']=sha(data)
    save_json(folder/'analysis.json',analysis)
    slot['analysis']=analysis
    slot['response_id']=analysis.get('response_id')
    slot['provider_request_id']=meta.get('headers',{}).get('x-request-id')
    cost=(analysis.get('accounting') or {}).get('estimated_api_cost_usd')
    if cost is None: summary['unknown_cost_slots'].append(sid)
    else: summary['estimated_known_api_cost_usd']=str(Decimal(summary['estimated_known_api_cost_usd'])+Decimal(cost))
    slot['status']='halted_after_response' if analysis['halt_reasons'] else 'response_recorded'
    persist(); backup()
    if analysis['halt_reasons']: raise Stop('Slot '+sid+': '+', '.join(analysis['halt_reasons']))
