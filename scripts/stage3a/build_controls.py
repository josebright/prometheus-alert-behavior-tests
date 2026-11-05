#!/usr/bin/env python3
"""Create labelled infrastructure controls before validation; never model outputs."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stage3a.contracts import load
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'controls/stage3a'

def main():
    manifest=[]
    def add(cid,task,raw,description,expect):
        path=DEST/(cid+'.yml')
        if path.exists(): raise SystemExit('Refusing to overwrite control '+cid)
        path.write_bytes(raw)
        manifest.append(dict(id=cid,task=task,path=str(path.relative_to(ROOT)),kind='infrastructure_control',description=description,expected=expect))
    def encode(obj): return (json.dumps(obj,indent=2)+'\n').encode()
    refs={}
    for task in ('R01','R02','R03','R04','R05','R06'):
        path=ROOT/('rules/reference.yml' if task=='R01' else f'rules/stage2/{task}/reference.yml')
        raw=path.read_bytes(); refs[task]=load(raw)
        add(task+'_reference',task,raw,'Unchanged reference; ordinary YAML for R01, JSON YAML for R02–R06',{'exit_code':0,'overall':'pass','behavior_execution':'pass'})
    def variant(cid,task,description,change,expect):
        obj=copy.deepcopy(refs[task]); change(obj,obj['groups'][0],obj['groups'][0]['rules'][0]); add(cid,task,encode(obj),description,expect)
    fail={'exit_code':1,'overall':'candidate_failure'}
    variant('equivalent','R01','Equivalent expression without matching reference text',lambda d,g,r:r.update(expr='0.05 < service_error_ratio'),{'exit_code':0,'overall':'pass'})
    variant('interval_60s','R01','Equivalent one-minute duration spelling',lambda d,g,r:g.update(interval='60s'),{'exit_code':0,'overall':'pass'})
    for cid,raw,desc in [
        ('malformed',b'groups: [\n','Malformed YAML'),
        ('duplicate_yaml',b'groups: []\ngroups: []\n','Duplicate YAML mapping key'),
        ('duplicate_json',b'{"groups": [], "groups": []}\n','Duplicate JSON mapping key'),
        ('fenced',b'```yaml\n'+(ROOT/'rules/reference.yml').read_bytes()+b'```\n','Markdown-fenced valid inner YAML, left unedited'),
        ('unsafe_tag',b'!!python/object/apply:os.system ["false"]\n','Unsafe constructor tag; must never execute'),
        ('empty',b'','Empty original response')]:
        add(cid,'R01',raw,desc,{**fail,'response_format':'fail'})
    variant('wrong_name','R01','Wrong alert name',lambda d,g,r:r.update(alert='WrongName'),{**fail,'syntax':'pass','structural_contract':'fail','required_identity':'fail','behavioral':'fail'})
    variant('extra_rule','R01','Extra alert invisible to expected-name firing assertions',lambda d,g,r:g['rules'].append(dict(alert='ExtraAlert',expr='service_error_ratio > 0')),{**fail,'syntax':'pass','structural_contract':'fail','behavior_execution':'pass','behavioral':'pass'})
    for cid,value in [('annotation','constant explanation'),('annotation_braces_quotes','brace {x} and [got: {y}], quote "quoted"; literal backslash \\ and newline\nnext')]:
        variant(cid,'R01','Extra constant annotation, metadata only',lambda d,g,r,v=value:r.update(annotations={'summary':v}),{**fail,'syntax':'pass','metadata':'fail','behavioral':'pass','required_identity':'pass','only_symptoms':['metadata_only']})
    variant('missing_service','R01','Aggregation removes required service identity',lambda d,g,r:r.update(expr='sum(service_error_ratio) > 0.05'),{**fail,'syntax':'pass','required_identity':'fail','behavioral':'unevaluable_identity'})
    variant('extra_label','R01','Extra constant label; never removed before execution',lambda d,g,r:r.update(labels={'severity':'warning'}),{**fail,'required_identity':'fail','behavioral':'pass'})
    variant('wrong_interval','R01','Explicit group interval violates one-minute contract',lambda d,g,r:g.update(interval='2m'),{**fail,'syntax':'pass','structural_contract':'fail'})
    variant('wrong_metric','R01','Unsupplied metric selected',lambda d,g,r:r.update(expr='other_metric > 0.05'),{**fail,'syntax':'pass','structural_contract':'fail','behavioral':'fail'})
    variant('rate','R01','Prohibited gauge rate and range',lambda d,g,r:r.update(expr='rate(service_error_ratio[2m]) > 0.05'),{**fail,'syntax':'pass','structural_contract':'fail'})
    variant('offset','R01','Prohibited offset',lambda d,g,r:r.update(expr='service_error_ratio offset 1m > 0.05'),{**fail,'syntax':'pass','structural_contract':'fail'})
    variant('evaluation_error','R04','Legal expression with ambiguous many-to-many matching at evaluation',lambda d,g,r:r.update(expr='(service_error_ratio + on() service_requests_last_minute) > 0'),{**fail,'syntax':'pass','behavior_execution':'candidate_evaluation_failure','behavioral':'unevaluable'})
    variant('no_rules','R01','Missing required alert rule',lambda d,g,r:g['rules'].clear(),{**fail,'syntax':'pass','structural_contract':'fail','required_identity':'fail'})
    variant('constant_expression','R01','Expression does not use the supplied metric',lambda d,g,r:r.update(expr='vector(1)'),{**fail,'syntax':'pass','structural_contract':'fail','behavioral':'fail'})
    # Copy existing mutations exactly, with expected observed outcomes, no target tags.
    # Resolve from the existing catalog rather than guessing historical filenames.
    catalog=json.loads((ROOT/'tests/stage2/catalog.json').read_text())
    selected=[('R01','rules/mutations/no_for.yml'),('R01','rules/mutations/inclusive.yml')]+[(c['task'],c['path']) for c in catalog['candidates'] if c['kind']=='mutation']
    for task,path in selected:
        cid='mutation_'+task+'_'+Path(path).stem
        exp={**fail,'syntax':'pass','behavior_execution':'assertion_failure'}
        if 'no_environment_label' in path: exp.update(required_identity='fail',behavioral='pass')
        add(cid,task,(ROOT/path).read_bytes(),'Exact copy of deliberate existing mutation '+path,exp)
    (DEST/'manifest.json').write_text(json.dumps({'notice':'Synthetic infrastructure controls, not model responses or model-performance evidence. Expected outcomes fixed before execution.','controls':manifest},indent=2)+'\n')
    print('Created',len(manifest),'controls')
if __name__=='__main__': main()
