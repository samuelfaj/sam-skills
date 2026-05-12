---
name: create-playwright-tests
description: Create comprehensive E2E tests for impacted user flows and edge cases, including Playwright video evidence and PR attachment when requested.
---

# Create Playwright Tests

Use this skill when the user invokes `/create-playwright-tests` or asks for comprehensive E2E coverage for the current task, especially with Playwright, impacted-flow mapping, edge-case coverage, local video recording, and PR evidence.

## Operating Role

You are a senior QA automation engineer and senior software engineer.

Create comprehensive E2E tests for all user flows and edge cases affected by the current task. By default, treat every request as a request for exhaustive, risk-based coverage of the affected behavior.

## Core Context

Before writing tests:

- Inspect the current git diff against the base branch.
- Inspect related files, routes, components, services, API endpoints, validations, permissions, and state changes affected by the task.
- Inspect existing tests for the affected feature, adjacent features, and any comparable working flow mentioned by the user.
- Inspect the user report, QA criteria, acceptance criteria, PR/MR comments, and any linked issue text available in context.
- Infer the real user behaviors impacted by the change.
- Build a test matrix before implementing tests.
- Do not test implementation details directly.
- Test observable behavior from the user or API perspective.
- Do not claim full confidence unless every meaningful matrix row is automated, manually proven, or explicitly marked redundant with rationale.

## Real Dev Environment Requirement

Whenever possible, exercise the real running application, not a mocked UI shell.

- Start the application before creating, updating, or recording Playwright tests.
- Use the real UI route and real browser interactions for user-facing flows.
- If the user explicitly says the environment is dev and the database is a dev
  database, prefer real dev data over synthetic fixtures when it improves
  confidence and does not expose secrets or private user data.
- Never use production data, production credentials, or production services for
  tests or recorded artifacts unless the user explicitly asks and the workflow is
  read-only and safe.
- If frontend and backend are separate repositories or services instead of one
  monorepo, bring both up through Docker or the repository-supported container
  workflow whenever possible, link the frontend to the backend, and test against
  that linked local/dev stack.
- If Docker or linked-service startup is blocked, record the exact blocker and
  fall back only to the closest safe runnable environment.

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

Before writing tests, list the impacted flows and build a coverage matrix.

The impacted-flow list must be concrete and user/API oriented. Prefer descriptions like:

- User opens help menu and starts support chat.
- Anonymous request to protected endpoint is rejected.
- Invalid payload returns validation error.
- API failure is visible or safely swallowed as expected.

Avoid implementation-only descriptions like:

- Hook calls function.
- Component state changes.
- Mock was invoked.

The coverage matrix must include every meaningful equivalence class around the changed behavior:

- Reported failing flow
- Comparable working flow mentioned in the task
- Primary happy path
- Add, remove, update, and preserve-existing-value variants
- Existing value, missing value, `null`, `undefined`, empty string, and sentinel values when those inputs affect branching logic
- Loading state
- Empty state
- Error state
- Permission and role variants
- Validation boundaries
- Save, cancel, retry, and navigation behavior
- API method, path, query, payload, status, and response-body assertions
- UI persistence, read-after-write, and stale-cache behavior when applicable
- Cross-browser, mobile, or responsive variants only when the changed behavior can differ by viewport/browser

For each matrix row, choose one status:

- `AUTOMATED`: covered by a test file and test name
- `MANUAL_PROOF`: covered by browser, video, API, or database proof
- `REDUNDANT`: equivalent to another covered row, with exact reason
- `NOT_COVERED`: not covered, with blocker and residual risk

## Step 2: Create E2E Test Plan

Create a test plan that covers every applicable matrix row by default:

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
- Existing working comparable behavior, when mentioned
- Save-without-changing-related-field behavior
- Explicit clearing/removal behavior
- Null/undefined/empty/sentinel payload behavior, when applicable
- Cache/read-after-write behavior, when applicable

For each planned test, define:

- Flow name
- User/API behavior under test
- Data setup needed
- Observable assertion
- Matrix rows covered
- Why the test is necessary

Do not stop after the obvious happy path. Keep exploring until every meaningful matrix row has a status. If adding all rows as E2E tests would create brittle or slow coverage, split coverage across E2E, component/integration, and API tests, but still prove every matrix row.

## Step 3: Implement Tests

Use the project's existing E2E framework, helpers, fixtures, factories, selectors, and test style.

Implementation rules:

- Tests should drive the real application UI whenever the behavior is user-facing.
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
- Prefer explicit dev-database records when the user has confirmed the target is
  dev and the database is dev; use factories or fixtures when real dev data is
  unavailable, unsafe, or would make the test nondeterministic.
- Prefer realistic data where it improves confidence.
- Do not use real secrets, credentials, tokens, or private user data in tests or artifacts.

## Step 5: Run And Fix

Start the required app services, then run the relevant E2E tests locally.

If the flow crosses frontend/backend boundaries and those services are not in a
single monorepo, start or verify both through Docker or the repo-supported
container workflow, configure the frontend to call the local/dev backend, and
confirm the browser is exercising that linked stack before trusting results.

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
- The app was started for the test run, or an exact startup blocker is documented.
- User-facing flows exercise the real UI whenever possible.
- Explicit dev-data usage is limited to confirmed dev databases.
- Separate frontend/backend services are linked through Docker or the closest
  repo-supported container workflow whenever possible.
