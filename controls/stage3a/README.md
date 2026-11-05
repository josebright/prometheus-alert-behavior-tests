# Stage 3A infrastructure controls

These files are deliberately constructed validation material, not sampled model
responses. They use the existing controlled synthetic observations. The manifest
records expected outcomes declared before execution. It is not scorer input:
`score_candidate.py` receives only a task ID and a candidate file, and never reads
this manifest or the earlier mutation catalog.

Reference copies, alternative-expression controls, invalid-format controls,
contract defects and earlier mutations exercise different scoring paths. No
control or future response is repaired before scoring. `build_controls.py`
creates these files and refuses to overwrite them; validation only reads them.
Future experimental outputs must be stored separately, outside this directory.

The diagnostic annotation control contains braces, brackets, escaped quotes,
a backslash and a newline. Its expected failure is solely the no-annotation
contract; it must not become a detection or timing failure.
