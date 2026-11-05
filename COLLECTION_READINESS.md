# Collection readiness — draft, not frozen

Prepared on 5 November 2026 (Africa/Lagos). **No model calls; no credential access; no push.**
One fixed model is planned, but its exact identifier, generation settings and budget remain unselected.
Collection is not authorized. Human review is still required.

## Readiness at a glance

| Item | State |
|---|---|
| Six standalone prompts | Exact texts below; raw files under `prompts/collection-draft/` |
| Plan and slots | `COLLECTION_PLAN.md`; `collection/slots.json`: 18 unattempted slots, three R01–R06 rounds |
| Preserved implementation | 66 validated input hashes match the successful Stage 3A run; 977 pre-existing files verified unchanged |
| Current commit | `c9f298e30478bba8de8fa43bcd60802aba0a2140` |
| Toolchain | Validated Python 3.14.6, PyYAML 6.0.3, promql-parser 0.11.0, promtool 3.15.1, Docker 29.8.2, linux/arm64 |
| Version evidence | Docker/promtool versions from the retained validation run; current Python/dependencies independently observed, no fresh Docker run |
| Uncommitted content | This plan/report, common contract, audit, pending settings, slots, preparation manifest, offline verifier and six ignored prompt files are new and uncommitted |
| Existing scorer/fixtures | No uncommitted changes; no requirement or expected outcome changed |
| Freeze | Blocked pending selections, adapter/extraction validation, prompt review and authorization |

Exact Prometheus pin:

`prom/prometheus@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2`

Full SHA-256 inventories, recorded versions and the explicit uncommitted-file list are in
[`collection/protocol-manifest.json`](collection/protocol-manifest.json). This is a preparation snapshot, not a freeze manifest.
Prompts remain gitignored; this report is a review copy and must never be attached to a generation request.

## Outstanding choices

- Provider, exact fixed model/snapshot (or disclosed alias limitation), endpoint/API and SDK version.
- Exact request envelope and response-text field mapping; validation of raw-payload capture and zero retries.
- Output-token cap, supported sampling/reasoning/verbosity settings, seed/stop policy, service tier and explicit/default settings.
- Timeouts/pacing, storage/cache policy, collection window and evidence backup/retention.
- Token allowances, monetary cap/currency, pricing basis/date, uncertain-charge reserve and explicit spending authorization.
- Human review of the exact prompts and support-limit disclosures; final committed/archived hashes and a new freeze record.

No numerical budget or model recommendation is inferred. `collection/settings.pending.json` uses null for unresolved selections, not defaults.
The inspector support limits are disclosed in the prompts and remain distinct from behavioural failures. See
[`collection/PROMPT_AUDIT.md`](collection/PROMPT_AUDIT.md) for source allowlisting and coverage.

Offline integrity check (does not call any model or execute Docker):

```sh
.venv-stage3a/bin/python scripts/check_collection_protocol.py
```

## Six exact generation prompts

Each block below is a byte-equivalent UTF-8 review copy of its `.txt` file, including its final newline.
Send only the selected file as the user message. The same bytes apply in all three rounds.

<details><summary>R01 — exact prompt (4855 bytes)</summary>

File: [prompts/collection-draft/R01.txt](prompts/collection-draft/R01.txt)

SHA-256: `72ff37feacd388ea833c3ab62937f3054714b49c54a16796e6278f4ef3797347`

