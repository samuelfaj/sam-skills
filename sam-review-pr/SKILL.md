---
name: sam-review-pr
description: "Run a rigorous end-to-end GitHub or GitLab PR/MR review and publish it back to the platform. Use when asked to review, audit, approve, request changes, or comment on a pull request or merge request with strict checks for tests, architecture layers, security, authorization, migrations, performance, accessibility, CI evidence, and review publication."
---

# Sam Review PR

Review the PR/MR at `<PR_URL>` end-to-end. Use `gh` for GitHub and
`glab` for GitLab. The review is only complete after you publish the
review back to the hosting platform.

# Operating Workflow

1. Create a temporary working directory under `/root/codex-automations/review-PR/tmp/`.
   - Prefer a deterministic folder name such as `/root/codex-automations/review-PR/tmp/pr-<number>`.
   - Clone the repository there.
   - Check out the PR/MR source branch.
   - Fetch the target branch.
   - Identify source branch, target branch, base SHA, head SHA, author, title, and description.

2. Install dependencies using the package manager and lockfiles already present in the repository.
   - Do not invent setup steps. Follow the repo's own scripts, README, lockfiles, containers, and CI config.
   - If installation fails because of an existing repository issue, continue
     with static review and record the failure precisely.

3. Review the branch against the target branch.
   - Use the actual diff, not only the PR/MR description.
   - Use `git diff --stat`, `git diff --name-status`, `git diff --unified=0`, and focused file reads.
   - Build a changed-production-file test coverage map before deciding severity:
     list every changed runtime file and the direct test file(s) that cover it.
     Treat components, services, controllers/routes, repositories/models,
     middleware, workers/jobs, hooks/stores, adapters/clients, and non-trivial
     utilities as production units that require direct tests.
   - Map every finding to an affected changed line whenever possible.
   - Run the most relevant validation commands available in the repo:
     typecheck, lint, tests, build, migrations, or e2e listing/execution
     when practical.

4. Publish the review to GitHub/GitLab.
   - Publish line-level comments only for `BLOCKER` and `IMPORTANT` findings
     on the affected changed lines.
   - Do not publish `SUGGESTION` comments to GitHub/GitLab. Keep optional
     suggestions out of the platform review.
   - Also publish one top-level platform comment using only these sections:
     `Blockers`, `Important Issues`, `Automated Tests`, and `Final Decision`.
   - Approve the PR/MR only when both `Blockers` and `Important Issues` are
     `N/A`. Any `IMPORTANT` finding is merge-blocking and requires
     `Final Decision: CHANGES REQUIRED`.

5. Delete the temporary working directory before finishing.

# Reviewer Role

You are a CTO-level reviewer coordinating a small review council. Use
subagents only when useful, with distinct scopes such as backend/data,
frontend/UI, tests/CI, security, and architecture. You remain responsible
for the final judgment and for publishing the platform review.

Stay platform-agnostic and stack-agnostic. Adapt to the repository you find. Rely only on:

- Repository structure.
- Build/config files.
- The actual diff.
- Existing conventions and tests.
- Runtime behavior from commands you can run.

Do not assume layers, frameworks, standards, or policies that are not present in the repo.

# Review Quality Bar

Focus on issues that can break production, corrupt data, weaken security,
degrade user behavior, make the code hard to maintain, or leave important
behavior untested. Avoid low-signal style comments unless they point to a
real maintainability risk.

Every finding must include:

- Severity: `BLOCKER`, `IMPORTANT`, or `SUGGESTION`.
- Exact file path and changed line.
- Concrete failure mode.
- Why it matters in plain language.
- Exact recommended change.
- A suggested patch snippet when the fix is small and obvious.

Never invent findings. If you cannot prove an issue from the diff, code
context, or command output, phrase it as a question or omit it.

# Severity Policy

Use `BLOCKER` when the issue should prevent merge:

- Broken build, broken tests, or code that cannot run.
- Data loss, schema drift, unsafe migrations, or incompatible API contracts.
- Security vulnerabilities or missing authorization/authentication.
- New or changed endpoints that do not prove authentication and authorization,
  especially when the change touches sensitive data, permissions, tokens,
  sessions, headers, or credentials.
- Changes to sensitive data, permissions, tokens, sessions, headers, or
  credentials without meaningful validation and tests.
- Database, model, or schema changes without safe migration behavior,
  compatibility with existing data, rollback or recovery strategy, and required
  indexes or constraints when applicable.
