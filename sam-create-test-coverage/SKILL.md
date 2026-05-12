---
name: sam-create-test-coverage
description: Create exhaustive risk-based test coverage across unit, component, integration, API/contract, and E2E tests for backend or frontend changes, choosing the smallest reliable test layer for maximum confidence.
---

# Sam Create Test Coverage

Use this skill when the user asks for tests, all tests, confidence, regression coverage, backend tests, React tests, API tests, integration tests, E2E tests, or maximum confidence for a change.

## Operating Role

You are a senior QA automation engineer and senior software engineer.

By default, treat every request as exhaustive, risk-based coverage for the affected behavior. Find every meaningful test case that can increase confidence, choose the smallest reliable test layer for each case, implement the tests, run them, and report exact confidence blockers.

## Critical Environment Rule

E2E tests that use real data may run only in `dev`.

- Do not run E2E tests with real data in production, staging, customer tenants, or any non-dev environment.
- If the environment is unclear, stop and identify it before running real-data E2E tests.
- Prefer deterministic seeded, mocked, or isolated test data over real data whenever possible.
- If real-data E2E is required, prove the target is dev before running it and state that proof in the final output.

## Core Context

Before writing tests:

- Inspect the current git diff against the base branch.
- Inspect affected files, routes, components, services, repositories, validators, schemas, hooks, permissions, cache, persistence, and state changes.
- Inspect existing tests for affected code, adjacent code, and any comparable working flow mentioned by the user.
- Inspect package scripts, test configs, CI config, Docker/dev setup, and nearby test commands to identify the correct runners.
- Inspect user report, QA criteria, acceptance criteria, PR/MR comments, linked issue text, and any task notes available in context.
- Infer the real user/API/system behaviors impacted by the change.
- Build a coverage matrix before implementing tests.
- Do not test implementation details directly when user/API observable behavior can prove the case.
- Do not claim full confidence unless every meaningful matrix row is automated, manually proven, or explicitly marked redundant with rationale.

## Intent-First Test Philosophy

Tests verify intent, not just behavior.

- Every new or updated test must encode why the behavior matters to the user,
  business rule, API contract, permission model, or system invariant.
- A test that only proves a hardcoded output is not enough. Example:
  `expect(getUserName()).toBe('John')` is weak if the function takes a fixed ID
  or the assertion mirrors implementation setup without proving the rule.
- Prefer tests that would fail when the business logic, policy, permission,
  data mapping, or workflow contract changes incorrectly.
- If you cannot write a test that would fail when the intended business logic
  changes, re-check the function boundary, requirement, or design before adding
  shallow coverage.
- Test names, setup, and assertions should make the intent visible without
  requiring the reader to reverse-engineer why the case exists.

## Step 1: Analyze Task Impact

Read the current branch diff against the base branch.

Identify every affected:

- Feature
- Screen
- Route
- API endpoint
- Request payload
- Response body
- Permission or role rule
- Validation rule
- State transition
- Cache behavior
- Persistence behavior
- Error state
- Loading state
- Empty state
- Regression risk
- Nearby behavior likely to be affected

Before writing tests, list impacted behaviors and build a coverage matrix.

The impacted-behavior list must be concrete and user/API/system oriented. Prefer descriptions like:

- User saves an assigned live stream without losing its series.
- POST `/v1/example` rejects invalid payload with 400 and field errors.
- Service preserves existing relation when optional field is omitted.
- React form shows empty state and disables Save when there are no options.

Avoid implementation-only descriptions like:

- Hook calls function.
- Component state changes.
- Mock was invoked.

## Step 2: Build Exhaustive Coverage Matrix

The matrix must include every meaningful equivalence class around the changed behavior:

- Reported failing flow
- Comparable working flow mentioned in the task
- Primary happy path
- Negative path
- Boundary values
- Add, remove, update, and preserve-existing-value variants
- Existing value, missing value, `null`, `undefined`, empty string, malformed value, and sentinel values when those inputs affect branching logic
- Loading state
- Empty state
- Error state
- Permission and role variants
- Validation boundaries
- Save, cancel, retry, and navigation behavior
- API method, path, query, payload, status, headers, and response-body assertions
- Persistence, read-after-write, cache invalidation, and stale-data behavior when applicable
- Cross-browser, mobile, or responsive variants only when changed behavior can differ by viewport/browser
- Backward compatibility and contract compatibility when existing clients may depend on behavior

For each matrix row, choose one status:

- `UNIT`: covered by a unit test for pure logic, mapper, validator, serializer, reducer, utility, or isolated hook behavior
- `COMPONENT`: covered by a React/component test for rendering, form state, interaction, accessibility state, or UI-only behavior
- `INTEGRATION`: covered by multiple modules/services/repositories/cache/persistence working together
- `API_CONTRACT`: covered by HTTP method/path/query/payload/status/response behavior
- `E2E`: covered by a real user/browser or full-stack journey
- `MANUAL_PROOF`: covered by browser, video, API, database, or log proof
- `REDUNDANT`: equivalent to another covered row, with exact reason
- `NOT_COVERED`: not covered, with blocker and residual risk

Do not default everything to E2E. Prefer fast lower-level tests when they prove the same contract. Use E2E for critical user journeys, cross-service wiring, auth/navigation, and video proof.

## Step 3: Select Test Layers

Choose the smallest reliable test layer for each matrix row:

- Use unit tests for pure logic, serialization, validation, mapping, helper functions, reducers, and deterministic branch logic.
- Use component tests for React rendering, form behavior, field serialization, accessibility states, and UI interactions that do not require a real backend.
- Use integration tests for service/repository/cache/persistence coordination and cross-module behavior.
- Use API/contract tests for endpoint request/response behavior, validation, auth, permissions, and HTTP-level compatibility.
- Use E2E tests for high-value user journeys, frontend-backend wiring, auth/navigation, real browser behavior, and flows needing video proof.

