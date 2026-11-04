# Study plan — Stage 2 specification draft

Status: **draft for review, no generation authorized or performed**. This stage
adds five requirement specifications and a documentation-based semantics review.
It does not implement R02–R06, create their executable fixtures or reference
rules, select a model, or collect experimental outputs. Updated R01 and every
prior execution record remain intact.

## Research question and scope

Do behavioural tests expose requirement violations in generated Prometheus
alert rules that syntax checks miss? The pilot will use six deliberately
chosen tasks, three separate API generations per task, and one fixed model:
**6 × 3 = 18 planned outputs**. This is a small descriptive pilot, not a
representative sample of monitoring work or evidence of operational safety.

All input sequences are controlled synthetic fixtures. Reference rules and
deliberate mutations are infrastructure-validation material, excluded from
experimental-output counts. Existing Stage 1 results concern only that
infrastructure; they are not model-performance results.

## Six tasks and planned generation slots

| Task | Contract focus | Proposed timing | Planned output IDs |
|---|---|---|---|
| [R01](requirements/R01.md) | Supplied per-service error ratio >0.05; strict boundary and interrupted persistence | 2m wait; immediate clearance | R01-G01, R01-G02, R01-G03 |
| [R02](requirements/R02.md) | Supplied p95 latency in seconds >0.5; no percentile calculation | 3m wait; immediate clearance | R02-G01, R02-G02, R02-G03 |
| [R03](requirements/R03.md) | Any instance breaches >0.05; one alert per service, continuity across instance handoffs | 2m service-level wait; immediate clearance | R03-G01, R03-G02, R03-G03 |
| [R04](requirements/R04.md) | Error ratio >0.05 AND supplied preceding-minute volume >=100, for the same service | 2m conjunction wait; immediate clearance | R04-G01, R04-G02, R04-G03 |
| [R05](requirements/R05.md) | Only environment=production; preserve service and environment | 2m wait; immediate clearance | R05-G01, R05-G02, R05-G03 |
| [R06](requirements/R06.md) | Firing retention after recovery, including renewal and re-arming | 2m initial wait; 3m retention from first false evaluation | R06-G01, R06-G02, R06-G03 |

All tasks use one-minute evaluation and complete observations. R01's updated
seven fixtures / 37 assertions are the preserved baseline. R02–R06 tables are
proposed expected outcomes, not executed tests. R02 is a unit-sensitive variant
of R01, not an orthogonal state-machine capability. The six tasks are purposeful
coverage choices and may share failure causes.

## Decisions to review before implementation

1. R02: supplied precomputed p95 latency gauge in seconds; strict 500 ms
   threshold and three-minute persistence. Confirm this statistic and timing.
2. R03: continuity belongs to the service-level any-instance condition. A
   violating-instance handoff does not reset the timer. A different interpretation
   requiring the same instance throughout would be a different requirement.
3. R04: volume is a supplied noncumulative preceding-minute count, with an
   inclusive threshold of 100 requests. Ratio equality at 0.05 remains excluded.
4. R05: the exact environment value is `production`; output retains that label.
   Only production and staging are in scope, both always explicitly labeled.
5. R06: retention is three minutes from the first false evaluation of an already
   firing alert. A true condition during retention, including at expiry, keeps
   it firing; after actual clearance, a new two-minute wait is required.
6. All tasks: exact identifying labels, no extra labels or annotations, one
   alert rule per task. This deliberately limits harmless formatting/content
   variation and must be stated explicitly to the model. Record extra-metadata
   violations separately from timing/threshold failures.
7. The model ID/version and generation settings remain **unselected**. No model
   recommendation or performance claim is made in this draft.

The defaults above make the draft internally explicit; they are proposals for
review, not silently settled operational policies. Documentation checks and the
R06 boundary interpretation are in [SEMANTICS.md](requirements/SEMANTICS.md).

## Separation between requirements, prompts and oracle

Generation prompts will contain only the approved plain-English contract:
metric names/types/units and full label schemas, observation assumptions,
thresholds, timing, grouping, alert identity and exact-label/annotation policy,
plus the common output-format instructions. For R02–R06, only the section
headed “Behavioural requirement — eligible for a future generation prompt” is
eligible; do not include the whole specification file. Compose R01's contract
from its requirement and label definitions, excluding its scenario table and
worked examples. Hash and review the exact final prompt text before any call.

**Never include reference rules, mutations, test files, scenario tables, input
sequences, expected firing tables, worked timing examples, test failures,
semantics review notes, or answer expressions in generation prompts.** No
repository retrieval, attached files, tool access, prior answers or scoring
feedback are provided to the generation model. The final prompt is a standalone
artifact assembled from an explicit text allowlist. This is not adversarial
prompt secrecy; the behavioural contract remains fully disclosed, while the
concrete scoring examples are withheld.

Proposed common output contract: return only a complete UTF-8 Prometheus rule
file as raw YAML, with exactly one rule group at a one-minute interval and
exactly one alert rule bearing the required name. No Markdown fences, prose,
recording rules, imports, external dependencies or extra alert rules. Use only
the supplied metrics and direct gauge observations; no rate/increase functions,
histogram calculations, subqueries, offsets or additional time-window
calculations. Alert persistence and retention provide the required timing.
Equivalent expressions meeting the contract are acceptable; matching a
reference expression's text is not required.

## Freeze and infrastructure validation before collection

