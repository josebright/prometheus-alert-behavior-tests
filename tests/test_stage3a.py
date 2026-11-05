"""Scorer tests: adversarial diagnostics, contracts, safe duplicate detection."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from stage3a.contracts import load, inspect_expression, inspect, FormatError
from stage3a.diagnostics import Reader, parse, DiagnosticError, symptoms, analyze

class ScorerTests(unittest.TestCase):
    def test_inconsistent_failure_never_passes(self):
        suite={'tests':[{'name':'x','alert_rule_test':[{'alertname':'A','eval_time':'0s','exp_alerts':[]}]}]}
        with self.assertRaises(DiagnosticError):
            analyze(suite,'R01','A',1,'','FAILED:\n name: x,\n alertname: A, time: 0s,\n exp:[], got:[]')
    def test_absent_rule_and_metric(self):
        no_rule=inspect({'groups':[{'name':'x','interval':'1m','rules':[]}]},'R01')
        self.assertIn('required_alert_name_absent',no_rule['identity'])
        no_metric=inspect({'groups':[{'name':'x','interval':'1m','rules':[{'alert':'ServiceErrorRatioHigh','expr':'vector(1)'}]}]},'R01')
        self.assertIn('required_metric_not_used:service_error_ratio',no_metric['structural'])
    def test_duplicate_nested_yaml_and_json(self):
        for raw in (b'groups:\n - name: a\n   name: b\n', b'{"groups":[{"name":"a","name":"b"}]}'):
            with self.assertRaises(FormatError): load(raw)
    def test_safe_tag_and_fences(self):
        for raw in (b'!!python/object/apply:os.system [false]',b'```yaml\ngroups: []\n```',b'\xff',b'---\ngroups: []\n---\ngroups: []'):
            with self.assertRaises(FormatError): load(raw)
    def test_yaml_and_json(self):
        self.assertEqual(load(b'groups: []'),load(b'{"groups": []}'))
    def test_quoted_diagnostic(self):
        value='brace } { got:[; "quote" and \\ backslash\nline'
        text='[{bad}]'  # Not interpreted as syntax inside a quoted annotation.
        r=Reader('[0: Labels:{alertname="A", service="api"} Annotations:{summary='+json.dumps(value+text)+'}]')
        self.assertEqual(r.alerts()[0]['annotations']['summary'],value+text)
    def test_go_escapes(self):
        self.assertEqual(Reader(r'"\a\x41\u0042\U00000043\101"').quoted(),'\aABCA')
    def test_fail_closed(self):
        for text in ('FAILED:', 'FAILED: garbage', 'SUCCESS', 'FAILED: rule: x, time: 0s, err: error\nunknown'):
            with self.assertRaises(DiagnosticError): parse(text)
        with self.assertRaises(DiagnosticError): analyze({'tests':[]},'R01','A',0,'SUCCESS plus mystery','')
    def test_annotation_not_detection(self):
        exp=[{'labels':{'alertname':'A','service':'api'},'annotations':{}}]
        got=[{'labels':{'alertname':'A','service':'api'},'annotations':{'x':'{}"'}}]
        self.assertEqual(symptoms(exp,got,'R01','A'),['metadata_only'])
    def test_missing_service_identity_is_ambiguous(self):
        exp=[{'labels':{'alertname':'A','service':'api'},'annotations':{}}]
        got=[{'labels':{'alertname':'A'},'annotations':{}}]
        self.assertEqual(symptoms(exp,got,'R01','A'),['required_identity','service_attribution_unevaluable'])
    def test_prohibited_constructs(self):
        for expr in ('rate(service_error_ratio[1m])','service_error_ratio offset 1m','service_error_ratio @ 100','max_over_time(service_error_ratio[2m:1m])','other_metric','{__name__="other_metric"}'):
            v,l,m=inspect_expression(expr,['service_error_ratio']); self.assertTrue(v,expr)
    def test_alternative_expression_and_named_selector(self):
        for expr in ('0.05 < service_error_ratio','{__name__="service_error_ratio"} > 0.05'):
            v,l,m=inspect_expression(expr,['service_error_ratio']); self.assertFalse(v+l)
    def test_unbounded_metric_selector_needs_review(self):
        v,l,m=inspect_expression('{__name__=~".+"}',['service_error_ratio']); self.assertTrue(l)
    def test_extra_rule_not_hidden(self):
        rule={'alert':'ServiceErrorRatioHigh','expr':'service_error_ratio > .05'}
        result=inspect({'groups':[{'name':'a','interval':'1m','rules':[rule,rule]}]},'R01')
        self.assertIn('exactly_one_alert_rule_required',result['structural'])
    def test_evaluation_error_never_implies_pass(self):
        suite={'tests':[{'name':'x','alert_rule_test':[{'alertname':'A','eval_time':'0s','exp_alerts':[]}]}]}
        a=analyze(suite,'R01','A',1,'\n','FAILED:\n rule: A, time: 0s, err: duplicate series\n')
        self.assertEqual(a['behavioral'],'unevaluable')
        self.assertEqual(a['scenarios'][0]['assertions'][0]['status'],'unevaluable_due_to_evaluation_error')
if __name__=='__main__': unittest.main()
