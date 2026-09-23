# Publication Policy

## Authorization

Set `requested: true` only when the user explicitly asks to publish, comment, approve, request changes, or update the remote review, or a parent authorized that exact action. Never broaden one comment into approval or another state change.

## Preflight (before the first write)

1. Confirm the validated report fingerprint.
2. Re-read the remote head and publication capabilities; on head drift write nothing.
3. Confirm the action is authorized and matches the decision: `APPROVE` needs an `APPROVE` decision, `REQUEST_CHANGES` needs `CHANGES_REQUIRED`.
4. Render comments to temporary files without secrets.

## Writes and Failure

- Inline only accepted `BLOCKER`/`IMPORTANT` findings whose exact side and line exist in the frozen diff. Suggestions never go inline; they enter an authorized summary only when explicitly requested.
- Keep one stable `review_id` per frozen report; inspect existing review state before any retry; record one receipt per confirmed write.
- On `PARTIAL`, stop; never replay confirmed writes; return receipts and the exact failing operation for later reconciliation.
- If the platform cannot represent the requested state, publish only an authorized summary and report the limitation.
- Revalidate the report after every publication state change.

## Report Fields

`{requested, expected_head_sha, observed_head_sha, review_id, action, status, inline_comments, receipts, error}`: *derived* `expected_head_sha` (bundle head) and `review_id` (`[A-Za-z0-9._:-]{12,128}`); non-empty `observed_head_sha` (re-read head; frozen head for a draft); action `NONE`, `COMMENT`, `REQUEST_CHANGES`, `APPROVE`; `error` null or non-empty; `inline_comments[]` `{finding_id, path, line, side}` match an accepted `BLOCKER`/`IMPORTANT`; `receipts[]` `{kind, id, url, status}` non-empty, credential-free.

| Status | Meaning | Action, receipts, error |
| --- | --- | --- |
| `NOT_REQUESTED` | local draft; only with `requested: false` | `NONE`, none, null |
| `PLANNED` | authorized, preflight passed, no confirmed write | action, none, null |
| `PUBLISHED` | every planned write has a receipt | action, yes, null |
| `PARTIAL` | ≥ 1 write succeeded and ≥ 1 failed | action, yes, error |
| `BLOCKED` | no write: head drift (forced), preflight or capability failure | `NONE`, none, error |
