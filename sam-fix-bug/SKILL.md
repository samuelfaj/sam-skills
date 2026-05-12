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
- Do not commit temporary planning documents such as `ANALYSIS.html`, `TDD.html`, or `TODO.html`.
- Do not skip tests. If a test cannot be implemented or run, explain exactly why.
- Continue until the Definition of Done is satisfied or a real blocker prevents further progress.

## User Experience Optimization Pass

For any user-visible workflow, treat a technically correct but confusing result
as incomplete. Keep the fix surgical, but verify the experience a real user sees.

Check, when applicable:

- Show human-readable labels instead of raw internal IDs.
- Selects, autocompletes, tables, audit rows, and detail views include useful
  context such as name, email, status, or type, not only opaque identifiers.
- Loading, empty, error, disabled, and permission-denied states are clear.
- Validation and action errors explain what the user can do next.
- Missing or unauthorized related data does not break the whole workflow.
- Backend/API contracts expose enough display-ready data, or a clear existing
  lookup path, so the frontend does not invent fragile labels or extra calls.
- Inputs, controls, icons, and dynamic states remain accessible by label,
  keyboard, focus state, screen reader, and contrast.
- User-facing data does not expose sensitive fields, raw PII, internal-only
  error details, or debug metadata.
- Display-data fixes do not introduce obvious N+1 queries, list overfetching,
  client-side lookup loops, or unbounded select/autocomplete payloads.
- Critical failures remain observable through useful logs, metrics, or trace
  context without leaking sensitive data.
- API, data, migration, and rollout changes stay backward compatible unless the
  bug fix explicitly requires a breaking change.

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
- User-facing display labels, states, and messages
- Accessibility, privacy, performance, observability, and compatibility risks

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
2. Backend / service-layer reviewer, including UI-facing contracts, DTO field
   names, display data, and compatibility when applicable
3. Frontend / UI-flow reviewer, including legibility, flow states, option
   labels, and user-facing messages when applicable
4. Testing / QA reviewer
5. Architecture / maintainability reviewer
6. Edge-case / regression-risk reviewer

Each reviewer must answer:

- What is likely causing the bug?
- What business rule should the system enforce?
- What existing code supports or contradicts that rule?
- What risks exist in fixing it?
- What tests are required to prove correctness?
- What user-visible labels, states, messages, or API contract details must stay
  understandable?
- What accessibility, privacy, performance, observability, or compatibility risk
  could the fix introduce?

Create local `ANALYSIS.html` as a valid standalone HTML document with:

- Bug summary
- Root-cause hypothesis
- Confirmed root cause, if known
- Real business rule
- Affected files and flows
- Test strategy
- Implementation risks
- Review council notes
- User experience optimization notes, when the bug touches a user-visible flow
- Accessibility, privacy, performance, observability, and compatibility notes,
  when relevant
- Recommended fix approach

`ANALYSIS.html` is local only. Never commit it.

## Step 4: TDD Implementation Plan

Spawn a TDD expert subagent only if the user explicitly allows subagents. Otherwise simulate the TDD expert yourself.

Create local `TDD.html` as a valid standalone HTML document with:

- Failing tests already added
- Additional tests to add
- Expected red/green/refactor cycle
- Minimal implementation plan
- Refactor boundaries
- Risks of overengineering
- User-facing display or API contract assertions to verify, when applicable
- Accessibility, privacy, performance, observability, and compatibility checks,
  when applicable
- Final validation checklist

`TDD.html` is local only. Never commit it.

## Step 5: TODO And Implementation

Create local `TODO.html` as a valid standalone HTML document with a complete task checklist.

Then implement the fix.

Implementation requirements:

- Make the smallest production-code change that satisfies the business rule.
- Keep behavior unchanged outside the target workflow.
- Preserve existing public APIs unless a change is unavoidable.
- Update or add tests as needed.
- Keep the diff easy to review.
- Remove dead code only if directly related to the fix.
- Avoid speculative abstractions.
- Do not expose raw internal IDs to users when a stable human label is available.
- If the UI needs entity labels or context, prefer the existing backend contract
  or the smallest compatible contract extension over frontend guesswork.
- Avoid adding frontend loops, backend N+1 queries, or unbounded payloads while
  making display data more usable.