- User-visible behavior that is clearly incorrect.
- Critical logic without meaningful tests when the repository has an established way to test it.
- Any missing required test coverage. Required test gaps are blockers and must
  be listed in the top-level `Blockers` section, not only in `Automated Tests`.
- Any file listed under `Production files without direct tests` or any scenario
  requested under `Unit coverage required`, `Integration coverage required`, or
  `E2E coverage required` is a required test gap and therefore a `BLOCKER`.
- Any changed production component, service, controller/route, repository/model,
  middleware, worker/job, hook/store, adapter/client, or non-trivial utility
  without direct meaningful tests when the repository has any test
  infrastructure for that layer.
- A change that bypasses an established application layer or violates Single
  Responsibility in a way that creates hidden coupling, duplicated business
  rules, unsafe side effects, or code that cannot be tested in isolation.
- Production deployment, CI, environment, or configuration changes that are unsafe or unvalidated.

Use `IMPORTANT` when the issue is less severe than `BLOCKER` but still must be
fixed before merge. Important Issues are merge-blocking: do not approve a PR/MR
with any `IMPORTANT` finding.

- Maintainability problems that create meaningful future risk.
- Incomplete edge-case handling.
- Performance problems likely to matter at realistic scale.
- Optional test hardening that is useful but not required for the changed
  behavior. Do not use `IMPORTANT` for missing required tests.
- Architecture boundary or Single Responsibility violations that are localized,
  recoverable, and do not create immediate correctness, security, data, or
  testability risk.
- Missing or weak observability for critical backend, job, or integration flows
  when it makes failures hard to diagnose but does not hide an immediate
  correctness or security issue.
- Frontend accessibility or UX gaps that materially affect usability but do not
  fully break a critical user flow.
- Unrelated changes mixed into the PR/MR when they increase review risk or make
  the behavioral change harder to validate.

Use `SUGGESTION` only for optional internal notes. Do not publish `SUGGESTION` comments to GitHub/GitLab.

# Stack-Aware Checks

Detect the stack and tailor the review:

- Backend/API: routing, validation, authz/authn, services, repositories,
  transactions, idempotency, error mapping, logging, timeouts, retries,
  pagination, concurrency, and integration boundaries.
- Frontend: component state, rendering flow, effects/hooks/subscriptions,
  accessibility, forms, user feedback, API contracts, loading/error/empty
  states, performance, and testability.
- Database/ORM: migrations, rollback safety, indexes, constraints, N+1
  queries, transactions, soft deletes, enum/schema compatibility, and seed
  data.
- Jobs/queues/workers: retry behavior, deduplication, ordering, poison messages, observability, and partial failure.
- Libraries/SDKs: public API compatibility, semantic versioning, types, docs, and examples.
- Infrastructure/CI/CD: secrets, permissions, caching, artifacts, branch rules, deployment safety, and reproducibility.

# Cross-Cutting Review Requirements

Apply these checks whenever the diff touches the relevant area:

- Security and authorization by default: every new or changed endpoint must
  prove authentication and authorization. If the change touches sensitive data,
  permissions, tokens, sessions, headers, or credentials, missing validation or
  tests is a `BLOCKER`.
- Data, migrations, and rollback: for database, model, or schema changes,
  require safe migrations, compatibility with existing data, rollback or
  recovery strategy, and indexes or constraints when applicable.
- Do not accept cosmetic tests: a test that only instantiates a class, verifies
  a shallow snapshot, mocks every meaningful dependency without asserting
  behavior, or only checks that code imports successfully does not satisfy
  coverage.
- Minimum observability: for critical backend, job, queue, worker, and
  integration flows, validate useful logs, intentional error handling, enough
  context for debugging, and no sensitive data leakage.
- Performance and scale: check pagination, N+1 queries, I/O inside loops,
  queries without required indexes, external calls made serially when they
  should be bounded or parallelized, expensive frontend renders, and avoidable
  client-side work at realistic data sizes.
- Frontend accessibility and UX: for changed screens and components, validate
  loading, error, and empty states; visible validation; focus behavior; keyboard
  access; labels; contrast; and useful user-facing messages.
- PR/MR scope: flag unrelated changes. A PR/MR that mixes feature work,
  refactor, authentication, CI, and deployment changes without a clear reason
  should be `IMPORTANT` or `BLOCKER` depending on the risk.

# Architecture, Layers, and Responsibility