After requirement approval and separate authorization to implement, build
R02–R06 reference rules and executable fixtures from the reviewed tables.
Verify all reference suites, including temporal boundaries and intended labels,
and validate the tests using deliberate mutations. These artefacts remain
outside generation prompts and are never counted as generated candidates.

Before the first generation, freeze all six requirements, exact prompt texts,
output-format policy, test suites, candidate-scoring harness, extraction policy,
model selection/settings, and the Prometheus version/digest. Preserve their
hashes and commit identifier in a study manifest. The present target is the
existing pinned Prometheus/promtool 3.15.1 image in `prometheus-image.txt`;
no upgrade or change is part of this stage.

Freeze a single exact model identifier (a versioned snapshot if available),
all supported generation parameters and explicit/default settings, output
budget, and API/client version before collection. Record actual response model
identifiers and relevant returned version metadata. If the provider cannot
pin a snapshot, disclose that limitation and the collection time window.
Do not claim reproducible model outputs merely because the evaluation harness
is reproducible. No API implementation details or credentials are needed now.

## Planned collection protocol

Use three rounds. In each round, make one separate API generation for each of
R01, R02, R03, R04, R05 and R06 in that fixed order. Every request uses a fresh
context, the same fixed model and settings, and the identical task prompt
across rounds. Each request seeks one response; a single request for three
alternatives does not satisfy this protocol. The fixed order is transparent
and feasible for this pilot; model drift or time/order effects remain limitations.

Preassign the 18 IDs in the task table. Preserve every original response exactly
as received, including malformed output, refusals, truncated output and duplicate
responses. Duplicates are observations and are not replaced. Store the complete
response payload and returned text separately; retain status, request ID,
start/end times, finish reason, usage and request parameters when available.
Never store authentication headers, API keys or other credentials.

Eighteen is the planned count, not an achieved result. Disable automatic retries
for collection. A transport error or a request with an uncertain completion is
recorded against its planned slot and reported separately; do not fabricate a
response or silently resample. Any additional attempt requires a documented
protocol amendment, preserving the failed/uncertain attempt and disclosing the
new request count. Never retry because an output scores poorly. Report actual
attempts, returned responses and scorable outputs separately.

## Original-response handling and scoring

Keep original response files immutable, with SHA-256 hashes. Write the returned
text unchanged as the candidate file: no fence stripping, YAML reformatting,
name correction, label fixes, expression repair, persistence fixes or choice
among multiple suggestions before scoring. A non-text, empty, truncated or
multi-answer response is retained and classified under the frozen policy;
a finished but malformed answer is an observed failure, not an infrastructure
error. Copying identical text bytes to a scoring path is not a repair.

For each output, record separate outcomes:

- **Response/format:** was one complete rule file returned under the output contract?
- **Syntax acceptance:** actual `promtool check rules` result on unchanged text,
  with raw stdout/stderr and exit code. This command includes parser/schema
  validation; “syntax” is the study's shorthand, not purely lexical validation.
- **Contract conformance:** group interval, single-rule structure, required name,
  allowed metrics/constructs and exact label/annotation policy. A name error or
  extra alert must not disappear because tests inspect only one alert name.
- **Behaviour:** actual firing-set assertions at every specified timestamp,
  distinguishing threshold, timing, recovery, grouping and label mismatches.
  Use the unchanged candidate in the frozen test harness. Run behaviour checks
  for syntax-accepted candidates whenever loading/evaluation permits; structural
  violations are still recorded separately. Clearly mark unevaluable cases.

Record infrastructure/loader/evaluation errors distinctly from assertion
mismatches. Do not score a Docker failure as a requirement violation. Record
missing labels or extra annotations as contract failures even when timing is
correct. Check prohibited constructs explicitly rather than claiming that a
finite output suite proves their absence. The scoring machinery for R02–R06
is a future implementation task, not delivered in this stage.

Per task, report counts out of three planned slots for response availability,
syntax acceptance, contract conformance, behaviour pass/fail and unevaluable
cases. Highlight syntax-accepted outputs with behavioural assertion failures.
For a conditional descriptive proportion, state the denominator explicitly:
syntax-accepted, behaviour-evaluable outputs; disclose excluded/unevaluable
outputs alongside it. Do not treat syntax-rejected outputs as syntax-missed
violations. Keep per-scenario diagnostics; aggregate only with clear denominators.

## Interpretation and research integrity

The three repeated outputs are **grouped by task**. There are six task groups,
not 18 independent tasks. Fresh request contexts do not establish statistical
independence. Summarize within-task variability and present an overall output
count only as a descriptive total; avoid independence-based confidence intervals,
significance tests or broad generalization from this pilot.

No results for generated candidates exist yet. All R02–R06 expected tables are
prospective specifications. Use no production telemetry, rate calculations,
missing-data semantics, Alertmanager deployment or additional infrastructure.
Firing-output assertions do not directly verify all internal pending states.
Passing finite scenarios cannot establish operational safety or completeness.

Record any correction to a requirement or oracle with its reason and version.
Freeze before generation. If a later oracle defect is discovered, retain the
original oracle and scores, document the correction, and rescore every stored
original response under the corrected version; do not edit responses or
regenerate favourable samples. Keep human review of the requirements, fixtures
and interpretation explicit.

Existing raw run directories and `stage1-review.zip` remain preserved locally.
The repository currently excludes `results/`, `prompts/` and `responses/` from
version control; ignored future study artefacts must still be preserved in an
explicit local archive/backup manifest. Publishing or changing those exclusions
is outside this specification stage. No API calls, model choice, generation,
reference implementation for R02–R06, or GitHub push occurs in this stage.
