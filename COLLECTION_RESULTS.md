# Collection results

Updated 2026-11-05T16:43:22.879478+01:00 (Africa/Lagos). Continuation status: **preflight_blocked**.
Original generation attempts: **9**. New continuation attempts: **0/9**.
Unchanged response texts available across the pilot: **8/18**.

The researcher interrupted the original run with Ctrl+C after eight saved responses
and an attempt record for R03-G02. The original audit scored those eight responses:
all six scoring dimensions passed for each. R03-G02 has no saved response ID or
response body and remains **completion unknown**. It was not resent. No documented
exact-response retrieval could be constructed from the saved correlation ID.

The approved [continuation amendment](collection/CONTINUATION_AMENDMENT.md) permits
only the nine previously unattempted slots in their original order. This amendment
was made after the eight original results were known. It does not replace outputs,
increase the sample, or seek failures. The model is still the **gpt-6.1-sol alias**;
fixed request settings cannot guarantee that alias weights stayed unchanged.

## Current continuation outcome

- OPENAI_API_KEY absent in this process; no continuation API requests made

Continuation metadata/access/token-count requests: **0**.
Continuation frozen for generation: **False**.
Offline preflight passed: **True**.
Original records verified unchanged: **True**.
Current code commit: `e5c9b0d4723fc94068f7204dfdbe067254edcfc1`; new continuation
source snapshots and the uncommitted-file list are recorded separately.

The exact prompts, prepared requests, settings, scorer, requirements and fixtures
were checked against the original freeze. Python and pinned dependencies matched.
The pinned Docker scorer reference control passed. The new offline controls test
eligibility, ordering, locking, SIGKILL, Ctrl+C, duplicate prevention, integrity
drift, uncertain responses, backup failure, and budget reserves. They are synthetic
infrastructure controls, not experimental outputs. Test commands, exit codes,
stdout and stderr are in the continuation record.

## Actual costs, reserves and usage

Known usage from 8 saved responses: `{"input_tokens": 7882, "output_tokens": 546, "total_tokens": 8428}`.
Estimated original known token cost: **US$0.021224**.
Estimated continuation known token cost: **US$0**.
Combined known token cost: **US$0.021224**.
Combined unknown-cost reserve: **US$0.09392**.
Original unknown slot: R03-G02. Additional unknown-cost slots:
`[]`.

Each unknown-cost request reserves the full **US$0.09392**, including its input
allowance and capped reasoning/output. It is never counted as zero. The initial
combined bound was **US$0.960424**: US$0.021224 known + US$0.09392 unknown reserve
+ nine full request allowances. Current known costs plus reserves plus all
remaining unattempted allowances total **US$0.960424**.
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
| R04-G02 | not_attempted | not evaluated |
| R05-G02 | not_attempted | not evaluated |
| R06-G02 | not_attempted | not evaluated |
| R01-G03 | not_attempted | not evaluated |
| R02-G03 | not_attempted | not evaluated |
| R03-G03 | not_attempted | not evaluated |
| R04-G03 | not_attempted | not evaluated |
| R05-G03 | not_attempted | not evaluated |
| R06-G03 | not_attempted | not evaluated |

Dimension totals: `{"behavioral": {"pass": 8}, "metadata": {"pass": 8}, "required_identity": {"pass": 8}, "response_format": {"pass": 8}, "structural_contract": {"pass": 8}, "syntax": {"pass": 8}}`.
Unknown and unattempted slots are not passes or failures. Repeats are grouped by
six tasks, not 18 independent tasks. Tests use synthetic inputs; passing does not
establish operational safety or directly inspect every internal pending state.
Human review remains necessary. All available outputs are retained unchanged.

## Evidence and execution

- Original: `results/collection/20261105T145211.528182Z`.
- Original audit and scores: `results/collection/20261105T145726.219088Z-audit`.
- Historical report preserved: `results/continuation-history/20261105T153413.832748Z/COLLECTION_RESULTS.md`.
- Continuation: `results/continuation/20261105T154316.913502Z`.
- Separate local backup: `.collection-backups/continuation-20261105T154316.913502Z`.
- New versioned review archive: `collection-review-20261105T154316.913502Z.zip`.

The original dispatch lock remains unchanged. An additional process lock and
persistent continuation/per-slot claims prevent concurrent dispatch and replay.
Earlier archives remain unchanged. The ZIP contains original, audit, amendment,
and continuation evidence. Sharing-copy path redactions and cache exclusions are
listed inside it; original response bytes are unchanged. Same-disk backups do not
protect against disk loss. No raw logs are pushed.

The continuation has not entered dispatch. To run the explicit continuation from
the project directory in a local zsh terminal, supply the key without sharing it:

```sh
read -rs 'OPENAI_API_KEY?API key (hidden input): '; printf '\n'
export OPENAI_API_KEY
.venv-stage3a/bin/python scripts/continue_collection.py --collect
unset OPENAI_API_KEY
```

This command uses the existing budget approval and reruns preflight. It packages
its outcome automatically. Do not run the original `run_collection.py` command.
