# Stage 1 validation summary

This repository tests requirement R01 using controlled synthetic gauge series.
It contains one reference rule, three deliberate mutations and six fixtures
with 31 firing-output assertions. These are infrastructure-validation material;
no experimental model outputs were collected.

Run from the repository root:

```sh
python3 scripts/check_stage1.py
```

Verified on 2026-11-04 with Prometheus/promtool 3.15.1, Docker 29.8.2 and
Python 3.14.6 on Apple Silicon. The container platform is linux/arm64.
The exact image digest is in `prometheus-image.txt`.

| Rule | Syntax exit | Behaviour exit | Interpretation |
|---|---:|---:|---|
| Reference | 0 | 0 | All 31 assertions passed |
| Remove two-minute persistence | 0 | 1 | Tests detected premature firing |
| Change strict threshold to inclusive | 0 | 1 | Tests detected firing at exactly 0.05 |
| Aggregate away service label | 0 | 1 | Tests detected missing service identity |

The runner returned 0: all expected outcomes occurred. A mutation's nonzero
behavioural exit is expected only when its output contains an assertion
mismatch. The runner returns 2 for unexpected outcomes or infrastructure errors.

The initial implementation used 3.7.3. It was upgraded to 3.15.1 after checking
the official release list. Requirement, rules, input sequences and expected
outcomes were unchanged; the upgraded run produced identical outcomes.

Each execution saves raw stdout/stderr, exact command arguments, timestamps,
exit codes, tool versions, input snapshots and SHA-256 hashes under
`results/stage1/`. Existing local archives are retained outside version control.
The recorded outcome above is a summary; rerun the command to produce a fresh
inspectable execution record.

The checks demonstrate detection of three known mistakes that syntax checking
accepts. They do not measure model performance or establish operational safety.
Empty firing output does not directly distinguish every internal pending state.
Assumptions include complete one-minute observations, one series per service,
and no additional alert retention. Human review remains necessary.
