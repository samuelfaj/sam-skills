# Conditional Platform Adapters

Load only the section for the detected platform. The core workflow depends on
capabilities, not on a host name or command.

Required read capabilities:

- Proposal metadata, base SHA, head SHA, source and target refs.
- Changed-file or Git-ref access.
- Current head refresh immediately before publication.

Optional write capabilities:

- Inline diff comment.
- Top-level summary.
- Approve or request-changes state.
- Existing-comment lookup for safe reconciliation.

## GitHub Adapter

Use an available authenticated connector, API client, or `gh` only after
confirming the target is GitHub. Resolve the pull request's immutable base and
head SHAs. For inline comments, use the frozen commit, changed path, side, and
line. Submit review state only when explicitly authorized and supported.

## GitLab Adapter

Use an available authenticated connector, API client, or `glab` only after
confirming the target is GitLab. Preserve base, start, and head diff refs for
inline positions. Use the old side for deletions and both paths for renames.
When request-changes state is unavailable, leave authorized unresolved
discussions plus a summary and record that limitation.

## Unknown Platform

If read capabilities exist, complete the validated local review. If the user
requested publication but no safe adapter exists, set publication to `BLOCKED`
with action `NONE`; do not improvise an API call.
