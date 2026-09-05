# Output Contract

Draft a JSON report and validate it against `context.json`.

```json
{
  "schema_version": 1,
  "target": {
    "base_sha": "<sha>",
    "head_sha": "<sha>",
    "context_fingerprint": "<sha256>"
  },
  "language": "EN-US",
  "change_types": ["BUG_FIX"],
  "file_coverage": [
    {"path": "src/example.ts", "section": "Description", "summary": "Updates behavior"}
  ],
  "evidence": [
    {
      "id": "E1",
      "type": "DIFF",
      "reference": "src/example.ts",
      "status": "INFO",
      "detail": "The changed branch implements the stated behavior"
    }
  ],
  "claims": [
    {
      "id": "C1",
      "category": "IMPLEMENTATION",
      "text": "The service now applies the new rule.",
      "evidence_ids": ["E1"]
    }
  ],
  "body": "## Description\n...",
  "remote_update": {
    "requested": false,
    "expected_head_sha": "<sha>",
    "observed_head_sha": "<sha>",
    "status": "NOT_REQUESTED",
    "receipts": [],
    "error": null
  }
}
```

Change types: `BUG_FIX`, `NEW_FEATURE`, `REFACTOR`, `DOCUMENTATION`, `OTHER`.

Evidence types:

- `DIFF` or `FILE`: reference a changed path.
- `COMMIT`: reference a commit SHA in context.
- `VALIDATION`: record `PASS`, `FAIL`, or `NOT_RUN` and exact command/detail.
- `USER`: reference an explicit user fact without embedding private content.
- `REMOTE`: reference proposal metadata read from the platform.

Other evidence uses status `INFO`. Claim categories are `SCOPE`,
`IMPLEMENTATION`, `TEST`, `SAFETY`, `ARCHITECTURE`, `BUSINESS_RULE`, and
`REFERENCE`. Positive test, safety, business-rule, and reference claims require
evidence.

Remote statuses are `NOT_REQUESTED`, `PLANNED`, `UPDATED`, `PARTIAL`, and
`BLOCKED`. Receipts contain non-empty `kind`, `id`, `url`, and `status` fields.

The validator checks target fingerprint, complete one-time file coverage,
evidence references, claim/body linkage, Description and Validation headings,
placeholders, outer code fences, and remote head drift. File coverage stays in
the report; paths and ledger summaries need not be repeated in the body. Each
coverage section must name a heading actually present in the body.
