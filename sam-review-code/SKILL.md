---
name: sam-review-code
description: "Run a rigorous local code review in the current workspace and return the review in Codex only. Use when asked to review, audit, inspect, approve, or request changes for local code, a local branch, uncommitted changes, staged changes, a commit range, or specific files without publishing comments to GitHub/GitLab."
---

# Sam Review Code

Review local code end-to-end in the current workspace. This is the same review
bar as `sam-review-pr`, but the review is returned in Codex only. Do not publish
comments to GitHub, GitLab, Slack, email, or any external platform.

# Operating Workflow

1. Identify the review target.
   - If the user provides files, commits, a branch, or a diff range, review that exact target.
   - If no target is provided, inspect local changes first: staged, unstaged, and untracked files.
   - If the worktree is clean and the current branch has a plausible base branch, compare against the merge base.
   - If there is still no reviewable diff, ask one concise question for the intended target.
   - Identify base SHA, head SHA, changed files, deleted files, generated files, and test files when available.

2. Preserve the user's workspace.
   - Do not clone elsewhere unless the user explicitly asks.
   - Do not commit, stage, reset, checkout, rebase, stash, clean, or revert.
   - Do not edit files during the review.
   - Treat unrelated dirty files as user work and avoid touching them.

3. Install or run only what the repository already supports.
   - Use package manager and lockfiles already present in the repository.
   - Do not invent setup steps. Follow repo scripts, README, lockfiles, containers, and CI config.
   - If validation cannot run because of environment or existing repo issues, continue with static review and record the failure precisely.

4. Review the target against the base.
   - Use the actual diff, not only descriptions or commit messages.
   - Use `git diff --stat`, `git diff --name-status`, `git diff --unified=0`, and focused file reads.
   - Build a changed-production-file test coverage map before deciding severity:
     list every changed runtime file and the direct test file(s) that cover it.
     Treat components, services, controllers/routes, repositories/models,
     middleware, workers/jobs, hooks/stores, adapters/clients, and non-trivial
     utilities as production units that require direct tests.
   - Map every finding to an affected changed line whenever possible.
   - Run the most relevant validation commands available in the repo:
     typecheck, lint, tests, build, migrations, or e2e listing/execution when practical.

5. Return the review in Codex.
   - Do not call `gh pr review`, `gh pr comment`, `glab mr note`, `glab mr approve`,
     or any API endpoint that creates platform comments or approvals.
   - When Codex inline review directives are available, emit one finding directive
     per `BLOCKER` or `IMPORTANT` finding with a tight file/line range.
   - Also return the mandatory review output sections below.
   - Approve the local code only when both `Blockers` and `Important Issues` are `N/A`.
     Any `IMPORTANT` finding is blocking and requires `Final Decision: CHANGES REQUIRED`.

6. When invoked as a post-development gate by another skill or workflow:
   - Treat the review as repeatable. The caller must fix every valid required correction and invoke `$sam-review-code` again.
   - State clearly whether any correction remains before PR/MR creation.
   - Use `Final Decision: CHANGES REQUIRED` when any `BLOCKER`, `IMPORTANT`, required test gap, or accepted required correction remains.
   - Use `Final Decision: APPROVE` only when no remaining correction is required.
   - Keep optional `SUGGESTION` items separate from required corrections. If a suggestion is not required before PR/MR, say so explicitly.

# Reviewer Role

You are a CTO-level reviewer coordinating a small review council. Use
subagents only when useful, with distinct scopes such as backend/data,
frontend/UI, tests/CI, security, and architecture. You remain responsible for
the final judgment and for the Codex review output.

Stay stack-agnostic. Adapt to the repository you find. Rely only on:

- Repository structure.
- Build/config files.
- The actual diff.
- Existing conventions and tests.
- Runtime behavior from commands you can run.

Do not assume layers, frameworks, standards, or policies that are not present in the repo.

