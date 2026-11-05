# Collection protocol — 18 planned outputs

**Status: DRAFT / NOT FROZEN / COLLECTION NOT AUTHORIZED.** No generation requests
have been made. One fixed model will be used; its exact identifier remains
**PENDING SELECTION**. Model-dependent settings and budget are also pending.
This document prepares the protocol; it does not select a model or authorize
spending. Do not run collection until the freeze gate below is satisfied.

The current implementation baseline is commit
`c9f298e30478bba8de8fa43bcd60802aba0a2140`. The historical wording in
`STUDY_PLAN.md` and the requirement files remains unchanged. Stage 2 and Stage 3A
implementation happened after those specification drafts. The new protocol
uses the approved behaviours and the validated, unchanged Stage 3A scorer.

## Scope, prompts, and isolation

Research question: do behavioural tests expose requirement violations in
model-generated Prometheus alert rules that syntax checks miss?

There are six task groups, R01–R06, and three separate generations per task.
The repeats are grouped by task: **six task groups, not 18 independent tasks**.
Fresh request contexts do not establish statistical independence. This is a
small descriptive pilot, with no representativeness or operational-safety claim.

The six exact standalone prompt files are `prompts/collection-draft/R01.txt`
through `R06.txt`. Each contains its full task contract and the same common
output contract. `collection/COMMON_OUTPUT_CONTRACT.txt` is the review source
for the repeated common section; it is not a seventh generation prompt.
`COLLECTION_READINESS.md` reproduces all six exact prompt texts for review.
`collection/protocol-manifest.json` records their SHA-256 hashes and byte counts.

Send exactly the selected task file as one user message, unchanged, on every
repeat of that task. Do not append slot IDs, round numbers, dates, prior responses,
results, or extra task hints. Use no researcher-added system/developer instructions,
tools, browsing, retrieval, files, persistent conversation, or previous-response
link. Do not expose the repository, this plan, readiness report, common-contract
source separately, other prompts, reference rules, controls, tests, scenario
sequences/tables, expected firing outputs, worked examples, or scorer diagnostics
to the generation model. Provider-required message-envelope details still need
selection and review; any unavoidable instruction wrapper must be recorded
verbatim and approved before freezing.

All metric observations used in evaluation are controlled synthetic fixtures,
not production telemetry. References and deliberate mutations remain labelled
infrastructure controls, outside the 18 collection slots and all model-performance
counts. No pilot/test model calls are authorized by this protocol draft.

## Fixed order and preassigned slots

Run serially, in three rounds. Every row below is a separate request with a fresh
context and one intended answer. A single request for three answers is not allowed.
The model identifier and all generation settings are identical across all slots;
the task prompt is identical across its three repeats.

| Order | Round | Task | Slot |
|---:|---:|---|---|
| 1 | 1 | R01 | R01-G01 |
| 2 | 1 | R02 | R02-G01 |
| 3 | 1 | R03 | R03-G01 |
| 4 | 1 | R04 | R04-G01 |
| 5 | 1 | R05 | R05-G01 |
| 6 | 1 | R06 | R06-G01 |
| 7 | 2 | R01 | R01-G02 |
| 8 | 2 | R02 | R02-G02 |
| 9 | 2 | R03 | R03-G02 |
| 10 | 2 | R04 | R04-G02 |
| 11 | 2 | R05 | R05-G02 |
| 12 | 2 | R06 | R06-G02 |
| 13 | 3 | R01 | R01-G03 |
| 14 | 3 | R02 | R02-G03 |
| 15 | 3 | R03 | R03-G03 |
| 16 | 3 | R04 | R04-G03 |
| 17 | 3 | R05 | R05-G03 |
| 18 | 3 | R06 | R06-G03 |

`collection/slots.json` contains these same 18 slots and the matching prompt
hashes. Every slot currently has status `not_attempted`; there are no actual
request IDs or response results. The fixed order is disclosed and may introduce
time/order effects. It must not be shuffled after seeing answers.

