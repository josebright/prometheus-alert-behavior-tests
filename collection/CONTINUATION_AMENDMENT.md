# Protocol amendment: continuation-v1

Authorized by the researcher on 5 November 2026 (Africa/Lagos), after the
interruption and inspection of eight completed outputs. This is a disclosed
post-interruption amendment, not part of the original pre-collection freeze.
It does not expand the sample or replace poor answers, duplicates, or failures.

The original run `results/collection/20261105T145211.528182Z` was interrupted with
Ctrl+C. Eight responses were saved. R03-G02 was journalled before dispatch but has
no saved response or response ID. A second invocation was blocked by the original
dispatch lock after seven metadata calls and zero generation calls. The offline
audit is `results/collection/20261105T145726.219088Z-audit`.

All original inputs, freeze manifests, responses, scores, reports, audit records,
the original dispatch lock, and existing review archives remain unchanged.
The historical current report is copied under `results/continuation-history/`.
`continuation-v1.json` identifies the exact source records and preservation hashes.

## Authorized continuation

Only these nine previously unattempted slots may be dispatched, once, in order:

1. R04-G02
2. R05-G02
3. R06-G02
4. R01-G03
5. R02-G03
6. R03-G03
7. R04-G03
8. R05-G03
9. R06-G03

R03-G02 remains completion unknown and is never resent. The documented
[response retrieval endpoint](https://developers.openai.com/api/reference/cli/resources/responses/methods/retrieve)
requires a response ID. This attempt saved only a request and a client-request
correlation ID, with `store: false`. No response ID is present in the original or
audit records. These identifiers are not interchangeable. Therefore no documented
exact-response retrieval can be constructed from the available records; no
retrieval or speculative generation is attempted.

## Unchanged experiment and separate code

Use original prepared request bytes and the same six prompt files. Verify their
hashes, current readiness report, model settings, requirements, scorer, fixtures,
dependencies, Python version, and Prometheus digest against the original freeze.
The frozen request uses gpt-6.1-sol, medium reasoning, standard processing,
non-streaming Responses API, maximum 8192 output tokens including reasoning,
6000 input tokens including overhead, no tools, no history, no repository access,
no scoring feedback, and no automatic retries. The model name remains an alias;
an unchanged alias does not prove identical underlying weights across the gap.

The new runner, continuation policy, amendment, tests, packaging code, current
commit, and uncommitted files are snapshotted separately. The original frozen
transport, text extraction, scoring code, and synthetic fixtures are unchanged.
Current pricing is rechecked, and model access and six input counts must pass
again before generation. A new continuation freeze links to the original freeze.
Missing credentials block live preflight; they do not consume a generation slot.

## Dispatch and interruption policy

The explicit command is:

```sh
.venv-stage3a/bin/python scripts/continue_collection.py --collect
```

It never deletes, replaces, or bypasses the original dispatch lock. That lock
continues to prevent the original runner from starting another pilot. A separate
OS advisory process lock prevents concurrent continuation processes. The process
lock is released by the OS on exit, including SIGKILL; its file is never deleted.
A persistent continuation claim and exclusive per-slot attempt files survive
process exit and prevent any redispatch. The whole continuation is refused after
it enters dispatch; there is no implicit resume after another interruption.

Each attempt is journalled and backed up before dispatch. Ctrl+C and SIGTERM cause
a halt and mark an active attempt uncertain. SIGKILL cannot be finalized in-process;
the persistent claims still refuse a second dispatch session. Any further uncertain
completion, provider/configuration error, model mismatch, accounting uncertainty,
or infrastructure/budget risk halts the continuation. No poor answer is retried.
Each request is sent serially. Scoring starts only after generation stops.

## Budget amendment

The existing US$10 approval remains valid; the operational ceiling stays US$5.
At [standard pricing](https://developers.openai.com/api/docs/pricing), US$2/M input
and US$10/M output with caching disabled, a request's full token-cost allowance is
`(6000*2 + 8192*10)/1,000,000 = US$0.09392`.

Reserve R03-G02's entire US$0.09392 as potentially spent. It is not counted as zero.
The eight saved usage records total US$0.021224 in estimated token cost. Therefore:

`0.021224 + 0.09392 + 9*0.09392 = US$0.960424`.

Before each dispatch, add known original and continuation costs, full allowances
for every unknown-cost attempt, and full allowances for remaining slots. Halt if
that total exceeds US$5. Output usage already includes reasoning; do not charge
reasoning twice. Estimates and reserves are reported separately from billing.

## Evidence, reporting, and limitations

Keep original payloads and extracted text unchanged, including failures and
duplicates. Report format, syntax, structure, metadata, required identity,
behaviour, and unevaluable outcomes separately. Keep R03-G02 in the 18-slot
denominator as unknown; do not treat the nine resumed slots as a new sample.
Repeated outputs remain grouped by six tasks, not 18 independent tasks.

Offline validation uses clearly labelled synthetic controls for eligibility,
ordering, concurrent locking, SIGKILL, Ctrl+C, duplicate dispatch, integrity drift,
budget reserves, and uncertain responses. These controls are not model outputs.
The eight original responses passed the frozen checks; that observation was known
before this amendment. Continuing only the preassigned unattempted slots is not
sampling to obtain failures. Finite synthetic tests do not prove operational safety
or directly inspect every internal pending state. Human review remains necessary.

The current report is regenerated as a factual combined status report, without
stale conditional boilerplate. Each review ZIP receives a unique versioned name
and includes original, audit, amendment, and continuation evidence, with hashes
and documented sharing-copy redactions. Older archives are never overwritten or
deleted under this amendment. Independent local backups share the same disk and
are not offsite disaster recovery. Raw logs and response payloads are never pushed.

Implementation review after the first blocked preflight added an explicit check
for any surviving per-slot claim even when the session claim is absent, plus its
regression test. Dispatch claims are copied into the run backup and review ZIP,
alongside the unchanged original lock. The first validation record and archive
remain intact. No request, prompt, expected outcome, or original record changed.
