# Output Contract

Draft a temporary JSON report, validate it, then render the local review.

## Structured Report

Use this shape:

```json
{
  "schema_version": 1,
  "target": {
    "mode": "local",
    "base_sha": "<sha-or-null>",
    "head_sha": "<sha-or-null>",
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
    {"path": "src/example.ts", "classification": "REVIEWED", "reason": "Runtime change reviewed"}
  ],
  "findings": [
    {
      "id": "F1",
      "severity": "BLOCKER",
      "status": "ACCEPTED",
      "scope": "IN_SCOPE",
      "path": "src/example.ts",
      "line": 10,
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
  }
}
```

Use `null` for unavailable SHAs and an empty finding list for a clean review. For
`REJECTED`, require `rejection_reason`. For `FOLLOW_UP` or `STOP_AND_ESCALATE`, explain
the scope boundary in `required_change`. Link `MISSING_REQUIRED` to its `BLOCKER` ID.

## Inline Findings

Emit one directive per accepted `BLOCKER` or `IMPORTANT` when supported:

```text
::code-comment{title="[BLOCKER] Short title" body="Concrete failure and required change." file="/absolute/path/to/file.ts" start=10 end=10 priority=0}
```

Use priority `0` for `BLOCKER` and `1` for `IMPORTANT`. Use only supported fields.

## Written Review

Write in EN-US unless the user requests another language. Return sections in this order:

1. `Findings` — accepted findings ordered by severity, or `N/A`.
2. `Rejected Candidates` — concise reasons, or omit when empty.
3. `Follow-ups` — explicitly non-blocking, or omit when empty.
4. `Changed-File Coverage` — reviewed/exempt totals and exceptions.
5. `Test Coverage` — scenario-level covered, required, optional, and unsupported proof.
6. `Validation Run` — exact commands and `PASS`, `FAIL`, or `NOT RUN`.
7. `Behavior Proof` — `PROVEN`, `NOT PROVEN`, or `NOT APPLICABLE`.
8. `Final Decision` — result, confidence, and remaining corrections.

Always include the structured report validator command and result under `Validation Run`.
A gating review is incomplete until it passes or an exact validator blocker is reported.

Lead with findings. Do not include an overall numeric rating. Do not repeat the same
test gap in multiple prose sections; reference its finding ID instead.
