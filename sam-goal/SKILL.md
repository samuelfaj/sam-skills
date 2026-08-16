---
name: sam-goal
description: "Finish a software goal completely with the smallest correct change: write checkable gates first, split independent units onto workers when the gate opens, verify every unit yourself, and never add a dependency. Use when the user runs /sam-goal, $sam-goal, or @sam-goal on claude-code, codex, or grok, says tree N, asks to finish a goal, fan out, write gates, or stop over-building."
---

# Sam Goal

Finish the asked goal. Prove it against files. Ship the first rung that holds.

Three failures this skill closes:

- reporting done at 80 percent
- doing ten independent units in one tired thread
- adding code, layers, or packages the goal did not need

Completeness applies to the asked outcomes. Minimality applies to the implementation of each outcome. Never trade one for the other.

## Non-Negotiable Contract

- Understand the request and the code it touches before writing a deliverable. The ladder shortens the solution, never the reading.
- Write gates to disk before deliverable work. Done means every box is checked with evidence, or honestly abandoned.
- Count independent units before any deliverable. If the split gate is open, write `DELEGATION.md` first, give each unit a written brief, and do not report done on a partial ledger.
- A worker or self-report is a claim. Re-run that unit's checks yourself and record what you ran.
- Never add a project dependency, plugin, hook, or package. Use the standard library, a native platform feature, or something already in the tree. A named package in the user request is the only exception, and it must be listed in `authorized_dependencies`.
- Do not invoke another skill. This package is the whole method.
- Re-measure every number at report time. A number from memory is unverified.
- Trust-boundary validation, data-loss handling, security, accessibility, hardware calibration, and anything explicitly requested are never optional.
- Bug fix means the shared root cause, not a patch on the one path named in the report.

## Resources

Always:

1. [references/output-contract.md](references/output-contract.md)
2. [references/host-runtime.md](references/host-runtime.md)
3. [references/method.md](references/method.md)
4. [references/ladder.md](references/ladder.md)
5. [references/gates.md](references/gates.md)

When the split gate is open, or tree depth is 4+:

6. [references/delegation.md](references/delegation.md)
7. [references/orchestration.md](references/orchestration.md)

Runtime scripts (invoke; do not reimplement):

- `scripts/detect_host.py`
- `scripts/scaffold_goal_dir.py`
- `scripts/check_gates.py`
- `scripts/check_ledger.py`
- `scripts/validate_goal_report.py`

## Workflow

```bash
SAM_GOAL_DIR="<absolute directory containing this SKILL.md>"
GOAL_DIR="${GOAL_DIR:-$PWD/goal}"
```

Intensity: `lite` | `full` (default) | `ultra`. Persist until the user changes it.
Action: `execute` (default) | `review` (diff only) | `audit` (whole tree). `review` and `audit` list cuts; they do not edit.
Invoke: `/sam-goal` on claude-code and grok; `$sam-goal` or `@sam-goal` on codex.

### 1. Bind the host

```bash
python3 -B "$SAM_GOAL_DIR/scripts/detect_host.py"
```

Honor `SAM_GOAL_HOST` or `SAM_ACTIVE_HOST`. Never infer the host from clients on disk. Read [references/host-runtime.md](references/host-runtime.md) and use only that host's spawn primitive. On `UNKNOWN` or `CONFLICT`, do not fan out: walk the briefs yourself. Record `host` in the report.

### 2. Scaffold

```bash
python3 -B "$SAM_GOAL_DIR/scripts/scaffold_goal_dir.py" --out "$GOAL_DIR"
```

Add `--mode delegated` when the split gate is already known open. Add `--tree N` when depth is 4 or more.

### 3. Understand, then count

