# Output Contract

Draft JSON before rendering the final response.

Required top-level fields:

- `baseline_fingerprint`, `bundle_fingerprint`
- `target`: `base_sha`, `head_sha`
- `intent`: `summary`, `invariants`, `no_go`
- `environment`: `kind`, `identity`, `real_data`, `evidence`
- `authorization`: `publish_requested`
- `command_definitions`: `changed`, `inspected`, `evidence`
- `criteria`, `risks`, `scenarios`, `tests`, `commands`, `artifacts`, `cleanup`
- `test_diff_audit`: `status`, `evidence`
- `test_wiring`: `status`, plus receipts and names when `PROVEN`
- `behavior_proof`: `status`, `evidence`
- `decision`: `COMPLETE`, `PARTIAL`, or `BLOCKED`

Use IDs `AC-###`, `R-###`, `S-###`, `T-###`, `CMD-###`, `ART-###`, and
`CL-###`. Every reference must be a string and every scenario/test,
test/command, and scenario/artifact link must be reciprocal. Criteria require
nonempty text; risks require evidence or description. Use command status `PASS`,
`FAIL`, or `NOT_RUN`; classify it as `TARGET`, `BASELINE`, `ENVIRONMENT`, or
`EXTERNAL`.

Each test must include a nonempty path and name plus `regression_proof.status`:
`RED_GREEN`, `MUTATION`, `CONTRACT`, or `NOT_PROVEN`, with evidence. Each
artifact must include linked scenario IDs, local or remote status, safety
review, and receipt when uploaded.

## Execution receipts and wiring

Every command with status `PASS` or `FAIL` requires `receipt`: the absolute path
of the `scripts/run_checked.py` receipt. `commands[].command` must equal the
receipt argv joined by spaces, and status plus classification must match the
receipt. `NOT_RUN` carries a reason and no receipt. The validator recomputes
`receipt_sha256` and every captured `log_sha256`; an edited receipt or log fails.
A `PASS` whose receipt records a non-zero exit code fails. `TARGET` commands must
record at least two runs, and differing exit codes mark the command `FLAKY`.

`test_wiring.status` is `PROVEN`, `NOT_PROVEN`, or `NOT_APPLICABLE`; the last two
require a `reason`. `PROVEN` requires `before_receipt`, `after_receipt`, and
`discovered_tests`, where each name is absent from the before-log and present in
the after-log.

`COMPLETE` is invalid when a required scenario is uncovered, target validation
fails, behavior is unproven, high-risk regression proof is `NOT_PROVEN`, changed
commands were not inspected, publication lacks authorization or receipt, the
test-diff audit fails, cleanup is blocked, any command is `FLAKY`, a `TARGET`
command did not run repeatedly and stably, or test wiring is neither `PROVEN` nor
`NOT_APPLICABLE`. When publication is requested,
every uploaded video or image must use host player/image embed markup (never a
hyperlink-only body or git-committed media) and pass remote readback.

`behavior_proof.status` is `PROVEN` only for real product UI + linked backend
paths. `FALLBACK` requires documented real-system attempts and blockers and is
not full confidence. Do not claim `COMPLETE` with silent test-only components or
shells when the real UI was available.
