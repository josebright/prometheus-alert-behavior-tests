#!/usr/bin/env python3
"""Compile the reviewed literal scenario tables; no inferred firing oracle."""
import copy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    'R02': ('ServiceLatencyHigh', 'service_latency_p95_seconds', 'service_latency_p95_seconds > 0.5', '3m'),
    'R03': ('ServiceAnyInstanceErrorHigh', 'service_instance_error_ratio', 'max by (service) (service_instance_error_ratio) > 0.05', '2m'),
    'R04': ('ServiceErrorRatioHighWithTraffic', 'service_error_ratio', '(service_error_ratio > 0.05) and on (service) (service_requests_last_minute >= 100)', '2m'),
    'R05': ('ProductionServiceErrorRatioHigh', 'service_error_ratio', 'service_error_ratio{environment="production"} > 0.05', '2m'),
    'R06': ('ServiceErrorRatioHighRetained', 'service_error_ratio', 'service_error_ratio > 0.05', '2m'),
}

def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')

def labels(task, identity):
    pieces = identity.split('/')
    result = {'service': pieces[0]}
    if task == 'R05':
        result['environment'] = {'P': 'production', 'S': 'staging'}[pieces[1]]
    elif task == 'R03' and len(pieces) == 2:
        result['instance'] = pieces[1]
    return result

def series(metric, identity, values, task):
    label_text = ','.join(k+'='+json.dumps(v) for k,v in labels(task, identity).items())
    return {'series': metric+'{'+label_text+'}', 'values': ' '.join(values)}

def compile_suite(task):
    name, metric, _, _ = TASKS[task]
    text = (ROOT/f'requirements/{task}.md').read_text()
    section = text.split('## Review-only scenarios', 1)[1]
    rows = [line for line in section.splitlines() if line.startswith('|')][2:]
    tests = []
    for row in rows:
        title, inputs, expectations = [cell.strip() for cell in row.strip('|').split('|')]
        supplied = []
        lengths = set()
        for item in inputs.split(';'):
            identity, values = item.strip().split(':', 1)
            if task == 'R04':
                pairs = re.findall(r'\(([^,]+),([^\)]+)\)', values)
                assert pairs and re.sub(r'\([^\)]+\)', '', values).strip() == ''
                for column, met in enumerate([metric, 'service_requests_last_minute']):
                    supplied.append(series(met, identity, [p[column].strip() for p in pairs], task))
                lengths.add(len(pairs))
            else:
                values = values.split()
                for value in values: float(value)
                lengths.add(len(values))
                supplied.append(series(metric, identity, values, task))
        assert len(lengths) == 1, title
        length = lengths.pop()
        by_time = {}
        for clause in expectations.split(';'):
            span, output = clause.strip().split(':', 1)
            match = re.fullmatch(r'(\d+)(?:–(\d+))?m', span)
            assert match, span
            start = int(match[1]); end = int(match[2] or match[1])
            output = output.strip().removesuffix(' only').removesuffix(' exactly once')
            alerts = [] if output == 'none' else [{'exp_labels': labels(task, identity.strip()), 'exp_annotations': {}} for identity in output.split(' and ')]
            for minute in range(start, end+1):
                assert minute not in by_time, (title, minute)
                by_time[minute] = {'eval_time': f'{minute}m', 'alertname': name, 'exp_alerts': copy.deepcopy(alerts)}
        assert set(by_time) == set(range(length)), (title, length, sorted(by_time))
        tests.append({'name': title, 'interval': '1m', 'input_series': supplied, 'alert_rule_test': [by_time[t] for t in range(length)]})
    return {'rule_files': ['rule.yml'], 'evaluation_interval': '1m', 'tests': tests}, rows

