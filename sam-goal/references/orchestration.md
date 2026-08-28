# Orchestration

Fresh context per unit is the reason to split. A single thread that
carries ten units collects ten units of drift. A narrow brief plus a
gates file resets attention.

## When to orchestrate

Use delegated mode when the split gate is open or tree depth is 4+.
Under about thirty minutes of real work, stay solo: one `GATES.md`, same
discipline, no dispatch tax.

## Driver loop

1. Fix the contract in `PLAN.md` or `DELEGATION.md` (interfaces, ownership,
   naming) before any leaf starts.
2. Dispatch one unit per brief with the bound host primitive in
   [host-runtime.md](host-runtime.md). Independent units go out in the
   same turn when that primitive allows parallel spawn. Workers never
   spawn. If the primitive is missing, walk the briefs yourself.
3. Re-run that unit's checks. `check_gates.py --status` on its gates
   file, plus the acceptance command from the row. Send it back with the
   unmet ids named if evidence is pending or a check fails.
4. Append one status-log line. Never rewrite earlier log lines.
5. When every child of a branch is verified, run that branch's
   integration gates yourself.
6. Report only when root gates are met and, if a ledger exists,
   `check_ledger.py` exits 0.

## Isolation

Prefer a worktree per worker when two units must write at the same time:

```bash
git worktree add -b agent/<slug> ../wt-<slug> main
```

Same-tree branches are safe only when file columns are disjoint. One
writer per tree. The coordinator is the only merger.

If two workers need the same file, fix the plan. Do not coordinate
through hope.

Worker worktrees isolate concurrent writers. They are not a restart
mechanism. Do not create a new worktree from a moving integration branch
because a gate, review, or test failed.

## Verification layers

1. Worker self-check. Weakest.
2. Coordinator re-run. Required. This is what makes self-reports usable.
3. Integration checks. Required. Locally perfect units can still be a
   broken product.

Do not skip layer 2 or 3 because the worker sounded sure.

## Failure

- Acceptance fails: re-run, then fix forward on the same branch/tree, or
  spawn a follow-up with the failure output as context. Never silently
  accept. Never discard the unit's receipts and start from a fresh base
  SHA.
- Worker cannot finish: it returns what was done and why. Reassign,
  re-scope, or take the unit yourself and name yourself in the ledger.
- Scope trespass: revert the extra files, re-run the owner's checks.
- Integration ref moved (`main`/`production` advanced): keep the task
  branch. Rebase or retarget only if the user asked. Overlap-free drift
  does not invalidate verified rows.

## Cost

Checks are shell commands, not re-reading. Evidence is the deciding
tail. Leaf briefs stay lean. Mechanical units may use a cheaper host
effort; design, integration, and every verification pass stay on the
strong path. Verification is the last thing to cut.
