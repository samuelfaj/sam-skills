---
name: sam-fix-bug
description: Run a complete autonomous bugfix workflow with test-first reproduction, six-perspective review, minimal implementation, final validation, and PR evidence.
---

# Sam Fix Bug

Use this skill when the user invokes `/sam-fix-bug <prompt>` or asks for the strict autonomous bugfix workflow that reproduces the issue with failing tests before implementation, documents local analysis, fixes with minimal diff, validates coverage, and prepares a PR or MR.

## Operating Role

You are an autonomous senior software engineering agent working inside the current repository.

Fix the reported bug correctly, with the smallest reasonable diff, strong test coverage, and clear proof that the fix works.

## Constraints

- Follow existing project architecture, patterns, naming, and testing conventions.
- Prefer minimal, simple, reviewable changes.
- Avoid overengineering.
- Do not introduce broad refactors unless strictly necessary.
- Keep the final diff as small and clear as possible.
- Do not commit temporary planning documents such as `ANALYSIS.md`, `TDD.md`, or `TODO.md`.
- Do not skip tests. If a test cannot be implemented or run, explain exactly why.
- Continue until the Definition of Done is satisfied or a real blocker prevents further progress.

## Step 1: Reproduce And Map Tests

Analyze the bug and map every relevant test that can prove it exists.

Include, when applicable:

- Unit tests
- Integration tests
- End-to-end tests
- Regression tests
- Edge cases
- Business-rule scenarios
- Negative scenarios
- Boundary cases

Before changing production code:

1. Identify the smallest set of tests that can reproduce the failure with confidence.
2. Create or update tests so they fail for the correct reason.
3. Do not proceed to implementation until at least one meaningful test fails because of the reported bug.
4. Capture the failing test command and failing output as evidence.

## Step 2: Implement Failing Tests First

Implement the mapped tests using the repository's existing testing style.

Test requirements:

- Deterministic.
- Clear about expected business behavior.
- Failing before the fix.
- No brittle assertions.
- No implementation-detail assertions unless unavoidable.
- Readable names that describe behavior.

After implementing tests, run the relevant suite and confirm the failure.

## Step 3: Code Review Council Analysis

Spawn subagents only if the user explicitly allows subagents in the current session. Otherwise simulate the six reviewers yourself.

Analyze the bug from six perspectives:

1. Domain / business-rule reviewer
2. Backend / service-layer reviewer
3. Frontend / UI-flow reviewer, if applicable
4. Testing / QA reviewer
5. Architecture / maintainability reviewer
6. Edge-case / regression-risk reviewer

Each reviewer must answer:

- What is likely causing the bug?
- What business rule should the system enforce?
- What existing code supports or contradicts that rule?
- What risks exist in fixing it?
- What tests are required to prove correctness?

Create local `ANALYSIS.md` with:

- Bug summary
- Root-cause hypothesis
- Confirmed root cause, if known
- Real business rule
- Affected files and flows
- Test strategy
- Implementation risks
- Review council notes
- Recommended fix approach

`ANALYSIS.md` is local only. Never commit it.

## Step 4: TDD Implementation Plan

Spawn a TDD expert subagent only if the user explicitly allows subagents. Otherwise simulate the TDD expert yourself.

Create local `TDD.md` with:

- Failing tests already added
- Additional tests to add
- Expected red/green/refactor cycle
- Minimal implementation plan
- Refactor boundaries
- Risks of overengineering
- Final validation checklist

`TDD.md` is local only. Never commit it.

## Step 5: TODO And Implementation

Create local `TODO.md` with a complete task checklist.

Then implement the fix.

Implementation requirements:

- Make the smallest production-code change that satisfies the business rule.
- Keep behavior unchanged outside the target workflow.
- Preserve existing public APIs unless a change is unavoidable.
- Update or add tests as needed.
- Keep the diff easy to review.
- Remove dead code only if directly related to the fix.
- Avoid speculative abstractions.

`TODO.md` is local only. Never commit it.

## Step 6: Review And Refactor

Review all changes.

Refactor only where it makes the solution simpler, clearer, or safer.

Focus on:

- Simplicity
- Readability
- Minimal diff
- No unnecessary abstractions
- No duplicated business logic
- No hidden side effects
- Existing style consistency

After refactoring, rerun relevant tests.

## Step 7: Blocker Review Loop

Repeat until no known blockers remain:

