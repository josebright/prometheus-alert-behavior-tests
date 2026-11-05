# Stage 2 infrastructure validation

Completed on 2026-11-05 (Africa/Lagos). This is implementation and validation
of the approved R02–R06 specification tables, not experimental model generation.
No model API call, model selection or sampled model output occurred. No GitHub
push was performed. Prior R01 material and all previous execution records remain
unchanged. The dated specifications and STUDY_PLAN.md are preserved as reviewed;
this report records the subsequently authorized implementation.

## Execute and inspect

```sh
python3 scripts/check_stage2.py
```

Requires Python standard library and a running Docker engine with pull access.
The pinned image is used exactly; no upgrade or floating tag is selected.
The runner exits 0 only when all references pass, every deliberate mutation is
rejected by recognized assertions, and the annotation control is metadata-only.
It exits 2 for surviving mutations, reference failures or validation/execution
errors. Expected mutation exit 1 is not a runner infrastructure failure.

Final record: `results/stage2/20261104T232544.081390Z/`.
UTC start: `2026-11-04T23:25:44.082115+00:00`; finish: `2026-11-04T23:58:51.539744+00:00`.
Runner exit: **0**; success: **true**.
This is 00:25–00:58 on November 5 in Lagos.

Image: `prom/prometheus@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2`.
Actual promtool: **3.15.1**, revision
`bae3eced0a5369e050e83ea73bc381d7c4b1a719`, linux/arm64.
Docker and Python versions, image ID and complete tool output are in the record.

## Reference results

All five references passed: **40 scenarios and 241 timestamp assertions**.
Every integer-minute timestamp listed in the approved tables is asserted.
No expected outcome was changed. R01 was preserved, not rerun or modified.

| Task | Scenarios | Assertions | Syntax exit | Behaviour exit |
|---|---:|---:|---:|---:|
| R02 | 6 | 37 | 0 | 0 |
| R03 | 8 | 42 | 0 | 0 |
| R04 | 9 | 47 | 0 | 0 |
| R05 | 8 | 42 | 0 | 0 |
| R06 | 9 | 73 | 0 | 0 |

The fixture compiler reads literal input sequences and literal expected firing
sets from each table. It expands time ranges but does not derive the oracle
from the reference expression or simulate expected alert timing. The runner
checks that executable fixtures still match the tables before executing them.

## Deliberate mutations: actual outcomes

All **13 mutations** were syntax-accepted in the final run and rejected by
actual expected/actual firing-output assertions. **Surviving mutations: none.**
Twelve produced missing or extra alerts; the missing-environment-label mutation
produced required-identity failures only. These are infrastructure-validation
materials, not the 18 outputs planned for the later study.

Counts below are failed scenario/timestamp assertions, not individual alerts.
Symptom categories overlap, so their counts should not be added as independent
failures. The metadata control is excluded from this mutation count.

| Mutation | Syntax exit | Behaviour exit | Failed assertions | Observed symptoms |
|---|---:|---:|---:|---|
| `R02-threshold_500` | 0 | 1 | 4 | missing-alert=4 |
| `R02-wait_2m` | 0 | 1 | 3 | extra-alert=3 |
| `R03-average` | 0 | 1 | 2 | missing-alert=2 |
| `R03-retained_instance` | 0 | 1 | 10 | required-identity=9, extra-alert=2, grouping=2, missing-alert=1 |
| `R03-instance_handoff_reset` | 0 | 1 | 10 | required-identity=9, missing-alert=1 |
| `R04-or` | 0 | 1 | 26 | extra-alert=26 |
| `R04-volume_strict` | 0 | 1 | 1 | missing-alert=1 |
| `R04-cross_service` | 0 | 1 | 5 | extra-alert=5 |
| `R05-no_filter` | 0 | 1 | 20 | extra-alert=20, required-identity=20, grouping=4 |
| `R05-no_environment_label` | 0 | 1 | 6 | required-identity=6 |
| `R06-no_retention` | 0 | 1 | 22 | missing-alert=22 |
| `R06-retention_1m` | 0 | 1 | 15 | missing-alert=15 |
| `R06-no_initial_wait` | 0 | 1 | 19 | extra-alert=19 |

### Inspection of each defect