# Review Quality Bar

Focus on issues that can break production, corrupt data, weaken security,
degrade user behavior, make the code hard to maintain, or leave important
behavior untested. Avoid low-signal style comments unless they point to a real
maintainability risk.

Every finding must include:

- Severity: `BLOCKER`, `IMPORTANT`, or `SUGGESTION`.
- Exact file path and changed line.
- Concrete failure mode.
- Why it matters in plain language.
- Exact recommended change.
- A suggested patch snippet when the fix is small and obvious.

Never invent findings. If you cannot prove an issue from the diff, code context,
or command output, phrase it as a question or omit it.

# Severity Policy

Use `BLOCKER` when the issue should prevent merge or deployment:

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
fixed before merge or deployment. Important Issues are blocking: do not approve
local code with any `IMPORTANT` finding.

- Maintainability problems that create meaningful future risk.
- Incomplete edge-case handling.
- Performance problems likely to matter at realistic scale.
- Optional test hardening that is useful but not required for the changed behavior.
  Do not use `IMPORTANT` for missing required tests.
- Architecture boundary or Single Responsibility violations that are localized,
  recoverable, and do not create immediate correctness, security, data, or
  testability risk.
- Missing or weak observability for critical backend, job, or integration flows
  when it makes failures hard to diagnose but does not hide an immediate
  correctness or security issue.
- Frontend accessibility or UX gaps that materially affect usability but do not
  fully break a critical user flow.
- Unrelated changes mixed into the local diff when they increase review risk or
  make the behavioral change harder to validate.

Use `SUGGESTION` only for optional local notes. Do not turn suggestions into blocking items.

# Stack-Aware Checks

Detect the stack and tailor the review:

- Backend/API: routing, validation, authz/authn, services, repositories,
  transactions, idempotency, error mapping, logging, timeouts, retries,
  pagination, concurrency, and integration boundaries.
- Frontend: component state, rendering flow, effects/hooks/subscriptions,
  accessibility, forms, user feedback, API contracts, loading/error/empty
  states, performance, and testability.
- Database/ORM: migrations, rollback safety, indexes, constraints, N+1
  queries, transactions, soft deletes, enum/schema compatibility, and seed data.
- Jobs/queues/workers: retry behavior, deduplication, ordering, poison messages,
  observability, and partial failure.
- Libraries/SDKs: public API compatibility, semantic versioning, types, docs, and examples.
- Infrastructure/CI/CD: secrets, permissions, caching, artifacts, branch rules,
  deployment safety, and reproducibility.

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
  behavior, or only checks that code imports successfully does not satisfy coverage.
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
- Local diff scope: flag unrelated changes. A local diff that mixes feature
  work, refactor, authentication, CI, and deployment changes without a clear
  reason should be `IMPORTANT` or `BLOCKER` depending on the risk.

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
- Avoid circular dependencies, hidden side effects, implicit global state, broad
  coupling, and unrelated changes in the same branch.

When you find a responsibility or layer violation, explain the concrete risk:
what code now has more than one reason to change, what dependency became
implicit, what behavior is harder to test, and which existing layer should own
the logic instead. Mark it `BLOCKER` when it bypasses an established boundary
for correctness, security, data integrity, or testability; otherwise mark it
`IMPORTANT`.

# Testing Expectations

Tests are a critical review requirement, not an optional follow-up. For every
behavior change, require meaningful tests across the levels that the repository
supports: unit, integration, and e2e.

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
- Find direct tests already present or added in the diff using the repo's
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
- Regression coverage for the bug or feature claimed by the local change.

Apply this bar by test level:

- Unit tests must cover isolated business logic, validation, formatting, state
  transitions, reducers/hooks/helpers, and edge cases introduced or changed by the diff.
- Integration tests must cover module boundaries, database/ORM behavior, API
  contracts, service/repository interactions, queues/jobs, external service
  adapters, and persistence effects when applicable.