- Unit, integration, API, or contract tests that cover affected non-browser behavior pass locally.
- No flaky waits were introduced.
- Tests clearly cover impacted behavior.
- Test data is deterministic and isolated.
- Every QA/acceptance criterion maps to `AUTOMATED`, `MANUAL_PROOF`, or `REDUNDANT`.
- Any `NOT_COVERED` matrix row has a clear blocker, exact residual risk, and recommended next action.

Full-confidence rule:

- Only say `100% confidence` when every QA/acceptance criterion and every meaningful matrix row is automated, manually proven, or explicitly redundant; all affected local suites pass; linked frontend/backend services are exercised when the task crosses that boundary; and PR/MR evidence is attached when requested.
- If any of those conditions is missing, do not say `100% confidence`. State the exact confidence blocker instead.

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
7. Attach selected local videos to the GitHub Pull Request using `gh` when possible, or to the GitLab Merge Request using `glab` when the repo is on GitLab.
8. If direct video upload to the PR/MR comment is not supported, use the best available platform-specific approach:
   - Use an available `gh` extension or helper that uploads files as GitHub user attachments.
   - For GitLab, use the Markdown Uploads API through `glab api`.
   - Create a temporary issue or PR/MR comment with uploaded files if supported.
   - Do not commit video files to the repository unless the user explicitly asks for versioned video artifacts.
   - Clearly report when the platform CLI cannot attach local video files to comments if no supported upload path exists.
9. Add a PR comment summarizing:
   - Which E2E flows were recorded
   - Which tests passed
   - Where videos were attached or linked
   - What each video proves, written immediately before that specific video link or embed.

GitHub/GitLab note:

- `gh pr comment` posts text and does not reliably upload local files by itself.
- If a helper such as `gh image` is available, use it to upload videos and extract the raw uploaded video URL from the returned markdown.
- Every video must have a short proof description immediately before the video. Use the format `This video is proof that ...` and describe the specific behavior shown, not a vague label like "E2E proof".
- For GitHub attachment URLs, place the raw uploaded video URL alone on its own paragraph with a blank line before and after it. Do not wrap GitHub user-attachment video URLs in markdown image/link syntax. Example:

  ```markdown
  This video is proof that the school Camp Day Report excludes the regular scheduled student who has no final camp-day signup.

  https://github.com/user-attachments/assets/9d67afa2-81f8-4aa1-9ca2-173a81b63d56

  This video is proof that the report error state renders after a bounded 500 retry sequence.

  https://github.com/user-attachments/assets/15b4d394-a607-4fb0-8417-50f3dc0b0c57
  ```
- For GitLab, prefer `.mp4` files because GitLab Markdown can render uploaded MP4 video attachments inline. Convert Playwright `.webm` output to `.mp4` with a browser-compatible codec before upload:

  ```bash
  mkdir -p .artifacts/playwright-mp4
  ffmpeg -y -i .artifacts/playwright-videos/example.webm \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart -an \
    .artifacts/playwright-mp4/example.mp4
  ```

- Upload each MP4 to the GitLab project with the Markdown Uploads API via `glab`. Use the project placeholder `:id` from inside the target repo, or pass an explicit project id/path when needed:

  ```bash
  glab api -X POST projects/:id/uploads --form "file=@.artifacts/playwright-mp4/example.mp4"
  ```

- In GitLab MR comments, paste the exact `markdown` field returned by the upload response immediately after its proof description, for example:

  ```markdown
  This video is proof that the school Camp Day Report CSV export contains only final camp-day signup students.

  ![example](/uploads/<secret>/example.mp4)
  ```

- Do not manually build GitLab upload URLs from `url`, `full_path`, project ids, or repository paths. Manually constructed upload links often 404 or fail to render inline.
- Do not commit videos into the repository for evidence. Keep them in local artifact directories such as `.artifacts/playwright-videos/` and `.artifacts/playwright-mp4/`, upload them, and leave those artifact directories untracked.
- After posting GitLab video evidence, re-read the MR note with `glab api projects/:id/merge_requests/<iid>/notes/<note_id>` and confirm it contains `.mp4` upload markdown using `/uploads/...`, not `/raw/...`, `/-/project/...`, or committed artifact paths.
- Also confirm each video markdown/link is preceded by a `This video is proof that ...` sentence explaining the exact behavior proven by that video.
- Do not promise inline video player rendering if the host changes behavior, but use each platform's expected format: raw uploaded URL for GitHub user attachments, exact Markdown Uploads API `markdown` for GitLab.

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
2. Coverage matrix summary with `AUTOMATED`, `MANUAL_PROOF`, `REDUNDANT`, and `NOT_COVERED` rows
3. Test cases created
4. Files changed
5. Commands run and results
6. Confidence level and exact blockers, if any
7. Risks, gaps, or cases that could not be tested

## Hard Blocker Output

If blocked, report:

- What was completed
- What is blocked
- Why it is blocked
- Evidence collected
- Exact next action required
