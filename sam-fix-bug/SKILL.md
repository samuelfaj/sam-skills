---
name: sam-fix-bug
description: "Repair broken existing behavior with exact reproduction, proven root cause, frozen scope, the smallest safe fix, and regression proof. Use for defects, regressions, crashes, wrong results, failed flows, or contract violations; not for new features, plan-only work, or review."
---

# Sam Fix Bug

Fix the defect at its owning boundary with the smallest safe diff. Stay stack-,
provider-, host-, tool-, and model-neutral.

## Non-Negotiable Contract

- Preserve unrelated staged, unstaged, and untracked work byte-for-byte. Never
  reset, checkout, stash, clean, rebase, or broadly restore the workspace.
- Stage, commit, push, publish, open a change request, or message an external
  system only when the user or a parent workflow (e.g. `sam-work`) explicitly
  requested that exact action; parent authorization is enough, never re-ask.
- Child mode (a parent workflow or phase worker invoked you): never ask;
  execute or return `BLOCKED` with receipts. Standalone: ask only blocking
  questions once evidence is exhausted.
- Never patch from the symptom alone: no production edit until the reachable
  failure and its root cause are proven; otherwise return `BLOCKED`.
- A missing mandatory dependency, gate, or proof returns `BLOCKED`; never
  simulate it or invent proof. Stop after two correction cycles unless new
  evidence appears.
- Return any change beyond the frozen goal, contract, or owner boundary to the
  parent as the exact gap (standalone: ask). File or line counts alone neither
  widen nor approve scope; justify each added path against the frozen goal.

## Resources

Use literal absolute paths: `<skill>` is this directory; `<tmp>` is the
parent's phase directory, else scratch outside `<repo>`. Re-read a file only
after compaction or when you cannot quote the needed section; a copy of
`evidence-policy.md` or `risk-lenses.md` already read from sam-create-feature,
sam-refine-task, or sam-simplify-task counts.

| Read | When |
|---|---|
| `references/output-contract.md` | Step 1, before freezing the report |
| `references/evidence-policy.md` | Step 2, before choosing proof |
| `references/risk-lenses.md` | After locating the failure boundary: only lenses the flow reaches; Browser-to-Service in full for browser-to-service failures |

## 1. Freeze

```bash
python3 <skill>/scripts/capture_scope.py --repo <repo> > <tmp>/baseline.json
python3 <skill>/scripts/validate_report.py --scaffold --baseline <tmp>/baseline.json <tmp>/report.json
```

Repeat `--path <repo-relative-path>` only for explicit user scope, with
identical arguments in every capture. Never open `baseline.json` or
`current.json`; the capture's stderr line summarizes them. Rewind (this skill
already wrote a report for this task): capture and scaffold in a fresh `<tmp>`
(under a parent, the handoff's phase dir) with `--from <prior report>`; never
move, edit, or overwrite the prior report.

Inspect relevant callers, routes, handlers, state, persistence, tests, logs,
schemas, and configuration, then freeze into the report: `bug` (observed and
expected behavior, affected flow), every `intent` field (goal: the business
rule or contract; must_not_change: behavior and no-go paths), initial owned
paths, the required `gates` (`NOT_RUN` until run), and publication
authorization (`external_actions[].requested`).

## 2. Reproduce and Prove Root Cause

Reproduce at the narrowest layer that still exercises the reported failure.
Trace the causal chain; separate root cause from downstream symptoms.

Record `reproduction.status`:

- `REPRODUCED`: observed through a meaningful test or runtime path.
- `PROVEN_BY_CONTRACT`: no direct execution, but code and an authoritative
  contract prove the violation.
- `BLOCKED`: evidence cannot separate a defect from environment, data,
  configuration, or external state.

## 3. Regression Proof and Minimal Fix

- Prefer a `DIFFERENTIAL` test that fails on the defect and passes after the
  fix; otherwise `ALTERNATIVE_PROOF` per the evidence policy.
- Keep public contracts unless the proven defect is the contract. No unrelated
  refactors, speculative abstractions, duplicated rules, sensitive-data
  exposure, N+1 work, or widened payloads.
- Map scenarios per the evidence policy, including adjacent regressions.

## 4. Validate and Gate

- Run the narrowest safe checks first, then broader ones proportional to risk;
  inspect changed command definitions before executing them. If a gate changes
  code, rerun the affected proof.
- Run applicable local review and coverage gates for runtime changes, and
  browser proof only for impacted browser flows. A gate the parent runs itself
  on the final head (e.g. `sam-work` review, coverage, or browser proof) is
  recorded parent-owned (output-contract `gates` row) and skipped;
  `behavior_proof` is never parent-owned.

## 5. Report and Decide

Capture `<tmp>/current.json` with the step 1 arguments, re-scaffold with
`--current <tmp>/current.json`, fill the report, and validate:

```bash
python3 <skill>/scripts/validate_report.py --baseline <tmp>/baseline.json --current <tmp>/current.json <tmp>/report.json
```

Never weaken the validator. Keep the report and evidence the caller needs;
remove only unused scratch.