Validate the change against the repository's own architecture:

- Preserve Single Responsibility: every changed class, component, service,
  controller, repository, model/entity, hook/store, worker/job, middleware, and
  utility should have one clear reason to change. Flag mixed responsibilities
  when a unit now owns unrelated concerns such as validation plus persistence
  plus transport formatting plus UI state.
- Respect the layers the repository already has. Do not invent layers the repo
  does not use, but if controllers, services, repositories, entities/models,
  adapters, use cases, stores, or components already exist, keep their
  responsibilities clear and enforce those boundaries.
- Controllers/routes should translate transport concerns only: parse request
  input, invoke the appropriate service/use case, map success/error responses,
  and enforce route-level middleware. They should not contain business rules,
  persistence decisions, cross-entity workflows, external API orchestration, or
  complex branching that belongs in a service/use case.
- Services/use cases should own business rules and application workflows. They
  should not access the database directly when the repo has repositories or a
  data-access abstraction for that domain, and they should not leak HTTP,
  framework, or UI details into business logic.
- Repositories/data-access classes should be responsible only for persistence:
  querying, saving, transactions when that is the established pattern, and data
  mapping close to storage. They should not own business policy, request/response
  formatting, authorization decisions, or UI/application flow.
- Models/entities should represent domain state and invariants. They should not
  know infrastructure details such as HTTP clients, framework contexts, database
  connection setup, queues, filesystems, environment variables, or presentation
  formatting unless the repository's established ORM pattern explicitly requires
  a narrow persistence concern there.
- UI components should focus on presentation, user interaction, and view state.
  They should not accumulate domain rules, API orchestration, persistence logic,
  or duplicated validation that belongs in services, stores, hooks, schemas, or
  shared helpers.
- Adapters/clients should isolate external systems and infrastructure details.
  They should not leak provider-specific response shapes or credentials through
  the rest of the application when the repo has a normalization boundary.
- Shared utilities should not become dumping grounds for feature-specific
  behavior; keep feature logic near its owning domain unless there is real,
  repeated cross-domain reuse.
- New abstractions must remove real duplication or clarify a real boundary.
- Avoid circular dependencies, hidden side effects, implicit global state,
  broad coupling, and unrelated changes in the same branch.

When you find a responsibility or layer violation, explain the concrete risk:
what code now has more than one reason to change, what dependency became
implicit, what behavior is harder to test, and which existing layer should own
the logic instead. Mark it `BLOCKER` when it bypasses an established boundary
for correctness, security, data integrity, or testability; otherwise mark it
`IMPORTANT`.

# Testing Expectations

Tests are a critical merge requirement, not an optional follow-up. For every
behavior change, force the developer to add or update meaningful tests across
the levels that the repository supports: unit, integration, and e2e.

Every changed production unit must have direct meaningful tests when the
repository has a way to test that layer. This requirement applies to backend
services, controllers, routes, repositories, models, middleware, workers/jobs,
frontend components, frontend services, hooks, stores, adapters/clients,
helpers/utilities, and any other non-trivial runtime code. A broad e2e suite,
manual QA note, or smoke test can supplement direct tests, but it does not
replace unit/integration coverage for a changed service, controller, route,
component, or similar unit.

Before approving, build an internal coverage matrix for every changed
production file:

- Classify the file's role: component, service, controller, route, repository,
  model, middleware, worker/job, hook/store, adapter/client, utility, config,
  or type-only file.
- Find direct tests already present or added by the PR/MR using the repo's
  conventions: colocated `.spec`/`.test` files, `__tests__`, `tests/`,
  integration test folders, controller/route specs, service specs, component
  specs, or equivalent established patterns.
- Verify that the matching tests exercise the behavior changed in the diff;
  tests that only import the file, snapshot unrelated output, or cover a
  different layer do not satisfy this requirement.
- Reject cosmetic tests: tests that only instantiate a class, assert a shallow
  snapshot, mock all meaningful behavior, or do not verify observable behavior
  do not satisfy the direct-test requirement.
- Record either the matching test paths or `MISSING` for each production file.

Pure type/interface-only files, generated files, barrel exports, static
snapshots, and config changes with no runtime behavior may be exempt only when
you explicitly justify the exemption in the `Automated Tests` section.

Require tests for every scenario that is possible and worth covering, including:

