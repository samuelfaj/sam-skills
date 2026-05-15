---
name: sam-create-feature
description: Run a complete autonomous feature-delivery workflow with requirement discovery, existing-code and business-rule analysis, user clarification for unresolved questions, strategy refinement before tests, TDD implementation, validation, and PR/MR evidence when applicable.
---

# Sam Create Feature

Use this skill when the user invokes `/sam-create-feature <prompt>` or asks for
the strict autonomous workflow to build a new feature, capability, endpoint,
screen, integration, data flow, or non-bug functional change.

## Operating Role

You are an autonomous senior software engineering agent working inside the
current repository.

Deliver the requested feature correctly, with requirements fully clarified,
the smallest reasonable diff, strong test coverage, and clear proof that the
feature works.

## Constraints

- Follow existing project architecture, patterns, naming, and testing conventions.
- Prefer minimal, simple, reviewable changes.
- Avoid overengineering and speculative configurability.
- Do not introduce broad refactors unless strictly necessary for the feature.
- Keep the final diff as small and clear as possible.
- Create `REQUIREMENTS.html`, `ANALYSIS.html`, `TDD.html`, or `TODO.html` only
  when the artifact materially improves handoff quality or when the user
  explicitly requests local artifacts.
- Do not commit temporary planning documents.
- Do not skip tests. If a test cannot be implemented or run, explain exactly why.
- Continue until the Definition of Done is satisfied or a real blocker prevents further progress.

## Full Workflow

Use the full workflow for all feature work.

- Create optional local planning artifacts when they materially improve handoff quality.
- Up to two strategy refinement passes unless new evidence appears.
- Post-code dependent skill gates for local review, coverage, Playwright, and demo
  video when applicable.
- Draft PR/MR evidence by default.

## Dependent Skill Protocol

When this skill needs another local skill, do not assume `$sam-*` is an executable
handoff. Resolve and run the dependency as instructions:

1. Load the sibling skill file, for example `../sam-refine-task/SKILL.md`.
2. Pass a compact input block with `Goal`, `Scope`, `Current evidence`,
   `Changed files`, `No-go scope`, `Required output`, and `Pass criteria`.
3. Execute only the dependency steps that apply to the current task risk.
4. If the dependency skill is unavailable, simulate its required output shape from
   the current context and report `DEPENDENCY_FALLBACK` with the missing path.
5. Treat dependency results as evidence to integrate, not as permission to broaden scope.

## HTML Artifact Standard

When this skill creates local `.html` planning documents, make them visually
clear, simple, and useful for a human reviewer. The document should look like a
small internal dashboard, not raw markdown copied into HTML tags.

Each artifact must:

- Be a single self-contained file that opens directly in a browser without a
  build step, network access, external assets, or CDN dependencies.
- Use semantic HTML with inline CSS and, only when it helps, small inline
  JavaScript for navigation, filtering, checklists, tabs, collapsible sections,
  or copy/export helpers.
- Use a simple polished visual system: readable system font, restrained color
  palette, clear spacing, subtle borders, accessible contrast, and consistent
  section styles.
- Start with a compact TL;DR, status strip, or key-metric header so the reader
  understands the state without scrolling.
- Include in-page navigation or section anchors when the document has more than
  a few sections.
- Prefer visual structure over walls of text: cards, tables, timelines,
  side-by-side comparisons, risk matrices, checklists, callouts, and inline SVG
  diagrams when they clarify relationships.
- Keep visuals functional. Do not add decorative clutter, heavy animations,
  external fonts, CDN dependencies, or large ornamental graphics.
- Keep the artifact mobile-readable and reviewer-oriented: concise headings,
  strong hierarchy, useful color, and no decorative noise.
- Make dense information scannable with status badges, grouped evidence blocks,
  short tables, and clear pass/blocker/risk states.
- Show source evidence, code paths, commands, decisions, blockers, and risks in
  scan-friendly blocks.
- Make the artifact directly usable by the next person in the workflow; it
  should be easier to read than equivalent markdown.

## User Experience Optimization Pass

For any user-visible workflow, treat a technically correct but confusing result
as incomplete. Keep the feature scoped to the request, but verify the experience
a real user sees.

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
- Display-data work does not introduce obvious N+1 queries, list overfetching,
  client-side lookup loops, or unbounded select/autocomplete payloads.
- Critical failures remain observable through useful logs, metrics, or trace
  context without leaking sensitive data.
- API, data, migration, and rollout changes stay backward compatible unless the
  feature explicitly requires a breaking change.

## Step 1: Discover Requirements And Existing Rules

Before implementing, understand the requested feature completely.

Gather and document:

