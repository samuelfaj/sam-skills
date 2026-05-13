# Sam Skills

Personal Codex skills.

## Skills

- `sam-create-playwright-tests`: map impacted flows, create comprehensive Playwright E2E coverage, record local videos, and attach PR evidence.
- `sam-create-task-demo-video`: create human-paced task demo videos, convert them to `.mp4`, verify playback, upload them, and comment on the GitHub PR or GitLab MR by default.
- `sam-create-test-coverage`: create exhaustive risk-based unit, component, integration, API/contract, and E2E coverage for backend or frontend changes.
- `sam-create-feature`: autonomous feature workflow with requirements discovery, TDD implementation, validation, and PR evidence.
- `sam-fix-bug`: autonomous bugfix workflow with failing tests first, local analysis notes, minimal implementation, validation, and PR evidence.
- `sam-compress-talk`: use AR0 compact task DSL with hidden reasoning and `dictionary.md` aliases for repeated thread terms.
- `sam-pr-description`: create standardized English GitHub PR or GitLab MR descriptions from branch commits, diffs, tests, safety, and business rules.
- `sam-refine-task`: stress-test a strategy, find loopholes, apply proper fixes, and loop until confidence is factual.
- `sam-simplify-task`: review completed work, remove unnecessary complexity, and prove behavior stayed correct.
- `sam-review-code`: rigorous local code review for current workspace changes, returned in Codex without PR/MR comments.
- `sam-review-pr`: rigorous end-to-end GitHub/GitLab PR or MR review with published platform comments.

## Custom instructions

Add to your global `CLAUDE.md` / `AGENTS.md`:

```
# RULES

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Rule 5 — Match the codebase's conventions, even if you disagree
If the codebase uses snake_case and you'd prefer camelCase: snake_case.
If the codebase uses class-based components and you'd prefer hooks: class-based.
Disagreement is a separate conversation. Inside the codebase, conformance > taste.
If you genuinely think the convention is harmful, surface it. Don't fork it silently.

## Rule 6 — Fail loud
If you can't be sure something worked, say so explicitly.
"Migration completed" is wrong if 30 records were skipped silently.
"Tests pass" is wrong if you skipped any.
"Feature works" is wrong if you didn't verify the edge case I asked about.
Default to surfacing uncertainty, not hiding it.

## Rule 7 — Checkpoint after every significant step
After completing each step in a multi-step task: summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back to me.
If you lose track, stop and restate.

## Rule 8 — Tests verify intent, not just behavior
Every test must encode WHY the behavior matters, not just WHAT it does.
A test like `expect(getUserName()).toBe('John')` is worthless if the function takes a hardcoded ID.
If you can't write a test that would fail when business logic changes, the function is wrong.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
```


## Install

Install every skill in this repo:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo samuelfaj/sam-skills \
  --path \
    sam-create-playwright-tests \
    sam-create-task-demo-video \
    sam-create-test-coverage \
    sam-create-feature \
    sam-fix-bug \
    sam-refine-task \
    sam-simplify-task \
    sam-review-code \
    sam-review-pr
```

Restart Codex after installing or updating skills.
