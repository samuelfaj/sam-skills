---
name: sam-create-feature
description: "Implement a new capability end-to-end with frozen scope, test-first delivery, behavior proof, and validated evidence; publish only on request. Use for new screens, endpoints, integrations, data flows, commands, or other functional additions; not for bug fixes, plan-only work, or review."
---

# Sam Create Feature

Deliver the requested capability with the smallest safe diff. Stay stack-,
provider-, host-, tool-, and model-neutral.

## Non-Negotiable Contract

- Preserve unrelated staged, unstaged, and untracked work byte-for-byte. Never
  reset, checkout, stash, clean, rebase, or broadly restore the workspace.
- Stage, commit, push, publish, open a change request, or message an external
  system only when the user or a parent workflow (e.g. `sam-work`) explicitly
  requested that exact action; parent authorization is enough, never re-ask.
- Child mode (a parent workflow or phase worker invoked you): never ask;
  execute or return `BLOCKED` with receipts. Standalone: ask only questions
  whose answers materially change product behavior, security, data, public
  contracts, or scope.
- Inspect changed commands, hooks, build definitions, and configuration before
  executing them. Never expose secrets in artifacts, commands, or output.
- A missing mandatory dependency, gate, or proof returns `BLOCKED`; never
  simulate it or turn missing proof into a pass. Stop after two correction
  cycles unless new evidence appears.
- Return any change beyond the frozen goal, contract, or owner boundary to the
  parent as the exact gap (standalone: ask). File or line counts alone neither
  widen nor approve scope; justify each added path against the frozen goal.

## Resources

Use literal absolute paths: `<skill>` is this directory; `<tmp>` is the
parent's phase directory, else scratch outside `<repo>`. Re-read a file only
after compaction or when you cannot quote the needed section; a copy of
`evidence-policy.md` or `risk-lenses.md` already read from sam-fix-bug,
sam-refine-task, or sam-simplify-task counts.

| Read | When |
|---|---|
| `references/output-contract.md` | Step 1, before freezing the report |
| `references/evidence-policy.md` | Step 2, before planning proof |
| `references/risk-lenses.md` | After discovering affected boundaries: only lenses the flow reaches |

## 1. Freeze

```bash
python3 <skill>/scripts/capture_scope.py --repo <repo> > <tmp>/baseline.json
python3 <skill>/scripts/validate_report.py --scaffold --baseline <tmp>/baseline.json <tmp>/report.json
```

Repeat `--path <repo-relative-path>` only for user-scoped paths, with identical
arguments in every capture. Never open `baseline.json` or `current.json`; the
capture's stderr line summarizes them. Rewind (this skill already wrote a
report for this task): capture and scaffold in a fresh `<tmp>` (under a parent,
the handoff's phase dir) with `--from <prior report>`; never move, edit, or
overwrite the prior report.

Study relevant code, tests, contracts, schemas, migrations, and conventions,
then freeze into the report: every `intent` field (goal: goal and target user;
must_not_change: behavior and no-go paths), acceptance criteria as
`requirements`, initial owned paths, and publication authorization
(`external_actions[].requested`).

## 2. Classify Risk and Plan Proof

Risk is `LIGHT`, `STANDARD`, or `HIGH_RISK` by affected behavior, not task
size; authentication, authorization, money, destructive data, concurrency,
public contracts, migrations, integrations, deployment, and critical user flows
are high risk.

Map scenarios per the evidence policy, including user states; link each
required scenario to a practical proof seam and record the required proof as
`gates` (`NOT_RUN` until run). Where a meaningful seam exists, work test-first
(`RED_GREEN`):

1. Add the smallest test that expresses the requirement and why it matters.
2. Prove it fails for the missing behavior.
3. Implement the smallest production change.
4. Prove it passes.

Otherwise use `ALTERNATIVE_PROOF` per the evidence policy. Never add a cosmetic
test solely to satisfy process.

## 3. Implement Within the Frozen Contract

- Follow existing architecture, naming, types, and dependency patterns; keep
  logic in the owning layer.
- Keep public compatibility unless a confirmed requirement changes it. No
  speculative abstractions, unrelated cleanup, N+1 work, unbounded payloads,
  sensitive-data exposure, or duplicated business rules.
- Add to `current_owned_paths` only files the feature requires.

## 4. Prove and Gate

- Run the narrowest safe checks first, then broader ones proportional to risk.
  If a gate changes code, rerun affected tests and any review this skill ran.
- Run applicable dependent gates with their actual local instructions: require
  local code review and coverage analysis for runtime changes, and browser
  proof only for impacted browser flows. A gate the parent runs itself on the
  final head (e.g. `sam-work` review, coverage, or browser proof) is recorded
  parent-owned (output-contract `gates` row) and skipped; `behavior_proof` is
  never parent-owned.

## 5. Report and Decide

Capture `<tmp>/current.json` with the step 1 arguments, re-scaffold with
`--current <tmp>/current.json`, fill the report, and validate:

```bash
python3 <skill>/scripts/validate_report.py --baseline <tmp>/baseline.json --current <tmp>/current.json <tmp>/report.json
```

Never weaken the report or validator to force completion. Keep the report and
evidence the caller needs; remove only unused scratch.