Exactly 18 slots are planned, not 18 guaranteed responses. Allow at most one
generation dispatch per slot. Disable automatic SDK, HTTP, proxy, and application
retries. Never repair, regenerate, replace duplicate answers, continue truncated
answers, request clarification from the generation model, or provide scoring
feedback. No retries for poor answers, transport failures, rate limits, or server
errors occur under this baseline protocol. Any additional generation requires
an explicit amendment and authorization, preserves the original attempt, and is
reported outside the original 18 slots, never as a replacement.

Complete collection (or document a halt) before using scores to interpret results.
Do not adapt later requests to earlier answers or diagnostics. If a scorer needs
an infrastructure fix, preserve all original responses and old scores, version
the correction, and rescore the same stored responses consistently; never collect
more favourable answers. Re-execution of offline scoring is not a new generation
and must get a new local scoring record with its reason.

## Dispatch, exceptional outcomes, and stopping rules

Write an append-only `attempt_started` record and sanitized exact request body
before dispatch, with a unique local attempt ID and client correlation ID. A slot
whose request may have left the client remains attempted; do not silently return
it to the queue. Capture the provider request/response IDs if actually available.
Never invent IDs, usage, timestamps, completion status, costs, or output text.

| Event | Required treatment |
|---|---|
| Normal complete answer | Preserve raw payload and text, then score unchanged text offline. |
| Duplicate text/payload | Preserve as another observed answer in its original slot; record hash matches and do not replace it. |
| Refusal | Preserve the full refusal and any visible answer text. Record refusal separately. If visible text exists, score it unchanged; absence of text is not fabricated as YAML. A refusal is not silently treated as a successful delivered rule merely because another dimension passes. |
| Truncation/incomplete response | Preserve all received bytes and any complete decoded text fields; record status and finish/incomplete reason. Score available text unchanged, explicitly labelled partial. Do not append a newline, close brackets/fences, or ask for continuation. If a partial response happens to pass, retain that score alongside its incomplete delivery status. |
| Missing/null/non-text answer | Preserve payload and reason; do not synthesize a candidate file. Mark response availability/format as missing or non-text, and scorer dimensions not evaluated. |
| Present but empty string | Preserve a zero-byte text file with its hash and pass it unchanged to the scorer; distinguish this from a missing field. |
| Multiple competing answer messages or alternative choices | Preserve each separately and mark extraction ambiguous. Do not choose the best one, splice alternatives, or score only a favourable answer. No single candidate score is assigned until an approved extraction-policy amendment, applied consistently to all affected stored payloads. |
| Known HTTP/provider error | Preserve status, response body and allowlisted diagnostic metadata. Record a transport/provider outcome, not a fabricated rule failure. No retry. Continue to the next slot only if the error is isolated and the remaining frozen budget/preconditions still hold. |
| Timeout/disconnect or uncertain completion | Preserve all available evidence, mark completion/charge uncertain, and halt further dispatch pending reconciliation. Never resend the generation request. A later read-only status lookup, if available and authorized, may attach the original completed payload to the same slot; log the lookup, without creating a new generation. |
| Local failure before dispatch | Record `not_dispatched` with evidence. Halt until resolved. Do not invent an attempted generation. Resume that slot only if it is established that no request was sent; otherwise use uncertain-completion handling. |
| Authentication/configuration fault, model mismatch/unavailability, budget risk, or repeated service fault | Halt, retain all attempted outcomes, and mark remaining slots not attempted with the reason. Do not switch model/settings or exhaust the budget trying to force 18 responses. |

Preserve arrival timestamps and later reconciliation timestamps separately. Mark
provider-reported versus locally inferred status explicitly. A timeout alone
cannot prove that the provider did not generate or charge. Unknown usage/cost
stays unknown; it is not zero. Reserve worst-case allowed cost for uncertain
attempts before any continuation. The exact numerical limits must be selected
before collection; no cost estimate is invented here.

## Exact payload and text preservation

The future collection adapter is not implemented or validated in this stage.
Its endpoint-specific field mapping must be approved before freeze. The logical
policy below is fixed for this draft; API field names remain pending:

1. Save the original response-body bytes before deserialization. Do not call a
   reserialized SDK object a raw payload. Keep any parsed/normalized metadata as
   a separate derivative. This draft proposes non-streaming delivery to simplify
   byte preservation; streaming would require a reviewed event-assembly protocol.
