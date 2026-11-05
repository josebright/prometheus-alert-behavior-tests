# Collection results

Updated 2026-11-05T20:58:49.259286+01:00 (Africa/Lagos). Continuation status: **continuation_complete**.
Original generation attempts: **9**. Continuation generation attempts: **9**.
Saved responses: **17 of 18 planned slots**. All **17 saved responses passed all six
scoring dimensions**: response format, syntax, structural contract, metadata,
required identity, and behaviour. Observed behavioural failures: **0** among the
17 evaluated responses. Remaining unattempted slots: **0**.

**Collection is complete and must not be restarted.**

The researcher interrupted the original run with Ctrl+C after eight saved responses
and an attempt record for R03-G02. The original audit scored those eight responses:
all six scoring dimensions passed for each. R03-G02 has no saved response ID or
response body and remains **completion_unknown_after_interruption**, not evaluated
and not resent. No documented exact-response retrieval could be constructed from
the saved correlation ID.

The approved [continuation amendment](collection/CONTINUATION_AMENDMENT.md) permits
only the nine previously unattempted slots in their original order. This amendment
was made after the eight original results were known. It does not replace outputs,
increase the sample, or seek failures. The model is still the **gpt-6.1-sol alias**;
fixed request settings cannot guarantee that alias weights stayed unchanged.

## Current continuation outcome

No continuation errors recorded.

Continuation metadata/access/token-count requests: **7**.
Continuation frozen for generation: **True**.
Offline preflight passed: **True**.
Original records verified unchanged: **True**.
Collection code commit: `90749447d2c17cb0300fa520a3939376efe15f5f`; new continuation
source snapshots and the uncommitted-file list are recorded separately.

The exact prompts, prepared requests, settings, scorer, requirements and fixtures
were checked against the original freeze. Python and pinned dependencies matched.
The pinned Docker scorer reference control passed. The new offline controls test
eligibility, ordering, locking, SIGKILL, Ctrl+C, duplicate prevention, integrity
drift, uncertain responses, backup failure, and budget reserves. They are synthetic
infrastructure controls, not experimental outputs. Test commands, exit codes,
stdout and stderr are in the continuation record.

## Actual costs, reserves and usage

Known usage from 17 saved responses: `{"input_tokens": 16966, "output_tokens": 1194, "total_tokens": 18160}`.
Estimated original known token cost: **US$0.021224**.
Estimated continuation known token cost: **US$0.024648**.
Combined known token cost: **US$0.045872**.
Combined unknown-cost reserve: **US$0.09392**.
Original unknown slot: R03-G02. Additional unknown-cost slots:
`[]`.

Each unknown-cost request reserves the full **US$0.09392**, including its input
allowance and capped reasoning/output. It is never counted as zero. The initial
combined bound was **US$0.960424**: US$0.021224 known + US$0.09392 unknown reserve
+ nine full request allowances. With no remaining unattempted slots, current
known costs plus the unknown-cost reserve total **US$0.139792**.
The approved budget stays **US$10** and the operational ceiling **US$5**.

These are token-cost estimates and conservative reserves, **not billing**. The
billing amount was not queried. [Verified standard pricing](https://developers.openai.com/api/docs/pricing)
is US$2/M input and US$10/M output; reasoning is already included in output usage.

## All 18 preassigned slots

| Slot | Status | Scoring dimensions |
|---|---|---|
| R01-G01 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R02-G01 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R03-G01 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R04-G01 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R05-G01 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R06-G01 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R01-G02 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R02-G02 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R03-G02 | completion_unknown_after_interruption | not evaluated |
| R04-G02 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R05-G02 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R06-G02 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R01-G03 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R02-G03 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R03-G03 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R04-G03 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R05-G03 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |
| R06-G03 | response_recorded | response_format=pass; syntax=pass; structural_contract=pass; metadata=pass; required_identity=pass; behavioral=pass |

Dimension totals: `{"behavioral": {"pass": 17}, "metadata": {"pass": 17}, "required_identity": {"pass": 17}, "response_format": {"pass": 17}, "structural_contract": {"pass": 17}, "syntax": {"pass": 17}}`.
The unknown slot is not counted as a pass or failure. Repeats are grouped by
six tasks, not 18 independent tasks. Tests use synthetic inputs; passing does not
establish operational safety or directly inspect every internal pending state.
Human review remains necessary. All available outputs are retained unchanged.

## Evidence and execution

- Original: `results/collection/20261105T145211.528182Z`.
- Original audit and scores: `results/collection/20261105T145726.219088Z-audit`.
- Historical report preserved: `results/continuation-history/20261105T153413.832748Z/COLLECTION_RESULTS.md`.
- Continuation: `results/continuation/20261105T195634.925879Z`.
- Separate local backup: `.collection-backups/continuation-20261105T195634.925879Z`.
- New versioned review archive: `collection-review-20261105T195634.925879Z.zip`.

The original dispatch lock remains unchanged. An additional process lock and
persistent continuation/per-slot claims prevent concurrent dispatch and replay.
Earlier archives remain unchanged. The ZIP contains original, audit, amendment,
and continuation evidence. Sharing-copy path redactions and cache exclusions are
listed inside it; original response bytes are unchanged. Same-disk backups do not
protect against disk loss. No raw logs are pushed.

Collection is complete. The persistent dispatch claims must remain in place;
do not restart collection or resend the uncertain R03-G02 request.
