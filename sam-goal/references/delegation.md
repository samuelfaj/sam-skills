# Delegation

The ledger is the contract. Write it before any deliverable file.

```markdown
# Delegation plan
Units: <N>

| # | Unit | Files (mine) | Worker | Acceptance | Status |
|---|------|--------------|--------|------------|--------|
| 1 | <what done looks like> | <paths> | worker-1 | <command or measure> | pending |

## Evidence

- <exact checks the coordinator re-ran, with output>
```

## Row rules

- One row per unit. No two rows share a file. If they seem to, the split
  is wrong or the shared surface belongs in `PLAN.md`.
- Acceptance is a command, a test, or a measurable threshold. "Works" is not.
- Status only: `pending` → `done` (worker claimed) → `verified`
  (coordinator re-ran the check).
- Placeholder rows whose unit cell is `...` are ignored by the checker.
- `scripts/check_ledger.py` exits 0 only when every real row is `verified`
  and `## Evidence` contains a strong line (a command, a path, or a
  measured result). The word `verified` is not evidence. A backticked
  `done` is not evidence. Angle-bracket template text is not evidence.

## Worker brief

Write `$GOAL_DIR/briefs/worker-<n>.md` with exactly these sections:

| Section | Required content |
| --- | --- |
| Goal | One sentence. What done looks like. |
| Scope | Owned files. Forbidden files. New files allowed, or none. |
| Context | Specs and upstream facts pasted in full. The worker cannot see the parent thread. |
| Acceptance | Checkable lines from the ledger row. |
| Verify | Exact commands to run before reporting. |
| Isolation | Worktree or branch. One writer. Do not merge. |

The worker also receives the ladder and its own gates file, not the
parent history and not other workers' output.

## Coordinator

You do not do an assigned unit's work unless the ledger names you as
that worker. After each return: re-run the check, update the row, append
evidence, then integrate. Interfaces, the whole suite, and a scope diff
are coordinator work. Workers never merge, never push, never touch
another row's files.
