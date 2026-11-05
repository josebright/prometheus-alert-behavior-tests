# Collection results

Status: **halted_uncertain_completion**. Generation requests attempted: **9/18**.
Protocol frozen: **True**. Model: `gpt-6.1-sol` (alias; no immutable
snapshot verified). Current source commit: `28de8721c5e1c32135c29761fa148d038d57fb18`.

This is an **offline interruption audit**, not a new collection run.
Original record: `results/collection/20261105T145211.528182Z`.
The user confirmed Ctrl+C followed by a rerun. The collector process was no longer
running. Original files, response bytes, and the dispatch lock are preserved.
The copied freeze describes the original collection implementation. No request
was retried and no API calls were made for this audit. The separate blocked rerun
made seven metadata/access/token-count calls and zero generation calls.

The runner now detects the existing dispatch lock before preflight and reports
`existing_pilot_blocked` clearly. This post-collection correction does not alter
the frozen code, response extraction, scorer, expected outcomes, or requirements.

- User reported Ctrl+C followed by a second invocation. The original process was confirmed absent; an attempted request has no saved response. No request is resent. The second invocation was blocked by the original dispatch lock.

Selected settings: medium reasoning, Responses API, non-streaming, standard
processing, 8192 capped output tokens including reasoning, 6000 input-token
allowance including overhead, one fresh user message, no tools/history/feedback,
zero retries. The approved budget remains **US$10**; the operational ceiling is
**US$5**. No repeat budget approval is required.

## Actual validation and preflight

Offline unit-test exit: `0`.
Synthetic transport fixture outcomes matched:
**23/23**.
Extracted reference text through pinned scorer: **pass**.
Fixtures cover success, refusal, truncation, empty/missing text, duplicates,
Unicode/CRLF/BOM preservation, multipart text, reasoning-item exclusion, ambiguous
messages, HTTP failures, uncertain completion, and usage/configuration problems.
They are not provider responses or model-performance measurements.

The six prompt files were checked byte-for-byte against the readiness report and
their hashes. The validated requirements/scorer/fixtures remain unchanged. Raw
commands, stdout, stderr, exit codes, input snapshots and hashes are retained.
Metadata/access/token-count requests attempted: **7**.
Account/model access: **verified by metadata retrieval**.
Live input-token counts: **recorded per task**.
A blocked preflight manifest is not a completed freeze; the runner creates a true
immutable freeze only after every live check passes.

## Usage and cost

Reported usage objects: **8**.
Aggregate known usage: `{"input_tokens": 7882, "output_tokens": 546, "total_tokens": 8428}`; null means no API usage was returned.
Estimated known API token cost: **US$0.021224**.
Unknown-cost slots: `["R03-G02"]`.
Actual billing amount: **not queried / unknown**. Estimates are not billing.
For zero generation requests, US$0 is the adapter's generation-cost estimate,
not a measured account balance or invoice.

At verified standard short-context rates of US$2/M uncached input and US$10/M
output, with caching disabled, the conservative 18-slot token-cost bound is:

`18 × ((6000 × 2 + 8192 × 10) / 1,000,000) = US$1.69056`.

This includes reasoning and non-visible output inside the cap, without double
counting. It excludes unrelated account activity, credit purchases and tax.
See [official pricing](https://developers.openai.com/api/docs/pricing) and the
[output-cap semantics](https://developers.openai.com/api/docs/guides/reasoning). Documentation review
must be refreshed after 24 hours before a later collection attempt.

## Slot outcomes

| Slot | Delivery/attempt status | Scoring outcomes |
|---|---|---|
| R01-G01 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
| R02-G01 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
| R03-G01 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
| R04-G01 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
| R05-G01 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
| R06-G01 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
| R01-G02 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
| R02-G02 | response_recorded | response_format=pass, syntax=pass, structural_contract=pass, metadata=pass, required_identity=pass, behavioral=pass |
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

Scoring dimension totals: `{"behavioral": {"pass": 8}, "metadata": {"pass": 8}, "required_identity": {"pass": 8}, "response_format": {"pass": 8}, "structural_contract": {"pass": 8}, "syntax": {"pass": 8}}`.
No result is fabricated for unavailable text. Response format, syntax, structure,
metadata, identity, behaviour and unevaluable outcomes stay separate. Report all,
some or no failures without extending the sample. Repeats are grouped by six tasks,
not 18 independent tasks. Finite synthetic tests do not establish operational safety.

## Files, backup and continuation

Primary record: `results/collection/20261105T145726.219088Z-audit`.
Separate local backup: `.collection-backups/20261105T145726.219088Z-audit`.
The backup is hash-verified and on the same local filesystem, not offsite.
The review archive is `collection-review.zip`; raw evidence is not pushed.
The archive contains original available payloads/text (none if no generation was
attempted), preflight/freeze status, usage/scoring records, selected protocol,
source snapshots and labelled offline validation evidence. Sharing-copy path
redactions and original/packaged hashes are documented inside the ZIP.

The adapter uses only the local environment variable. In the same zsh terminal:

```sh
read -rs 'OPENAI_API_KEY?API key (hidden input): '; printf '\n'
export OPENAI_API_KEY
.venv-stage3a/bin/python scripts/run_collection.py --collect
unset OPENAI_API_KEY
```

Do not paste the key into chat, print it, or put it in a command history entry.
A sibling terminal/process does not automatically inherit a newly exported key.
The command uses the existing budget authorization, but must pass fresh preflight.
Do not bypass a persistent generation-dispatch lock after an attempted pilot.

## Limits

Live transport/account behaviour remains unverified if the key is absent. Model
metadata visibility does not guarantee generation quota/permission. A moving alias
limits reproducibility. Unknown usage/schema or missing optional cache counts
halts conservatively. Offline fixtures cannot establish provider compliance with
caps. Same-volume backups do not protect against disk failure. Original local
records are preserved; sharing copies may redact personal paths. If a credential
is echoed by the provider, its raw body is withheld and the exception is recorded.
Human review remains necessary. No model or setting is silently substituted.

The credential-body handling correction and its revalidation are documented in
`collection/ADAPTER_PROTOCOL.md` under Implementation correction record. Earlier
preflight records remain preserved; no expected experimental outcome was changed.

## Post-collection guard validation

Record: `results/collection-adapter/20261105T145545.977648Z`.
Overall success: `True`; unit-test exit: `0`;
synthetic controls matched: 23/23;
scorer integration: `pass`. This validation includes
the regression test that an existing lock stops before transport or snapshots.
It made no model API calls. The original frozen implementation is retained.
