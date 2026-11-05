# Selected collection adapter protocol

This supplements the preserved draft plan; it does not rewrite its prompts,
requirements, scorer, fixtures or historical pending-settings snapshot. The user
selected OpenAI `gpt-6.1-sol`, medium reasoning, non-streaming Responses, standard
processing, 8192 output tokens, 6000 total input tokens per request, and approved
US$10. The operational ceiling is US$5. That approval is already granted.

## API review and request

Reviewed 5 November 2026. `api-review.json` records exact source URLs, rates,
review timestamp and assumptions. It expires after 24 hours for live dispatch;
refresh official documentation and the record before later execution.

- [Model reference](https://developers.openai.com/api/docs/models/gpt-6.1-sol):
  medium reasoning is supported. Only the alias was verified; no immutable dated
  snapshot is assumed. Request exactly this alias and halt if the returned model
  differs, including an unverified dated identifier. Never substitute a model.
- [Supported settings](https://developers.openai.com/api/docs/guides/latest-model):
  do not send temperature, top_p, top_logprobs or requested log probabilities with
  medium reasoning. No seed/stop support is assumed. Omitted/default fields are
  itemized in `settings.selected.json`, not given invented effective values.
- [Responses reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create):
  one user message containing exact prompt bytes decoded as UTF-8; no researcher
  instructions, prior response, conversation or tools. Use `service_tier=default`,
  `stream=false`, `background=false`, `store=false`, `tool_choice=none`, empty tools,
  plain text with medium verbosity, disabled input truncation, medium effort and
  standard reasoning mode. The latter prevents pro-mode billing. No server-hosted
  multi-agent mode is enabled. Exact request fields are in the selected settings.
- [Token counting](https://developers.openai.com/api/docs/guides/token-counting):
  before generation, count each of the six requests using the documented input
  token endpoint with the same model/input/reasoning/text/tool fields. Require a
  valid count <=6000, including structural overhead. Character-based estimates
  are not used. Counts are metadata preflight calls, not model generations.
- [Reasoning/token limits](https://developers.openai.com/api/docs/guides/reasoning):
  max_output_tokens limits total generated output, including reasoning and hidden
  formatting tokens. Reasoning usage is already inside output_tokens, never added
  again. An incomplete answer can consume budget without producing visible text.
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching):
  explicit cache mode with no breakpoints disables cache reads/writes. The adapter
  sends `prompt_cache_options={"mode":"explicit"}` and no breakpoints or prewarm.
  Unexpected or unknown cache usage halts rather than assuming a zero surcharge.
- [Model metadata](https://developers.openai.com/api/reference/resources/models/methods/retrieve):
  verify authenticated retrieval of the exact model without test generation.
  Metadata visibility is not a quota/Responses-permission guarantee. A generation
  authorization or configuration error still halts with no retry.

The global endpoint is fixed to api.openai.com. Environment-based alternate hosts,
proxies and redirects are not used. The sole credential is OPENAI_API_KEY read
inside the process; its value never enters argv, request-body files, stdout,
exception messages or recorded headers. No .env or credential files are read.
No SDK is added: the transport is Python 3.14.6 standard-library HTTPS with verified
TLS. Existing PyYAML 6.0.3 and promql-parser 0.11.0 remain pinned for the scorer.
The interpreter/dependencies and all source hashes are included in each manifest.

## Budget

Official [standard pricing](https://developers.openai.com/api/docs/pricing):
US$2 per million uncached input tokens and US$10 per million output tokens for
this short-context configuration. Caching, tools, pro execution and regional/fast
processing are not enabled. The bound is:

`18 × ((6000 × 2 + 8192 × 10) / 1,000,000) = US$1.69056`.

Per slot: US$0.09392. This is below US$5 and within the approved US$10.
Each pre-dispatch check reserves the full bound for every remaining slot.
The exact API usage object is retained; an estimated cost is computed only from
valid reported counts. Missing cache/usage data, excess input/output, a processing
mismatch, or other budget uncertainty halts. Report known estimated cost and
unknown-cost slots separately. Never present estimates as a billing statement;
taxes, purchased credits and unrelated account charges are outside this estimate.

## Extraction and preservation

The original HTTP response body is retained byte-for-byte, including whitespace
and JSON escapes, before strict JSON parsing. Only selected response headers are
recorded: x-request-id, content-type, date, openai-version and openai-processing-ms.
No auth headers, cookies or environment dumps. Duplicate JSON keys/nonstandard
constants/invalid UTF-8 prevent trusted extraction; raw bytes are still retained.

A single assistant message is eligible. Ignore reasoning items for candidate text,
but keep them in the original response. Concatenate all output_text blocks of that
one message in provider order without an inserted separator. Save each source
field path and block as well. Preserve Unicode, BOM, CRLF, whitespace and final
newlines. Refusal content is retained as refusal metadata, never substituted for
missing answer text. Multiple assistant messages are ambiguous, not an invitation
to select the best answer. Unknown item types fail closed. Empty text creates an
empty file; missing text creates no candidate. Truncated or refusal-associated
visible text is scored unchanged with delivery flags retained.

If an API error echoes the exact configured credential, no body containing that
credential is written: record its hash/length and a credential-withheld flag, then
halt. This explicitly documented privacy exception is not lossless raw-body
preservation and cannot be reported as such. Exception messages are not logged.

Every network operation gets a new directory, exact sanitized request body,
unique client correlation ID, wall-clock timestamps and monotonic elapsed time.
An attempted record is written/fsynced and backed up before sending. The transport
performs one send: no automatic retries, redirects, fallback models or replacement
generations. Partial bodies captured before a timeout/read error are preserved;
completion stays uncertain even if the available body happens to contain text.
An abrupt process termination can leave an attempt record without a body: that
slot is uncertain and is never automatically replayed.

## Preflight, freeze, dispatch and scoring

The runner verifies prompt bytes against the readiness report and checks original
baseline hashes. It executes labelled offline fixtures and a reference extraction
through the unchanged pinned scorer. It checks settings/pricing freshness, budget,
credential presence, exact model metadata and six input counts. A missing key or
failed check produces an immutable *blocked preflight* manifest, not a completed
freeze. No generation follows a blocked preflight.

Once all checks pass, create an immutable freeze manifest with settings, model
alias limitation, docs/pricing, prompts, extraction policy, source/dependency/
fixture hashes, preflight results, actual commit ID, and snapshots of relevant
uncommitted implementation files. No freeze claim is based on commit ID alone.
The original scorer version and pinned Prometheus digest are included.

A persistent generation-dispatch lock prevents rerunning this authorization as
another pilot. Never delete it merely to bypass an uncertain attempt. Serially
execute only the existing 18 slots in three R01–R06 rounds. Duplicates, refusals,
truncations and malformed/empty answers are retained, not replaced. This adapter
conservatively halts on every HTTP/provider error (including 429/5xx), uncertain
completion, model/settings/usage mismatch, unexpected schema, backup failure or
budget risk. Known extraction ambiguity can be retained without selecting text.

Only after collection completes or halts, score every available unambiguous text
using the preserved scorer snapshot and original task fixture. No scores or
responses enter later prompts. Keep response/format, syntax, structural, metadata,
identity, behavioural and unevaluable outcomes separate. There is no guaranteed
quota of failures; report all, some or none without expanding the sample.

Primary originals: `results/collection/<run-id>/`. Verified backup:
`.collection-backups/<run-id>/`, independently copied with hashes, on the same
local filesystem. This meets local-copy separation, not offsite/disaster recovery.
Both are excluded from Git. No old run is overwritten. Live resume requires a
review of the persistent guard and attempt records; the adapter has no automatic
resume or resend option. This limitation prevents accidental extra generations.

## Commands and local key setup

Offline validation (no provider calls):

```sh
.venv-stage3a/bin/python scripts/validate_collection_adapter.py --with-scorer
```

With Docker running, configure the key in the same local zsh terminal without
pasting it into chat or shell history:

```sh
read -rs 'OPENAI_API_KEY?API key (hidden input): '; printf '\n'
export OPENAI_API_KEY
.venv-stage3a/bin/python scripts/run_collection.py --collect
unset OPENAI_API_KEY
```

A different terminal/process does not inherit a newly exported key automatically.
Do not print the variable. No repeat budget approval is required. After a successful
or blocked run, package that specific directory using `scripts/package_collection.py`.
A future generation run must still pass fresh preflight and must not bypass a prior
live-dispatch lock. Human review remains necessary; offline transport fixtures are
synthetic infrastructure controls, not model outputs or performance evidence.

## Implementation correction record

The initial preflight record `results/collection/20261105T121855.183202Z`
passed offline validation and stopped with no configured key and zero provider
requests. Subsequent code review found that inspecting a deliberately withheld
credential-echoing body (`None`) could raise an exception instead of returning an
explicit halted outcome. The inspector now returns that halted outcome, and the
existing credential-echo unit test also checks it. No expected fixture outcome,
requirement, prompt, scorer or behavioural test was changed.

Revalidation in `results/collection/20261105T122036.277369Z` passed all 23 transport
fixtures, 12 unit tests and the extracted-reference scorer integration. It also
stopped before any provider request because the key was absent. Both original
records and their backups are preserved. The final packaging preflight repeats
these checks with this correction record included in its input snapshot.
