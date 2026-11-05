"""Regression tests for the evidence classifier; no Docker or model API needed."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from classify_stage2 import EvidenceError, analyze, classify, parse_alerts, parse_failures

class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.alert={'labels':{'alertname':'Example','service':'api'},'annotations':{}}
        self.required=['alertname','service']
        self.fixed={'alertname':'Example'}

    def test_annotation_is_only_metadata(self):
        actual={'labels':dict(self.alert['labels']),'annotations':{'summary':'constant'}}
        self.assertEqual(classify([self.alert],[actual],self.required,self.fixed),['metadata_only'])

    def test_missing_environment_is_identity_not_detection(self):
        expected={'labels':{**self.alert['labels'],'environment':'production'},'annotations':{}}
        self.assertEqual(classify([expected],[self.alert],self.required+['environment'],{**self.fixed,'environment':'production'}),['required_identity'])

    def test_instance_labels_not_normalized_away(self):
        actual=[{'labels':{**self.alert['labels'],'instance':name},'annotations':{}} for name in ['a','b']]
        self.assertEqual(classify([self.alert],actual,self.required,self.fixed),['extra_alert','grouping','required_identity'])

    def test_missing_alert(self):
        self.assertEqual(classify([self.alert],[],self.required,self.fixed),['missing_alert'])

    def test_comma_separated_multiple_alerts(self):
        raw='''[0: Labels:{alertname="Example", instance="a", service="api"} Annotations:{},
                1: Labels:{alertname="Example", instance="b", service="api"} Annotations:{}]'''
        alerts=parse_alerts(raw)
        self.assertEqual(len(alerts),2)
        self.assertEqual(alerts[1]['labels']['instance'],'b')
        self.assertEqual(classify([self.alert],alerts,self.required,self.fixed),['extra_alert','grouping','required_identity'])

    def test_malformed_separator_is_not_ignored(self):
        with self.assertRaises(EvidenceError):
            parse_alerts('[0: Labels:{} Annotations:{} ERROR 1: Labels:{} Annotations:{}]')

    def test_staging_is_extra_and_wrong_identity(self):
        actual={'labels':{**self.alert['labels'],'environment':'staging'},'annotations':{}}
        self.assertEqual(classify([], [actual], self.required+['environment'], {**self.fixed,'environment':'production'}),['extra_alert','required_identity'])

    def test_loader_error_not_a_detected_defect(self):
        for text in ['FAILED: error loading rules', 'yaml: parse error', 'FAILED:\nname: x,\nalertname: Example, time: 1m,\nexp:[], got:[']:
            with self.assertRaises(EvidenceError): parse_failures(text)

    def test_metadata_analysis_has_no_timing_or_threshold_targets(self):
        suite={'tests':[{'name':'case','alert_rule_test':[{'eval_time':'3m','alertname':'Example','exp_alerts':[{'exp_labels':{'service':'api'},'exp_annotations':{}}]}]}]}
        stderr='''  FAILED:
    name: case,
    alertname: Example, time: 3m,
        exp:[0: Labels:{alertname="Example", service="api"} Annotations:{}],
        got:[0: Labels:{alertname="Example", service="api"} Annotations:{summary="constant"}]
'''
        result=analyze(suite,{'targeted_obligations':['timing','threshold']},{'alertname':'Example','required_labels':self.required},1,'',stderr)
        self.assertTrue(result['metadata_only_failure'])
        self.assertTrue(result['detection_and_timing_pass'])
        self.assertEqual(result['targeted_obligation_counts'],{})

if __name__=='__main__': unittest.main()
