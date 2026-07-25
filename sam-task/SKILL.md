---
name: sam-task
description: "Run the full task pipeline: sam-plan, sam-refine-task, sam-work delivery, then a closure loop of sam-review plus sam-council that fixes material findings until both gates are clean on one head. Use when the user runs /sam-task, wants plan-to-PR delivery with final adversarial cleanup, or asks to plan refine implement and close all review/council issues."
---

# Sam Task

## Purpose

Turn one user request into a planned, refined, delivered, and adversarially
closed task. Orchestrate child skills fail-closed. Do not treat a child as done
because it was invoked—capture and validate its terminal result.

## Non-Negotiable Contract

- Run phases in order: `plan` → `refine` → `work` → `closure`. Never skip.
- Never report `COMPLETE` while any phase is missing, stale, unvalidated, or
  non-terminal, or while the closure loop still has material findings.
- Invoking this skill authorizes plan-dir writes, task-branch delivery writes
  allowed by `sam-work`, and in-scope corrections in refine/closure loops. It
  does not authorize merge, deploy, production data access, or destructive
  cleanup of unrelated user work.
- Autonomous: never pause for permission, confirmation, or mid-run questions.
  Prefer repo evidence and frozen prompt; otherwise `BLOCKED` with exact gaps.
- Do not emulate missing children. Read each child `SKILL.md` and its required
  resources when that phase starts.
- Preserve unrelated dirty work. Keep secrets out of reports and plan HTML.
- Child retry/exhaustion limits remain active; exhaustion is `BLOCKED`, never
  silent success.

## Required skills

Before mutating the target repository for delivery, ensure these exist and
follow them when their phase runs:

1. `../sam-plan/SKILL.md`
2. `../sam-refine-task/SKILL.md`
3. `../sam-work/SKILL.md` (and every skill it requires)
4. `../sam-review/SKILL.md`
5. `../sam-council/SKILL.md`

Also read:

- [references/phase-contract.md](references/phase-contract.md)
- [references/closure-loop.md](references/closure-loop.md)
- [references/output-contract.md](references/output-contract.md)

Runtime validation:

```bash
SAM_TASK_DIR="<absolute directory containing this SKILL.md>"
python3 -B "$SAM_TASK_DIR/scripts/validate_task_report.py" task-report.json
```

## Autonomous execution

Same non-interactive rules as `sam-work`: no `AskUserQuestion`, no “should I
continue?”, no waiting for OS grants mid-flow. Announce progress without
blocking. On ambiguity: evidence first, else `BLOCKED`.

## Canonical phases

### 1. Plan — `sam-plan`

Run against the frozen user prompt. Honor complexity routing (`simple` plans
stay compact; do not force deep ceremony). Prefer the child's compact freeze;
do not require an HTML pack unless the user asked for one.

- Require validated `READY_TO_EXECUTE` with `$PLAN_DIR/plan-report.json` and a
  freeze validator receipt of `VALID` (hard core only). HTML pack is optional
  and is **not** a plan-phase gate.
- `NOT_CONFIDENT` or `BLOCKED` → workflow `BLOCKED` (record plan residuals).
- Freeze plan dir, depth, thesis, acceptance criteria, no-go, steps/DoD, and
  risk flags into the task ledger from the plan report. Downstream phases
  consume this freeze; they do not renegotiate goal silently.

### 2. Refine — `sam-refine-task`

Refine the **planned strategy** (and repo evidence), still read-only on product
code.

- `HIGH_CONFIDENCE` with no open required item → continue.
- `NOT_CONFIDENT` → revise the plan (re-run `sam-plan` sections as needed) or
  strategy notes, then refine again within child limits.
- `BLOCKED` or exhaustion → workflow `BLOCKED`.

If refine changes the executable strategy, update plan artifacts so work does
not implement a stale thesis.

### 3. Work — `sam-work`

Hand off frozen goal, acceptance, invariants, no-go, and plan path. Run the
full delivery workflow (implement through proposal, browser proof when
applicable, demo video). Parent authorization covers every write `sam-work`
requires.

- Require child `COMPLETE` with validated `work-report.json`.
- Any other terminal → workflow `BLOCKED` with the work ledger.

### 4. Closure loop — `sam-review` + `sam-council`

Follow [references/closure-loop.md](references/closure-loop.md).

Each iteration on one frozen head:

1. `sam-review` local-only (no publish, no questions).
2. `sam-council` on delivered thesis + current diff/receipts (`fast` default;
   escalate per council triggers).
3. If both clean → closure `CLEAN`.
4. If material findings → smallest in-scope fix, refresh stale `sam-work`
   gates for the new head, then next iteration.
5. Stop at max 5 iterations without cleanliness → `BLOCKED`.

Both gates must pass on the **same** final head. Review `APPROVE` alone is
insufficient without an accepted council terminal; council pass alone is
insufficient without review `APPROVE`.

## Completion

After the last mutation:

1. Confirm `plan`, `refine`, `work`, and `closure` are terminal and current.
2. Confirm `target.final_head_sha` matches work + closure proofs and proposal
   remote head when a proposal exists.
3. Write `task-report.json` per the output contract.
4. Validate:

```bash
python3 -B "$SAM_TASK_DIR/scripts/validate_task_report.py" task-report.json
```

`COMPLETE` only if the validator prints `VALID`.

## Final response

Report:

1. `COMPLETE`, `BLOCKED`, or `IN_PROGRESS`
2. Plan depth/dir and refine result
3. Work result (proposal URL, classification)
4. Closure iterations used; final review and council statuses
5. Final head and validator receipt
6. Exact blockers or open findings if not complete

Run `scripts/test_task_harness.py` only when changing this skill.