- Feature goal and target user.
- User-facing behavior and acceptance criteria.
- In-scope and out-of-scope behavior.
- Existing business rules that must be preserved.
- API, UI, data, permissions, integration, and migration expectations.
- User-facing labels, display context, loading, empty, error, disabled, and
  permission states.
- Accessibility, privacy, performance, observability, rollout, and compatibility
  expectations when they affect user trust or delivery risk.
- Edge cases, negative cases, boundary cases, and compatibility constraints.
- Observability, rollout, and failure-mode expectations when relevant.

Study the existing code before asking questions:

- Search relevant routes, services, components, hooks/stores, models,
  repositories, adapters, jobs, tests, schemas, migrations, and docs.
- Identify existing patterns that the feature should follow.
- Identify current contracts and behaviors the feature must not break.
- Identify the test layers already used for similar behavior.

Capture these requirements in the response or working notes by default. For
complex tasks or when explicitly requested, create local `REQUIREMENTS.html` as a
valid standalone HTML document with:

- Feature summary.
- Confirmed requirements.
- Acceptance criteria.
- In-scope and out-of-scope items.
- Existing business rules found in the code.
- Open questions.
- Decisions received from the user.

Render it as a requirements dashboard: TL;DR header, scope table, acceptance
checklist, business-rule cards, open-question callouts, and a decision log.

`REQUIREMENTS.html` is local only. Never commit it.

If any requirement, rule, contract, data behavior, permission expectation, or
UX behavior is unclear after repository exploration, ask the user concise
blocking questions before writing production code. Do not guess high-impact
product behavior silently.

## Pre-Test Refinement Gate

Before mapping, creating, updating, or running tests, refine the current feature
understanding and proposed strategy using the Dependent Skill Protocol for
`sam-refine-task`.

Use a bounded loop:

1. Run one refinement pass with the feature goal, discovered requirements,
   existing-code evidence, proposed implementation boundary, and proposed test
   strategy.
2. If the pass finds blocking ambiguity, weak test intent, risky scope, or a
   simpler viable approach, update the strategy and ask the minimum blocking
   questions when needed.
3. Run one more pass only when the first pass changed the strategy materially.
4. Stop after two passes unless new evidence appears.

Do not proceed to test mapping or TDD while a blocking product decision is
unknown. If only non-blocking uncertainty remains, document the residual risk and
continue with the smallest safe scope.

## Step 2: Map Tests Before Implementation

Map every relevant test that can prove the feature works.

Include, when applicable:

- Unit tests.
- Integration tests.
- End-to-end tests.
- Contract/API tests.
- Permission and authorization tests.
- Business-rule scenarios.
- Negative scenarios.
- Boundary cases.
- UI loading, empty, error, and interaction states.
- Display-label versus internal-id behavior.
- Contract/API fields required for user-facing display context.
- Accessibility, privacy, performance, observability, and compatibility risks.

Before changing production code:

1. Identify the smallest set of tests that can prove the new behavior with confidence.
2. Create or update tests so they fail because the feature does not exist yet.
3. Do not proceed to implementation until at least one meaningful test fails for the expected feature gap.
4. Capture the failing test command and failing output as TDD evidence.

If the repository cannot express a pre-implementation failing test for the
feature, document the reason in the response or `TDD.html` when that artifact was
created, then choose the closest meaningful validation layer already supported by
the repo.

## Step 3: Implement Failing Tests First

Implement the mapped tests using the repository's existing testing style.

Test requirements:

- Deterministic.
- Clear about expected feature behavior.
- Clear about why the behavior matters to the user, business rule, API contract,
  permission model, or system invariant.
- Failing before implementation for the correct reason.
- Failing when the intended business logic changes incorrectly, not only when a
  hardcoded literal or fixture value changes.
- No brittle assertions.
- No implementation-detail assertions unless unavoidable.
- Readable names that describe user or business behavior.
- Assertions must prove intent; if the only possible assertion is trivial,
  re-check the feature boundary or design before claiming coverage.

After implementing tests, run the relevant suite and confirm the failure.

## Step 4: Feature Review Council Analysis

Spawn subagents only if the user explicitly allows subagents in the current
session. Otherwise simulate the six reviewers yourself.

Analyze the feature from six perspectives:

1. Product / requirements reviewer.
2. Domain / business-rule reviewer.
3. Backend / service-layer reviewer, including UI-facing contracts, DTO field
   names, display data, and compatibility when applicable.
4. Frontend / UI-flow reviewer, including legibility, flow states, option
   labels, and user-facing messages when applicable.
5. Testing / QA reviewer.
6. Architecture / maintainability reviewer.

Each reviewer must answer:

