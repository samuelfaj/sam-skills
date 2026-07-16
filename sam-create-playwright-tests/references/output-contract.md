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

`COMPLETE` is invalid when a required scenario is uncovered, target validation
fails, behavior is unproven, high-risk regression proof is `NOT_PROVEN`, changed
commands were not inspected, publication lacks authorization or receipt, the
test-diff audit fails, or cleanup is blocked.
