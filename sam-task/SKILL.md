---
name: sam-task
description: "Run the full task pipeline: sam-plan, sam-refine-task, sam-work delivery, closure review/council, and a proposal-only learning audit. Use when the user runs /sam-task, wants plan-to-PR delivery with final adversarial cleanup, or asks to plan refine implement close findings and capture reusable lessons."
---

# Sam Task

## Purpose

Turn one user request into a planned, refined, delivered, adversarially closed,
and learning-audited task. Orchestrate child skills fail-closed. Do not treat a
child as done because it was invoked—capture and validate its terminal result.

## Non-Negotiable Contract

- Exclusive top pipeline: if this turn also named `sam-goal`, do not run
  this pipeline; `sam-goal` owns the turn. Precedence: `sam-goal` > `sam-task` > `sam-work` > `sam-orchestrate`.
  Children this winner requires (`sam-plan`, `sam-refine-task`, `sam-work`,
  `sam-review`, `sam-council`) remain allowed.
- Run phases in order: `plan` → `refine` → `work` → `closure` → `learn`.
  Never skip.
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
- Learning is proposal-only. Never write a candidate into repository
  instructions, a skill, or host memory without a later explicit user action.
- Advisors are subordinate consults, never a phase and never a gate. An advisor
  answer cannot close a phase, replace a validator receipt, or end this run.

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

For periodic cross-version evaluation, read
[references/behavior-evals.md](references/behavior-evals.md) and use the
versioned catalog in `assets/behavior-eval-scenarios.json`.

Runtime validation:

```bash
SAM_TASK_DIR="<absolute directory containing this SKILL.md>"
python3 -B "$SAM_TASK_DIR/scripts/validate_task_report.py" task-report.json
```

Behavior evaluation is a separate manual or scheduled gate:

```bash
python3 -B "$SAM_TASK_DIR/scripts/validate_behavior_eval.py" \
  behavior-eval-run.json --require-complete-suite
```

## Autonomous execution

Same non-interactive rules as `sam-work`: no `AskUserQuestion`, no “should I
continue?”, no waiting for OS grants mid-flow. Announce progress without
blocking. On ambiguity: evidence first, else `BLOCKED`.

## Advisors (subordinate, non-phase)

The provider-specific advisor skills (`sam-*-advisor`) are optional bounded
consults **inside** a phase. This workflow owns the phase ledger, the terminals,
and the final response at all times.

Rules:

- Allowed only inside `plan`, `refine`, or `closure`. Never inside `work`—that
  phase is owned by the `sam-work` ledger.
- At most 3 consults per run, one focused question each. Never delegate a phase,
  an implementation, or the whole task to an advisor.
- Bind `model` and `effort` in this workflow and pass both to the advisor skill.
  Read **only the advisor row** for the active host from
  `../sam-orchestrate/references/host-runtime-matrix.md`. That document's
  capability ladder, delegation topology, and controller-only rules do **not**
  apply here and must not replace these phases. Use a user-supplied effort
  exactly when the user gives one.
- The advisor's `## Output` block is an inline consult record returned to this
  workflow. It never becomes the final response and never ends the run.
- An advisor failure (CLI, model, effort, or auth unavailable) is a residual, not
  a blocker. Record it and continue the phase on repo evidence.
- Treat every advisor claim as analysis. A phase still closes only on its own
  child terminal plus validator receipt.

Record every consult in `advisor_consults` per the output contract.

## Canonical phases

Every delegated phase inherits the host Token Saver decision through
`RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` when present. Phase workers preserve the
receipt and provider-neutral capability/lane environment across nested spawns,
retries, resumes, and recovery; they never reconstruct or widen admission.
Skills and exact-output evidence remain lossless.

Before each controlled child spawn, record a provider-neutral Subagents row
with `${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill} subagent begin --node
<stable-id>` and close that exact run id with the matching `subagent end
--status <completed|failed|cancelled>`. This bridge is telemetry only: it must
inherit the host Token Saver receipt and must not invent capabilities,
summarize exact output, or call an unobserved child done.

### 1. Plan — `sam-plan`

Run against the frozen user prompt. Honor complexity routing (`simple` plans
stay compact; do not force deep ceremony). Prefer the child's compact freeze;
do not treat HTML as the machine gate (sam-plan still emits light HTML for humans).

- Require validated `READY_TO_EXECUTE` with `$PLAN_DIR/plan-report.json` and a
  freeze validator receipt of `VALID` (hard core only). Light HTML from
  sam-plan is the human artifact, not the machine plan-phase gate.