```text
Implement requirement R01 as a Prometheus alert rule. The supplied observations are controlled synthetic inputs, not production telemetry.

Task requirement

Use service_error_ratio, a supplied gauge representing a unitless error-ratio fraction. Use it directly; do not apply rate(). Its complete ordinary input label schema is exactly service, a stable nonempty string, with one series per service. There are no other input or external labels. Values are finite and observations are complete before each evaluation.

Evaluate every minute, starting at minute zero with no pending or firing alerts. For each service independently, the ratio must be strictly greater than 0.05 at every evaluation for two elapsed minutes before the alert fires. Equality does not qualify. Any false evaluation before firing resets the waiting period; time before an interruption does not count toward the next waiting period. Clear a firing alert at the first evaluation where the ratio is at or below 0.05. No additional firing retention applies. Continuity means continuity at scheduled evaluations, without assumptions about unobserved changes between samples.

Required alert name: ServiceErrorRatioHigh. Emit exactly one alert per affected service. Its exact identifying output labels are alertname="ServiceErrorRatioHigh" and the original service value. No other output labels or annotations are permitted. Do not merge services.

Common output contract

Return only one complete UTF-8 Prometheus 3.15.1 rule file as raw YAML. JSON-formatted YAML is also acceptable. Do not include Markdown fences, surrounding prose, multiple documents, multiple alternatives, recording rules, imports, or external dependencies. Use standard safe YAML types, string mapping keys, and no duplicate keys, including collisions introduced by merges. The document must be a mapping with groups as its only top-level field.

Use exactly one named rule group, an explicit group interval equivalent to one minute, and exactly one alert rule with the required alert name. Supported group fields are name, interval, rules, and optional labels. Supported alert-rule fields are alert, expr, for, keep_firing_for, labels, and annotations; omit fields you do not need. No other fields are supported. Annotations must be absent or an empty mapping: no annotation entries are permitted, even constant ones. Any group/rule label declarations may use only service, plus environment for R05. They must preserve the required original identifying values. Do not declare alertname in a labels mapping; the alert field supplies that name. Do not add labels, including severity or instance. The identifying output labels specified for the task are exact; neither the input metric name nor alertstate belongs to that set.

Reference every supplied metric and no other metric. Use the supplied gauge observations directly at the current evaluation. Do not replace the required metric inputs with a constant expression. Do not compute rates, increases, histograms, additional window statistics, or missing-data behaviour. Do not use range selectors, subqueries, offset modifiers (including zero offsets), or @ modifiers. Alert persistence and any specified firing retention provide the required timing.

PromQL operators, matching, and aggregations may be used subject to the task's behaviour. If function calls are used, the automatically supported set is: abs, ceil, floor, round, clamp, clamp_min, clamp_max, exp, ln, log2, log10, sqrt, sgn, scalar, vector, label_replace, label_join, sort, sort_desc. In particular, rate, irate, increase, delta, idelta, deriv, predict_linear, double_exponential_smoothing, holt_winters, changes, resets, timestamp, time, absent, absent_over_time, all functions ending in _over_time, and all functions starting with histogram_ are prohibited. Other function calls require manual inspection and may be unevaluable; their absence from the supported set is not by itself a demonstrated behavioural defect.

For automatic inspection, each metric selector must identify its supplied metric by name or an exact __name__ equality matcher. Unbounded/regex-only metric-name selection, selector-level OR matcher extensions, and query calls inside label/annotation templates require manual review; avoid them. Selector-level OR matchers are distinct from ordinary PromQL binary operators. An expression accepted by Prometheus but unsupported by the independent inspection parser is reported as an inspection limitation, not automatically a behavioural failure.

Keep the response within 200,000 UTF-8 bytes, 20,000 YAML lexical tokens, and 60 mapping/sequence nesting levels. Exceeding these inspection limits makes scoring incomplete rather than establishing a behavioural defect. Any expression satisfying the full contract is acceptable; no particular expression text is required.
```

</details>

<details><summary>R02 — exact prompt (4941 bytes)</summary>

File: [prompts/collection-draft/R02.txt](prompts/collection-draft/R02.txt)

SHA-256: `1fa4caaea488e5ca3c6a4e175befdb4bbdafa98afa46ec7cb80a423f601eb671`

