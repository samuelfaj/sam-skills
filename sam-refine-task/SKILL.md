---
name: sam-refine-task
description: "Stress-test and revise a technical strategy without implementing it, returning a validated confidence decision. Use for implementation plans, debugging hypotheses, migrations, rollouts, releases, test strategies, or architecture approaches that need hardening before execution."
---

# Sam Refine Task

## Non-Negotiable Contract

- Deliver an executable, factually defensible strategy, neutral on stack,
  provider, host, tool, and model.
- Never expose secrets, credentials, private data, or sensitive paths in plans,
  commands, reports, or returned evidence.
- Never edit, stage, commit, reset, checkout, stash, clean, publish, deploy, or
  mutate local or external state. Preserve unrelated dirty work byte-for-byte.
- Separate facts, assumptions, and unknowns; never raise confidence because a
  plan sounds plausible.
- Keep risk analysis inside the stated goal unless an adjacent risk directly
  invalidates the strategy.
- Stop after two refinement passes unless new evidence appears.
- Never weaken the validator to force confidence.

## Resources

| Read | When |
| --- | --- |
| `references/output-contract.md` | Step 1, before filling the report |
| `references/risk-lenses.md` | Step 3 |
| `references/evidence-policy.md` | When recording evidence, scenarios, behavior proof, or gates |

Identical sibling copies of the last two count as read.
Re-read a file only after compaction or when you cannot quote what you need.
Use literal absolute paths (`<skill-dir>` is this SKILL.md's absolute
directory) and one fresh scratch directory per run, outside the repository.
Under a parent, `<scratch>` is the handoff's phase directory and
`<scratch>/report.json` is its report path (if none,
`<PLAN_DIR>/refine-report.json`).

## 1. Freeze

```bash
python3 -B <skill-dir>/scripts/capture_scope.py --repo <repo> > <scratch>/baseline.json
python3 -B <skill-dir>/scripts/validate_report.py --scaffold --baseline <scratch>/baseline.json <scratch>/report.json
```

Add `--path <repo-relative-path>` (repeatable) only for explicit scope,
identically in every capture. Fill the scaffolded report in place as you work.
Freeze the report `intent` plus non-goals, proposed steps, expected outcome,
success criteria, constraints, no-go scope, required evidence, and unresolved
decisions.

Under a parent, never ask: decide from available evidence or return
`BLOCKED`/`NOT_CONFIDENT` with exact unknowns. Standalone, ask one concise
blocking question only when the strategy is too ambiguous to evaluate and
repository evidence cannot resolve it.

## 2. Ledger

Claims are `FACT` (code, tests, logs, runtime evidence, authoritative docs, or
a recorded user decision), `ASSUMPTION` (plausible, unverified), or `UNKNOWN`
(missing or contradictory evidence); mark material claims. Inspect only what
tests the strategy (code, tests, configuration, schemas, deployment
definitions, issue text, review history, safe runtime evidence); never treat
unavailable external state as known.

Given a `plan-report.json`, copy it to `<scratch>/plan-snapshot.json`, cite the
copy as `plan_report`, and reuse its FACTs instead of re-deriving them: re-read
each locator you rely on (re-run a `command:` locator; a `decision:` locator
must name a recorded decision) and record `plan_ref` evidence saying what you
saw. Your re-read, not the plan's status, is the guarantee. Spend new effort
where the plan was silent.

## 3. Loopholes

Apply only the `risk-lenses.md` lenses the strategy reaches, plus
requirements, ownership, failure handling, operational dependencies,
environment drift, test seams, and observability as they apply. Record at
least one adversarial candidate and cover the negative, permission, and
recovery paths the strategy reaches. Each loophole states the failure mode and
evidence, impact on the goal, smallest correction, required verification, and
status. Prefer deleting steps, branches, modes, abstractions, or manual
coordination; add no speculative process that closes no proven loophole.

## 4. Verify and Decide

Map every material claim to a proof command, test, runtime check, artifact,
rollback exercise, or explicit user decision. Run a second pass only if the
first materially changes the strategy or new evidence appears; recheck facts,
loopholes, scope, recovery, and proof mapping, editing the report in place and
bumping `scope.cycle`. Decide per the contract `decision` row.

To refine again from a prior refinement report, first capture the tree as in
step 1. If its `fingerprint` equals the prior report's
`target.baseline_fingerprint`, edit the report and bump `scope.cycle`, reusing
the prior baseline by path; otherwise that capture is the new baseline: re-run
the step 1 scaffold with `--from <prior report>` (it bumps the cycle). Under a
parent, never edit, move, or overwrite a report or capture the parent already
cited: work at the handoff's new report path (copy the prior report there to
edit it).

## 5. Validate

```bash
python3 -B <skill-dir>/scripts/capture_scope.py --repo <repo> > <scratch>/current.json
python3 -B <skill-dir>/scripts/validate_report.py --baseline <scratch>/baseline.json --current <scratch>/current.json <scratch>/report.json
```

For a `target` or `file_coverage` error, re-run the step 1 scaffold with
`--current <scratch>/current.json` and validate again. Fix from the
validator's error lines and patch the report in place; do not read validator
source or rewrite the whole report.

Never move a file the report cites; remove only unused scratch.

## Return

Child mode (a parent or phase worker invoked this skill): the final message is
exactly this block.

```
RESULT sam-refine-task <HIGH_CONFIDENCE|NOT_CONFIDENT|BLOCKED>
report: <absolute report path>
validator: <exact last line of the validator output>
head: <target.current_head_sha> fingerprint: <target.current_fingerprint>
open: <n>
- <one line per decision.remaining item, max 10>
```

Standalone: at most 15 lines (decision, refined strategy, key facts, removed
and remaining assumptions, loopholes and corrections, verification plan,
blockers, residual risk, report path). Never paste the JSON.
