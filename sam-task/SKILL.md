---
name: sam-task
description: "Full pipeline: sam-plan, sam-refine-task, sam-work delivery, closure review/council, and a proposal-only learning audit. Use when the user runs /sam-task or wants plan-to-PR delivery with adversarial closure and captured lessons."
---

# Sam Task

Turn one request into a planned, refined, delivered, adversarially closed, and learning-audited task.

## Non-Negotiable Contract

- Exclusive top pipeline: if this turn also named `sam-goal`, do not run this pipeline; `sam-goal` owns the turn. Precedence: `sam-goal` > `sam-task` > `sam-work` > `sam-orchestrate`. Children this winner requires (`sam-plan`, `sam-refine-task`, `sam-work`, `sam-review`, `sam-council`) remain allowed.
- Phases run strictly in this order and are never skipped; never start one while an earlier one is open, stale, unvalidated, or non-terminal:

| id | skill | accepted terminal |
| --- | --- | --- |
| `plan` | `sam-plan` | `READY_TO_EXECUTE` |
| `refine` | `sam-refine-task` | `HIGH_CONFIDENCE` |
| `work` | `sam-work` | `COMPLETE` |
| `closure` | `sam-review+sam-council` | `CLEAN` |
| `learn` | `sam-task` | `LEARNING_AUDITED` |

- `COMPLETE` only when all five phases are terminal and current for one final head, closure has no material findings, and the validator prints `VALID`.
- Invoking this skill authorizes plan-dir writes, read-only refine analysis, every write `sam-work` authorizes, and in-scope corrections in refine and closure, including re-running invalidated `sam-work` gates. It never authorizes merge, deploy, production data access, destructive cleanup of unrelated user work, or publishing review comments unless a later explicit user request adds that. Child "ask / confirm / publish only when authorized" rules are overridden for the run, exactly as in `sam-work`.
- Autonomous: never pause for permission, confirmation, or mid-run questions. Use repo evidence and the frozen prompt; otherwise `BLOCKED` with exact gaps.
- A child is done only through its terminal plus a validator receipt, never because it was invoked. Never emulate a missing child. Child retry and exhaustion limits stay active; exhaustion is `BLOCKED`, never silent success.
- Preserve unrelated dirty work. Keep secrets out of reports and plan HTML. Planning artifacts never substitute for implementation receipts.

## Routing

You are the controller. Use literal absolute paths; `<SAM_TASK_DIR>` is this skill's directory, and `../` resolves from it. Before delivery mutations confirm the five child skills exist; a missing one is `BLOCKED`.

| You read | When |
| --- | --- |
| `../sam-work/SKILL.md` | at start: its § Phase isolation governs every phase you dispatch |
| `references/closure-loop.md` | closure starts |
| `references/output-contract.md` | closure starts |
| `../sam-council/SKILL.md` | you run a council (plan `COUNCIL_REQUIRED`; closure after review `APPROVE`) |
| `../sam-orchestrate/references/host-runtime-matrix.md`, the active host's advisor row only | an advisor consult |
| `references/behavior-evals.md`, `assets/behavior-eval-scenarios.json` | periodic cross-version evaluation only (scored by `scripts/validate_behavior_eval.py`) |

## Dispatch

- `<STATE>` = `$(git -C <repo> rev-parse --path-format=absolute --git-common-dir)/sam-task/<workflow_id>` (untracked, durable). `PLAN_DIR` (absolute, passed to `sam-plan`): the user- or host-named directory, else `<repo>/plan` if gitignored, else `<STATE>/plan`. `<RUN_DIR>` is `<PLAN_DIR>/run`, or `<STATE>/run` when `PLAN_DIR` is inside the repo and not gitignored.
- Compute `<PROMPT_SHA256>` once (sha256 of the exact prompt bytes); pass it to `sam-plan` (`--prompt-hash`) and to `sam-work` `init --prompt-sha256`.
- Your phase dirs: plan `<PLAN_DIR>` (updated in place), `<RUN_DIR>/refine-<k>/`, `<RUN_DIR>/closure-<n>/review/`, and `<RUN_DIR>/closure-<n>/council/`.
- Flatten work: run the `sam-work` ledger yourself (no `sam-work` worker) and dispatch each of its phases.
- `record` is for `sam-work` phases only. For plan, refine, closure review, and council, get your receipt with `python3 -B <SAM_TASK_DIR>/../<child>/scripts/<validator> <args from validator-args.json; none for plan and council> <report>`: `sam-plan` `validate_plan_report.py`, `sam-refine-task` `validate_report.py`, `sam-review` `validate_review.py`, `sam-council` `validate_council_report.py`.

## Phases

### 1. Plan (`sam-plan`)