- **R02-threshold_500** — Threshold/units: no alert at 4m in Boundary then recovery, where .80 seconds must fire; all four expected firing observations are missing.
- **R02-wait_2m** — Timing: fires at 3m in Boundary then recovery instead of 4m; also early at interrupted-wait 5m and isolation 3m.
- **R03-average** — Aggregation/threshold: (.09 + .01)/2 does not breach, hiding the affected instance; required alerts at 3m and 4m are missing.
- **R03-retained_instance** — Grouping and identity: two alerts at 3m/4m when both instances breach, and instance labels remain. Handoff also leaves the 3m alert missing.
- **R03-instance_handoff_reset** — Timing: selected instance changes at 2m, so the 3m alert is missing and appears at 4m. Nine other mismatches are forbidden instance identity; this is not a timing-only mutation.
- **R04-or** — Conjunction: fires with low error but enough traffic, high error but low/zero traffic, and when predicates belong to different services. Some recovery and firing times are also wrong.
- **R04-volume_strict** — Threshold: volume exactly 100 is wrongly excluded, so the required alert at 3m is missing.
- **R04-cross_service** — Service matching: api fires at 2–4m using web volume in the cross-service scenario; web also fires at 3–4m in One qualifying service.
- **R05-no_filter** — Environment selection: staging alerts appear, including at 2–4m when only staging breaches. Both environments can create duplicate service outputs.
- **R05-no_environment_label** — Required identity only: all six firing times and services match, but environment=production is absent. No missing/extra-alert or timing/detection failure is reported.
- **R06-no_retention** — Recovery: clears at 4m instead of remaining firing through 6m in Full retention. Renewed breaches also lose continuity after premature clearance.
- **R06-retention_1m** — Recovery: clears at 5m instead of 7m in Full retention; 5m/6m are missing. Renewals/expiry cases expose further early-clearance effects.
- **R06-no_initial_wait** — Timing: fires on the spike at 1m and retains it through 4m, although it should never fire. Initial firing and post-clearance re-arming are also early.

## Annotation-only control and classification

`R02-extra_annotation` differs from R02's reference only by the constant
annotation `summary: Constant review annotation`. The rule executes unchanged.
It passed syntax (exit 0) and failed strict output tests (exit 1) at four firing
timestamps. All four mismatches were **metadata-only**. Required labels,
cardinality and firing times match the reference; detection/timing passes,
identity passes, and no timing, threshold, recovery, grouping, missing-alert,
extra-alert or required-identity failure is assigned to this control.

The classifier compares complete observed label sets; it does not strip labels
before execution. Candidate bytes are copied unchanged, hashed on the host and
inside the container, and mounted read-only in a separate directory per candidate.
A label such as instance can affect persistence, so an extra identifying label
is an identity-contract error, not automatically harmless metadata. Pairing by
service is only a diagnostic step; it never changes strict pass/fail or masks
multiple alerts. Missing environment is not treated as a missing detection.

Observed symptoms are recorded separately from the deliberate mutation catalog's
**targeted obligations** (timing, threshold, recovery, grouping). Those tags are
known design intent plus inspected examples, not an automatic causal inference
system for arbitrary future model outputs. Metadata-only or identity-only
mismatches receive no targeted timing/detection tags. Nine focused classifier
regression tests passed, including annotation-only, multiple-alert lists,
identity failures, and rejection of malformed/loader-error diagnostics.

Per-candidate `*-scenarios.json` files include every scenario and timestamp,
expected labels/annotations, strict result, observed symptoms and targeted
obligations. On failures they retain parsed full actual labels and annotations.
On passing assertions the evidence is promtool's exact assertion pass; no
standalone actual-state dump is invented (`actual_from_failure_diagnostic` is
null). Raw tool streams remain available for independent review.

## Errors, corrections and preserved attempts

1. First attempt `20261104T232144.679615Z` exited 2. All reference executions passed,
   but 7 mutation reports were rejected by our diagnostic parser
   because multiple-alert lists contain comma separators. These were recorded
   as validation errors, not counted as behavioural detections. The parser was
   corrected to require valid comma separators and sequential indices, with
   regression tests. No rule, input sequence or expectation changed.
2. Second attempt `20261104T232402.321169Z` exited 2. The parser correction worked,
   but the R03 retained-instance syntax subprocess returned a YAML parse error.
   The same candidate bytes had passed syntax in the first attempt and loaded
   in the next behavioural subprocess. Its cause is **unconfirmed**; reuse of
   a bind-mounted file path was a possible contributor, not an established cause.
   This attempt's syntax error was not counted as behavioural evidence.