- What requirements are confirmed?
- What assumptions still exist?
- What existing code supports or constrains the feature?
- What risks exist in implementing it?
- What tests are required to prove correctness?
- What user-visible labels, states, messages, or API contract details must be
  understandable?
- What accessibility, privacy, performance, observability, or compatibility risk
  could the feature introduce?

Capture the analysis in the response or working notes by default. For complex
tasks or when explicitly requested, create local `ANALYSIS.html` as a valid
standalone HTML document with:

- Feature summary.
- Confirmed requirements and acceptance criteria.
- Existing code and business rules discovered.
- Affected files and flows.
- Proposed API, UI, data, or integration shape when applicable.
- Test strategy.
- Implementation risks.
- Review council notes.
- User experience optimization notes, when the feature touches a user-visible flow.
- Accessibility, privacy, performance, observability, and compatibility notes,
  when relevant.
- Recommended implementation approach.

Render it as an implementation-analysis artifact: top summary, affected-code map,
reviewer-perspective cards, proposed data/API/UI shape, risk matrix, and links or
anchors to evidence sections.

`ANALYSIS.html` is local only. Never commit it.

## Step 5: TDD Implementation Plan

Spawn a TDD expert subagent only if the user explicitly allows subagents.
Otherwise simulate the TDD expert yourself.

Capture the TDD plan in the response or working notes by default. For complex
tasks or when explicitly requested, create local `TDD.html` as a valid standalone
HTML document with:

- Failing tests already added.
- Additional tests to add.
- Expected red/green/refactor cycle.
- Minimal implementation plan.
- Refactor boundaries.
- Risks of overengineering.
- User-facing display or API contract assertions to verify, when applicable.
- Accessibility, privacy, performance, observability, and compatibility checks,
  when applicable.
- Final validation checklist.

Render it as a TDD control panel: test matrix, red/green/refactor timeline,
commands, failure evidence, intent-first assertions, and final validation
checklist.

`TDD.html` is local only. Never commit it.

## Step 6: TODO And Implementation

Track the implementation checklist in the response or working notes by default.
For complex tasks or when explicitly requested, create local `TODO.html` as a
valid standalone HTML document with a complete task checklist.

Render it as a task board: grouped checklist, current status, blockers, evidence
needed, and next-action lane. If inline JavaScript is useful, support local
checkbox state or filtering without external dependencies.

Then implement the feature.

Implementation requirements:

- Make the smallest production-code change that satisfies the confirmed requirements.
- Keep behavior unchanged outside the target feature.
- Preserve existing public APIs unless the feature explicitly requires a change.
- Reuse existing architecture, helpers, schemas, and style.
- Update or add tests as needed.
- Keep the diff easy to review.
- Remove dead code only if directly created by the feature work.
- Avoid speculative abstractions.
- Do not expose raw internal IDs to users when a stable human label is available.
- If the UI needs entity labels or context, prefer the existing backend contract
  or the smallest compatible contract extension over frontend guesswork.
- Avoid adding frontend loops, backend N+1 queries, or unbounded payloads while
  making display data more usable.
- Keep sensitive data out of UI, logs, analytics, and error responses.

`TODO.html` is local only. Never commit it.

## Step 7: Review And Refactor

Review all changes.

Refactor only where it makes the solution simpler, clearer, or safer.

Focus on:

- Requirements alignment.
- Simplicity.
- Readability.
- Minimal diff.
- No unnecessary abstractions.
- No duplicated business logic.
- No hidden side effects.
- Existing style consistency.

After refactoring, rerun relevant tests.

## Step 8: Blocker Review Loop

Repeat until no known blockers remain:

1. Run or simulate the six review perspectives again.
2. Ask each reviewer to list blockers, including:
   - Missing or ambiguous requirement.
   - Incorrect business rule.
   - Missing test coverage.
   - Fragile tests.
   - Overengineering.
   - Unnecessary diff.
   - Possible regressions.
   - Unhandled edge cases.
   - Inconsistent implementation.
   - Raw IDs or ambiguous labels shown to users.
   - Backend contract forces poor UX or fragile frontend lookups.
   - Unclear loading, empty, error, disabled, or permission state.
   - Accessibility regression.
   - Sensitive data exposed in UI, logs, analytics, or errors.
   - N+1 query, unbounded payload, or client-side lookup loop.
   - Missing observability for critical failure paths.
   - Unnecessary breaking contract or rollout risk.
   - PR review concerns.
3. Consolidate blockers.
4. Fix every valid blocker.
5. Rerun tests.
6. Repeat until the blocker list is empty.

Do not ignore a blocker unless there is a clear reason. If a blocker is
rejected, document why in local notes.

