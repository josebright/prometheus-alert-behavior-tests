# Prompt assembly and contract audit

Status: draft for human review. Only the six task `.txt` files are model-visible
inputs. This audit, manifests, plan, readiness report, source files and evidence
must not be included in a request. Prompts are already gitignored; the readiness
report is an exact review copy, not a model attachment.

## Source allowlist and edits

| Prompt | Allowed source | Assembly treatment |
|---|---|---|
| R01 | R01 opening behavioural paragraph and alert/label definitions; common observation/schema conventions | Restates the generic contract and identity, excluding all sequences, named sample services, firing tables and timing walkthroughs. |
| R02 | R02 “Behavioural requirement — eligible for a future generation prompt” | Restates gauge/units/schema, three-minute wait, equality and immediate recovery; no review-only scenarios. |
| R03 | R03 eligible behavioural section | Includes service-level continuity across instance changes and exact identity; no instance sequences, answer expressions, or walkthrough. |
| R04 | R04 eligible behavioural section | Includes both metric schemas, direct gauges, same-service conjunction and inclusive traffic boundary; no paired input samples. |
| R05 | R05 eligible behavioural section | Includes exact environment values, independent production behaviour and retained environment identity; no sample services or series. |
| R06 | R06 eligible behavioural section | Rephrases the relative-time enumeration as a general elapsed-time retention rule, retaining renewal/expiry/re-arming semantics and removing worked timestamp examples. |

`collection/COMMON_OUTPUT_CONTRACT.txt` elaborates the common output contract in
`STUDY_PLAN.md` using the enforced field/support policy in
`scripts/stage3a/contracts.py`. It adds no reference expressions or fixture values.
The full `SEMANTICS.md` and its implementation notes are never copied into prompts;
shared generic observation/identity assumptions are expressed as requirements.

## Enforced constraint coverage

| Scorer/requirement obligation | Disclosure in every relevant prompt |
|---|---|
| UTF-8, one safe YAML mapping/document, JSON YAML allowed, no empty/prose/fenced/multiple-answer response | Common contract opening paragraph; complete rule file required |
| String keys, duplicates including merge collisions, safe constructors | Common contract opening paragraph |
| Only top-level groups; exactly one group and one alert | Common contract; explicit field allowlists |
| Explicit one-minute interval, valid named group, required alert name | Common contract and task-specific name |
| Only supported group/rule fields; no recording/import/extra rules | Common contract exact field lists |
| Required metrics referenced, no unsupplied metric/constant replacement | Task metric/schema paragraphs and common contract |
| Types, units, finite complete observations, exact input label schema | Task requirements; no input samples supplied |
| Trigger, threshold boundary, wait/reset, recovery, grouping and independence | Task-specific behavioural paragraphs |
| No annotations; exact output labels, no extra declarations or alertname override | Common contract plus exact task identity; R05 alone permits environment |
| Current direct gauges; no rate/histogram/window/range/subquery/offset/@ | Common prohibited-construct paragraph and function list |
| Supported stateless functions and unsupported-function review | Common exact supported function list and separate prohibited names/prefixes/suffixes |
| Exact metric selectors; selector OR extensions; template query inspection | Common support-disclosure paragraph |
| 200,000 bytes, 20,000 lexical YAML tokens, depth 60 | Common size/support paragraph; explicitly an inspection limit |
| Parser disagreement and unknown diagnostics | Support limitation disclosed; protocol preserves unevaluable outcomes, never inferred behavioural defects |

No implementation, oracle, expected-output or requirement file is changed.
The common restriction against new percentile computation applies explicitly to
R02's supplied latency statistic; the common contract does not add a blanket
ban on all aggregation operators beyond the approved behaviour.

## Support limits are not new behavioural results

Some inspector paths return review/unevaluable statuses rather than candidate
violations: unresolved metric selector scope, selector OR matcher extensions,
unrecognised functions, template queries, expression-parser disagreement and
resource limits. The prompts disclose these limits so they are not hidden.
They must remain separately reported; do not reinterpret them as detected timing,
threshold, recovery or grouping violations. The final prompts and these support
constraints need human review before collection, while model/settings remain pending.

The offline verification checks exact prompt bytes/common suffixes, slot order,
hash preservation, selected structural policy disclosures and obvious leakage
markers/reference-expression strings. These checks support human review; they
cannot prove complete semantic equivalence or the absence of every possible clue.
