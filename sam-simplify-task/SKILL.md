---
name: sam-simplify-task
description: "Simplify code from a completed task without changing behavior, public contracts, unrelated dirty work, or existing proof. Use after the implementation works to cut duplication, branching, state, indirection, speculative flexibility, or review burden; not for features, unknown bugs, or broad cleanup."
---

# Sam Simplify Task

Remove task-introduced complexity without redesigning behavior. Stay stack-,
provider-, host-, tool-, and model-neutral.

## Non-Negotiable Contract

- Never expose secrets, credentials, private data, or sensitive paths in diffs,
  commands, reports, artifacts, or returned evidence.
- Operate only after the primary task and its proof exist.
- Preserve user-visible behavior, public contracts, security, permissions,
  migrations, compatibility handling, and observability.
- Preserve unrelated staged, unstaged, and untracked work byte-for-byte. Never
  reset, checkout, stash, clean, rebase, or broadly restore the workspace.
- Stage, commit, publish, or message an external system only when the user or a
  parent workflow (e.g. `sam-work`) explicitly requested that exact action;
  parent authorization is enough, never re-ask.
- Child mode (a parent workflow or phase worker invoked you): never ask; if
  ownership cannot be reconstructed safely, return `BLOCKED` with receipts.
  Standalone: ask at most one blocking question, only for that case. Never
  claim code because it is adjacent or untidy.
- Return any change beyond the frozen goal, contract, or owner boundary to the
  parent as the exact gap (standalone: ask). File or line counts alone neither
  widen nor approve scope; justify each added path against the frozen goal.
  Stop after two simplification cycles unless new evidence appears.

## Resources

Use literal absolute paths: `<skill>` is this directory; `<tmp>` is the
parent's phase directory, else scratch outside `<repo>`. Re-read a file only
after compaction or when you cannot quote the needed section; a copy of
`evidence-policy.md` or `risk-lenses.md` already read from sam-fix-bug,
sam-create-feature, or sam-refine-task counts.

| Read | When |
|---|---|
| `references/output-contract.md` | Step 1, before freezing the report |
| `references/evidence-policy.md` | Step 2, before deciding whether proof suffices to edit |
| `references/risk-lenses.md` | Step 3: only lenses the candidates reach |

## 1. Freeze Completed Work

```bash
python3 <skill>/scripts/capture_scope.py --repo <repo> > <tmp>/baseline.json
python3 <skill>/scripts/validate_report.py --scaffold --baseline <tmp>/baseline.json <tmp>/report.json
```

Repeat `--path <repo-relative-path>` only for explicit scope, with identical
arguments in every capture. Never open `baseline.json` or `current.json`; the
capture's stderr line summarizes them. Rewind (this skill already wrote a
report for this task): capture and scaffold in a fresh `<tmp>` (under a parent,
the handoff's phase dir) with `--from <prior report>`; never move, edit, or
overwrite the prior report.

Freeze into the report: task-owned changed paths as initial owned paths and
every `intent` field (goal: intended behavior; must_not_change: unrelated dirty
paths, no-go paths, and public contracts). Identify existing tests, runtime
proof, review findings, and known limitations.

## 2. Establish the Safety Baseline

If a prior report qualifies for reuse (output-contract `evidence` row), cite its
final-state checks instead of re-running them. Standalone, first re-run that
report's validator; under a parent, its phase receipt suffices. Without such a
report, run the narrowest relevant passing checks before editing and record
exact commands and results. Inspect changed command definitions before
executing them; keep backups and patches outside the repository.

A structural change that could alter behavior with no practical detecting proof
is `BLOCKED` or `SKIPPED`; never guess.

## 3. Classify Candidates

Review every task-owned file and only enough adjacent code to understand it.
Look for removable duplication, branches, needlessly stored derived state,
pass-through wrappers, speculative options, mixed abstraction levels, misplaced
logic, brittle test setup, and artifacts the task made obsolete.

- `APPLIED`: clearly safer or easier to understand, in scope, and provable.
- `SKIPPED`: subjective, churn-heavy, contract-changing, or not worth the risk.
- `BLOCKED`: valuable but needs missing proof, access, or a user decision.

Prefer deletion and existing canonical helpers. Moving the same concepts,
branches, modes, or layers is not simplification.

## 4. Apply and Verify

Apply one coherent simplification at a time; remove only imports, tests,
fixtures, or helpers it made obsolete. After each change:

1. Inspect the exact diff.
2. Confirm only owned paths changed.
3. Run fresh targeted proof proportional to risk.
4. Undo only that exact patch if behavior changes or complexity merely moves.

Run a second cycle only when the first exposes new objective simplification;
stop at subjective polish.

## 5. Report and Decide

Capture `<tmp>/current.json` with the step 1 arguments, re-scaffold with
`--current <tmp>/current.json`, fill the report, and validate:

```bash
python3 <skill>/scripts/validate_report.py --baseline <tmp>/baseline.json --current <tmp>/current.json <tmp>/report.json
```

Never weaken the validator. Keep the report and referenced evidence for caller
re-validation; remove only unused scratch.