- Record absolute `plan.freeze_path` for parent re-validation on COMPLETE.
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
- Copy the validated refine report to a durable path (default
  `$PLAN_DIR/refine-report.json`) and record absolute `refine_report_path` for
  parent re-validation on COMPLETE. Temp-only refine reports are not sufficient.

If refine changes the executable strategy, update plan artifacts so work does
not implement a stale thesis.

### 3. Work — `sam-work`

Hand off frozen goal, acceptance, invariants, no-go, and plan path. Run the
full delivery workflow (implement through proposal, browser proof, demo video).
Parent authorization covers every write `sam-work` requires.

- Require child `COMPLETE` with validated `work-report.json`.
- Any other terminal → workflow `BLOCKED` with the work ledger.

Web-surface determination is a receipt, not a judgement call. Before handing off,
decide `target.web_surface` from repository evidence and record that evidence:

- `true` when the repo serves a browser-reachable UI (HTTP/dev server script,
  web framework entrypoint, routed pages/components, or an existing browser
  test target).
- `false` only with concrete evidence of no browser surface. Absent, unclear, or
  unchecked evidence is `true`.

When `target.web_surface` is `true`, Playwright **video is mandatory**:

- Require `sam-work` phase `playwright` = `COMPLETE` with at least one video
  discovered, every discovered video uploaded, and rendered-player readback.
- `NOT_APPLICABLE`, zero videos, or "video not requested" is a `BLOCKED`
  workflow—never a passing run. Do not accept screenshots or a textual claim
  as a substitute.
- A demo video is required on every run regardless of `web_surface`.

Pass `web_surface` into the handoff so the child sets `request.web_system` to the
same value. The task validator cross-checks both and reads the child's
`video_inventory`; `work: COMPLETE` alone is not video proof.

### 4. Closure loop — `sam-review` + `sam-council`

Follow [references/closure-loop.md](references/closure-loop.md).

Each iteration on one frozen head:

1. `sam-review` local-only (no publish, no questions).
2. `sam-council` on delivered thesis + current diff/receipts (`fast` default;
   escalate per council triggers).
3. If both clean → closure `CLEAN`.
4. If material **in-scope** findings (`BLOCKER`/`IMPORTANT` on the frozen
   goal) → smallest in-scope fix, refresh stale `sam-work` gates for the
   new head, then next iteration. `FOLLOW_UP`, suggestions, and newly
   discovered items outside frozen acceptance are parked; they do not
   start another iteration.
5. Stop at max 5 iterations without cleanliness → `BLOCKED`. Fix forward
   on the task branch. Do not replace the branch or worktree because a
   gate failed or the integration base moved.

Both gates must pass on the **same** final head. Review `APPROVE` alone is
insufficient without an accepted council terminal; council pass alone is
insufficient without review `APPROVE`.

### 5. Learn — proposal-only audit

After closure is clean, inspect only the final run's evidence for reusable
rules. Follow [references/phase-contract.md](references/phase-contract.md).

- Emit `LEARNING_AUDITED` even when `candidates` is empty.
- Propose a candidate only when current-run evidence supports a narrow rule.
- Record its scope, destination, sensitivity, and revalidation trigger.
- Do not turn a one-off failure, an inference, or stale memory into a rule.
- Keep `writes_performed: []`. Promotion is outside this workflow and requires
  a separate explicit user action.

## Completion

After the last mutation:

1. Confirm `plan`, `refine`, `work`, `closure`, and `learn` are terminal and
   current.
2. Confirm `target.final_head_sha` matches work + closure proofs and proposal
   remote head when a proposal exists.
3. Re-read the child `video_inventory`: at least one uploaded demo video, plus at
   least one uploaded Playwright video whenever `target.web_surface` is `true`.
4. Write `task-report.json` per the output contract.
5. Validate:

```bash
python3 -B "$SAM_TASK_DIR/scripts/validate_task_report.py" task-report.json
```

`COMPLETE` only if the validator prints `VALID`.

## Final response

Report:

1. `COMPLETE`, `BLOCKED`, or `IN_PROGRESS`
2. Plan depth/dir and refine result
3. Work result (proposal URL, classification)
4. `web_surface` with its evidence, and the Playwright + demo video inventory
   (discovered/uploaded, player readback)
5. Closure iterations used; final review and council statuses
6. Learning candidate count and proposal-only receipt
7. Advisor consults used (count, phase, decision) or `none`
8. Final head and validator receipt
9. Exact blockers or open findings if not complete

This structure is the run's final response. An advisor's output format never
replaces it.

Run `scripts/test_task_harness.py` and
`scripts/test_behavior_eval_harness.py` only when changing this skill.