```text
Implement requirement R02 as a Prometheus alert rule. The supplied observations are controlled synthetic inputs, not production telemetry.

Task requirement

Use service_latency_p95_seconds, a gauge containing an already computed 95th-percentile request latency for the preceding one-minute observation window. Its unit is seconds; the threshold is 0.5 seconds (500 milliseconds). Values are finite and nonnegative. Use this supplied value directly; do not calculate a percentile, rate, increase, or new time-window statistic.

The complete ordinary input label schema is exactly service, a stable nonempty string. There is exactly one series per service, with no other input or external labels. A complete sample is available before every one-minute evaluation. Evaluate from minute zero with no pending or firing alerts. Continuity refers to scheduled evaluations, not unobserved changes between samples.

For each service, alert when latency is strictly greater than 0.5 seconds continuously at evaluations for three elapsed minutes. Equality does not qualify. A false evaluation before firing resets the waiting period. Clear a firing alert at the first evaluation at or below 0.5 seconds. No additional firing retention applies.

Required alert name: ServiceLatencyHigh. Emit exactly one alert per affected service, with exactly alertname="ServiceLatencyHigh" and the original service value as its identifying output labels. No additional labels or annotations are permitted. Do not merge services.

Common output contract

Return only one complete UTF-8 Prometheus 3.15.1 rule file as raw YAML. JSON-formatted YAML is also acceptable. Do not include Markdown fences, surrounding prose, multiple documents, multiple alternatives, recording rules, imports, or external dependencies. Use standard safe YAML types, string mapping keys, and no duplicate keys, including collisions introduced by merges. The document must be a mapping with groups as its only top-level field.

Use exactly one named rule group, an explicit group interval equivalent to one minute, and exactly one alert rule with the required alert name. Supported group fields are name, interval, rules, and optional labels. Supported alert-rule fields are alert, expr, for, keep_firing_for, labels, and annotations; omit fields you do not need. No other fields are supported. Annotations must be absent or an empty mapping: no annotation entries are permitted, even constant ones. Any group/rule label declarations may use only service, plus environment for R05. They must preserve the required original identifying values. Do not declare alertname in a labels mapping; the alert field supplies that name. Do not add labels, including severity or instance. The identifying output labels specified for the task are exact; neither the input metric name nor alertstate belongs to that set.

Reference every supplied metric and no other metric. Use the supplied gauge observations directly at the current evaluation. Do not replace the required metric inputs with a constant expression. Do not compute rates, increases, histograms, additional window statistics, or missing-data behaviour. Do not use range selectors, subqueries, offset modifiers (including zero offsets), or @ modifiers. Alert persistence and any specified firing retention provide the required timing.

PromQL operators, matching, and aggregations may be used subject to the task's behaviour. If function calls are used, the automatically supported set is: abs, ceil, floor, round, clamp, clamp_min, clamp_max, exp, ln, log2, log10, sqrt, sgn, scalar, vector, label_replace, label_join, sort, sort_desc. In particular, rate, irate, increase, delta, idelta, deriv, predict_linear, double_exponential_smoothing, holt_winters, changes, resets, timestamp, time, absent, absent_over_time, all functions ending in _over_time, and all functions starting with histogram_ are prohibited. Other function calls require manual inspection and may be unevaluable; their absence from the supported set is not by itself a demonstrated behavioural defect.

For automatic inspection, each metric selector must identify its supplied metric by name or an exact __name__ equality matcher. Unbounded/regex-only metric-name selection, selector-level OR matcher extensions, and query calls inside label/annotation templates require manual review; avoid them. Selector-level OR matchers are distinct from ordinary PromQL binary operators. An expression accepted by Prometheus but unsupported by the independent inspection parser is reported as an inspection limitation, not automatically a behavioural failure.

Keep the response within 200,000 UTF-8 bytes, 20,000 YAML lexical tokens, and 60 mapping/sequence nesting levels. Exceeding these inspection limits makes scoring incomplete rather than establishing a behavioural defect. Any expression satisfying the full contract is acceptable; no particular expression text is required.
```

</details>

<details><summary>R03 — exact prompt (5195 bytes)</summary>

File: [prompts/collection-draft/R03.txt](prompts/collection-draft/R03.txt)

SHA-256: `5d03a6ab34b5d47c88fe78c57830c1ff66a85e45c03f4a3b39f8926e9768b9c9`

