# Stage 2 semantics review — specification only

Checked 2026-11-04 against official Prometheus documentation. The proposed
execution target remains the existing pinned Prometheus 3.15.1 image; it was
not changed or run for this specification stage. R02–R06 are proposals, not
implemented rules, executable fixtures, or measured results. This document is
review material and must not be included in generation prompts.

## Shared conventions for the proposed pilot

All listed series are controlled synthetic inputs, not production telemetry.
Each row is an independent scenario beginning with no alert state. Values in
lists correspond to 0m, 1m, 2m, etc., with a sample available before evaluation
at every timestamp. Finite values only; no missing samples, stale markers,
restarts, evaluation failures, delayed observations or changing label sets.
Time ranges in tables include every integer-minute evaluation. Nothing is
asserted beyond the last supplied sample. Continuity is observed continuity
at evaluations; this pilot makes no claim about between-sample changes.

All schemas list every ordinary input label. The implicit `__name__` is the
specified metric name. No job/cluster/region labels or configured external
labels are assumed. Services and instances may use any stable nonempty names;
`api`, `web`, `a` and `b` are scenario examples, not an allowed-value list.
Each task runs in an isolated metric namespace, so R05's environment-bearing
schema does not coexist with R01's service-only schema.

Firing tables describe the complete expected set for the task's required alert
name. Required labels are exact; no extra labels or annotations are permitted.
The empty set permits no firing alerts but does not distinguish inactive from
pending states. The application metric name is not an output alert label.
Prometheus-generated `ALERTS` storage-series metadata such as `alertstate`
is outside the identifying label set being specified here.

## Source checks and their implications

- **Persistence and clearance:** `for` delays firing while a label identity
  remains active; without retention, a false evaluation deactivates the alert.
  Existing labels may be overwritten by configured alert labels. This supports
  explicit waits, exact identities and clearance contracts.
  [Official alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/).
- **Evaluation and retention configuration:** rule groups support an explicit
  interval; alert rules have separate persistence and retention durations.
  [Official rule configuration](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/).
- **Filtering, grouping and conjunction:** comparisons normally remove
  nonmatching elements; boolean comparisons instead retain 0/1 values. Set
  intersection matches label sets, and aggregation can retain selected labels.
  These semantics matter to R03's service identity and R04's same-service
  conjunction. The specifications prescribe behaviour, not a required PromQL
  expression. [Official operators](https://prometheus.io/docs/prometheus/latest/querying/operators/).
- **Environment selection:** label equality matches an exact string, supporting
  R05's explicit `production` value.
  [Official query selectors](https://prometheus.io/docs/prometheus/latest/querying/basics/#time-series-selectors).
- **Gauge type:** gauges may rise or fall; the supplied latency, ratios and
  refreshed window count are used as gauges. Their particular units and
  upstream meanings are study design choices, not facts about standard built-in
  Prometheus metrics. [Official metric types](https://prometheus.io/docs/concepts/metric_types/#gauge).
- **Future assertions:** promtool alert tests specify the complete firing set
  for a given alert name. Expected labels omit `alertname` because it is selected
  separately, and omit the input metric name. Future fixtures must preserve
  this distinction. [Official rule unit tests](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/#alert_test_case).

## R06 retention boundary: pinned-version source check

The alerting overview describes retention broadly. To settle the one-minute
boundary precisely, also inspected the official 3.15.1 implementation:
[`rules/alerting.go`, Eval, lines 449–493](https://github.com/prometheus/prometheus/blob/v3.15.1/rules/alerting.go#L449-L493).
For an already firing alert, the first evaluation without a matching condition
sets `KeepFiringSince`; retention continues while elapsed time is less than
its duration. A true condition clears that recovery timer. A pending alert
receives no such retention.

Consequently, the proposed 3m retention starting at a false observation at 4m
keeps the alert firing at 4m, 5m and 6m and clears it at 7m if still false.
If true again at 7m, it continues firing and cancels the recovery timer.
This is a source-based interpretation, not a new test result. These boundaries
must be verified against the pinned tool when R06 implementation is authorized.
Retention is distinct from Prometheus's storage of resolved alerts and from
Alertmanager notification scheduling.

## Choices still requiring study review

Thresholds and durations in R02–R06 are illustrative pilot choices, not
operational recommendations. R02 adds unit-sensitive latency handling but
shares the R01 temporal structure. R03 explicitly uses service-level continuity
across instance handoffs. R04 uses an inclusive 100-request window-count gate.
R05 preserves `environment=production`. R06 uses first-false-observation
retention and tests renewed breaches. No documentation question about these
proposed semantics remains unidentified, but executable R02–R06 validation
has not occurred. All choices remain subject to human review before freezing.
