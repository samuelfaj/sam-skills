# Publication Policy

Publication is an external mutation. The local review contract never grants it.

## Authorization

- Set `requested: true` only when the user explicitly asks to publish, comment,
  approve, request changes, or update the remote review.
- A URL, proposal ID, or request to review authorizes read access only.
- Do not broaden a request for one comment into approval or other state change.
- When a proposal review ends without publication authorization, return the
  complete validated decision first, then ask one concise question offering
  only actions compatible with that decision.
- Do not ask a publication question for local, branch, commit, or range targets.

## Preflight

Before the first write:

1. Confirm the validated report fingerprint.
2. Re-read the remote head and publication capabilities.
3. Abort all writes on head drift.
4. Confirm the action matches the decision and user authorization.
5. Render comments to temporary files without secrets.

## Idempotency and Failure

Use one stable `review_id` for the frozen report. Inspect existing review state
before retrying. Record one receipt per confirmed write.

- `PLANNED`: authorized and preflight passed; no writes confirmed.
- `PUBLISHED`: all planned writes have receipts.
- `PARTIAL`: at least one write succeeded and at least one failed.
- `BLOCKED`: no write occurred because preflight or capability failed.
- `NOT_REQUESTED`: local draft only.

On `PARTIAL`, stop. Do not replay already confirmed writes. Return receipts and
the exact failing operation so a later run can reconcile safely.

Never approve when a required finding remains. Never publish optional
suggestions inline. If the platform cannot represent a requested review state,
publish only a summary when authorized and report the capability limitation.