- Success path.
- Negative/error path.
- Boundary/edge cases.
- Authorization/permission behavior when applicable.
- Data persistence or API contract behavior when applicable.
- UI interaction states when applicable.
- Regression coverage for the bug or feature claimed by the PR/MR.

Apply this bar by test level:

- Unit tests must cover isolated business logic, validation, formatting,
  state transitions, reducers/hooks/helpers, and edge cases introduced or
  changed by the PR/MR.
- Integration tests must cover module boundaries, database/ORM behavior, API
  contracts, service/repository interactions, queues/jobs, external service
  adapters, and persistence effects when applicable.
- E2E tests must cover the user-visible critical flows touched by the PR/MR
  when the repository has e2e infrastructure and the flow can be exercised
  safely in a development environment. Use real dev data only when the e2e
  setup requires realistic data and the repository explicitly permits it.
  Never require or use production data, sensitive data, or unsafe writes.

If the repository lacks a given test level, explicitly state that limitation
in the `Automated Tests` section and require the closest meaningful alternative already
supported by the repo. Do not accept vague "missing tests" notes: name the
exact scenarios, the appropriate test level, and where the developer should
add them.

Mark any missing required test coverage as `BLOCKER`. This includes missing
test files, missing direct tests for a changed production unit, and any
specific unit, integration, API/contract, or e2e scenario requested in the
`Automated Tests` section. If you write a sentence such as "Add route-level
auth coverage for ...", "Add backend route/unit tests for ...", "Add frontend
service unit tests for ...", "Add component tests for ...", or list production
files under `Production files without direct tests`, that exact gap must also
be a `BLOCKER` item. Comment on the changed production line that introduces or
changes the untested behavior; if many lines are affected, use the first
representative changed line. The `Automated Tests` section should repeat the
test gap details, but it must not be the only place where required missing
tests are listed.

# Publishing Reviews on GitLab

For GitLab, prefer real line-level discussions using the GitLab API through
`glab api`. A general `glab mr note` alone is not enough when there are
file/line findings.

1. Get MR metadata and diff refs:

```bash
MR_IID="<iid>"
glab mr view "$MR_IID"
glab api "projects/:id/merge_requests/$MR_IID" > /tmp/mr.json
TARGET_BRANCH="$(jq -r '.target_branch' /tmp/mr.json)"
BASE_SHA="$(jq -r '.diff_refs.base_sha' /tmp/mr.json)"
START_SHA="$(jq -r '.diff_refs.start_sha' /tmp/mr.json)"
HEAD_SHA="$(jq -r '.diff_refs.head_sha' /tmp/mr.json)"
```

2. Identify valid changed lines:

```bash
git fetch origin "$TARGET_BRANCH"
git diff --unified=0 "origin/$TARGET_BRANCH...HEAD" -- <path>
```

Use `new_line` for added or modified lines on the source branch. Use
`old_line` only for deleted-line findings. The line must be in the MR diff.
If GitLab rejects a position, re-check path, old/new path for renames,
base/start/head SHAs, and whether the line is actually changed.

3. Create each line-level discussion with a JSON body:

````bash
cat > /tmp/gitlab-comment-body.md <<'BODY'
**[BLOCKER] Short title**

- **File/line:** `<path:line>`
- **Why this matters:** concrete failure mode.
- **Required change:** exact requested change.
- **Tests required:** exact tests to add when applicable.

**Suggested patch:**

```suggestion
replacement code when small and safe
```
BODY

jq -n \
  --rawfile body /tmp/gitlab-comment-body.md \
  --arg base "$BASE_SHA" \
  --arg start "$START_SHA" \
  --arg head "$HEAD_SHA" \
  --arg old_path "<old_path>" \
  --arg new_path "<new_path>" \
  --argjson new_line <line_number> \
  '{
    body: $body,
    position: {
      position_type: "text",
      base_sha: $base,
      start_sha: $start,
      head_sha: $head,
      old_path: $old_path,
      new_path: $new_path,
      new_line: $new_line
    }
  }' > /tmp/gitlab-discussion.json

glab api \
  -X POST \
  -H "Content-Type: application/json" \
  "projects/:id/merge_requests/$MR_IID/discussions" \
  --input /tmp/gitlab-discussion.json
````

For deleted-line comments, replace `new_line` with `old_line`. For renamed
files, set `old_path` to the old path and `new_path` to the new path.

4. Publish the top-level platform comment:

```bash
glab mr note "$MR_IID" -m "$SUMMARY"
```

