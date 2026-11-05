# Stage 3A — offline candidate scorer

Stage 3A is implemented and validated locally. No model API was called.
Human review is still required. All controls are
infrastructure-validation material, not sampled model outputs. All observations
are the preserved controlled synthetic fixtures, not production telemetry.

## Files and repeatable commands

- `scripts/score_candidate.py`: standalone task/response scorer and raw recorder.
- `scripts/stage3a/contracts.py`: safe duplicate-aware YAML inspection and PromQL
  contract checks; no candidate rewriting.
- `scripts/stage3a/diagnostics.py`: strict quoted-string-aware diagnostic parser
  and classification from observed outputs.
- `requirements-stage3a.txt`: `PyYAML==6.0.3`, `promql-parser==0.11.0`.
- `scripts/stage3a/build_controls.py`, `controls/stage3a/`: labelled controls,
  their predeclared expectations, and provenance. These are kept separate from
  future experimental model outputs.
- `scripts/validate_stage3a.py`, `tests/test_stage3a.py`: control runner and focused
  parser/contract tests.
- `scripts/package_stage3a.py`: explicit-run packaging with hashes and documented
  sharing-copy path redactions.
- `.gitignore`: adds local review ZIP exclusion. `results/` remains excluded.
- This report and local `stage3a-review.zip`.

From the repository root, with Docker running and the existing pinned image
already present:

```sh
python3 -m venv .venv-stage3a
.venv-stage3a/bin/python -m pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: -r requirements-stage3a.txt
.venv-stage3a/bin/python scripts/validate_stage3a.py --jobs 3
```

Score one unchanged response (the same CLI supports R01–R06):

```sh
.venv-stage3a/bin/python scripts/score_candidate.py R01 controls/stage3a/R01_reference.yml
```

The optional `--jobs 3` runs independent controls concurrently in separate immutable
mounts; the default is sequential execution. It does not change scoring or fixtures.

The validation command returns 0 only when every predeclared control outcome
matches and the unit tests pass. Expected rejected controls do not make this
validation command fail. The individual scorer returns **0** for an accepted
candidate, **1** for an observed candidate violation (including candidate
syntax/evaluation failure), and **2** for incomplete scoring, diagnostic or
inspection limitations, or infrastructure/scorer errors. Always inspect the
separate outcome fields; a candidate may have a known defect and incomplete
scoring at the same time. No candidate is repaired or resampled.

## What is checked

The caller's original bytes are copied to `candidate.original`, hashed, and copied
unchanged to a unique candidate mount as `rule.yml`. The frozen task fixture is
copied byte-for-byte as `test.yml`. Candidate and fixture copies are made read-only;
Docker receives only this directory, mounted read-only with networking disabled.
Container-visible hashes are checked before and after syntax/behaviour execution.
The original, fixture and scorer input hashes are checked again after execution.
The image pin and actual promtool version must match the existing configuration.

Every result separately reports:

| Dimension | Meaning |
|---|---|
| Response/format | UTF-8, one YAML mapping document, safe constructors, no duplicate keys; fenced/prose/malformed output is never extracted or repaired |
| Syntax | Actual `promtool check rules rule.yml` on the original bytes, including format-rejected controls |
| Structural contract | Exactly one group and one alert rule, explicit interval equivalent to 1m, required name, supplied metrics, prohibited temporal/histogram constructs and unsupported fields |
| Metadata | No annotations, including static declarations even if nothing fires |
| Required identity | Correct alert name and exact required output labels; additional labels are retained during execution and treated as identity violations |
| Behaviour | Missing/extra firing outputs and grouping at frozen timestamps; metadata-only mismatch does not become a timing/detection defect |

Syntax-accepted, safely parsed candidates are tested even when a structural
violation is already known. An extra alert rule cannot hide behind tests that
assert only the required name: the complete parsed rule structure is checked
independently. An unknown diagnostic is never interpreted as success.

The inspector walks an expression AST rather than requiring reference-expression
text. Arithmetic, comparisons, aggregation and matching can differ. Range
selectors, subqueries, offsets, noncurrent `@` observations, rate/increase,
histogram and other temporal calculations are detected explicitly. Selectors
whose metric scope cannot be resolved, unfamiliar functions, template queries,
or inspection-parser disagreement require review rather than a silent pass.
The supplied metrics must be referenced, not merely replaced by a constant vector.
Static analysis does not prove mathematical equivalence.