## Step 9: Final Test Coverage

Map every relevant test scenario for the new feature.

Include:

- Unit tests.
- Integration tests.
- End-to-end tests.
- Contract/API tests.
- Permission and authorization tests.
- Business-rule scenarios.
- Negative cases.
- Boundary cases.
- UI states, if applicable.
- Display-label versus internal-id assertions, when applicable.
- Contract/API tests proving fields required for user-facing display context,
  when applicable.
- Accessibility and keyboard/focus behavior, when browser-testable.
- Privacy/security assertions for sensitive data, when applicable.
- Performance or query-count coverage for display-data changes, when practical.
- Contract compatibility and observability checks, when relevant.
- Regression risks around adjacent behavior.

Implement any missing tests needed to prove the feature works.

Run appropriate test suites.

Collect final proof:

- Test commands used.
- Passing test output summary.
- Screenshots or videos for UI/e2e flows, showing human-readable labels and
  relevant states when applicable.
- Accessibility, privacy, performance, observability, or compatibility evidence
  when those risks are relevant.
- Relevant before/after evidence.

## Step 10: Post-Code Gates

After coding, run these gates:

1. Run `sam-review-code` against the final local diff.
2. Fix every valid correction and rerun relevant tests.
3. Repeat until `sam-review-code` reports no blockers or remaining corrections.
4. Run `sam-create-test-coverage` against the final local diff.
5. Implement every required test or fix found by `sam-create-test-coverage`.
6. Run `sam-create-playwright-tests` for impacted browser flows when applicable.
7. Implement every required Playwright test or fix found by that skill.
8. Run `sam-create-task-demo-video` only when demo evidence is requested or
   reviewer-facing visual proof is needed.

If a dependent gate changes production or test code, return to the review step
and repeat only the affected gates.

## Step 11: Prepare Pull Request Or Merge Request

Before creating PR/MR:

- Ensure `REQUIREMENTS.html`, `ANALYSIS.html`, `TDD.html`, and `TODO.html` are not committed.
- Ensure only relevant source and test files are included.
- Check `git diff`.
- Check `git status`.
- Run final test suite.
- Confirm `sam-review-code`, `sam-create-test-coverage`, applicable
  `sam-create-playwright-tests`, and applicable `sam-create-task-demo-video`
  completed with no unresolved blockers.
- Confirm there are no unrelated changes.

Create PR/MR using the available tool:

- Use `gh pr create` for GitHub as draft.
- Use `glab mr create` for GitLab as draft.

PR/MR description must include:

- Feature summary.
- Requirements and acceptance criteria.
- User decisions or assumptions.
- Existing code and business rules followed.
- Implementation summary.
- Tests added or updated.
- Test evidence.
- Screenshots or e2e proof, if applicable.
- Notes for reviewers.
- Known limitations or follow-up risks.

Do not include or commit `REQUIREMENTS.html`, `ANALYSIS.html`, `TDD.html`, or `TODO.html`.

## Definition Of Done

Task is complete only when all are true:

- Requirements are discovered and no blocking ambiguity remains.
- Relevant existing code and business rules were studied before implementation.
- Blocking questions were asked and user decisions were recorded when needed.
- At least one meaningful test fails before implementation for the expected feature gap, or the closest supported validation limitation is documented.
- Feature is implemented with minimal production-code changes.
- All relevant tests pass.
- New coverage exists for required feature behavior.
- Edge cases were considered.
- Applicable UX, accessibility, privacy, performance, observability, and
  compatibility risks were checked without broadening the feature unnecessarily.
- Six-perspective review loop reports no unresolved blockers.
- `sam-review-code` and `sam-create-test-coverage` completed and all required
  coverage gaps are resolved.
- Applicable `sam-create-playwright-tests` and `sam-create-task-demo-video`
  completed or have documented non-applicability.
- Final diff is simple and reviewable.
- Temporary planning files are not committed.
- Draft PR/MR is created.
- PR/MR includes requirements, test proof, and screenshot/e2e evidence when applicable.

Stop only when Definition of Done is satisfied or a hard blocker is reached.

If a hard blocker is reached, report:

- What was completed.
- What is blocked.
- Why it is blocked.
- What evidence was collected.
- Exact next action required.

## Required Final Response Shape

Report in this order:

1. Requirements discovered.
2. Questions asked and user decisions.
3. Existing code and business rules studied.
4. Tests created before implementation.
5. Files changed.
6. Commands run and results.
7. Review-loop blockers and resolution.
8. Review gate result.
9. Test coverage gate result.
10. Playwright/demo evidence result or non-applicability reason.
11. PR/MR link.
12. Risks, gaps, or untested cases.