For each planned test, define:

- Flow name
- Matrix row covered
- Business intent: why this behavior matters
- Selected layer
- Why that layer is sufficient
- Data setup needed
- Observable assertion
- Failure mode: what business-logic change should make this test fail
- Command to run it

If a row needs multiple layers, add them. Example: React form serialization bug may need unit schema tests, component interaction tests, and one E2E proof for the critical workflow.

## Step 4: Implement Tests

Use the project's existing test frameworks, helpers, fixtures, factories, selectors, mocks, test database setup, and test style.

Implementation rules:

- Each test must prove intent, not merely exercise a line or return a fixture value.
- Avoid assertions that only restate hardcoded setup unless they prove a rule,
  contract, permission, mapping, or invariant.
- If the only possible assertion is trivial, improve the seam or choose a
  higher-value test layer before claiming coverage.
- Reuse existing utilities instead of creating duplicate helpers.
- Prefer stable user-facing selectors and `data-testid` when available.
- Prefer `getByRole`, `getByLabel`, and `getByText` for React/browser tests.
- Avoid brittle waits, sleeps, visual-position assumptions, and implementation-detail assertions.
- Tests must be deterministic and independent.
- Keep tests readable and grouped by behavior.
- Do not rely on test execution order.
- Use route responses, visible elements, URL changes, network responses, HTTP assertions, database reads, or explicit state instead of sleeps.
- If a stable selector is missing, add the smallest user-meaningful selector only when needed and consistent with the project.
- Keep production code changes limited to what tests legitimately need or what the bug fix requires.

## Step 5: Data Setup And Safety

Use existing project patterns for data:

- Factories
- Fixtures
- Seed helpers
- API setup helpers
- Test database setup
- Existing authenticated user/session helpers
- Existing cleanup patterns
- Docker/dev service setup when applicable

Data rules:

- Each test creates only the data it needs.
- Clean up data when project pattern requires it.
- Avoid shared mutable data across tests.
- Prefer realistic data where it improves confidence.
- Do not use real secrets, credentials, tokens, or private user data in tests or artifacts.
- E2E tests with real data must run only in `dev`; verify and state the dev target before running them.

## Step 6: Run, Fix, And Expand

Run tests in this order when applicable:

1. New targeted tests.
2. Existing affected tests.
3. Unit/integration/API/contract tests for touched backend behavior.
4. Component/unit tests for touched React behavior.
5. E2E tests for critical user journeys.
6. Typecheck and lint for touched test/code files.
7. Relevant full suite when practical.
8. Docker or linked frontend/backend proof when the task crosses services.

If tests fail, classify the failure:

- Real product bug
- Bad test setup
- Flaky timing
- Missing selector
- Environment issue
- Incorrect assumption about behavior
- Pre-existing unrelated suite failure

Fix test issues directly.

If a real product bug is found:

- Document it clearly.
- Fix it only if it is in scope for the current task.
- If out of scope, report the bug, evidence, and recommended next action.

Keep expanding until every meaningful matrix row has a status.

## Step 7: Evidence And PR/MR Updates

When PR/MR evidence is requested:

- Attach screenshots, videos, logs, or command evidence only when they materially improve confidence.
- For videos in GitHub or GitLab, place the raw video URL alone on its own paragraph with a blank line before and after it. Do not wrap the video URL in markdown image/link syntax in the final PR/MR comment.
- Use available CLI tools (`gh`, `glab`) to update PR/MR comments when requested.
- Include exact commands and pass/fail results.
- Distinguish local targeted success from full-suite or remote-check status.

Video URL format:

```markdown
Aqui está o vídeo funcionando:

https://github.com/user-attachments/assets/9d67afa2-81f8-4aa1-9ca2-173a81b63d56

Continua com algum texto...
```

## Completion Criteria

Coverage work is complete only when:

- Every QA/acceptance criterion maps to `UNIT`, `COMPONENT`, `INTEGRATION`, `API_CONTRACT`, `E2E`, `MANUAL_PROOF`, or `REDUNDANT`.
- Every meaningful matrix row has a status.
- Every new or updated test states or clearly expresses the business/user/API
  intent it protects.
- New coverage would fail for the intended business-logic regression, not only
  for a changed literal or mocked fixture.
- New tests pass locally.
- Existing affected tests pass locally.
- Relevant suite status is known.
- Typecheck/lint status is known when applicable.
- Cross-service proof exists when backend/frontend integration is part of the task.
- Any `NOT_COVERED` row has a clear blocker, exact residual risk, and recommended next action.

Full-confidence rule:

- Only say `100% confidence` when every QA/acceptance criterion and every meaningful matrix row is automated, manually proven, or explicitly redundant; all affected local suites pass; linked frontend/backend services are exercised when the task crosses that boundary; E2E with real data, if any, ran only in verified dev; and PR/MR evidence is attached when requested.
- If any of those conditions is missing, do not say `100% confidence`. State the exact confidence blocker instead.

## Required Output Shape

Report results in this order:

1. Impacted behavior discovered
2. Coverage matrix with selected test layer and status
3. Tests created or updated
4. Files changed
5. Commands run and results
6. Environment/data safety notes, including dev-only proof for any real-data E2E
7. Confidence level and exact blockers, if any
8. Risks, gaps, or cases that could not be tested

## Hard Blocker Output

If blocked, report:

- What was completed
- What is blocked
- Why it is blocked
- Evidence collected
- Exact next action required
