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
- `test_wiring`: `status`, plus receipts and names when `PROVEN`
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

## Execution receipts

Every command with status `PASS` or `FAIL` requires `receipt`: the absolute path
of the `scripts/run_checked.py` receipt. `commands[].command` must equal the
receipt argv joined by spaces, and status plus classification must match the
receipt exactly. `NOT_RUN` carries a reason and no receipt.

The validator recomputes `receipt_sha256` and every captured `log_sha256`, so an
edited receipt or log fails. A `PASS` whose receipt records a non-zero exit code
fails. `TARGET` commands must record at least two runs; differing exit codes make
the command `FLAKY`.

## Test wiring

```json
{
  "test_wiring": {
    "status": "PROVEN",
    "before_receipt": "/abs/receipts/CMD-900.receipt.json",
    "after_receipt": "/abs/receipts/CMD-901.receipt.json",
    "discovered_tests": ["test_rejects_expired_token"],
    "evidence": ["runner discovery before and after the change"]
  }
}
```

`status` is `PROVEN`, `NOT_PROVEN`, or `NOT_APPLICABLE`; the last two require a
`reason`. For `PROVEN`, each name in `discovered_tests` must be absent from the
before-log and present in the after-log.

## Decision gates

`FULL` is invalid with uncovered required scenarios, target failures, failed
audit, any regression test marked `NOT_PROVEN`, unsafe real-data environment,
unverified real-system claims, uninspected changed commands, unauthorized
publication, blocked cleanup, any `FLAKY` command, a `TARGET` command that did not
run repeatedly and stably, test wiring that is not `PROVEN` or `NOT_APPLICABLE`,
or a test linked to `HIGH`/`CRITICAL` risk whose proof is not `RED_GREEN` or
`MUTATION`.

When the bundle carries a `security`, `data`, `contract`, or `concurrency` risk
tag, at least one declared risk must be `HIGH` or `CRITICAL`.
