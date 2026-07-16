# Unified Review Output Contract

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
    {"command": "...", "status": "PASS", "classification": "TARGET", "reason": "..."}
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

Use the same report schema for every target mode. For `local`, `branch`,
`commit`, and `range`, publication must remain a clean `NOT_REQUESTED` state.
For `proposal`, keep `NOT_REQUESTED` until the user authorizes one compatible
action. After returning the validated local decision, ask whether to publish
when no action was supplied. Revalidate any `PLANNED`, `PUBLISHED`, `PARTIAL`,
or `BLOCKED` publication update before reporting it.
