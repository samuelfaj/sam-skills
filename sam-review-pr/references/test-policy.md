# Test Policy

Build scenario coverage before mapping test files.

For each changed behavior, consider applicable success, negative, boundary,
permission, persistence, compatibility, concurrency, partial-failure, recovery,
and user-visible scenarios.

Classify each scenario:

- `COVERED`: meaningful proof exercises the changed behavior.
- `MISSING_REQUIRED`: merge safety depends on this proof.
- `MISSING_OPTIONAL`: useful hardening, not merge-blocking.
- `UNSUPPORTED`: the repository lacks a safe practical seam; record the limit.
- `NOT_APPLICABLE`: no meaningful scenario at that level.

A missing test is `MISSING_REQUIRED` only when all are true:

1. Runtime behavior changed.
2. A reachable regression path exists.
3. The repository has a practical established seam.
4. The proof is necessary to make the proposal safe to merge.

Link every `MISSING_REQUIRED` scenario to one accepted `BLOCKER` finding. Do not
require one direct test file per runtime file. A test at another level may be
the correct proof when it observes the owning contract.

Reject tests that only import, instantiate, snapshot unrelated output, or mock
away the behavior under review. For a bug fix, prefer proof that would fail for
the defective behavior and pass for the corrected behavior when a safe
comparison is practical.