def build():
    catalog = {'notice': 'Synthetic infrastructure validation, not sampled model outputs.', 'tasks': {}, 'candidates': []}
    for task, (name, metric, expression, wait) in TASKS.items():
        suite, rows = compile_suite(task)
        dump(ROOT/f'tests/stage2/{task}.test.yml', suite)
        catalog['tasks'][task] = {'alertname': name, 'required_labels': ['alertname','service'] + (['environment'] if task == 'R05' else []), 'scenario_rows': rows, 'scenarios': len(suite['tests']), 'assertions': sum(len(t['alert_rule_test']) for t in suite['tests'])}
        ref = {'groups': [{'name': task, 'interval': '1m', 'rules': [{'alert': name, 'expr': expression, 'for': wait}]}]}
        if task == 'R06': ref['groups'][0]['rules'][0]['keep_firing_for'] = '3m'
        def candidate(variant, changes, targets, description, kind='mutation'):
            obj = copy.deepcopy(ref); rule = obj['groups'][0]['rules'][0]
            for key,value in changes.items():
                if value is None: rule.pop(key, None)
                else: rule[key] = value
            path = f'rules/stage2/{task}/{variant}.yml'
            dump(ROOT/path, obj)
            catalog['candidates'].append({'id': task+'-'+variant, 'task': task, 'kind': kind, 'path': path, 'targeted_obligations': targets, 'description': description})
        candidate('reference', {}, [], 'Reference for the reviewed requirement.', 'reference')
        if task == 'R02':
            candidate('threshold_500', {'expr': 'service_latency_p95_seconds > 500'}, ['threshold'], 'Mistakes the 500 ms threshold for 500 seconds.')
            candidate('wait_2m', {'for': '2m'}, ['timing'], 'Waits two instead of three minutes.')
            candidate('extra_annotation', {'annotations': {'summary': 'Constant review annotation'}}, [], 'Reference with only one extra constant annotation.', 'metadata_control')
        elif task == 'R03':
            candidate('average', {'expr': 'avg by (service) (service_instance_error_ratio) > 0.05'}, ['grouping','threshold'], 'Uses an average rather than any-instance condition.')
            candidate('retained_instance', {'expr': 'max by (service, instance) (service_instance_error_ratio) > 0.05'}, ['grouping','timing'], 'Retains each instance as a separate alert identity and waiting timer.')
            candidate('instance_handoff_reset', {'expr': 'topk by (service) (1, service_instance_error_ratio) > 0.05'}, ['timing','grouping'], 'Selects one breaching instance per service but keeps its instance identity; handoff restarts the wait. Also violates output-label contract.')
        elif task == 'R04':
            candidate('or', {'expr': expression.replace(' and ', ' or ')}, ['threshold'], 'Either metric can trigger instead of requiring their conjunction.')
            candidate('volume_strict', {'expr': expression.replace('>= 100', '> 100')}, ['threshold'], 'Excludes the required inclusive volume boundary.')
            candidate('cross_service', {'expr': expression.replace('on (service)', 'on ()')}, ['grouping'], 'Any qualifying volume series can enable a different service.')
        elif task == 'R05':
            candidate('no_filter', {'expr': 'service_error_ratio > 0.05'}, ['grouping','threshold'], 'Allows staging to fire.')
            candidate('no_environment_label', {'expr': 'max by (service) (service_error_ratio{environment="production"}) > 0.05'}, [], 'Removes the required environment label from production alerts.')
        elif task == 'R06':
            candidate('no_retention', {'keep_firing_for': None}, ['recovery'], 'Clears immediately without retention.')
            candidate('retention_1m', {'keep_firing_for': '1m'}, ['recovery'], 'Retains for one instead of three minutes.')
            candidate('no_initial_wait', {'for': None}, ['timing'], 'Fires immediately, including on a brief spike.')
    dump(ROOT/'tests/stage2/catalog.json', catalog)
    return catalog

if __name__ == '__main__':
    c = build()
    print(json.dumps({k: {'scenarios':v['scenarios'], 'assertions':v['assertions']} for k,v in c['tasks'].items()}, indent=2))
