---
name: sam-work
description: Execute a software task through the complete bug-or-feature implementation, refinement, review, simplification, test-coverage, proposal, browser-proof, and demo-video workflow. Use when the user wants end-to-end delivery with no silently skipped phase, fresh proof after every change, a created or updated pull/merge request, and published video evidence.
---

# SAM Work

## Purpose

Turn one user request into a delivered pull or merge request through a fail-closed sequence of implementation and proof gates. Do not treat a child skill as complete merely because it was invoked. Capture and validate its terminal result.

This workflow authorizes only the external actions named by this contract: push the task branch, create or update its proposal, and publish the required videos on that proposal. It does not authorize merge, deployment, approval, unrelated comments, destructive cleanup, or production data access.

## Non-Negotiable Contract

Execute and prove every canonical phase. Never report `COMPLETE` while a phase is missing, stale, non-terminal, unvalidated, or silently skipped. Playwright may be `NOT_APPLICABLE` only for a proven non-web system; every other unavailable phase blocks completion.

## Required skills

Before changing the target repository, read these files completely and follow their referenced resources when each phase starts:

1. `../sam-fix-bug/SKILL.md`
2. `../sam-create-feature/SKILL.md`
3. `../sam-refine-task/SKILL.md`
4. `../sam-review/SKILL.md`
5. `../sam-simplify-task/SKILL.md`
6. `../sam-create-test-coverage/SKILL.md`
7. `../sam-pr-description/SKILL.md`
8. `../sam-create-playwright-tests/SKILL.md`
9. `../sam-create-task-demo-video/SKILL.md`

If any required skill is absent or its contract cannot be honored, return `BLOCKED`. Do not emulate a missing skill from memory.

Announce the complete workflow, the bug/feature classification, the target repository, the authorized external writes, and the pass criteria before implementation.

## Operating rules

- Preserve unrelated user work. Never reset, overwrite, or include it in the task bundle.
- Freeze the original prompt hash, repository root, base, branch, acceptance criteria, invariants, no-go surfaces, and initial change fingerprint.
- Classify `BUG` only when expected existing behavior is broken or regressed. Otherwise classify `FEATURE`. Record concrete evidence; do not infer from issue labels alone.
- Use `sam-fix-bug` for `BUG`; use `sam-create-feature` for `FEATURE`.
- Run phases in the canonical order below. A later correction may rewind invalidated gates, but never removes a phase from the ledger.
- For every child skill, run its deterministic validator and store the receipt. A narrative claim is not a receipt.
- A loop ends only on its accepted terminal state with zero open required items. An iteration that finds issues must have correction receipts before the next iteration.
- Child-skill retry limits remain active. If a child contract requires stopping after repeated cycles without new evidence, mark the workflow `BLOCKED`; never translate exhaustion into confidence.
- Any repository change invalidates every later proof tied to the old head. Repeat affected gates until implementation, refinement, review, simplification, coverage, proposal, browser proof when applicable, and demo proof are current for one final head.
- Use verified development data only for browser tests and recordings. Never use production, customer, or ambiguous targets. Record environment identity before authentication or mutation.
- Keep dedicated test/demo identities, a mutation ledger, cleanup receipts, redaction proof, and artifact hashes.
- Do not declare “all tests,” “simplest possible,” or “no issues” without the terminal child result plus current-head evidence.

## Canonical phases

### 1. Implement

Run the selected implementation skill against the original request. Require its complete acceptance, validation, and scope evidence. If it is blocked, stop with a workflow report.

### 2. Refine loop

Run `sam-refine-task` on the implemented strategy and current diff.

- `HIGH_CONFIDENCE` with no open required item closes the gate.
- `NOT_CONFIDENT` requires concrete corrections through the selected implementation contract, fresh validation, then another refinement pass.
- `BLOCKED` blocks the workflow.

### 3. Review loop

Run `sam-review` on an immutable bundle for the current head without publishing a review decision.

- `APPROVE` with no actionable finding closes the gate.
- `CHANGES_REQUIRED` requires corrections, validation, bundle rebuild, and another review.
- `BLOCKED` blocks the workflow.
- `COMMENT_ONLY` is not a passing code-review result.

### 4. Simplification loop

Run `sam-simplify-task` on the current change.

- `SIMPLEST_DEFENSIBLE` or `NO_CHANGE`, with no open simplification, closes the gate.
- Applied simplifications require focused validation and fresh refinement/review proof.
- `BLOCKED` blocks the workflow.

### 5. Coverage loop

Run `sam-create-test-coverage` against acceptance criteria, risks, changed seams, and existing tests.

- `FULL` with no uncovered required risk closes the gate.
- `PARTIAL` requires implementing the missing justified coverage, validating it, and running the gate again.
- Production-code changes made for testability rewind refinement, review, and simplification. Test-only changes rewind review and any proof whose bundle changed.
- `BLOCKED` blocks the workflow.

Before proposal work, rerun invalidated gates until phases 1-5 all validate the same current head.

### 6. Proposal

Resolve an existing open proposal for the task branch. Run `sam-pr-description` against the real base, commits, diff, and proof set. Validate the description before any platform write.

- If no proposal exists, create exactly one pull or merge request with the validated body.
- If one exists, update it instead of creating a duplicate.
- Push the exact reviewed head, then read back proposal URL/ID, rendered description, remote head, and required CI state when configured.
- Store the creation/update and readback receipts. Do not merge.

### 7. Web browser proof

Always perform and record the applicability decision.

If the delivered system is web-accessible, run `sam-create-playwright-tests` against a real linked development UI/backend and verified real development data. Require `COMPLETE`, cleanup, and current-head proof. Configure video capture where necessary, inventory every produced browser-test video, hash it, upload every video to the proposal, and read the rendered proposal surface back. Every uploaded artifact must render as an inline/native video player; a file link alone does not pass.

If the system is not web-accessible, record `NOT_APPLICABLE` with repository/runtime evidence. This is the only phase that may be not applicable.

If browser-test work changes the repository, push it, refresh the proposal description, and rerun every invalidated gate before continuing.

### 8. Demo video

Run `sam-create-task-demo-video` using the verified real development environment and data. Require `PUBLISHED`, validated media, privacy proof, cleanup, upload receipt, and rendered-player readback on the proposal.

If the feature cannot be demonstrated honestly in a runnable surface after the child skill's allowed fallback attempts, return `BLOCKED`. Never replace this phase with screenshots or a textual claim.

## Freshness and completion

After the last repository mutation:

1. Recompute the final head and change fingerprint.
2. Repeat every stale phase until all eight phase records are current for that head.
3. Push and confirm the proposal remote head equals the final local head.
4. Confirm every required CI check that exists reached a passing terminal state.
5. Re-read the rendered proposal and verify the validated description plus every expected video player.
6. Run the workflow validator:

```bash
python3 scripts/validate_work_report.py work-report.json
```

Read `references/output-contract.md` before creating the report. `COMPLETE` is allowed only when the validator passes. Otherwise return `BLOCKED` or `IN_PROGRESS` with exact remaining work and receipts already obtained.

## Final response

Report:

1. `COMPLETE`, `BLOCKED`, or `IN_PROGRESS`.
2. Bug/feature classification and selected implementation skill.
3. Phase ledger with iteration count, terminal status, current head, and validator receipt.
4. Tests and required CI results.
5. Proposal URL and remote-head readback.
6. Development-environment identity and cleanup status.
7. Browser-video and demo-video inventory with hashes, upload receipts, and player-readback proof.
8. Exact blockers or remaining work; never hide a skipped or stale phase.
