# Platform Adapters

Depend on capabilities, not host names or commands; use an authenticated connector, API client, or the platform CLI (`gh`, `glab`) only after confirming the platform.

## Proposal Target

Resolve platform, repository identity, proposal ID, draft state, base/head refs and their immutable SHAs, and capabilities. Required reads: proposal metadata, source/target refs, changed-file or Git-ref access, a current-head refresh right before publication. Optional writes: inline diff comment, top-level summary, approve/request-changes state, existing-comment lookup for safe reconciliation. Obtain the exact refs locally, then build with `--mode proposal --base <ref> --head <ref> --platform <kind> --repository <id> --change-id <id> --comparison merge-base` (`direct` only when the platform defines the exact base-to-head range).

Standalone with no authorized action, ask one question offering only compatible actions: `APPROVE`: none, comment, or approve; `CHANGES_REQUIRED`: none, comment, or request changes; `BLOCKED`: none or comment the blocker; `COMMENT_ONLY`: none or comment. An answer authorizes only that action.

## GitHub

Inline comments use the frozen commit, changed path, side, and line. Submit review state only when explicitly authorized and supported.

## GitLab

Keep base, start, and head diff refs for inline positions; use the old side for deletions and both paths for renames. Without request-changes state, leave authorized unresolved discussions plus a summary and record the limitation.

## Unknown Platform

With read capabilities, complete the validated local review. If publication was requested but no safe adapter exists, set publication `BLOCKED` with action `NONE`; never improvise an API call.
