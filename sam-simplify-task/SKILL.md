---
name: sam-simplify-task
description: Run a post-task simplification loop that reviews completed work, removes unnecessary complexity with strict maintainability pressure, and proves behavior stayed correct.
---

# Sam Simplify Task

Use this skill when the user invokes `/sam-simplify-task` or asks to run a
post-implementation simplification pass after the task is done.

This skill reviews all completed work, finds code that can be made simpler, and
applies the smallest safe simplifications while preserving behavior.

## Operating Role

You are a senior software engineer doing a final code-health pass after
implementation, tests, and task proof already exist.

Your job is not to redesign the feature. Your job is to make the completed work
easier to understand, easier to review, and less risky to maintain.

## Research-Informed Principles

Use these principles while simplifying:

- Refactor in small behavior-preserving steps.
- Prefer progress over perfection; stop when the change is clearly simpler and
  further cleanup becomes subjective polish.
- Favor code-health improvement that reduces future reader effort.
- Treat overengineering, speculative flexibility, excessive indirection,
  duplicated logic, mixed abstraction levels, unclear names, and needless state
  as simplification targets.
- Keep changes small enough to review and roll back.
- Validate behavior with tests and runtime proof rather than assuming refactors
  are safe.
- Remember tests are maintainable code too; simplify brittle or overcomplicated
  tests when doing so preserves useful coverage.

## Thermo-Nuclear Simplification Bar

Apply this as an addition to the normal post-task simplification loop. Be
ambitious about structural simplification, but only when behavior can remain
unchanged and proof is available.

Look for a behavior-preserving "code judo" move:

- Delete whole categories of complexity instead of polishing them.
- Reframe state so conditionals disappear instead of centralizing the same
  branches.
- Collapse duplicate branches into one direct flow.
- Move feature logic to the canonical owning layer or existing helper.
- Replace condition chains with an explicit typed model, dispatcher, policy, or
  state machine when that removes scattered special cases.
- Delete wrappers, identity abstractions, generic magic, casts, optionality, and
  pass-through helpers that do not simplify callers.
- Split a file that crossed or is about to cross 1000 lines because of the task
  when a focused module would make the change easier to review.
- Separate orchestration from business logic and group related updates more
  atomically when partial state is harder to reason about.

Do not accept a refactor that merely moves complexity around. A simplification
must reduce the number of concepts, branches, states, helpers, or layers a
future reader must hold.

## Constraints

- Run this after the primary task implementation is complete.
- Do not change user-facing behavior unless the user explicitly asks.
- Do not broaden scope into unrelated cleanup.
- Do not chase style preferences unless they directly improve clarity or match
  established project style.
- Do not introduce new abstractions unless they remove real duplication,
  clarify mixed abstraction levels, or match an existing local pattern.
- Do not remove tests, validation, permissions, security checks, observability,
  migrations, or compatibility handling just because they look verbose.
- Do not hide complexity by moving it to a worse place.
- Do not touch unrelated dirty worktree changes.
- If simplification would be risky without missing tests or environment access,
  stop and report the blocker instead of guessing.

## Step 1: Identify The Completed Work

Determine the exact work to simplify:

- Current branch and base branch
- Files changed by the task
- User-facing behavior or API contract that must remain unchanged
- Tests and proof already produced
- Known review comments, TODOs, or follow-up constraints
- Unrelated local changes that must be ignored

If the task scope is unclear, ask a concise blocking question before editing.

## Step 2: Establish A Safety Baseline

Before simplifying, establish what proves behavior is currently correct:

- Inspect existing tests for changed behavior.
- Run the smallest relevant passing test suite when practical.
- Note any test or environment blocker.
- Capture current diff shape and changed-file list.

Do not begin risky simplification without a baseline that can catch behavioral
regressions, unless the user explicitly accepts the risk.

## Step 3: Find Simplification Opportunities

Review every task-touched file and nearby code needed to understand it.

Look for:

- Code that can be deleted because it is unused, redundant, or replaced by the
  final approach.
- Duplicate logic that can be collapsed into an existing helper or one local
  helper.
- Speculative options, flags, hooks, config, props, parameters, or extension
  points not required by the task.
- Functions doing multiple levels of abstraction at once.
- Deep nesting, long conditionals, repeated boolean expressions, or control flow
  that can be made linear with guard clauses or clearer branching.
- State that can be derived instead of stored.
- Data transformations that can be closer to the boundary where they belong.
- Names that hide domain meaning or force readers to inspect implementation.
- Comments explaining what unclear code does, where clearer code or a `why`
  comment would be better.
- Test setup that is more complex than the behavior being asserted.
- Test assertions that are brittle, duplicated, or tied to implementation
  details instead of observable behavior.
- Files, exports, mocks, fixtures, or utilities created during implementation
  that are no longer needed.

Classify each opportunity:

- `APPLY`: clearly simpler, safe, and in scope.
- `SKIP`: subjective, too risky, or not worth the churn.
- `BLOCKED`: likely useful but missing tests, access, or clarification.

## Step 4: Apply The Smallest Safe Simplifications

For each `APPLY` item:

- Make one coherent simplification at a time.
- Preserve public APIs and contracts unless the task already changed them.
- Prefer deleting code over moving code.
- Prefer local simplification over shared abstraction.
- Prefer existing project helpers over new helpers.
- Keep file and module boundaries consistent with the codebase.
- Remove imports, types, tests, fixtures, or docs made obsolete by your own
  simplification.

After each meaningful simplification, re-check the diff to confirm the change is
actually smaller or clearer.

## Step 5: Verify Behavior Stayed Correct

Run validation proportional to risk:

- Targeted unit/component tests for changed logic.
- Integration/API tests for contract or data-flow changes.
- Playwright/E2E tests for user-facing flows when simplification touches UI or
  cross-service behavior.
- Typecheck, lint, or build when the repo uses them and the simplification could
  break compile-time guarantees.

If validation fails:

- Fix the simplification if the failure exposes a real safe cleanup issue.
- Revert only your own simplification if it changed behavior or creates churn.
- Leave the original implementation intact if simplification is not clearly
  safer.

## Step 6: Repeat Until Simple Enough

Repeat:

1. Re-read the diff.
2. Search for remaining real complexity.
3. Apply only high-confidence simplifications.
4. Verify again.

Stop when one of these is true:

- `SIMPLEST DEFENSIBLE`: no remaining in-scope simplification clearly improves
  maintainability without adding risk or churn.
- `NO CHANGE`: implementation is already simple enough; no edit is justified.
- `BLOCKED`: useful simplification requires missing tests, environment access,
  user clarification, or unsafe scope expansion.

Do not keep editing after the remaining changes are subjective polish.

## Output Format

Return:

- `Decision`: `SIMPLEST DEFENSIBLE`, `NO CHANGE`, or `BLOCKED`
- `Simplifications applied`
- `Simplifications skipped`
- `Behavior preserved`
- `Validation run`
- `Residual risk`
- `Files changed`
- `Next action`

If no code changes were made, say why. If changes were made, explain why the new
code is simpler without claiming perfection.
