---
name: sam-goal
description: "Finish a software goal with the smallest correct change: gates first, independent units on workers, every unit verified, no new dependencies. Use when the user runs /sam-goal, $sam-goal, or @sam-goal, says tree N, finish a goal, fan out, write gates, or stop over-building."
---

# Sam Goal

Finish the asked goal, prove it against files, and ship the first rung that holds. Completeness applies to the asked outcomes; minimality applies to each outcome's implementation. Never trade one for the other.

## Non-Negotiable Contract

- Understand the request and the code it touches before writing a deliverable. The ladder shortens the solution, never the reading.
- Write gates to disk before deliverable work. Done means every box is checked with evidence, or honestly abandoned.
- Count independent units before any deliverable. If the split gate is open, write `DELEGATION.md` first, give each unit a written brief, and do not report done on a partial ledger.
- A worker or self-report is a claim. Re-run that unit's checks yourself and record what you ran.
- Never add a project dependency, plugin, hook, or package. Use the standard library, a native platform feature, or something already in the tree. A named package in the user request is the only exception, and it must be listed in `authorized_dependencies`.
- Do not invoke another skill. This package is the whole method. If this turn also named `sam-task`, `sam-work`, `sam-orchestrate`, or a `sam-orchestrate-*` profile, those bodies are context only — execute this skill alone. Exclusive top pipeline precedence: `sam-goal` > `sam-task` > `sam-work` > `sam-orchestrate`.
- Fix forward on the current branch/tree. A failed gate, missing test, review finding, or moved integration ref (`main`/`production`) is a new commit or a parked note. It is not a new worktree, reset, rebase, or discarded receipt chain.
- Findings outside frozen gates are parked. They do not become new units in this run.
- Re-measure every number at report time. A number from memory is unverified.
- Trust-boundary validation, data-loss handling, security, accessibility, hardware calibration, and anything explicitly requested are never optional.
- Bug fix means the shared root cause, not a patch on the one path named in the report.

## Resources

| Reference | Read when |
| --- | --- |
| [references/gates.md](references/gates.md) | Step 4, before writing gates |
| [references/ladder.md](references/ladder.md) | Step 5 on `execute`; step 7 on `review` or `audit` |
| [references/method.md](references/method.md) | Choosing tree depth: the user said tree N, or the goal may need depth 4+ |
| [references/orchestration.md](references/orchestration.md) | The split gate is open or tree depth is 4+ |
| [references/output-contract.md](references/output-contract.md) | Step 9, before writing the report |

Read each file once; re-read only after context compaction or when you cannot quote the section you need.

Invoke the stdlib `python3` scripts on every host; never reimplement them or wrap them in a plugin, hook, or package. Replace `<skill>` (this SKILL.md's directory) and `<goal>` (default `<cwd>/goal`) with literal absolute paths, not shell variables.

## Workflow

Intensity: `lite` | `full` (default) | `ultra`; it persists until the user changes it. Action: `execute` (default) | `review` (diff only) | `audit` (whole tree). `review` and `audit` list cuts; they never edit.

### 1. Bind the host

`python3 -B <skill>/scripts/detect_host.py`

Honor `SAM_GOAL_HOST` or `SAM_ACTIVE_HOST`. Never infer the host from clients on disk. Any status other than `DETECTED` or `OVERRIDE` (exit 2): never fan out; walk the briefs yourself.

### 2. Scaffold

`python3 -B <skill>/scripts/scaffold_goal_dir.py --out <goal>`

Add `--mode delegated --workers N` once the split gate is open, and `--tree N` when depth is 4+. Re-running keeps existing files.

### 3. Understand, then count

Trace the live flow the request touches; for a bug, grep every caller and fix the shared function once. Count independent units: neither needs the other's in-progress state. The split gate opens on any of **3+ independent units**, **5+ files**, or **30+ minutes**. Record `gate open: N units` or `single-agent: N units, below threshold` either way. Never invent a split inside sequential work; one large sequential unit stays one unit.

### 4. Write the ledgers before deliverable work

Replace every scaffold placeholder.

- Always: `<goal>/GATES.md` per gates.md.
- Split gate open: `<goal>/DELEGATION.md` and one brief per row, per orchestration.md.
- Tree 4+ or a build beyond one sitting: `<goal>/PLAN.md` plus one gates file per leaf and branch under `<goal>/gates/`.

### 5. Climb the ladder, then implement

Stop at the first ladder.md rung that holds and implement it fully, no placeholders. Then run one review pass on the diff, inside the frozen gates: expert re-read plus defect hunt (edge cases, error paths, every caller, the never-optional items). Repeat it only when the previous pass changed code, at most two repeats. No polish pass; step 7 shrinks.

### 6. Work the units

**Solo** (gate closed, tree 3 or less): do the work yourself. Run step 8's `check_gates.py` without `--recheck` as checks start to pass.

**Delegated** (gate open): you are the coordinator; run the driver loop in orchestration.md. Do not silently implement an assigned unit.

### 7. Overbuild pass

On the current diff (`execute`, `review`) or the whole tree (`audit`), list cuts per ladder.md § Overbuild tags. On `execute`, apply only the cuts that preserve every gate. On `review` or `audit`, list them, edit nothing, and continue to step 8.

### 8. Check the final tree

```bash
python3 -B <skill>/scripts/check_gates.py --recheck --timeout 120 <goal>
python3 -B <skill>/scripts/check_ledger.py <goal>/DELEGATION.md   # delegated only
```

`--recheck` re-runs every `CHECK` on the final tree, met or not, and unchecks failures: it is the report-time re-measure. Re-measure each listed `MANUAL` gate by hand. Only exit 0 is complete. Caught writing the status summary while boxes or rows are open: stop and take the next unmet item.

### 9. Report

Write `<goal>/goal-report.json` with the fields output-contract.md marks as yours, then:

`python3 -B <skill>/scripts/validate_goal_report.py --derive <goal>/goal-report.json`

`COMPLETE` is allowed only when it prints `VALID`. Fix from the validator's error lines and patch the report in place; do not read validator source or rewrite the whole report.

## Return

At most 15 lines (goal-report.json holds the rest): `COMPLETE`, `IN_PROGRESS`, or `BLOCKED`; the absolute goal directory and validator line; the spawn primitive used, or `walked briefs`; gates N of N, abandoned ids, and ledger N of N when delegated; the ladder rung and new packages (none unless the user named them); the overbuild `net` line; exact remaining work or blockers.

Trivial one-line factual answers skip this machinery. An explicit `/sam-goal` on a tiny task still gets one solo gate and a validated report.
