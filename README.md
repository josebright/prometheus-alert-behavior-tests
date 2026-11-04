# Prometheus alert behavior tests

Run from this folder with Python 3 and a running Docker engine:

```sh
python3 scripts/check_stage1.py
```

Docker must have permission to use its socket and pull from Docker Hub. The
runner uses native `linux/arm64` and Prometheus **v3.15.1**, then pins subsequent
runs to the recorded repository digest in `prometheus-image.txt`. This setup
was built for Apple Silicon; it intentionally checks ARM64 rather than
silently using x86 emulation. No Python packages are required.

Version 3.15.1 was the latest stable release on 2026-11-04, verified against
the [official download page](https://prometheus.io/download/). The runner
checks the actual promtool version against this selection.

Read [the requirement and expected-outcome table](requirements/R01.md) first,
then [the reference rule](rules/reference.yml), [the synthetic tests](tests/R01.test.yml),
and [the validation summary](VALIDATION.md).

The same oracle is run against the reference and three separate mutations.
The runner returns **0** only if every syntax check passes, the reference
passes all behavioural assertions, and each mutation fails with an assertion
mismatch (exit 1). It returns **2** for unexpected results, Docker/tool errors,
or test-loading errors. Mutation failures are expected validation results;
inspect their raw logs to see which assertions detected them. This is not
a general-purpose classifier for arbitrary future Prometheus errors.

Each invocation creates a unique UTC-named directory in `results/stage1/`.
It includes immutable input copies, SHA-256 hashes, exact command argument
arrays, start/end timestamps, raw stdout/stderr, exit codes, Docker version,
image inspection, promtool version and a machine-readable summary. Containers
have no network access; pulling the image requires network access. Do not put
secrets in these files or logs. Raw run archives and the detailed local report
are excluded from version control; rerunning the command creates new evidence.

Official documentation consulted on 2026-11-04:

- [Alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/):
  `for` delays firing while the expression remains active; omitting
  `keep_firing_for` allows immediate deactivation at a false evaluation.
- [Unit testing rules](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/):
  input samples begin at time zero, evaluation and input intervals are
  explicit, and `exp_alerts` asserts the complete firing set for an alert name.
- [Checking rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/):
  `promtool check rules` validates rule files without starting a server.

These fixtures, reference rules and deliberate mutations validate the test
infrastructure. They are not production telemetry, sampled LLM outputs, or
measurements of LLM performance. Firing-output assertions do not directly
verify every internal pending state. Passing these finite examples does not
establish operational safety, Alertmanager delivery, or correctness under
missing samples, restarts, extra labels or unobserved between-sample changes.
This infrastructure needs human review. Stage 1 ends here.
