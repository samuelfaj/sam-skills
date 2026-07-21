---
name: sam-work
description: Execute a software task through the complete bug-or-feature implementation, refinement, review, simplification, test-coverage, proposal, browser-proof, and demo-video workflow without asking for permission or confirmation on any step. Use when the user wants end-to-end delivery with no silently skipped phase, fresh proof after every change, a created or updated pull/merge request, and published video evidence.
---

# SAM Work

## Purpose

Turn one user request into a delivered pull or merge request through a fail-closed sequence of implementation and proof gates. Do not treat a child skill as complete merely because it was invoked. Capture and validate its terminal result.

Invoking this skill **is** the explicit user request for every action required by the contract below. It authorizes only these external writes: stage and commit task-owned work on the task branch, push that branch, create or update its proposal, and publish the required Playwright and demo videos on that proposal. It does not authorize merge, deployment, review approval, unrelated comments, destructive cleanup of user work, or production data access.

## Non-Negotiable Contract

Execute and prove every canonical phase. Never report `COMPLETE` while a phase is missing, stale, non-terminal, unvalidated, or silently skipped. Playwright may be `NOT_APPLICABLE` only for a proven non-web system; every other unavailable phase blocks completion.

## Autonomous execution (non-interactive)

**Always run the full workflow. Never pause for permission on any step.**

This section **overrides** every child skill’s “ask”, “request approval”, “confirm”, “unless explicitly requested”, or “publish only when authorized” language for the duration of the run.

**Forbidden mid-run interactions (zero exceptions):**

- Asking permission, confirmation, approval, “go ahead”, multiple-choice gates, or “should I continue?” for any phase or tool call.
- Asking clarifying questions, target questions, scope questions, environment questions, or publication questions after the workflow has started.
- Stopping for OS grants (screen recording, accessibility, camera, microphone), host/tool approval dialogs, or interactive consent. Attempt immediately with available capabilities.
- Re-asking for commit, push, PR/MR create/update, test runs, service boot, Playwright, video record/convert/upload, or re-runs after fixes.
- Using `AskUserQuestion`, waiting for a chat reply, or holding the session for human input.

**Authorized without re-asking (this invocation is the request):**

- Stage and commit task-owned work on the task branch; push that branch.
- Create or update the single task proposal; rewrite its description when required by freshness.
- Run tests, start verified local/dev/test services, capture Playwright video, record the demo MP4, convert media, upload every required video, and verify players.
- Apply in-scope corrections from refine/review/simplify/coverage loops within child retry limits.

**When something is ambiguous or impossible:**

1. Prefer repository evidence, frozen prompt, existing proposal, and verified local/dev/test targets.
2. If still blocked, record the assumption or exact failure and return `BLOCKED` (or continue remaining safe phases, then report).
3. Never pause to ask. “Could not X” in the final report is the correct outcome—not a mid-flow prompt.

Announce progress only as non-blocking status. Announcements must not wait for a reply.

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

State the complete workflow, the bug/feature classification, the target repository, the authorized external writes, and the pass criteria before implementation—then **continue without waiting**.

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
- Never interrupt the phase ledger to solicit permission. Execute, prove, or fail closed with receipts.

## Canonical phases

### 1. Implement

Run the selected implementation skill against the original request with parent authorization for task-owned stage/commit on the task branch. Child “do not commit unless asked” and “stop and request approval” rules become: execute in frozen scope, or return `BLOCKED` with receipts—**never ask**. Require complete acceptance, validation, and scope evidence. If blocked, stop with a workflow report.

### 2. Refine loop

Run `sam-refine-task` on the implemented strategy and current diff.

- `HIGH_CONFIDENCE` with no open required item closes the gate.
- `NOT_CONFIDENT` requires concrete corrections through the selected implementation contract, fresh validation, then another refinement pass.
- `BLOCKED` blocks the workflow.

### 3. Review loop

Run `sam-review` on an immutable bundle for the current head **local-only**: do not publish review decisions, do not offer publication choices, and do not ask which review action to take.

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

- If no proposal exists, create exactly one pull or merge request with the validated body—do not ask whether to open it.
- If one exists, update it instead of creating a duplicate—do not ask whether to update it.
- Push the exact reviewed head without requesting push permission, then read back proposal URL/ID, rendered description, remote head, and required CI state when configured.
- Store the creation/update and readback receipts. Do not merge.

### 7. Web browser proof

Always perform and record the applicability decision.

If the delivered system is web-accessible, run `sam-create-playwright-tests` against a real linked development UI/backend and verified real development data. Require `COMPLETE`, cleanup, and current-head proof. **Always enable and capture video** where the runner supports it—do not ask whether to record. Inventory every produced browser-test video, hash it, **upload every video to the proposal without asking**, and read the rendered proposal surface back. Every uploaded artifact must render as an inline/native video player; a file link alone does not pass.

If recording, capture, conversion, or upload fails, keep going through remaining attempts and cleanup, then report the exact failure under this phase. Do not pause for OS screen-recording permission or user confirmation.

If the system is not web-accessible, record `NOT_APPLICABLE` with repository/runtime evidence. This is the only phase that may be not applicable.

If browser-test work changes the repository, push it, refresh the proposal description, and rerun every invalidated gate before continuing.

### 8. Demo video

Run `sam-create-task-demo-video` using the verified real development environment and data with **publication pre-authorized** on the frozen proposal. Require `PUBLISHED`, validated media, privacy proof, cleanup, upload receipt, and rendered-player readback on the proposal. Start recording and upload immediately; never ask for permission to record, convert, or publish.

If the feature cannot be demonstrated honestly in a runnable surface after the child skill's allowed fallback attempts, or media tooling/OS capture denies the run, return `BLOCKED` with the exact attempt ledger. Never replace this phase with screenshots or a textual claim, and never wait for the user to fix permissions mid-flow.

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