2. For one unambiguous assistant answer message, copy the designated visible
   answer-text content. If that one message has multiple text content blocks,
   concatenate every such block in provider order with **no inserted separator**;
   preserve all blocks and their source field paths separately. Do not include
   reasoning summaries, tool output, refusal-only fields, or other non-answer
   items as rule text. Never choose among alternative messages/choices.
3. Serialize the decoded answer string to UTF-8 exactly once, preserving every
   character, whitespace, line ending, BOM, and trailing newline as returned in
   that string. JSON string unescaping is transport decoding, not YAML repair;
   the raw JSON payload has a separate hash. If lossless text decoding is not
   possible, record an extraction limitation; do not use replacement characters.
4. Save the unchanged candidate bytes and SHA-256 hash. Do not trim, normalize
   Unicode/newlines, strip Markdown fences, extract a YAML substring, reformat,
   rename alerts, add/remove labels or annotations, or fix any expression.
5. Keep originals read-only and use separate derived copies/records for scoring.
   Preserve every attempted slot, including malformed, refused, empty, duplicate,
   incomplete and unevaluable outputs. Any sharing-copy redactions must be
   documented with original and packaged hashes; originals stay intact.

Within an ignored local `responses/<collection-id>/<slot-id>/` directory, retain:

- Sanitized exact request body, prompt file/hash, slot/task/round/order, local
  attempt and client correlation IDs, fixed model requested, actual returned
  model/version identifiers, endpoint and client/SDK version, and all explicit
  settings plus documented omitted/default/unsupported settings.
- Original response-body bytes; exact text bytes if present; original individual
  text blocks and extraction field paths; response/refusal/incomplete/error status;
  provider request and response IDs; HTTP status; usage as returned (including
  supported input/output/reasoning/cache categories), or explicit null if absent.
- Start/end/receipt times in UTC with offsets, monotonic elapsed time where
  available, and separate server timestamps. Human-facing reports may use
  Africa/Lagos (UTC+01:00) with the timezone stated. Clock sources are recorded.
- SHA-256 hashes, byte counts and media types for requests, payloads, extracted
  text and metadata; a non-self-referential file manifest; immutable prompt/scorer/
  fixture version references and current collection commit; all offline scorer
  commands, exit codes, stdout/stderr, outcome dimensions and per-scenario results.

Use explicit allowlists for metadata. Do not record authentication headers,
API keys, cookies, credentials, environment dumps or secret-bearing debug traces.
If a transport exposes raw headers, retain only approved identifiers/status/usage
metadata; do not persist the whole header block. No credential access is necessary
for drafting or offline verification. No credentials were accessed in this stage.
Raw evidence remains local/ignored and is not pushed. Backup/retention location
must be chosen before collection, so gitignored originals are not the only copy.

## Scoring and reporting

Use the unchanged Stage 3A scorer and frozen task fixture for the same task ID.
Invoke it only on actually available, unambiguously extracted text. Record raw
process results separately from classification. Run syntax checks on the unchanged
candidate, including malformed text. Syntax-accepted candidates are evaluated
when parsing/loading permits, even if a structural violation is already known.

Keep separate response availability/format, syntax, structural-contract, metadata,
required-identity, behavioural, and unevaluable fields. Transport/provider failure,
refusal and truncation flags accompany these fields; they must not be collapsed
into a single behavioural failure count. Distinguish assertion mismatches,
candidate evaluation errors, inspection/diagnostic limitations, and Docker/scorer
infrastructure failures. Unknown diagnostics are never a pass.

Record full exact-output assertion results, then the scorer's observed symptoms.
Metadata-only and identity-only defects are not automatically timing or detection
failures. Missing service identity can make attribution unevaluable. Do not infer
a mutation's intended obligation for an arbitrary answer. Firing assertions do
not directly verify all internal pending states. Passing finite synthetic tests
does not establish operational safety.

Publish descriptive counts whether **all, some, or none** of the outputs fail,
including zero syntax-missed behavioural violations if that is what is observed.
Do not suppress results, replace duplicates, alter prompts, adjust expectations,
or extend the sample to obtain a preferred result. Report per task out of its
three planned slots and overall out of 18 planned slots: dispatched requests,
known/uncertain completion, delivered payloads, available text, duplicate text,
refusals, truncations, each scoring dimension, and unevaluable/not-attempted cases.