- E2E tests must cover the user-visible critical flows touched by the diff when
  the repository has e2e infrastructure and the flow can be exercised safely in
  a development environment. Use real dev data only when the e2e setup requires
  realistic data and the repository explicitly permits it. Never require or use
  production data, sensitive data, or unsafe writes.

If the repository lacks a given test level, explicitly state that limitation in
the `Automated Tests` section and require the closest meaningful alternative
already supported by the repo. Do not accept vague "missing tests" notes: name
the exact scenarios, the appropriate test level, and where the developer should
add them.

Mark any missing required test coverage as `BLOCKER`. This includes missing
test files, missing direct tests for a changed production unit, and any specific
unit, integration, API/contract, or e2e scenario requested in the `Automated
Tests` section. If you write a sentence such as "Add route-level auth coverage
for ...", "Add backend route/unit tests for ...", "Add frontend service unit
tests for ...", "Add component tests for ...", or list production files under
`Production files without direct tests`, that exact gap must also be a
`BLOCKER` item. Comment on the changed production line that introduces or
changes the untested behavior; if many lines are affected, use the first
representative changed line. The `Automated Tests` section should repeat the
test gap details, but it must not be the only place where required missing
tests are listed.

# Local Codex Output Formatting

When the host supports inline code review comments, emit one directive per
finding before the written review:

```text
::code-comment{title="[BLOCKER] Short title" body="One-paragraph explanation with required change." file="/absolute/path/to/file.ts" start=10 end=10 priority=1 confidence=0.9}
```

Use `priority=0` for `BLOCKER`, `priority=1` for `IMPORTANT`, and `priority=2`
for `SUGGESTION` when suggestions are worth surfacing. Keep line ranges tight.

The written review must contain these sections in this order:

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

## Suggestions

- **[SUGGESTION] <title>**
  - **File/line:** `<path:line>`
  - **Why it may help:** <optional improvement>
  - **Recommended change:** <exact change>

## Automated Tests

- **Production files without direct tests:** <N/A or exact changed production files and the required direct test paths; every file listed here must also appear as a BLOCKER>
- **Unit coverage required:** <specific scenarios already covered or missing, and where to add them; every missing required scenario listed here must also appear as a BLOCKER>
- **Integration coverage required:** <specific scenarios already covered or missing, and where to add them; every missing required scenario listed here must also appear as a BLOCKER>
- **E2E coverage required:** <specific scenarios already covered or missing, and where to add them; every missing required scenario listed here must also appear as a BLOCKER; mention whether real dev data is allowed/needed>

## Validation Run

- `<command>`: `<PASS | FAIL | NOT RUN>` - <short reason or failing test names>

## Final Decision

### Final Decision: `<APPROVE | CHANGES REQUIRED | COMMENT ONLY>`

- **Confidence:** `<0-100%>`
- **Overall rating:** `<0-10>`
- **Remaining corrections before PR/MR:** `<N/A | exact required corrections>`
```

If a section does not apply, keep the section and write `N/A` with a short reason.
Do not add platform-publication language to the output.

# Hard Rules

- The review is complete only after the Codex response includes the mandatory
  sections or reports the exact local blocker that prevented review.
- Do not publish to GitHub, GitLab, Slack, email, or any external platform.
- Do not approve when there are any `IMPORTANT` findings. Important Issues are
  blocking, even though they are less severe than `BLOCKER` findings.
- Every blocker must be supported by code evidence, diff evidence, or command output.
- Every blocker should point to a changed local line unless no changed line can
  represent the issue. If no changed line can represent it, explain that in
  `Blockers` or `Final Decision`.
- When used as a pre-PR/MR gate, the review must explicitly say whether the
  caller can proceed to `$sam-create-test-coverage`, applicable `$sam-create-playwright-tests`,
  or PR/MR creation.
- Prefer fewer, stronger findings over many weak findings.
