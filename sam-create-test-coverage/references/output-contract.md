# Output Contract

Draft and validate JSON before rendering the final response.

Required fields:

- `baseline_fingerprint`, `bundle_fingerprint`
- `target`: `base_sha`, `head_sha`
- `intent`: `summary`, `invariants`, `no_go`
- `environment`: `kind`, `identity`, `real_data`, `evidence`
- `authorization`: `publish_requested`
- `command_definitions`: `changed`, `inspected`, `evidence`
- `criteria`, `behaviors`, `risks`, `scenarios`, `tests`, `commands`, `artifacts`, `cleanup`
- `test_diff_audit`: `status`, `evidence`
- `real_system_proof`: `status`, `evidence`
- `decision`: `FULL`, `PARTIAL`, or `BLOCKED`

Use stable IDs `AC-###`, `B-###`, `R-###`, `S-###`, `T-###`, `CMD-###`,
`ART-###`, and `CL-###`. Scenario layers are `UNIT`, `COMPONENT`,
`INTEGRATION`, `API_CONTRACT`, `E2E`, or `MANUAL`. Every reference must be a
string and every scenario/test, test/command, and scenario/artifact link must
be reciprocal. Criteria require nonempty text; risks require evidence or
description.

Each test requires a nonempty path and name plus `regression_proof.status`:
`RED_GREEN`, `MUTATION`, `CONTRACT`, or `NOT_PROVEN`, with evidence. Each
command requires status `PASS`, `FAIL`, or `NOT_RUN` and classification
`TARGET`, `BASELINE`, `ENVIRONMENT`, or `EXTERNAL`.

`FULL` is invalid with uncovered required scenarios, target failures, failed
audit, unproven required regression tests, unsafe real-data environment, unverified
real-system claims, uninspected changed commands, unauthorized publication, or
blocked cleanup.
