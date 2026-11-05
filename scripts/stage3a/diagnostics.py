"""Fail-closed parser for pinned promtool's Go-quoted assertion diagnostics."""
import collections
import json
import re

class DiagnosticError(ValueError): pass

def canonical(alerts): return sorted(json.dumps(a, sort_keys=True) for a in alerts)

class Reader:
    def __init__(self, text): self.text, self.pos = text, 0
    def ws(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace(): self.pos += 1
    def take(self, value):
        self.ws()
        if not self.text.startswith(value, self.pos): raise DiagnosticError('Expected '+repr(value)+' at '+str(self.pos))
        self.pos += len(value)
    def match(self, pattern):
        self.ws(); m = re.compile(pattern).match(self.text, self.pos)
        if not m: raise DiagnosticError('Unrecognized diagnostic at '+str(self.pos))
        self.pos = m.end(); return m
    def peek(self, value): self.ws(); return self.text.startswith(value, self.pos)
    def quoted(self):
        self.take('"'); result = ''
        escapes = {'a':'\a','b':'\b','f':'\f','n':'\n','r':'\r','t':'\t','v':'\v','\\':'\\','"':'"'}
        while self.pos < len(self.text):
            ch = self.text[self.pos]; self.pos += 1
            if ch == '"': return result
            if ch != '\\': result += ch; continue
            if self.pos == len(self.text): break
            ch = self.text[self.pos]; self.pos += 1
            if ch in escapes: result += escapes[ch]
            elif ch in 'xuU' or ch in '01234567':
                size,base = (2,16) if ch=='x' else (4,16) if ch=='u' else (8,16) if ch=='U' else (2,8)
                digits = self.text[self.pos:self.pos+size]; self.pos += size
                if base == 8: digits = ch+digits
                try:
                    if len(digits) != (3 if base==8 else size): raise ValueError()
                    result += chr(int(digits,base))
                except ValueError as e: raise DiagnosticError('Invalid Go escape') from e
            else: raise DiagnosticError('Unknown Go escape')
        raise DiagnosticError('Unterminated quoted value')
    def mapping(self):
        self.take('{'); result = {}
        if self.peek('}'): self.take('}'); return result
        while True:
            key = self.quoted() if self.peek('"') else self.match(r'[A-Za-z_][A-Za-z0-9_]*')[0]
            self.take('='); value = self.quoted()
            if key in result: raise DiagnosticError('Duplicate diagnostic key')
            result[key] = value
            if self.peek('}'): self.take('}'); return result
            self.take(',')
    def alerts(self):
        self.take('['); result = []
        if self.peek(']'): self.take(']'); return result
        while True:
            index = int(self.match(r'\d+')[0])
            if index != len(result): raise DiagnosticError('Nonsequential alert index')
            self.take(':'); self.take('Labels:'); labels = self.mapping()
            self.take('Annotations:'); annotations = self.mapping()
            result.append(dict(labels=labels, annotations=annotations))
            if self.peek(']'): self.take(']'); return result
            self.take(',')

def parse(stderr):
    r = Reader(stderr); r.take('FAILED:'); failures = {}; evaluations = []
    while True:
        r.ws()
        if r.pos == len(r.text): break
        if r.peek('rule:'):
            m = r.match(r'rule: ([^\n]+?), time: ([^,\n]+), err: ([^\n]+)')
            evaluations.append({'rule':m[1], 'time':m[2], 'error':m[3]}); continue
        m = r.match(r'name: ([^\n]+),\s*\n\s*alertname: ([^,\n]+), time: ([^,\n]+),')
        r.take('exp:'); expected = r.alerts(); r.take(','); r.take('got:'); actual = r.alerts()
        key = (m[1], m[3])
        if key in failures: raise DiagnosticError('Duplicate assertion diagnostic')
        failures[key] = dict(alertname=m[2], expected=expected, actual=actual)
    if not failures and not evaluations: raise DiagnosticError('No failure evidence')
    return failures, evaluations

def symptoms(expected, actual, task, alertname):
    result = set(); keys = {'alertname','service'} | ({'environment'} if task=='R05' else set())
    for a in actual:
        labels = a['labels']
        if set(labels)!=keys or labels.get('alertname')!=alertname or (task=='R05' and labels.get('environment')!='production'):
            result.add('required_identity')
        if a['annotations']: result.add('metadata')
    # Pair by service for diagnostic counts only; never alter labels for execution.
    # A missing service identity makes per-service detection ambiguous, not a proven
    # missing+extra detection pair. Global cardinality remains directly observable.
    if any('service' not in a['labels'] for a in actual):
        result.add('service_attribution_unevaluable')
        if len(actual)<len(expected): result.add('missing_alert')
        if len(actual)>len(expected): result.add('extra_alert')
    else:
        exp = collections.Counter(a['labels'].get('service') for a in expected)
        got = collections.Counter(a['labels'].get('service') for a in actual)
        for service in set(exp)|set(got):
            if exp[service]>got[service]: result.add('missing_alert')
            if got[service]>exp[service]: result.add('extra_alert')
            if got[service]>1: result.add('grouping')
        # Wrong identities with unchanged service/cardinality are identity failures.
        if sorted(json.dumps(a['labels'],sort_keys=True) for a in expected)!=sorted(json.dumps(a['labels'],sort_keys=True) for a in actual) and exp==got:
            result.add('required_identity')
    if canonical(expected)!=canonical(actual) and not result: raise DiagnosticError('Unclassified mismatch')
    if result=={'metadata'}: return ['metadata_only']
    return sorted(result)

def analyze(suite, task, alertname, code, stdout, stderr):
    if code==0:
        if stdout.strip()!='SUCCESS' or stderr.strip(): raise DiagnosticError('Unexpected success diagnostics')
        failures, evaluations = {}, []
    elif code==1:
        if stdout.strip(): raise DiagnosticError('Unexpected failure stdout')
        failures, evaluations = parse(stderr)
    else: raise DiagnosticError('Unrecognized test process exit '+str(code))
    known = {(t['name'],c['eval_time']) for t in suite['tests'] for c in t['alert_rule_test']}
    if set(failures)-known: raise DiagnosticError('Unknown scenario or timestamp')
    scenarios = []; counts = collections.Counter()
    for t in suite['tests']:
        assertions = []
        for c in t['alert_rule_test']:
            expected = [dict(labels={'alertname':c['alertname'],**a['exp_labels']},annotations=a.get('exp_annotations',{})) for a in c['exp_alerts']]
            f = failures.get((t['name'],c['eval_time']))
            if f and canonical(f['expected'])==canonical(f['actual']):
                raise DiagnosticError('Failure diagnostic contains identical expected and actual sets')
            if f and (f['alertname']!=c['alertname'] or canonical(expected)!=canonical(f['expected'])):
                raise DiagnosticError('Diagnostic expectation does not match frozen fixture')
            observed = symptoms(expected,f['actual'],task,alertname) if f else []
            counts.update(observed)
            status = 'assertion_failure' if f else 'unevaluable_due_to_evaluation_error' if evaluations else 'pass'
            assertions.append(dict(eval_time=c['eval_time'],status=status,expected=expected,
                actual_from_diagnostic=f['actual'] if f else None,observed_symptoms=observed,
                evidence='explicit_failure_diagnostic' if f else 'no_pass_inference_after_evaluation_error' if evaluations else 'promtool_exact_assertion_pass'))
        scenarios.append(dict(name=t['name'],assertions=assertions))
    detection = any(counts[k] for k in ('missing_alert','extra_alert','grouping'))
    behavioral = 'unevaluable' if evaluations else 'fail' if detection else 'unevaluable_identity' if counts['service_attribution_unevaluable'] else 'pass'
    return dict(scenarios=scenarios,failed_assertions=len(failures),evaluation_errors=evaluations,
        observed_symptom_counts=dict(counts),behavioral=behavioral,
        required_identity='fail' if counts['required_identity'] else 'unevaluable' if evaluations else 'pass',
        metadata='fail' if counts['metadata'] or counts['metadata_only'] else 'unevaluable' if evaluations else 'pass')
