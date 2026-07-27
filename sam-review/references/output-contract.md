# Unified Review Output Contract

## Contents

1. Report shape
2. Vocabularies and linking rules
3. Execution receipts
4. Target modes and publication

Draft a JSON report and validate it before rendering or publishing.

```json
{
  "schema_version": 1,
  "target": {
    "mode": "proposal",
    "base_sha": "<sha>",
    "head_sha": "<sha>",
    "bundle_fingerprint": "<sha256>"
  },
  "intent": {
    "intended_behavior": ["..."],
    "must_not_change": ["..."],
    "invariants": ["..."],
    "owner_boundary": "...",
    "user_visible_change": false
  },
  "scope": {
    "baseline_file_count": 1,
    "baseline_non_test_lines": 10,
    "current_file_count": 1,
    "current_non_test_lines": 10,
    "review_cycle": 1,
    "scope_expansion_approved": false,
    "remaining_findings_reclassified": false
  },
  "file_coverage": [
    {"path": "src/example.ts", "classification": "REVIEWED", "reason": "..."}
  ],
  "findings": [
    {
      "id": "F1",
      "severity": "BLOCKER",
      "status": "ACCEPTED",
      "scope": "IN_SCOPE",
      "path": "src/example.ts",
      "line": 10,
      "side": "NEW",
      "failure_mode": "...",
      "impact": "...",
      "evidence": ["..."],
      "required_change": "...",
      "test_gap": false,
      "rejection_reason": null
    }
  ],
  "test_coverage": [
    {"behavior": "...", "level": "UNIT", "status": "COVERED", "paths": ["tests/example.test.ts"], "reason": "...", "finding_id": null}
  ],
  "validations": [
    {"command": "...", "status": "PASS", "classification": "TARGET", "reason": "...", "receipt": "/abs/receipts/CMD-001.receipt.json"}
  ],
  "behavior_proof": {"status": "NOT_APPLICABLE", "evidence": []},
  "decision": {
    "result": "CHANGES_REQUIRED",
    "confidence": "HIGH",
    "non_gating_requested": false,
    "remaining_corrections": ["F1"]
  },
  "publication": {
    "requested": false,
    "expected_head_sha": "<sha>",
    "observed_head_sha": "<sha>",
    "review_id": "<stable-id>",
    "action": "NONE",
    "status": "NOT_REQUESTED",
    "inline_comments": [],
    "receipts": [],
    "error": null
  }
}
```

Finding severities are `BLOCKER`, `IMPORTANT`, and `SUGGESTION`. Decisions are
`APPROVE`, `CHANGES_REQUIRED`, `BLOCKED`, and `COMMENT_ONLY`. Publication actions
are `NONE`, `COMMENT`, `REQUEST_CHANGES`, and `APPROVE`; statuses are
`NOT_REQUESTED`, `PLANNED`, `PUBLISHED`, `PARTIAL`, and `BLOCKED`.

For rejected findings, set `rejection_reason`. Link every
`MISSING_REQUIRED` test to a blocker. Inline comments reference an accepted
required finding, exact changed path, side, and line. Receipts contain `kind`,
`id`, `url`, and `status` without credentials.

Every validation with status `PASS` or `FAIL` requires `receipt`: the absolute
path of the `scripts/run_checked.py` receipt. `command` must equal the receipt
argv joined by spaces, and status plus classification must match the receipt.
`NOT_RUN` carries a reason and no receipt. The validator recomputes
`receipt_sha256` and every captured `log_sha256`, so an edited receipt or log
fails, and a `PASS` with a non-zero recorded exit code fails. `TARGET` and
`INTRODUCED` validations must record at least two runs; `APPROVE` is rejected
when any validation is flaky or a target validation did not run stably.

Use the same report schema for every target mode. For `local`, `branch`,
`commit`, and `range`, publication must remain a clean `NOT_REQUESTED` state.
For `proposal`, keep `NOT_REQUESTED` until the user authorizes one compatible
action. After returning the validated local decision, ask whether to publish
when no action was supplied. Revalidate any `PLANNED`, `PUBLISHED`, `PARTIAL`,
or `BLOCKED` publication update before reporting it.
