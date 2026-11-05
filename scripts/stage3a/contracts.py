"""Read-only contract inspection. Promtool remains the syntax authority."""
import yaml
import promql_parser as p

TASKS = {
 'R01': ('ServiceErrorRatioHigh', ['service_error_ratio']),
 'R02': ('ServiceLatencyHigh', ['service_latency_p95_seconds']),
 'R03': ('ServiceAnyInstanceErrorHigh', ['service_instance_error_ratio']),
 'R04': ('ServiceErrorRatioHighWithTraffic', ['service_error_ratio','service_requests_last_minute']),
 'R05': ('ProductionServiceErrorRatioHigh', ['service_error_ratio']),
 'R06': ('ServiceErrorRatioHighRetained', ['service_error_ratio']),
}
class FormatError(ValueError): pass
class LimitError(ValueError): pass
class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for k, v in node.value:
            key = self.construct_object(k, deep=deep)
            if not isinstance(key, str):
                raise FormatError('Mapping keys must be strings')
            if key in result:
                raise FormatError('Duplicate mapping key: '+key)
            result[key] = self.construct_object(v, deep=deep)
        return result

def load(raw):
    if len(raw) > 200_000: raise LimitError('Response exceeds 200000-byte inspection limit')
    try:
        text = raw.decode('utf-8')
        if not text.strip(): raise FormatError('Empty response')
        # Token/depth limits bound the safe loader; neither aliases nor input are rewritten.
        depth = count = 0
        for token in yaml.scan(text):
            count += 1
            if isinstance(token, (yaml.tokens.BlockMappingStartToken, yaml.tokens.BlockSequenceStartToken,
                                  yaml.tokens.FlowMappingStartToken, yaml.tokens.FlowSequenceStartToken)):
                depth += 1
            if isinstance(token, (yaml.tokens.BlockEndToken, yaml.tokens.FlowMappingEndToken, yaml.tokens.FlowSequenceEndToken)):
                depth -= 1
            if count > 20000 or depth > 60: raise LimitError('YAML complexity limit')
        value = yaml.load(text, Loader=UniqueLoader)
        if not isinstance(value, dict): raise FormatError('Expected one YAML mapping document')
        return value
    except (UnicodeDecodeError, yaml.YAMLError) as e:
        raise FormatError(str(e)) from e

def inspect_expression(expr, allowed):
    violations, limitations, metrics = [], [], set()
    try: tree = p.parse(str(expr))
    except (ValueError, TypeError) as e:
        return [], ['PromQL inspection parser could not parse expression: '+str(e)], []
    def visit(n):
        if isinstance(n, (p.MatrixSelector, p.SubqueryExpr)):
            violations.append('range_or_subquery')
        if isinstance(n, p.VectorSelector):
            if n.offset is not None: violations.append('offset')
            if n.at is not None: violations.append('noncurrent_observation_at_modifier')
            names = {n.name} if n.name else set()
            names |= {m.value for m in n.matchers.matchers if m.name == '__name__' and m.op == p.MatchOp.Equal}
            if n.matchers.or_matchers:
                limitations.append('OR selector matchers require manual contract review')
            if not names: limitations.append('Metric selector without exact metric name requires review')
            for name in names:
                metrics.add(name)
                if name not in allowed: violations.append('unsupplied_metric:'+name)
        if isinstance(n, p.Call):
            name = n.func.name
            if name in {'rate','irate','increase','delta','idelta','deriv','predict_linear','double_exponential_smoothing','holt_winters','changes','resets','timestamp','time','absent','absent_over_time'} or name.endswith('_over_time') or name.startswith('histogram_'):
                violations.append('prohibited_function:'+name)
            elif name not in {'abs','ceil','floor','round','clamp','clamp_min','clamp_max','exp','ln','log2','log10','sqrt','sgn','scalar','vector','label_replace','label_join','sort','sort_desc'}:
                limitations.append('Function needs direct-observation policy review:'+name)
        return True
    p.walk(tree, pre_visit=visit)
    return sorted(set(violations)), sorted(set(limitations)), sorted(metrics)

def inspect(document, task):
    name, metrics = TASKS[task]
    structural, identity, metadata, limits = [], [], [], []
    if set(document) != {'groups'}: structural.append('top_level_fields_must_be_groups_only')
    groups = document.get('groups')
    if not isinstance(groups, list):
        return dict(structural=['groups_must_be_list'], identity=[], metadata=[], limitations=[], metrics=[])
    if len(groups) != 1: structural.append('exactly_one_group_required')
    all_rules = []; observed_metrics = set()
    for group in groups:
        if not isinstance(group, dict): structural.append('group_must_be_mapping'); continue
        if set(group) - {'name','interval','rules','labels'}: structural.append('unsupported_group_fields')
        try: interval_ok = p.parse_duration(str(group.get('interval'))).total_seconds() == 60
        except ValueError: interval_ok = False
        if not interval_ok: structural.append('explicit_one_minute_group_interval_required')
        rules = group.get('rules')
        if not isinstance(rules, list): structural.append('rules_must_be_list'); continue
        all_rules.extend(rules)
        for rule in rules:
            if not isinstance(rule, dict): structural.append('rule_must_be_mapping'); continue
            if set(rule) - {'alert','expr','for','keep_firing_for','labels','annotations'}: structural.append('unsupported_rule_fields')
            if rule.get('alert') != name:
                structural.append('required_alert_name'); identity.append('required_alert_name')
            if rule.get('annotations'): metadata.append('annotations_not_permitted')
            for obj in (group.get('labels', {}), rule.get('labels', {})):
                if isinstance(obj, dict):
                    permitted = {'service'} | ({'environment'} if task=='R05' else set())
                    if set(obj)-permitted: identity.append('additional_label_declaration')
            for obj in (rule.get('labels', {}), rule.get('annotations', {}), group.get('labels', {})):
                if isinstance(obj, dict) and any('{{' in str(v) and 'query' in str(v) for v in obj.values()):
                    limits.append('Template query requires manual supplied-metric inspection')
            v,l,m = inspect_expression(rule.get('expr',''), metrics)
            structural.extend(v); limits.extend(l); observed_metrics.update(m)
    if len(all_rules) != 1: structural.append('exactly_one_alert_rule_required')
    if not any(isinstance(r, dict) and r.get('alert') == name for r in all_rules):
        identity.append('required_alert_name_absent')
    if not limits:
        structural.extend('required_metric_not_used:'+m for m in sorted(set(metrics)-observed_metrics))
    return dict(structural=sorted(set(structural)), identity=sorted(set(identity)),
                metadata=sorted(set(metadata)), limitations=sorted(set(limits)), metrics=sorted(observed_metrics))