- Run on the frozen prompt. Honor complexity routing (`simple` plans stay compact; never force deep ceremony). The light HTML is the human artifact, never the machine gate.
- Advance only on `READY_TO_EXECUTE` with `<PLAN_DIR>/plan-report.json` and a `VALID` freeze receipt (hard core). `NOT_CONFIDENT` or `BLOCKED` → workflow `BLOCKED` with plan residuals.
- `COUNCIL_REQUIRED`: run `sam-council` at controller level on `<PLAN_DIR>/council-packet.md` (you spawn the seats), then dispatch a plan worker with the validated council report path to fold, render, and validate.
- Freeze plan dir, depth, thesis, acceptance, no-go, steps/DoD, and risk flags into the ledger; later phases consume this freeze and never renegotiate the goal silently.

### 2. Refine (`sam-refine-task`)

- Refine the planned strategy and repo evidence, read-only on product code.
- `HIGH_CONFIDENCE` with no open required item → continue. `NOT_CONFIDENT` → revise the plan (re-run `sam-plan` sections) or strategy, then refine again within child limits. `BLOCKED` or exhaustion → `BLOCKED`.
- Record absolute `refine_report_path` = the last run's `<RUN_DIR>/refine-<k>/report.json`; a report only in child scratch space does not count. If refine changes the executable strategy, update the plan artifacts before work.

### 3. Work (`sam-work`, flattened)

- Before handoff record `target.web_surface` from repo evidence: `true` when the repo serves a browser-reachable UI (HTTP/dev server script, web framework entrypoint, routed pages/components, or an existing browser test target); `false` only with concrete evidence of no browser surface; absent, unclear, or unchecked evidence is `true`.
- Run the ledger with the frozen goal, acceptance, invariants, no-go, and plan path. Require `COMPLETE` with a validated `work-report.json`; any other terminal → `BLOCKED` with the work ledger.
- `web_surface: true` makes the Playwright video mandatory (`sam-work` phase 7); `NOT_APPLICABLE`, zero videos, or "video not requested" is `BLOCKED`.

### 4. Closure (`sam-review` then `sam-council`)

Run it per `references/closure-loop.md`.

### 5. Learn (proposal-only)

After closure is `CLEAN`, inspect only the final run's evidence for reusable rules. Emit `LEARNING_AUDITED` even with no candidates. Propose a candidate only when current-run evidence supports a narrow rule, with every candidate field of output contract § Learning object. Never promote a one-off failure, an inference, or stale memory. Keep `writes_performed: []`: never edit repository instructions, a skill, or host memory; promotion needs a separate explicit user action.

## Advisors

- Optional bounded consults inside `plan`, `refine`, or `closure` only; never `work`. At most 3 per run, one focused question each. Never delegate a phase, an implementation, or the task.
- Bind `model` and `effort` here and pass both: from the advisor row (Routing; the matrix's capability ladder, delegation topology, and controller-only rules do not apply here), or the user's exact effort when given.
- The advisor's `## Output` block is an inline consult record, never the final response or the end of the run. Its claims are analysis; a phase closes only on its own child terminal plus validator receipt.
- An advisor failure (CLI, model, effort, or auth unavailable) is a residual, not a blocker; continue on repo evidence.
- Record each consult in `advisor_consults[]` when it happens: `id` (`A-###`, unique), `advisor` (`sam-<runtime>-advisor`), `phase` (`plan`/`refine`/`closure`), `model`, `effort` (`low`/`medium`/`high`/`xhigh`/`max`), `effort_source` (`MATRIX_DEFAULT`/`USER_SPECIFIED`), `question`, `status` (`ANSWERED`/`FAILED`; `FAILED` needs `failure_reason` and a `residuals` entry, never `blockers`), `caller_decision` (`ACCEPTED`/`REJECTED`/`UNRESOLVED`), `decision_reason`, `evidence[]`.

## Completion

At closure start run step 1 to create `<RUN_DIR>/task-report.json`; record each closure iteration and the `learning` object in it as they happen, and re-run step 1 after each edit. After the last mutation:

1. `python3 -B <SAM_TASK_DIR>/scripts/scaffold_task_report.py <RUN_DIR>/task-report.json --workflow-id <workflow_id> --freeze <freeze_path> --refine <refine_report_path> --work <WORK_DIR>/work-report.json --web-surface true|false --web-surface-evidence "<evidence>"`.
2. Fill the remaining `SCAFFOLD:` fields and `status`.
3. `python3 -B <SAM_TASK_DIR>/scripts/validate_task_report.py <RUN_DIR>/task-report.json`; re-run it after every edit. Fix from the validator's error lines and patch the report in place; do not read validator source or rewrite the whole report.

## Final response

At most 15 lines plus the report path, never the JSON: terminal; plan depth/dir and refine result; proposal URL and classification; `web_surface` with evidence and the Playwright + demo video inventory; closure iterations and final review/council statuses; learning candidate count; advisor consults or `none`; final head and validator receipt; exact blockers or open findings.

Maintainers: run `scripts/test_task_harness.py` and `scripts/test_behavior_eval_harness.py` only when changing this skill.