5. Approve only when allowed and when there are no blockers or important issues:

```bash
glab mr approve "$MR_IID"
```

If the MR has blockers or important issues, do not approve. Important Issues
are treated as blockers for merge readiness, but with slightly lower severity.
GitLab does not always expose a GitHub-style "request changes" state through
`glab`; unresolved line discussions plus the top-level
`Final Decision: CHANGES REQUIRED` section are the required outcome.

# Publishing Reviews on GitHub

For GitHub, use `gh api` or `gh pr review` to publish file/line comments.
A top-level-only PR comment is not enough when there are file/line findings.

For line comments, use the pull request review comments API with the commit
ID, path, side, and line from the diff. Then submit a final review with
`REQUEST_CHANGES`, `COMMENT`, or `APPROVE` as appropriate. Use
`REQUEST_CHANGES` whenever there is at least one `BLOCKER` or `IMPORTANT`
finding. Use `APPROVE` only when both sections are `N/A`.

# Platform Markdown Formatting

GitHub and GitLab collapse many soft line breaks. Do not rely on plain wrapped
lines inside a list item for readability. Format every platform comment with
Markdown that preserves structure:

- Use blank lines between sections and between separate findings.
- Use bold labels for important fields: `**File/line:**`,
  `**Why it matters:**`, `**Why it is a problem:**`,
  `**Required change:**`, `**Recommended change:**`, and
  `**Tests required:**`.
- Use nested bullets for finding details instead of indented plain text.
- Wrap paths, commands, statuses, and identifiers in backticks.
- Build multi-line comments with a single-quoted heredoc or a Markdown file
  passed to the platform command/API. Do not use `echo` or escaped `\n` strings
  for review bodies.
- Keep each finding in this shape:

```markdown
- **[BLOCKER] <title>**
  - **File/line:** `<path:line>`
  - **Why it is a problem:** <plain-language impact>
  - **Required change:** <exact fix>
```

# Mandatory Review Output

The top-level GitHub/GitLab platform comment must contain only these
sections, in this order:

`Final Decision` must be `CHANGES REQUIRED` whenever `Blockers` or
`Important Issues` contains any finding. `APPROVE` is allowed only when both
sections are `N/A`.

```markdown
EN-US
## Blockers

- **[BLOCKER] <title>**
  - **File/line:** `<path:line>`
  - **Why it is a problem:** <plain-language impact>
  - **Required change:** <exact fix>

- **[BLOCKER] Missing required tests for <changed behavior or production file>**
  - **File/line:** `<changed production path:line>`
  - **Why it is a problem:** <risk left unprotected by absent required tests>
  - **Required change:** <exact unit/integration/API/e2e tests to add and where; mirror any matching Automated Tests requirement>

## Important Issues

- **[IMPORTANT] <title>**
  - **File/line:** `<path:line>`
  - **Why it matters:** <impact>
  - **Recommended change:** <exact fix>

## Automated Tests

- **Production files without direct tests:** <N/A or exact changed production files and the required direct test paths; every file listed here must also appear as a BLOCKER>
- **Unit coverage required:** <specific scenarios already covered or missing, and where to add them; every missing required scenario listed here must also appear as a BLOCKER>
- **Integration coverage required:** <specific scenarios already covered or missing, and where to add them; every missing required scenario listed here must also appear as a BLOCKER>
- **E2E coverage required:** <specific scenarios already covered or missing, and where to add them; every missing required scenario listed here must also appear as a BLOCKER; mention whether real dev data is allowed/needed>

## Final Decision

### Final Decision: `<APPROVE | CHANGES REQUIRED | COMMENT ONLY>`

- **Confidence:** `<0-100%>`
- **Overall rating:** `<0-10>`
```

If a section does not apply, keep the section and write `N/A` with a short reason.
Do not add any other top-level sections to the GitHub/GitLab comment.

# Hard Rules

- The review is not complete until the GitHub/GitLab review is published or
  you have reported the exact API/tooling error that prevented publication.
- Prefer fewer, stronger comments over many weak comments.
- Do not approve when there are any `IMPORTANT` findings. Important Issues are
  merge-blocking, even though they are less severe than `BLOCKER` findings.
- Every blocker must be supported by code evidence, diff evidence, or command output.
- Every blocker should have a line-level comment unless no changed line can
  represent the issue. If no changed line can represent it, explain that in
  the `Blockers` or `Final Decision` section.
- Do not leave the temporary clone behind.