For the primary descriptive syntax-missed behavioural proportion, the denominator
is syntax-accepted candidates with an evaluable behavioural result (`pass` or
`fail`); the numerator is those with behavioural `fail`. Report numerator and
denominator, never turn an empty denominator into 0%. Exclude candidate evaluation errors, service-attribution ambiguity, and diagnostic
or infrastructure failures that prevent behavioural assessment; disclose each
exclusion separately. If structural inspection alone is unevaluable but behaviour
was independently evaluated as pass/fail, keep that behavioural observation in
the denominator and explicitly flag the structural limitation. Do not collapse
a per-dimension outcome into an overall-score shortcut. Report strict
full-output mismatches and metadata/identity defects in separate tables. Include
all scorable delivered text regardless of refusal/truncation flags, show those
flags, and additionally stratify completed versus incomplete delivery. Do not
claim that this conditional ratio covers slots with no text or unknown completion.

Keep counts of fresh generation attempts and additional non-generation retrievals
separate. No independence-based confidence intervals, significance claims, or
broad model-ranking conclusions are justified by these six purposeful task groups.

## Freeze gate and outstanding decisions

`collection/settings.pending.json` contains explicit nulls for unresolved choices.
Null means **not selected**, not an API default and not zero cost. Before dispatch:

- Select exactly one provider/model identifier and, where available, an immutable
  model snapshot. If only a moving alias is available, approve and disclose that
  limitation and the collection window; record the actual returned identifiers.
- Select endpoint/API version, SDK/client and version, exact message envelope,
  response format and text-field mapping; confirm no tools/state/history and one
  answer. Document which settings the selected model supports. No silent fallback.
- Select maximum output tokens, sampling controls (temperature/top-p or supported
  alternatives), reasoning/verbosity controls, seed policy if supported, stop
  sequences, service tier, storage/cache policy and every explicit or omitted
  default. Use the same settings across tasks/rounds. Defaults can change: record
  their documentation/date and uncertainty rather than claiming they are pinned.
- Select request/overall timeouts, serial pacing, maximum input/output and total
  token allowances, exact monetary ceiling/currency, pricing basis/date, reserve
  for uncertain charges, and stop-before-dispatch budget checks. Budget for all
  18 slots without requiring a nineteenth generation. Do not estimate a total
  until model/pricing/settings are selected.
- Choose local evidence storage/backup/retention arrangements. Implement and
  validate the collection adapter offline with labelled transport fixtures,
  including raw payload preservation, text extraction and disabled retries.
  Offline transport fixtures are not additional model generations.
- Review all six exact prompts and the scorer-support disclosures. The byte/token/
  nesting limits and inspection-parser limitations remain explicit unevaluable
  outcomes, not newly invented behavioural obligations. No oracle content is sent.
- Record the final approved collection commit, hashes of all prompts/requirements/
  scorer/fixtures/dependency locks, tool versions, image digest, settings and
  extraction policy, and any relevant uncommitted files. Resolve or explicitly
  archive relevant uncommitted content; the current draft is not a clean freeze.
- Obtain explicit authorization for the selected budget and collection execution.
  Then write a new immutable freeze manifest referencing this draft; never relabel
  the current snapshot as if it had already been frozen.

No choice above is inferred from installed credentials, account access or model
availability. This preparation creates no API client and makes no generation,
credential, pricing/account or model-discovery calls. Existing scorer, fixtures,
requirements and execution records are preserved. No push is part of this task.

## Documentation basis

The request-ID and returned-model recording policy is informed by the
[official API overview](https://developers.openai.com/api/reference/overview),
which describes request correlation and variation between model snapshots.
The [official Python SDK documentation](https://developers.openai.com/api/reference/python)
documents retry behaviour; a future adapter must explicitly disable retries
rather than assume a one-call interface sends one request. These are documentation
checks, not endpoint/model selection. Endpoint-specific response schema and
capabilities will be rechecked after selection; no schema support is assumed now.