```text
Implement requirement R03 as a Prometheus alert rule. The supplied observations are controlled synthetic inputs, not production telemetry.

Task requirement

Use service_instance_error_ratio, a supplied gauge measured as a unitless fraction in [0,1]. Its complete ordinary input label schema is exactly service and instance, both nonempty strings. One series exists per unique (service, instance) pair. Instance names need only be unique within a service. Every represented service has at least one instance. The series set and labels stay fixed, with no other input or external labels. Use the ratio directly without rate calculations.

Evaluate every minute from minute zero, initially with no pending or firing alerts. Every declared instance has a complete finite sample available before each evaluation. Continuity is defined at these evaluations.

For each service, the condition holds if at least one of its instances has an error ratio strictly greater than 0.05. Require this service-level condition to remain true for two elapsed minutes before firing. The breaching instance may change during the wait: continuity belongs to the service, not to a particular instance. Do not use an average or sum of instance ratios as the criterion. If all of a service's instances are at or below 0.05, reset a pending wait or immediately clear its firing alert. No additional retention applies.

Required alert name: ServiceAnyInstanceErrorHigh. Emit exactly one alert per affected service, even when multiple instances breach. Its exact identifying output labels are alertname="ServiceAnyInstanceErrorHigh" and the original service value. Remove instance from the alert identity. No additional labels or annotations are permitted. Services remain independent.

Common output contract

Return only one complete UTF-8 Prometheus 3.15.1 rule file as raw YAML. JSON-formatted YAML is also acceptable. Do not include Markdown fences, surrounding prose, multiple documents, multiple alternatives, recording rules, imports, or external dependencies. Use standard safe YAML types, string mapping keys, and no duplicate keys, including collisions introduced by merges. The document must be a mapping with groups as its only top-level field.

Use exactly one named rule group, an explicit group interval equivalent to one minute, and exactly one alert rule with the required alert name. Supported group fields are name, interval, rules, and optional labels. Supported alert-rule fields are alert, expr, for, keep_firing_for, labels, and annotations; omit fields you do not need. No other fields are supported. Annotations must be absent or an empty mapping: no annotation entries are permitted, even constant ones. Any group/rule label declarations may use only service, plus environment for R05. They must preserve the required original identifying values. Do not declare alertname in a labels mapping; the alert field supplies that name. Do not add labels, including severity or instance. The identifying output labels specified for the task are exact; neither the input metric name nor alertstate belongs to that set.

Reference every supplied metric and no other metric. Use the supplied gauge observations directly at the current evaluation. Do not replace the required metric inputs with a constant expression. Do not compute rates, increases, histograms, additional window statistics, or missing-data behaviour. Do not use range selectors, subqueries, offset modifiers (including zero offsets), or @ modifiers. Alert persistence and any specified firing retention provide the required timing.

PromQL operators, matching, and aggregations may be used subject to the task's behaviour. If function calls are used, the automatically supported set is: abs, ceil, floor, round, clamp, clamp_min, clamp_max, exp, ln, log2, log10, sqrt, sgn, scalar, vector, label_replace, label_join, sort, sort_desc. In particular, rate, irate, increase, delta, idelta, deriv, predict_linear, double_exponential_smoothing, holt_winters, changes, resets, timestamp, time, absent, absent_over_time, all functions ending in _over_time, and all functions starting with histogram_ are prohibited. Other function calls require manual inspection and may be unevaluable; their absence from the supported set is not by itself a demonstrated behavioural defect.

For automatic inspection, each metric selector must identify its supplied metric by name or an exact __name__ equality matcher. Unbounded/regex-only metric-name selection, selector-level OR matcher extensions, and query calls inside label/annotation templates require manual review; avoid them. Selector-level OR matchers are distinct from ordinary PromQL binary operators. An expression accepted by Prometheus but unsupported by the independent inspection parser is reported as an inspection limitation, not automatically a behavioural failure.

Keep the response within 200,000 UTF-8 bytes, 20,000 YAML lexical tokens, and 60 mapping/sequence nesting levels. Exceeding these inspection limits makes scoring incomplete rather than establishing a behavioural defect. Any expression satisfying the full contract is acceptable; no particular expression text is required.
```

</details>

<details><summary>R04 — exact prompt (5360 bytes)</summary>

File: [prompts/collection-draft/R04.txt](prompts/collection-draft/R04.txt)

SHA-256: `b5925971cb1bbc464e2524f6690a5b5c9a407c955b38d76c4605e29ea2343189`