- Keep sensitive data out of UI, logs, analytics, and error responses.

`TODO.html` is local only. Never commit it.

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
   - Raw IDs or ambiguous labels shown to users
   - Backend contract forces poor UX or fragile frontend lookups
   - Unclear loading, empty, error, disabled, or permission state
   - Accessibility regression
   - Sensitive data exposed in UI, logs, analytics, or errors
   - N+1 query, unbounded payload, or client-side lookup loop
   - Missing observability for critical failure paths
   - Unnecessary breaking contract or rollout risk
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
- Contract/API tests, when UI data shape is involved
- Regression tests
- Edge cases
- Negative cases
- Previously failing scenario
- Related business-rule scenarios
- Display-label versus internal-id assertions, when applicable
- UI loading, empty, error, disabled, and permission states, when applicable
- Accessibility and keyboard/focus behavior, when browser-testable
- Privacy/security assertions for sensitive data, when applicable
- Performance or query-count coverage for display-data changes, when practical
- Contract compatibility and observability checks, when relevant

Implement any missing tests needed to prove the fix works.

Run appropriate test suites.

Collect final proof:

- Test commands used
- Passing test output summary
- Screenshots or videos for UI/e2e flows, showing human-readable labels and
  relevant states when applicable
- Accessibility, privacy, performance, observability, or compatibility evidence
  when those risks are relevant
- Relevant before/after evidence

## Step 9: Mandatory Post-Code Gates

After coding, run the mandatory gates in this exact order and complete each one
fully before moving to the next:

1. Invoke `$sam-review-code` against the final local diff.
2. Fix every valid correction from `$sam-review-code`.
3. Rerun relevant tests after each correction.
4. Invoke `$sam-review-code` again.
5. Repeat until `$sam-review-code` reports no blockers or remaining corrections.
6. Invoke `$create-test-coverage` against the final local diff and complete it.
7. Implement every required test or fix found by `$create-test-coverage`.
8. Invoke `$create-playwright-tests` for the impacted user flows and edge cases
   and complete it.
9. Implement every required Playwright test or fix found by
   `$create-playwright-tests`.
10. Invoke `$create-task-demo-video` for the completed workflow and complete it.
11. Attach or collect the generated demo-video evidence required by that skill.

If `$create-test-coverage`, `$create-playwright-tests`, or
`$create-task-demo-video` changes production or test code, restart this sequence
from `$sam-review-code` and repeat the gates in the same order until the full
sequence completes with no blockers.

Do not create the PR/MR while `$sam-review-code`, `$create-test-coverage`,
`$create-playwright-tests`, or `$create-task-demo-video` still has a required
correction, unresolved blocker, missing evidence artifact, or unknown relevant
test status.

## Step 10: Prepare Pull Request Or Merge Request

Before creating PR/MR:

- Ensure `ANALYSIS.html`, `TDD.html`, and `TODO.html` are not committed.
- Ensure only relevant source and test files are included.
- Check `git diff`.
- Check `git status`.
- Run final test suite.
- Confirm `$sam-review-code` has no remaining corrections.
- Confirm `$create-test-coverage` completed fully with no unresolved blocker.
- Confirm `$create-playwright-tests` completed fully with no unresolved blocker.
- Confirm `$create-task-demo-video` completed fully and produced demo evidence.
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

Do not include or commit `ANALYSIS.html`, `TDD.html`, or `TODO.html`.

## Definition Of Done

Task is complete only when all are true:

- Bug is reproduced by at least one failing test before the fix.
- Real business rule is documented locally.
- Fix is implemented with minimal production-code changes.
- All relevant tests pass.
- New regression coverage exists.
- Edge cases were considered.
- Applicable UX, accessibility, privacy, performance, observability, and
  compatibility risks were checked without broadening the fix unnecessarily.
- Six-perspective review loop reports no unresolved blockers.
- Mandatory post-code gate sequence completed in order:
  `$sam-review-code`, `$create-test-coverage`, `$create-playwright-tests`,
  `$create-task-demo-video`.
- `$sam-review-code` loop reports no blockers or remaining corrections.
- `$create-test-coverage` completed and all required coverage gaps are resolved.
- `$create-playwright-tests` completed and all required browser coverage gaps
  are resolved.
- `$create-task-demo-video` completed and demo-video evidence is available.
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
