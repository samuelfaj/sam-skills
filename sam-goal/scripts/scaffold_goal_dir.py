#!/usr/bin/env python3
"""Create a goal output directory with starter ledger files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


GATES = """# Gates: <task>

Scope: <one line: what this unit of work delivers>

- [ ] G1: <observable outcome, stated so a stranger could judge it>
  CHECK: <shell command that proves it>
  EXPECT: <substring the command output must contain, or /regex/>
  EVIDENCE: pending
"""

DELEGATION = """# Delegation plan
Units: <N>

| # | Unit | Files (mine) | Worker | Acceptance | Status |
|---|------|--------------|--------|------------|--------|
<rows>
| ... | ... | ... | ... | ... | ... |

## Rules of this ledger

- One row per unit. No two rows share a file.
- Acceptance is checkable: a command, a test, a measurable criterion.
- Status: `pending` → `done` (worker reported) → `verified` (coordinator re-ran).
- No done for the task until every row is `verified`.

## Evidence

- <coordinator writes here: the exact checks they ran, with output>
"""

PLAN = """# Plan: <task>

Depth: tree <N>   Mode: delegated

## Contract

Decided BEFORE fan-out.

- Interfaces: <signatures, file formats, API shapes>
- Data ownership: <which unit owns which files; no two units share a file>
- Naming and conventions: <casing, folder layout, error handling>

## Tree

- 1 <task>
  - 1.1 <leaf> ........ gates/leaf-1.1.md

## Status log

Append-only.

- plan written, contract fixed
"""

ROW = "| <n> | <one line: what done looks like> | <paths, comma-separated> | worker-<n> | <checkable: command / test / measure> | pending |"

BRIEF = """# Worker brief: worker-<n>, <unit name>

You own one unit. Finish it, verify it, report it. Do not touch anything outside your scope. Do not spawn subagents.

## Goal

<One sentence. What done looks like.>

## Scope

- **You own:** <exact files>
- **You must NOT touch:** <exact files/dirs>
- New files: <allowed paths, or none>
- New packages: <package the user named, or none>

## Context

<Dependencies pasted in full. You cannot see the coordinator thread.>

## Acceptance

- <checkable criterion from the ledger row>
- Gates file: <path, or none>

## Method

Read the code first. Then stop at the first rung that holds:

1. Not needed? Skip it and say so.
2. Reuse what the codebase already has.
3. Standard library.
4. Native platform feature.
5. A dependency already present. Never add a new one unless Scope names it.
6. One line.
7. Otherwise the minimum that works.

Less code, not the flimsier algorithm; between equal options take the one correct on edge cases. Mark a known ceiling with a `sam-goal:` comment naming the upgrade path.

Never skip: trust-boundary validation, data-loss handling, security, accessibility, hardware calibration, anything this brief requests. Non-trivial logic leaves one runnable check. No placeholders.

After implementing, run one review pass on your diff, limited to Acceptance: expert re-read plus defect hunt (edge cases, error paths, callers). Repeat it only when it changed code, at most two repeats.

## Verify (run these before reporting done)

```bash
<exact commands with expected output>
```

## Isolation

- Worktree/branch: `git worktree add -b agent/<slug> ../wt-<slug> main`
- One writer per worktree. Do not merge.

## Report back

- Files changed
- Verify exit code and the deciding tail (at most 2 lines), not the full output
- Anything you could not finish and why
"""


def write_new(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Goal directory")
    parser.add_argument("--mode", choices=("solo", "delegated"), default="solo")
    parser.add_argument("--tree", type=int, default=2)
    parser.add_argument("--workers", type=int, help="Delegated only: briefs and ledger rows to write")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    goal_dir = Path(args.out).expanduser()
    goal_dir = goal_dir.resolve() if goal_dir.is_absolute() else (Path.cwd() / goal_dir).resolve()
    if goal_dir.exists() and not goal_dir.is_dir():
        print(f"error: path exists and is not a directory: {goal_dir}", file=sys.stderr)
        return 2
    if args.tree < 1:
        print("error: --tree must be >= 1", file=sys.stderr)
        return 2
    if args.workers is not None and (args.mode != "delegated" or args.workers < 1):
        print("error: --workers needs --mode delegated and N >= 1", file=sys.stderr)
        return 2
    workers = args.workers or 1
    goal_dir.mkdir(parents=True, exist_ok=True)
    created = {"GATES.md": write_new(goal_dir / "GATES.md", GATES)}
    if args.mode == "delegated":
        rows = "\n".join(ROW.replace("<n>", str(n)) for n in range(1, workers + 1))
        created["DELEGATION.md"] = write_new(
            goal_dir / "DELEGATION.md", DELEGATION.replace("<rows>", rows)
        )
        for n in range(1, workers + 1):
            name = f"briefs/worker-{n}.md"
            created[name] = write_new(goal_dir / name, BRIEF.replace("<n>", str(n)))
    if args.tree >= 4:
        created["PLAN.md"] = write_new(goal_dir / "PLAN.md", PLAN.replace("<N>", str(args.tree)))
        created["gates/leaf-1.1.md"] = write_new(goal_dir / "gates" / "leaf-1.1.md", GATES)
    result = {
        "goal_dir": str(goal_dir),
        "mode": args.mode,
        "tree_depth": args.tree,
        "created": sorted(name for name, wrote in created.items() if wrote),
        "existing": sorted(name for name, wrote in created.items() if not wrote),
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(str(goal_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