```text
Implement requirement R04 as a Prometheus alert rule. The supplied observations are controlled synthetic inputs, not production telemetry.

Task requirement

Use both of these supplied metrics directly:
- service_error_ratio: a gauge containing a unitless fraction in [0,1]; its complete ordinary input label schema is exactly service.
- service_requests_last_minute: a gauge containing the nonnegative integer count of requests in the preceding one-minute window; its complete ordinary input label schema is exactly service.

The service label is a stable nonempty string. There is exactly one series of each metric per service, and the same service set for both metrics. No other input or external labels exist. The volume gauge is a refreshed window count that can rise or fall, not a cumulative counter or requests-per-second rate. Do not derive rates, increases, or window sums. The supplied error ratio is finite even when volume is zero; do not divide by volume or recompute the ratio.

Evaluate every minute from minute zero with complete synchronized observations available before every evaluation. Start with no pending or firing alerts. Continuity means continuity at these evaluations.

For the same service, require both error ratio strictly greater than 0.05 AND volume greater than or equal to 100 requests in the preceding minute. The conjunction must remain true for two elapsed minutes before firing. If either condition becomes false, reset a pending wait or clear a firing alert at that first false evaluation. No retention applies. Neither condition alone, nor conditions satisfied by different services, may trigger an alert.

Required alert name: ServiceErrorRatioHighWithTraffic. Emit exactly one alert per affected service, with exactly alertname="ServiceErrorRatioHighWithTraffic" and the original service value as its identifying output labels. No additional labels or annotations are permitted.

Common output contract

Return only one complete UTF-8 Prometheus 3.15.1 rule file as raw YAML. JSON-formatted YAML is also acceptable. Do not include Markdown fences, surrounding prose, multiple documents, multiple alternatives, recording rules, imports, or external dependencies. Use standard safe YAML types, string mapping keys, and no duplicate keys, including collisions introduced by merges. The document must be a mapping with groups as its only top-level field.

Use exactly one named rule group, an explicit group interval equivalent to one minute, and exactly one alert rule with the required alert name. Supported group fields are name, interval, rules, and optional labels. Supported alert-rule fields are alert, expr, for, keep_firing_for, labels, and annotations; omit fields you do not need. No other fields are supported. Annotations must be absent or an empty mapping: no annotation entries are permitted, even constant ones. Any group/rule label declarations may use only service, plus environment for R05. They must preserve the required original identifying values. Do not declare alertname in a labels mapping; the alert field supplies that name. Do not add labels, including severity or instance. The identifying output labels specified for the task are exact; neither the input metric name nor alertstate belongs to that set.

Reference every supplied metric and no other metric. Use the supplied gauge observations directly at the current evaluation. Do not replace the required metric inputs with a constant expression. Do not compute rates, increases, histograms, additional window statistics, or missing-data behaviour. Do not use range selectors, subqueries, offset modifiers (including zero offsets), or @ modifiers. Alert persistence and any specified firing retention provide the required timing.

PromQL operators, matching, and aggregations may be used subject to the task's behaviour. If function calls are used, the automatically supported set is: abs, ceil, floor, round, clamp, clamp_min, clamp_max, exp, ln, log2, log10, sqrt, sgn, scalar, vector, label_replace, label_join, sort, sort_desc. In particular, rate, irate, increase, delta, idelta, deriv, predict_linear, double_exponential_smoothing, holt_winters, changes, resets, timestamp, time, absent, absent_over_time, all functions ending in _over_time, and all functions starting with histogram_ are prohibited. Other function calls require manual inspection and may be unevaluable; their absence from the supported set is not by itself a demonstrated behavioural defect.

For automatic inspection, each metric selector must identify its supplied metric by name or an exact __name__ equality matcher. Unbounded/regex-only metric-name selection, selector-level OR matcher extensions, and query calls inside label/annotation templates require manual review; avoid them. Selector-level OR matchers are distinct from ordinary PromQL binary operators. An expression accepted by Prometheus but unsupported by the independent inspection parser is reported as an inspection limitation, not automatically a behavioural failure.

Keep the response within 200,000 UTF-8 bytes, 20,000 YAML lexical tokens, and 60 mapping/sequence nesting levels. Exceeding these inspection limits makes scoring incomplete rather than establishing a behavioural defect. Any expression satisfying the full contract is acceptable; no particular expression text is required.
```

</details>

<details><summary>R05 — exact prompt (5155 bytes)</summary>

File: [prompts/collection-draft/R05.txt](prompts/collection-draft/R05.txt)

SHA-256: `f1eb39db8bb939cb7ebab2f4be5e9612614aa65886ada258e5def0ef42324d17`