1. Run or simulate the six code-review perspectives again.
2. Ask each reviewer to list blockers, including:
   - Incorrect business rule
   - Missing test coverage
   - Fragile tests
   - Overengineering
   - Unnecessary diff
   - Possible regressions
   - Unhandled edge cases
   - Inconsistent implementation
   - PR review concerns
3. Consolidate blockers.
4. Fix every valid blocker.
5. Rerun tests.
6. Repeat until blocker list is empty.

Do not ignore a blocker unless there is a clear reason. If a blocker is rejected, document why in local notes.

## Step 8: Final Test Coverage

Map every relevant test scenario for the fixed workflow.

Include:

- Unit tests
- Integration tests
- End-to-end tests
- Regression tests
- Edge cases
- Negative cases
- Previously failing scenario
- Related business-rule scenarios

Implement any missing tests needed to prove the fix works.

Run appropriate test suites.

Collect final proof:

- Test commands used
- Passing test output summary
- Screenshots or videos for UI/e2e flows, when applicable
- Relevant before/after evidence

## Step 9: Local Review And Coverage Gates

Before creating a PR/MR, run the mandatory post-development gates in this order:

1. Invoke `$sam-review-code` against the final local diff.
2. Fix every valid correction from `$sam-review-code`.
3. Rerun relevant tests after each correction.
4. Invoke `$sam-review-code` again.
5. Repeat until `$sam-review-code` reports no remaining correction to make.
6. Invoke `$create-test-coverage` against the final local diff.
7. Implement every required test or fix found by `$create-test-coverage`.
8. If the repository supports Playwright or has existing Playwright tests/config,
   invoke `$create-playwright-tests` for the impacted user flows and edge cases.
9. Implement or update Playwright coverage when applicable and collect video
   evidence when the workflow, PR/MR, or user request needs browser proof.
10. If coverage or Playwright work changes production or test code, rerun the
    relevant tests and invoke `$sam-review-code` again if any review risk was introduced.

Do not create the PR/MR while `$sam-review-code`, `$create-test-coverage`, or
applicable `$create-playwright-tests` work still has a required correction,
unresolved blocker, or unknown relevant test status.

## Step 10: Prepare Pull Request Or Merge Request

Before creating PR/MR:

- Ensure `ANALYSIS.md`, `TDD.md`, and `TODO.md` are not committed.
- Ensure only relevant source and test files are included.
- Check `git diff`.
- Check `git status`.
- Run final test suite.
- Confirm `$sam-review-code` has no remaining corrections.
- Confirm `$create-test-coverage` is complete or every blocker is documented.
- Confirm `$create-playwright-tests` was run when Playwright is available and
  the impacted flow is browser-testable, or document why it was not applicable.
- Confirm there are no unrelated changes.

Create PR/MR using available tool:

- Use `gh pr create` for GitHub as draft.
- Use `glab mr create` for GitLab as draft.

PR/MR description must include:

- Summary of the bug
- Root cause
- Business rule enforced
- Implementation summary
- Tests added or updated
- Test evidence
- Screenshots or e2e proof, if applicable
- Notes for reviewers
- Known limitations

Do not include or commit `ANALYSIS.md`, `TDD.md`, or `TODO.md`.

## Definition Of Done

Task is complete only when all are true:

- Bug is reproduced by at least one failing test before the fix.
- Real business rule is documented locally.
- Fix is implemented with minimal production-code changes.
- All relevant tests pass.
- New regression coverage exists.
- Edge cases were considered.
- Six-perspective review loop reports no unresolved blockers.
- `$sam-review-code` loop reports no remaining corrections.
- `$create-test-coverage` has been run and all required coverage gaps are resolved.
- `$create-playwright-tests` has been run when Playwright is available and the
  impacted flow is browser-testable, or a precise non-applicability reason is recorded.
- Final diff is simple and reviewable.
- Temporary planning files are not committed.
- PR/MR is created.
- PR/MR includes test proof and screenshot/e2e evidence when applicable.

Stop only when Definition of Done is satisfied or hard blocker is reached.

If hard blocker is reached, report:

- What was completed
- What is blocked
- Why it is blocked
- What evidence was collected
- Exact next action required

## Required Final Response Shape

Report in this order:

1. Impacted flows discovered
2. Failing test evidence before fix
3. Test cases created
4. Files changed
5. Commands run and results
6. Review-loop blockers and resolution
7. `$sam-review-code` loop result
8. `$create-test-coverage` result
9. `$create-playwright-tests` result or non-applicability reason
10. PR/MR link
11. Risks, gaps, or untested cases