Promtool's diagnostic values use Go quoting. The new parser consumes the entire
diagnostic, respects quoted braces/brackets/escaped quotes, checks list indices,
and compares every parsed expected alert with the frozen fixture. It records
actual alert sets only where promtool explicitly prints them. A successful
assertion is recorded as pass evidence, not fabricated as a raw observed trace.
This follows the [pinned promtool unit-test implementation](https://github.com/prometheus/prometheus/blob/v3.15.1/cmd/promtool/unittest.go).

`metadata_only` requires matching firing identities with only annotations changed.
Missing service identity makes service attribution unevaluable; the scorer does
not invent a missing-plus-extra service pair. Other observable symptoms are
`missing_alert`, `extra_alert`, `grouping`, and `required_identity`. No known
mutation's intended defect tags are assigned to arbitrary candidates. Timestamp
and scenario records expose boundary/recovery discrepancies, but a finite firing
mismatch does not by itself establish a threshold or persistence root cause.

Candidate evaluation errors are recorded separately from assertion failures.
Because pinned promtool's rule-evaluation error messages omit scenario names,
any such error conservatively prevents pass inference for otherwise unreported
assertions in that candidate's suite. Explicit failure diagnostics remain saved.
Docker startup/command errors and unrecognized diagnostics have separate statuses.

## Executed results

Final record: `results/stage3a/20261105T082902.000765Z`. Started 2026-11-05T08:29:02.001661+00:00; finished
2026-11-05T08:34:24.244959+00:00. Actual runner exit: **0**.

**42/42 controls matched predeclared outcomes; 15/15 focused unit tests passed.**
Eight positive controls were accepted: all six references, an equivalent expression,
and the `60s` interval spelling. The six references passed **278 timestamp assertions**.
The other 34 controls were rejected as expected. All **15 existing mutations** were
syntax-accepted and produced assertion failures; none survived. The R05 missing-
environment mutation is an identity failure with matching firing times, not evidence
of a timing/detection defect.

Actual syntax totals: **37 accepted, 5 rejected**. Promtool accepted an empty file
as zero rules; the independent response check rejected it, and no behaviour test
was inferred. The extra-rule and wrong-interval controls passed the firing fixtures
but failed structural checks. Both annotation controls had **six metadata-only
assertion failures** each, with identity and firing behaviour passing. The missing-
service control had six identity mismatches and unevaluable service attribution.

The evaluation-error control passed syntax but encountered two reported many-to-many
matching errors. It also had 23 explicit assertion mismatches in other evaluated
cases; these are retained, but the suite's behavioural outcome is **unevaluable**.
It is not counted as an ordinary, fully evaluated behavioural rejection. There were
**no Docker/infrastructure failures, scorer errors, or diagnostic-parser limitations
in the final control execution**. Synthetic malformed-diagnostic unit tests verify
that unknown/inconsistent evidence fails closed instead of passing.

Actual toolchain: Python `3.14.6`, PyYAML
`6.0.3`, promql-parser `0.11.0`,
promtool `3.15.1`, native `linux/arm64` image on host `arm64`.
The original image pin remains:

```text
prom/prometheus@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2
```

The complete actual promtool build/revision, Docker client/server versions, image
ID and dependency versions are in each candidate summary and raw command logs.
Original bytes, mounted copies, immutable fixture snapshots, commands, timestamps,
stdout, stderr, actual process exit codes, hashes and per-scenario assertions are
retained in each candidate directory. `file-hashes.json` inventories execution
evidence; `preservation.json` verifies **977 pre-existing files unchanged** and
all **40 original controls and their expectations unchanged** between these runs.

In this table, “test exit 1” can represent exact-output assertion differences or
candidate evaluation errors; it is not automatically a behavioural defect.
The separate failed dimensions identify the actual contract outcome. A dash means
not executed/not available, never a pass.

| Control | Syntax exit | Test exit | Explicit failed assertions | Failed dimensions / qualification |
|---|---:|---:|---:|---|
| `R01_reference` | 0 | 0 | 0 | all pass |
| `R02_reference` | 0 | 0 | 0 | all pass |
| `R03_reference` | 0 | 0 | 0 | all pass |
| `R04_reference` | 0 | 0 | 0 | all pass |
| `R05_reference` | 0 | 0 | 0 | all pass |
| `R06_reference` | 0 | 0 | 0 | all pass |
| `equivalent` | 0 | 0 | 0 | all pass |
| `interval_60s` | 0 | 0 | 0 | all pass |
| `malformed` | 1 | — | — | response_format, syntax |
| `duplicate_yaml` | 1 | — | — | response_format, syntax |
| `duplicate_json` | 1 | — | — | response_format, syntax |
| `fenced` | 1 | — | — | response_format, syntax |
| `unsafe_tag` | 1 | — | — | response_format, syntax |
| `empty` | 0 | — | — | response_format |
| `wrong_name` | 0 | 1 | 6 | structural_contract, required_identity, behavioral |
| `extra_rule` | 0 | 0 | 0 | structural_contract, required_identity |
| `annotation` | 0 | 1 | 6 | metadata |
| `annotation_braces_quotes` | 0 | 1 | 6 | metadata |
| `missing_service` | 0 | 1 | 6 | required_identity; behaviour unevaluable_identity |
| `extra_label` | 0 | 1 | 6 | required_identity |
| `wrong_interval` | 0 | 0 | 0 | structural_contract |
| `wrong_metric` | 0 | 1 | 6 | structural_contract, behavioral |
| `rate` | 0 | 1 | 6 | structural_contract, behavioral |
| `offset` | 0 | 1 | 5 | structural_contract, behavioral |
| `evaluation_error` | 0 | 1 | 23 | required_identity; behaviour unevaluable |
| `mutation_R01_no_for` | 0 | 1 | 10 | behavioral |
| `mutation_R01_inclusive` | 0 | 1 | 4 | behavioral |
| `mutation_R02_threshold_500` | 0 | 1 | 4 | behavioral |
| `mutation_R02_wait_2m` | 0 | 1 | 3 | behavioral |
| `mutation_R03_average` | 0 | 1 | 2 | behavioral |
| `mutation_R03_retained_instance` | 0 | 1 | 10 | required_identity, behavioral |
| `mutation_R03_instance_handoff_reset` | 0 | 1 | 10 | required_identity, behavioral |
| `mutation_R04_or` | 0 | 1 | 26 | behavioral |
| `mutation_R04_volume_strict` | 0 | 1 | 1 | behavioral |
| `mutation_R04_cross_service` | 0 | 1 | 5 | behavioral |
| `mutation_R05_no_filter` | 0 | 1 | 20 | required_identity, behavioral |
| `mutation_R05_no_environment_label` | 0 | 1 | 6 | required_identity |
| `mutation_R06_no_retention` | 0 | 1 | 22 | behavioral |
| `mutation_R06_retention_1m` | 0 | 1 | 15 | behavioral |
| `mutation_R06_no_initial_wait` | 0 | 1 | 19 | behavioral |
| `no_rules` | 0 | 1 | 6 | structural_contract, required_identity, behavioral |
| `constant_expression` | 0 | 1 | 23 | structural_contract, required_identity, behavioral |

The final scorer has no knowledge of the control catalog's expected outcome or
mutation intent. The validation runner compares its independent results with
predeclared control expectations only after scoring.

Create the review archive from both retained runs:

```sh
python3 scripts/package_stage3a.py results/stage3a/20261105T082902.000765Z results/stage3a/20261105T075225.718950Z
```

`stage3a-review.zip` contains the final scorer/specifications/fixtures/controls,
this report, and both execution records with their exact historical source
snapshots. Personal project paths are replaced only in sharing-copy execution
metadata/logs; candidates, mounted inputs and snapshots remain byte-identical.
`REDACTIONS.md`, `MANIFEST.json` and `SHA256SUMS` document and verify the sharing
copy. Original local records are never rewritten. Nothing is pushed to GitHub.


## Review corrections and retained earlier evidence

The first execution, `results/stage3a/20261105T075225.718950Z`, passed all
40 original controls and 13 focused unit tests. Subsequent code review identified
three inspection gaps to close before collection:

1. A purported failed assertion containing identical expected and actual sets
   could be accepted as having no classified symptoms. Such inconsistent evidence
   now produces a diagnostic-parser limitation, with a regression test. This was
   found by code review; real promtool did not emit it during the control run.
2. No-rule responses now explicitly fail required-name identity, in addition to
   rule count. Responses using no supplied metric explicitly fail the metric
   contract. Two new controls cover these cases.
3. The runner gained optional bounded concurrency for independent immutable
   candidate mounts; this does not change expected firing outputs.

The original 40 candidate files and their expected outcomes were retained without
edits. The final run re-executes them plus the two new controls using the tightened
scorer. No requirement, fixture, expected firing output, or existing execution
record was corrected to make the scorer pass. The earlier source snapshots,
raw logs and outcomes remain available in the local review ZIP.

## Limits and review before collection

- The auxiliary PromQL parser is independently versioned, not Prometheus's own
  Go parser. Promtool remains authoritative for syntax. Unsupported valid syntax
  or contract-inspection ambiguity produces incomplete scoring and needs review.
- Safe YAML parsing uses [PyYAML SafeLoader](https://pyyaml.org/wiki/PyYAMLDocumentation)
  with a duplicate-key constructor. Merge-key collisions are rejected
  conservatively. Limits of 200,000 bytes, 20,000 tokens and 60 nesting levels
  produce a recorded inspection limitation, not a syntax or behavioural pass.
- Docker commands have a 120-second timeout. Timeouts are execution limitations;
  they are not counted as behavioural detection. Novel error formats fail closed.
- Identity faults may prevent service-specific interpretation. Annotation-only
  behaviour pass means firing identities/times match the fixtures; it does not
  mean the full no-annotation contract passes.
- Finite synthetic tests do not establish operational safety, all internal pending
  states, or correctness on untested observations. There are no production,
  missing-data, restart or Alertmanager claims. Human review is still required.
- The study plan/specification files retain their historical wording and remain
  unchanged. No model is selected and no experimental generation is performed.
  Controls cannot be counted among the planned 18 outputs.

Dependency releases are pinned from their project distributions:
[PyYAML 6.0.3](https://pypi.org/project/PyYAML/6.0.3/) and
[promql-parser 0.11.0](https://pypi.org/project/promql-parser/0.11.0/).
Prometheus usage follows its [official promtool documentation](https://prometheus.io/docs/prometheus/latest/command-line/promtool/).