```text
Implement requirement R05 as a Prometheus alert rule. The supplied observations are controlled synthetic inputs, not production telemetry.

Task requirement

Use service_error_ratio, a supplied gauge measured as a unitless fraction in [0,1]. Its complete ordinary input label schema is exactly service (a nonempty string) and environment (exactly production or staging, case-sensitive). One series exists per declared (service, environment) pair. Both environments may use the same service name. The series set and labels stay fixed; no other input or external labels exist. This task is isolated from other task schemas. Use the ratio directly, without rate or other window calculations.

Evaluate every minute from minute zero. Each declared series has a complete finite sample available before every evaluation. Start with no pending or firing alerts. Continuity refers to scheduled observations.

Only series with environment="production" are eligible. For each eligible service, require the ratio to be strictly greater than 0.05 continuously for two elapsed minutes before firing. A production value at or below 0.05 resets a pending wait or immediately clears a firing alert. No additional retention applies. Staging values never start, prolong, reset, or clear a production alert and must never produce an alert themselves. Do not combine environments or different services.

Required alert name: ProductionServiceErrorRatioHigh. Emit exactly one alert per affected production service. Its exact identifying output labels are alertname="ProductionServiceErrorRatioHigh", the original service value, and environment="production". Retain the environment label. No additional labels or annotations are permitted.

Common output contract

Return only one complete UTF-8 Prometheus 3.15.1 rule file as raw YAML. JSON-formatted YAML is also acceptable. Do not include Markdown fences, surrounding prose, multiple documents, multiple alternatives, recording rules, imports, or external dependencies. Use standard safe YAML types, string mapping keys, and no duplicate keys, including collisions introduced by merges. The document must be a mapping with groups as its only top-level field.

Use exactly one named rule group, an explicit group interval equivalent to one minute, and exactly one alert rule with the required alert name. Supported group fields are name, interval, rules, and optional labels. Supported alert-rule fields are alert, expr, for, keep_firing_for, labels, and annotations; omit fields you do not need. No other fields are supported. Annotations must be absent or an empty mapping: no annotation entries are permitted, even constant ones. Any group/rule label declarations may use only service, plus environment for R05. They must preserve the required original identifying values. Do not declare alertname in a labels mapping; the alert field supplies that name. Do not add labels, including severity or instance. The identifying output labels specified for the task are exact; neither the input metric name nor alertstate belongs to that set.

Reference every supplied metric and no other metric. Use the supplied gauge observations directly at the current evaluation. Do not replace the required metric inputs with a constant expression. Do not compute rates, increases, histograms, additional window statistics, or missing-data behaviour. Do not use range selectors, subqueries, offset modifiers (including zero offsets), or @ modifiers. Alert persistence and any specified firing retention provide the required timing.

PromQL operators, matching, and aggregations may be used subject to the task's behaviour. If function calls are used, the automatically supported set is: abs, ceil, floor, round, clamp, clamp_min, clamp_max, exp, ln, log2, log10, sqrt, sgn, scalar, vector, label_replace, label_join, sort, sort_desc. In particular, rate, irate, increase, delta, idelta, deriv, predict_linear, double_exponential_smoothing, holt_winters, changes, resets, timestamp, time, absent, absent_over_time, all functions ending in _over_time, and all functions starting with histogram_ are prohibited. Other function calls require manual inspection and may be unevaluable; their absence from the supported set is not by itself a demonstrated behavioural defect.

For automatic inspection, each metric selector must identify its supplied metric by name or an exact __name__ equality matcher. Unbounded/regex-only metric-name selection, selector-level OR matcher extensions, and query calls inside label/annotation templates require manual review; avoid them. Selector-level OR matchers are distinct from ordinary PromQL binary operators. An expression accepted by Prometheus but unsupported by the independent inspection parser is reported as an inspection limitation, not automatically a behavioural failure.

Keep the response within 200,000 UTF-8 bytes, 20,000 YAML lexical tokens, and 60 mapping/sequence nesting levels. Exceeding these inspection limits makes scoring incomplete rather than establishing a behavioural defect. Any expression satisfying the full contract is acceptable; no particular expression text is required.
```

</details>

<details><summary>R06 — exact prompt (5625 bytes)</summary>

File: [prompts/collection-draft/R06.txt](prompts/collection-draft/R06.txt)

SHA-256: `2170d78b3522bc41dfd750a1a5e2c99dc62517ec28e1293b96c7843491bc5c9d`

