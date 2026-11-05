"""Strict pinned-promtool diagnostic parser and post-execution classification.

This never rewrites a candidate or its label set. Observed output symptoms are
separate from the catalog's known, deliberately targeted obligations.
"""
import collections
import json
import re

class EvidenceError(ValueError):
    pass

def canonical(alerts):
    return sorted(json.dumps(a, sort_keys=True) for a in alerts)

def parse_map(text):
    result = {}
    pattern = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("(?:[^"\\]|\\.)*")')
    position = 0
    for match in pattern.finditer(text):
        if text[position:match.start()].strip(' ,\n\t'):
            raise EvidenceError('Unrecognized label-map content')
        if match[1] in result:
            raise EvidenceError('Duplicate label in output')
        result[match[1]] = json.loads(match[2])
        position = match.end()
    if text[position:].strip(' ,\n\t'):
        raise EvidenceError('Unrecognized label-map suffix')
    return result

def parse_alerts(text):
    if not text.startswith('[') or not text.endswith(']'):
        raise EvidenceError('Expected alert list')
    body = text[1:-1]
    pattern = re.compile(r'(\d+):\s*Labels:\{([^}]*)\}\s*Annotations:\{([^}]*)\}', re.S)
    found = list(pattern.finditer(body))
    position = 0
    for index, match in enumerate(found):
        separator = body[position:match.start()]
        if (index == 0 and separator.strip()) or (index > 0 and not re.fullmatch(r'\s*,\s*', separator)):
            raise EvidenceError('Unrecognized alert-list separator')
        if int(match[1]) != index:
            raise EvidenceError('Nonsequential alert-list indices')
        position = match.end()
    if body[position:].strip():
        raise EvidenceError('Unrecognized alert-list diagnostic')
    return [{'labels': parse_map(m[2]), 'annotations': parse_map(m[3])} for m in found]

def parse_failures(stderr):
    """Fail closed on loader errors, unfamiliar output, or partial diagnostics."""
    text = stderr.strip()
    if not text.startswith('FAILED:'):
        raise EvidenceError('Nonzero exit without assertion diagnostics')
    text = text[len('FAILED:'):]
    head = re.compile(r'\s*name: ([^\n]+),\s*\n\s*alertname: ([^,\n]+), time: ([^,\n]+),\s*\n')
    matches = list(head.finditer(text))
    if not matches or text[:matches[0].start()].strip():
        raise EvidenceError('Missing or unrecognized assertion headers')
    failures = {}
    for index, match in enumerate(matches):
        end = matches[index+1].start() if index+1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        details = re.fullmatch(r'exp:(\[.*\]),\s*got:(\[.*\])', body, re.S)
        if not details:
            raise EvidenceError('Incomplete expected/actual assertion diagnostic')
        key = (match[1], match[3].strip())
        if key in failures:
            raise EvidenceError('Duplicate assertion diagnostic')
        failures[key] = {'alertname': match[2], 'expected': parse_alerts(details[1]), 'actual': parse_alerts(details[2])}
    return failures

def expected_alerts(case):
    return [{'labels': {'alertname':case['alertname'], **a['exp_labels']}, 'annotations':a.get('exp_annotations', {})} for a in case['exp_alerts']]

def classify(expected, actual, required_labels, fixed_labels):
    """Annotation-only differences cannot introduce detection or timing failures.

All identifying labels, including unexpected ones, remain available and are
checked. Pairing by service below is diagnostic only, never an acceptance test.
"""
    symptoms = set()
    for alert in actual:
        labels = alert['labels']
        if set(labels) != set(required_labels) or any(labels.get(k) != v for k,v in fixed_labels.items()):
            symptoms.add('required_identity')
    expected_groups = collections.defaultdict(list)
    actual_groups = collections.defaultdict(list)
    for a in expected: expected_groups[a['labels'].get('service')].append(a)
    for a in actual: actual_groups[a['labels'].get('service')].append(a)
    for service in set(expected_groups) | set(actual_groups):
        exp = expected_groups[service]; got = actual_groups[service]
        if len(exp) > len(got): symptoms.add('missing_alert')
        if len(got) > len(exp): symptoms.add('extra_alert')
        if len(got) > 1: symptoms.add('grouping')
        if len(exp) == len(got) == 1:
            if exp[0]['labels'] != got[0]['labels']:
                symptoms.add('required_identity')
            if exp[0]['annotations'] != got[0]['annotations']:
                symptoms.add('annotation_mismatch')
    if symptoms == {'annotation_mismatch'}:
        symptoms = {'metadata_only'}
    if canonical(expected) != canonical(actual) and not symptoms:
        raise EvidenceError('Unclassified output mismatch')
    return sorted(symptoms)

def analyze(suite, candidate, task, code, stdout, stderr):
    if code == 0:
        if 'SUCCESS' not in stdout or stderr.strip():
            raise EvidenceError('Unexpected successful-process output')
        failures = {}
    elif code == 1:
        if stdout.strip():
            raise EvidenceError('Unexpected stdout with failed assertions')
        failures = parse_failures(stderr)
    else:
        raise EvidenceError(f'Non-assertion process exit {code}')
    expected_keys = {(test['name'], case['eval_time']) for test in suite['tests'] for case in test['alert_rule_test']}
    if set(failures) - expected_keys:
        raise EvidenceError('Diagnostics reference an unknown scenario/time')
    scenarios = []
    for test in suite['tests']:
        assertions = []
        for case in test['alert_rule_test']:
            key = (test['name'], case['eval_time'])
            exp = expected_alerts(case)
            failure = failures.get(key)
            symptoms = []
            if failure:
                if failure['alertname'] != case['alertname'] or canonical(failure['expected']) != canonical(exp):
                    raise EvidenceError('Parsed expectation differs from immutable test input')
                fixed = {'alertname': task['alertname']}
                if 'environment' in task['required_labels']: fixed['environment'] = 'production'
                symptoms = classify(exp, failure['actual'], task['required_labels'], fixed)
            # These tags describe known mutation intent, not an inferred root cause.
            targeted = candidate['targeted_obligations'] if set(symptoms) & {'missing_alert','extra_alert','grouping'} else []
            assertions.append({'eval_time':case['eval_time'], 'strict_pass':not bool(failure), 'expected':exp, 'actual_from_failure_diagnostic': failure['actual'] if failure else None, 'evidence':'explicit_expected_actual_diagnostic' if failure else 'promtool_exact_assertion_pass', 'observed_symptoms':symptoms, 'targeted_obligations_for_detection_mismatch':targeted})
        scenarios.append({'name':test['name'], 'strict_pass':all(a['strict_pass'] for a in assertions), 'assertions':assertions})
    counts = collections.Counter(s for scenario in scenarios for a in scenario['assertions'] for s in a['observed_symptoms'])
    targets = collections.Counter(s for scenario in scenarios for a in scenario['assertions'] for s in a['targeted_obligations_for_detection_mismatch'])
    return {'scenarios':scenarios, 'failed_assertions':len(failures), 'observed_symptom_counts':dict(counts), 'targeted_obligation_counts':dict(targets), 'detection_and_timing_pass':not any(counts[k] for k in ['missing_alert','extra_alert','grouping']), 'required_identity_pass':not bool(counts['required_identity']), 'metadata_only_failure':bool(failures) and set(counts)=={'metadata_only'}}