3. Final attempt `20261104T232544.081390Z` used a distinct, never-overwritten candidate mount
   and verified container-visible hashes before checks. All 19 candidate syntax
   checks passed, the five references passed, all 13 mutations were rejected,
   and the annotation control was correctly isolated. There were no parser or
   execution errors in this final run.

4. Packaging initially stopped before writing a ZIP because the secret scanner
   matched its own literal private-key-header test string in its Python source.
   The packaging-only check was corrected to require a PEM header followed by
   encoded content. The top-level packager in the ZIP is this corrected version;
   the original version remains in the final run's input snapshot, with its
   original hash. `postrun-packaging-correction.json` records both hashes.
   This change does not touch candidates, fixtures, scoring or execution logs.

All candidate files, specifications, executable fixture contents and expected
outputs are identical across the three attempts. Final raw mismatch diagnostics
agree with the first attempt's raw diagnostics after correct parsing. Earlier
records retain their original summaries, errors and input snapshots. No expected
outcome discrepancy was found. Preservation audit verified 561 existing files.
The earlier stage1-review.zip had already been deleted at the user's request;
it was not recreated or treated as an existing preservation target.

## Files and evidence

- `rules/stage2/R02/` through `R06/`: five reference files, 13 mutations and one
  annotation control, stored in JSON syntax (valid YAML).
- `tests/stage2/R02.test.yml` through `R06.test.yml`: executable synthetic fixtures.
- `tests/stage2/catalog.json`: source table rows, coverage, candidate descriptions
  and known targeted obligations; not generation-prompt material.
- `scripts/build_stage2.py`: deterministic table-to-fixture compilation and
  explicit infrastructure candidate definitions. Use only to rebuild these
  controlled materials; it is not a response-repair tool.
- `scripts/check_stage2.py`: captured execution, immutable per-candidate mounts,
  pinned-version checks and per-scenario analysis.
- `scripts/classify_stage2.py`, `tests/test_stage2_classifier.py`: strict diagnostic
  parsing and classification with regression tests.
- `scripts/package_stage2.py`: local review archive with documented redactions.
- `STAGE2_VALIDATION.md`: this report.

The final run includes input snapshots and SHA-256 hashes, invocation,
commands/arguments, timestamps, versions, stdout, stderr, subprocess exit codes,
runner exit code, per-scenario reports, summary, coverage and preservation audits.
The two earlier attempts are included in the review bundle for transparency.

Create the local review archive with:

```sh
python3 scripts/package_stage2.py results/stage2/20261104T232544.081390Z results/stage2/20261104T232144.679615Z results/stage2/20261104T232402.321169Z
```

The command refuses to overwrite an existing ZIP. `stage2-review.zip` includes
the specifications, recorded validation implementation, corrected packaging
utility and all three supporting attempts.
Credentials, .env files, chat transcripts and unrelated files are excluded.
Sharing-copy replacements for personal project paths and temporary mount paths
are documented in REDACTIONS.md and MANIFEST.json, with original and packaged
hashes. Candidate and fixture bytes remain unchanged. Nothing is pushed.

## Limits and unresolved issues

No surviving mutation or unresolved reference/expected-output failure remains.
The transient second-attempt syntax-read error's underlying cause remains
unconfirmed; its raw evidence is retained. The new isolation/hash checks passed.

This is a small infrastructure pilot with synthetic inputs. The diagnostic
parser is deliberately restricted to the observed pinned promtool format and
fails closed on unfamiliar output. The current candidate catalog uses JSON-
formatted YAML; this runner is not yet a general arbitrary-YAML model-output
scoring harness. Timing/threshold/recovery intent tags apply to these known
mutations only. These limitations must be addressed or frozen explicitly before
experimental model collection; no model outputs have been collected here.

Firing-output assertions do not directly verify every pending state or establish
operational safety. Finite fixtures and deliberate defects cannot establish
complete correctness or model performance. Human review remains necessary.
The official semantics sources remain in requirements/SEMANTICS.md; the compiler
uses the documented [promtool unit-test format](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/),
and grouping/matching follow the [official operator semantics](https://prometheus.io/docs/prometheus/latest/querying/operators/).
