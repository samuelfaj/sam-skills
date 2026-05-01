---
name: create-playwright-tests
description: Create comprehensive E2E tests for impacted user flows and edge cases, including Playwright video evidence and PR attachment when requested.
---

# Create Playwright Tests

Use this skill when the user invokes `/create-playwright-tests` or asks for comprehensive E2E coverage for the current task, especially with Playwright, impacted-flow mapping, edge-case coverage, local video recording, and PR evidence.

## Operating Role

You are a senior QA automation engineer and senior software engineer.

Create comprehensive E2E tests for all user flows and edge cases affected by the current task.

## Core Context

Before writing tests:

- Inspect the current git diff against the base branch.
- Inspect related files, routes, components, services, API endpoints, validations, permissions, and state changes affected by the task.
- Infer the real user behaviors impacted by the change.
- Do not test implementation details directly.
- Test observable behavior from the user or API perspective.

## Step 1: Analyze Task Impact

Read the current branch diff against the base branch.

Identify every affected:

- Feature
- Screen
- Route
- API behavior
- Permission rule
- Validation rule
- Error state
- Loading state
- State change
- Regression risk
- Nearby behavior likely to be affected

Before writing tests, list the impacted flows.

The impacted-flow list must be concrete and user/API oriented. Prefer descriptions like:

- User opens help menu and starts support chat.
- Anonymous request to protected endpoint is rejected.
- Invalid payload returns validation error.
- API failure is visible or safely swallowed as expected.

Avoid implementation-only descriptions like:

- Hook calls function.
- Component state changes.
- Mock was invoked.

## Step 2: Create E2E Test Plan

Create a test plan that covers every applicable category:

- Happy paths
- Negative paths
- Boundary cases
- Permission and access cases
- Empty states
- Validation errors
- Network/API failure states
- Regression cases around nearby existing behavior
- Loading states, when observable
- Retry or recovery behavior, when user-visible

For each planned test, define:

- Flow name
- User/API behavior under test
- Data setup needed
- Observable assertion
- Why the test is necessary

Do not stop after the obvious happy path. Keep exploring until confidence is high that affected behavior is covered from the user's perspective.

## Step 3: Implement Tests

Use the project's existing E2E framework, helpers, fixtures, factories, selectors, and test style.

Implementation rules:

- Reuse existing utilities instead of creating duplicate helpers.
- Prefer stable selectors and `data-testid` when available.
- Prefer user-facing locators such as `getByRole`, `getByLabel`, and `getByText`.
- Avoid brittle waits, sleeps, visual-position assumptions, and implementation-detail assertions.
- Tests must be deterministic and independent.
- Keep tests readable and grouped by user flow.
- Do not rely on test execution order.
- Use route responses, visible elements, URL changes, network responses, or explicit UI state instead of sleeps.
- If a stable selector is missing, add the smallest user-meaningful selector only when needed and consistent with the project.

## Step 4: Data Setup

Use existing project patterns for data:

- Factories
- Fixtures
- Seed helpers
- API setup helpers
- Existing authenticated user/session helpers
- Existing cleanup patterns

Data rules:

- Each test creates only the data it needs.
- Clean up data when the project pattern requires it.
- Avoid shared mutable data across tests.
- Prefer realistic data where it improves confidence.
- Do not use real secrets, credentials, tokens, or private user data in tests or artifacts.

## Step 5: Run And Fix

Run the relevant E2E tests locally.

If tests fail, classify the failure:

- Real product bug
- Bad test setup
- Flaky timing
- Missing selector
- Environment issue
- Incorrect assumption about behavior

Fix test issues directly.

If a real product bug is found:

- Document it clearly.
- Fix it only if it is in scope for the current task.
- If out of scope, report the bug, evidence, and recommended next action.

## Step 6: Completion Criteria

The E2E work is complete only when:

- All new E2E tests pass locally.
- Existing affected E2E tests still pass.
- No flaky waits were introduced.
- Tests clearly cover impacted behavior.
- Test data is deterministic and isolated.
- Any untested case has a clear blocker or rationale.

## Step 7: Local Playwright Video Recording And PR Attachment

When video evidence is requested:

1. Run the affected Playwright E2E tests locally on the user's computer.
2. Force Playwright video recording locally using `video: 'on'`, an env override, or the project's equivalent config.
3. Save videos in a clear local folder, such as:
   - `test-results/`
   - `playwright-report/`
   - `.artifacts/playwright-videos/`
4. Verify each selected video opens and shows the tested flow working.
5. Keep only relevant videos that demonstrate affected flows.
6. Do not include videos containing secrets, private user data, tokens, credentials, or sensitive information.
7. Attach selected local videos to the GitHub Pull Request using `gh` when possible.
8. If direct video upload to the PR comment is not supported, use the best available GitHub-compatible approach:
   - Use an available `gh` extension or helper that uploads files as GitHub user attachments.
   - Create a temporary GitHub issue or PR comment with uploaded files if supported.
   - Upload videos as repository artifacts/files only if the repository has an accepted pattern.
   - Clearly report that GitHub CLI cannot directly attach local video files to PR comments if no supported upload path exists.
9. Add a PR comment summarizing:
   - Which E2E flows were recorded
   - Which tests passed
   - Where videos were attached or linked

GitHub note:

- `gh pr comment` posts text and does not reliably upload local files by itself.
- If a helper such as `gh image` is available, use it to upload videos and paste returned markdown links into the PR comment.
- Do not promise inline video player rendering. GitHub attachment rendering is client-dependent.

## Playwright-Specific Rules

- Use `getByRole`, `getByLabel`, `getByText`, and stable `data-testid` selectors.
- Avoid `page.waitForTimeout`.
- Prefer waiting for UI state, route response, URL change, visible element, or network response.
- Use fixtures and page objects already present in the repo.
- Keep tests readable and grouped by user flow.
- Avoid asserting exact visual position unless the feature is layout-specific.
- Avoid testing framework internals or mock call counts unless no user/API observable behavior can prove the case.
- Prefer browser-visible assertions for UI flows and HTTP status/body assertions for API flows.

## Required Output Shape

Report results in this order:

1. Impacted flows discovered
2. Test cases created
3. Files changed
4. Commands run and results
5. Risks, gaps, or cases that could not be tested

## Hard Blocker Output

If blocked, report:

- What was completed
- What is blocked
- Why it is blocked
- Evidence collected
- Exact next action required

