# Sam Skills

Personal Codex skills.

## Skills

- `sam-create-playwright-tests`: map impacted flows, create comprehensive Playwright E2E coverage, record local videos, and attach PR evidence.
- `sam-create-task-demo-video`: create human-paced task demo videos, convert them to `.mp4`, verify playback, upload them, and comment on the GitHub PR or GitLab MR by default.
- `sam-create-test-coverage`: create exhaustive risk-based unit, component, integration, API/contract, and E2E coverage for backend or frontend changes.
- `sam-create-feature`: autonomous feature workflow with requirements discovery, TDD implementation, validation, and PR evidence.
- `sam-fix-bug`: autonomous bugfix workflow with failing tests first, local analysis notes, minimal implementation, validation, and PR evidence.
- `sam-orchestrate`: run Codex as a controller-only orchestrator that delegates execution to subagents with controlled `gpt-5.4-mini`/`gpt-5.5` effort and a final `gpt-5.5 medium` review.
- `sam-orchestrate-claude`: Claude port of `sam-orchestrate` that delegates execution to subagents across `haiku`/`sonnet`/`opus`/`fable` by cost and risk, with a final `opus medium` review.
- `sam-pr-description`: create standardized English GitHub PR or GitLab MR descriptions from branch commits, diffs, tests, safety, and business rules.
- `sam-refine-task`: stress-test a strategy, find loopholes, apply proper fixes, and loop until confidence is factual.
- `sam-simplify-task`: review completed work, remove unnecessary complexity, and prove behavior stayed correct.
- `sam-review-code`: rigorous local code review for current workspace changes, returned in Codex without PR/MR comments.
- `sam-review-pr`: rigorous end-to-end GitHub/GitLab PR or MR review with published platform comments.

## Workflow Defaults

- `sam-create-feature` and `sam-fix-bug` always use the full workflow.
- Cross-skill references are not treated as magic commands. A skill that needs
  another skill must load the sibling `SKILL.md`, pass a compact input block,
  execute only applicable steps, and report `DEPENDENCY_FALLBACK` if the sibling
  skill is unavailable.
- Local planning artifacts such as `REQUIREMENTS.html`, `ANALYSIS.html`,
  `TDD.html`, and `TODO.html` are optional. Create them only when they materially
  improve handoff quality or when explicitly requested. Never commit them.
- Any skill that creates `.html` artifacts must make them human-readable and
  visually simple: semantic HTML, inline CSS, readable typography, restrained
  colors, clear spacing, accessible contrast, status badges/tables/cards where
  useful, and no external assets or decorative clutter.
- Video evidence tasks must upload every safe relevant video to GitHub or GitLab
  when a PR/MR can be resolved. Comments must use the exact platform-renderable
  format: raw `https://github.com/user-attachments/assets/...` URLs on their own
  paragraph for GitHub, and the exact GitLab Markdown Uploads API `markdown`
  field with `/uploads/...` for GitLab.

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

### Codex from GitHub

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo samuelfaj/sam-skills \
  --path \
    sam-create-playwright-tests \
    sam-create-task-demo-video \
    sam-create-test-coverage \
    sam-create-feature \
    sam-fix-bug \
    sam-orchestrate \
    sam-pr-description \
    sam-refine-task \
    sam-simplify-task \
    sam-review-code \
    sam-review-pr
```

Restart Codex after installing or updating skills.

### Codex from local checkout

```bash
cd /path/to/sam-skills
mkdir -p ~/.codex/skills
find . -maxdepth 1 -type d -name 'sam-*' -exec sh -c '
  for skill do
    name=$(basename "$skill")
    rm -rf "$HOME/.codex/skills/$name"
    cp -R "$skill" "$HOME/.codex/skills/$name"
  done
' sh {} +
```

### Claude from local checkout

```bash
cd /path/to/sam-skills
mkdir -p ~/.claude/skills
find . -maxdepth 1 -type d -name 'sam-*' -exec sh -c '
  for skill do
    name=$(basename "$skill")
    rm -rf "$HOME/.claude/skills/$name"
    cp -R "$skill" "$HOME/.claude/skills/$name"
  done
' sh {} +
```

### Verify installs

```bash
for dest in ~/.codex/skills ~/.claude/skills; do
  echo "$dest"
  find "$dest" -maxdepth 2 -path '*/sam-*/SKILL.md' -print | sort
done
```

Every installed skill must have a `SKILL.md` with a `name: sam-*` field. Restart
Codex and Claude after installing or updating skills.
