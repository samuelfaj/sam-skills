# Orchestration

## Spawn

Bind exactly one row; never mix primitives. The coordinator fans out; workers never spawn.

| Host | Primitive | Parallel | Nesting |
| --- | --- | --- | --- |
| `claude-code` | native Task / Agent tool | yes, independent units | coordinator only |
| `codex` | native agent spawn, fresh thread | yes, independent units | no; `max_depth` is 1 |
| `grok` | native `spawn_subagent` | yes, independent units | no; children do not spawn children |

Never use another host's scheduler, `/loop`, `ultracode`, or workflow dialect. Primitive missing or host not `DETECTED`/`OVERRIDE`: walk the briefs yourself. A sequential ledger still counts; an invented spawn does not.

## Ledger and briefs

`scaffold_goal_dir.py --mode delegated --workers N` writes N pending ledger rows and `briefs/worker-1..N.md`. Fill every placeholder; paste brief context in full, since the worker cannot see the parent thread. A worker gets its brief and its own gates file, never the parent transcript or other workers' output.

- One row per unit; no two rows share a file. If they seem to, the split is wrong or the shared surface belongs in `PLAN.md`.
- Acceptance is a command, a test, or a measurable threshold. "Works" is not.
- Status only: `pending` → `done` (worker claimed) → `verified` (coordinator re-ran the check).
- `check_ledger.py` ignores rows whose unit cell is `...`. It exits 0 only when every real row is `verified` and `## Evidence` holds a strong line (a command, a path, or a measured result). The word `verified`, a backticked `done`, and angle-bracket template text are not evidence.

## Driver loop

1. Fix interfaces, ownership, and naming in `PLAN.md` or `DELEGATION.md` before any leaf starts.
2. Dispatch one unit per brief. Independent units go out in the same turn when the primitive allows parallel spawn.
3. When a unit returns, re-run `check_gates.py --recheck <its gates file>` and the row's acceptance command from the worker's worktree, or after merging it (`CHECK` commands run in the current directory); a worker's self-check is the weakest layer. On a failure, send it back with the unmet ids named.
4. Set the row to `verified` only after that re-run passes; append what you ran and saw under `DELEGATION.md` `## Evidence`, plus one status-log line in `PLAN.md` when it exists (never rewrite earlier lines).
5. When every child of a branch is verified, run that branch's integration gates yourself. Finished parts can still be a broken whole.
6. Report only when root gates are met and `check_ledger.py` exits 0.

Never skip step 3 or 5 because a worker sounded sure. Do an assigned unit's work only when the ledger names you. Interfaces, the whole suite, and the scope diff are coordinator work. Workers never merge, push, or touch another row's files.

## Isolation

Isolation is git worktrees or disjoint files, not a host feature. Give each worker a worktree (command in the brief) when two units write at the same time; same-tree work needs disjoint files. One writer per tree; the coordinator is the only merger. Two workers needing one file means: fix the plan.

Worker worktrees isolate concurrent writers. They are not a restart mechanism. Never create a new worktree from a moving integration branch because a gate, review, or test failed.

## Failure

- Acceptance fails: fix forward on the same branch/tree, or spawn a follow-up with the failure tail as context. Never silently accept. Never discard the unit's receipts and start from a fresh base SHA.
- Worker cannot finish: it returns what was done and why. Reassign, re-scope, or take the unit yourself and name yourself in the ledger.
- Scope trespass: revert the extra files, then re-run the owner's checks.
- Integration ref moved (`main`/`production` advanced): keep the task branch. Rebase or retarget only if the user asked. Overlap-free drift does not invalidate verified rows.

## Cost

Checks are shell commands, not re-reading; evidence is the deciding tail. Leaf briefs stay lean. Mechanical units may use a cheaper host effort; design, integration, and every verification pass stay on the strong path.