```text
Implement requirement R06 as a Prometheus alert rule. The supplied observations are controlled synthetic inputs, not production telemetry.

Task requirement

Use service_error_ratio, a supplied gauge containing a unitless fraction in [0,1]. Its complete ordinary input label schema is exactly service, a stable nonempty string, with one series per service and no other input or external labels. Use the ratio directly, without rate calculations.

Evaluate every minute from minute zero. Complete finite observations are available before each evaluation. Start with no pending or firing alerts. Continuity refers to scheduled evaluations.

For each service, require a ratio strictly greater than 0.05 continuously for two elapsed minutes before initially firing. A value at or below 0.05 before firing resets the wait. A pending alert never receives firing retention.

Once firing, retain the alert for three elapsed minutes measured from the first evaluation where the condition becomes false. Keep it firing while less than three minutes have elapsed since that first false evaluation. Clear it at the first evaluation reaching three elapsed minutes if the condition has remained false. The timer is anchored to that first false evaluation, not the preceding true sample, and does not restart on every false observation.

If the condition becomes true while the alert is still retained, continue firing without a second wait and cancel the recovery timer. The next false evaluation starts a new three-minute retention period. A true condition exactly at the expiry evaluation also continues firing; evaluate the current condition before resolving. After actual clearance, a later true condition must satisfy a fresh two-minute wait. Timers and alert identities are independent for each service.

Required alert name: ServiceErrorRatioHighRetained. Emit exactly one alert per firing or retained service. Its exact identifying output labels are alertname="ServiceErrorRatioHighRetained" and the original service value. No additional labels or annotations are permitted. Retention concerns the Prometheus firing state, not notification intervals, delivery delays, or Alertmanager grouping.

Common output contract

Return only one complete UTF-8 Prometheus 3.15.1 rule file as raw YAML. JSON-formatted YAML is also acceptable. Do not include Markdown fences, surrounding prose, multiple documents, multiple alternatives, recording rules, imports, or external dependencies. Use standard safe YAML types, string mapping keys, and no duplicate keys, including collisions introduced by merges. The document must be a mapping with groups as its only top-level field.

Use exactly one named rule group, an explicit group interval equivalent to one minute, and exactly one alert rule with the required alert name. Supported group fields are name, interval, rules, and optional labels. Supported alert-rule fields are alert, expr, for, keep_firing_for, labels, and annotations; omit fields you do not need. No other fields are supported. Annotations must be absent or an empty mapping: no annotation entries are permitted, even constant ones. Any group/rule label declarations may use only service, plus environment for R05. They must preserve the required original identifying values. Do not declare alertname in a labels mapping; the alert field supplies that name. Do not add labels, including severity or instance. The identifying output labels specified for the task are exact; neither the input metric name nor alertstate belongs to that set.

Reference every supplied metric and no other metric. Use the supplied gauge observations directly at the current evaluation. Do not replace the required metric inputs with a constant expression. Do not compute rates, increases, histograms, additional window statistics, or missing-data behaviour. Do not use range selectors, subqueries, offset modifiers (including zero offsets), or @ modifiers. Alert persistence and any specified firing retention provide the required timing.

PromQL operators, matching, and aggregations may be used subject to the task's behaviour. If function calls are used, the automatically supported set is: abs, ceil, floor, round, clamp, clamp_min, clamp_max, exp, ln, log2, log10, sqrt, sgn, scalar, vector, label_replace, label_join, sort, sort_desc. In particular, rate, irate, increase, delta, idelta, deriv, predict_linear, double_exponential_smoothing, holt_winters, changes, resets, timestamp, time, absent, absent_over_time, all functions ending in _over_time, and all functions starting with histogram_ are prohibited. Other function calls require manual inspection and may be unevaluable; their absence from the supported set is not by itself a demonstrated behavioural defect.

For automatic inspection, each metric selector must identify its supplied metric by name or an exact __name__ equality matcher. Unbounded/regex-only metric-name selection, selector-level OR matcher extensions, and query calls inside label/annotation templates require manual review; avoid them. Selector-level OR matchers are distinct from ordinary PromQL binary operators. An expression accepted by Prometheus but unsupported by the independent inspection parser is reported as an inspection limitation, not automatically a behavioural failure.

Keep the response within 200,000 UTF-8 bytes, 20,000 YAML lexical tokens, and 60 mapping/sequence nesting levels. Exceeding these inspection limits makes scoring incomplete rather than establishing a behavioural defect. Any expression satisfying the full contract is acceptable; no particular expression text is required.
```

</details>