Read the request and the live flow it touches. Then count independent units (neither needs the other's in-progress state).

Split gate opens on any of: **3+ independent units**, **5+ files**, or **30+ minutes**. Write `gate open: N units` or `single-agent: N units, below threshold` into the report either way.

Do not invent a split inside sequential work. One large sequential unit stays one unit.

### 4. Write the ledgers before deliverable work

Replace the scaffold placeholders.

- Always: `$GOAL_DIR/GATES.md` per [references/gates.md](references/gates.md). Outcomes, not activities. Prefer a `CHECK`/`EXPECT` pair. Any number you will report gets its own measuring gate.
- Split gate open: `$GOAL_DIR/DELEGATION.md` next, before any deliverable file, per [references/delegation.md](references/delegation.md). Non-overlapping file ownership. Checkable acceptance per row. Status starts `pending`.
- Tree 4+ or a build beyond one sitting: `$GOAL_DIR/PLAN.md` plus one gates file per leaf and branch under `$GOAL_DIR/gates/`. Fix interfaces and file ownership before fan-out.

### 5. Climb the ladder, then implement

After the ledgers exist, stop at the first rung that holds. Full rungs, intensity, and the overbuild tags live in [references/ladder.md](references/ladder.md).

Each leaf or solo stretch uses four passes on that minimal solution: implement fully, expert re-read, defect hunt, free polish. No placeholders. A pass that finds nothing, plus a fully checked gates file, is the finish line.

`lite`: build what was asked and name the lazier alternative in one line.
`full`: the ladder is mandatory.
`ultra`: delete first; ship the one-liner and challenge leftover requirement in the same breath.

### 6. Work the units

**Solo** (gate closed, tree 3 or less): do the work yourself. Update `GATES.md` as checks pass.

**Delegated** (gate open): you are the coordinator. Do not silently implement an assigned unit. For each row, write a brief (`$GOAL_DIR/briefs/worker-<n>.md`) with goal, owned files, forbidden files, pasted context, acceptance, verify commands, and isolation. Spawn one worker per independent row with the bound host primitive in [references/host-runtime.md](references/host-runtime.md). Workers never spawn. If the primitive is missing or host status is `UNKNOWN`/`CONFLICT`, walk the briefs yourself. Isolation: one writer per worktree or disjoint files. Workers never merge.

After each unit returns:

1. Re-run its acceptance check.
2. Set the row to `verified` only after that re-run, or fix/reassign and then verify.
3. Append what you ran and saw under `## Evidence` in `DELEGATION.md`.
4. Run the integration checks yourself. Finished parts can still be a broken whole.

### 7. Check the files

```bash
python3 -B "$SAM_GOAL_DIR/scripts/check_gates.py" --timeout 120 "$GOAL_DIR"
```

When a ledger exists:

```bash
python3 -B "$SAM_GOAL_DIR/scripts/check_ledger.py" "$GOAL_DIR/DELEGATION.md"
```

Exit 0 is the only complete ledger. A checked box with `EVIDENCE: pending` is unmet. An impossible gate stays in the file as `ABANDON: <id> <reason>`.

If you catch yourself writing the status summary while boxes or rows are open, stop and take the next unmet item.

### 8. Overbuild pass

On the current diff (`review` / `execute`) or the whole tree (`audit`), list cuts only: location, tag, what to delete, what replaces it. Tags: `delete`, `stdlib`, `native`, `yagni`, `shrink`. End with `net: -<N> lines possible.` Nothing to cut: `Lean already. Ship.` Do not flag the one required runnable check as bloat.

On `execute`, apply only the cuts that preserve every gate. On `review` / `audit`, list and stop.

### 9. Report

Write `$GOAL_DIR/goal-report.json` from [references/output-contract.md](references/output-contract.md). Re-measure every number. Paste checker summaries into `checks`. Then:

```bash
python3 -B "$SAM_GOAL_DIR/scripts/validate_goal_report.py" "$GOAL_DIR/goal-report.json"
```

`COMPLETE` is allowed only when that validator prints `VALID`.

## Return

1. `COMPLETE`, `IN_PROGRESS`, or `BLOCKED`
2. Bound host (`claude-code` | `codex` | `grok` | unknown) and spawn primitive used
3. Intensity, action, mode, unit count, split-gate decision
4. Ladder rung taken, what was skipped, authorized new packages (must be none unless the user named them)
5. Gates: N of N, abandoned ids, checker summary
6. If delegated: ledger N of N, what you verified, evidence
7. Overbuild `net` line
8. Absolute `GOAL_DIR` and validator result
9. Exact remaining work or blockers

Trivial one-line factual answers do not need this machinery. An explicit `/sam-goal` on a tiny task still gets one solo gate and a validated report.
