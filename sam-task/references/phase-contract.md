# Phase Contract

## Contents

1. Ordered phases
2. Child skill terminals
3. Authority and inheritance
4. Freshness

## Ordered phases

| id | Skill | Accepted terminal |
| --- | --- | --- |
| `plan` | `sam-plan` | `READY_TO_EXECUTE` |
| `refine` | `sam-refine-task` | `HIGH_CONFIDENCE` |
| `work` | `sam-work` | `COMPLETE` |
| `closure` | `sam-review` + `sam-council` loop | `CLEAN` |

Run strictly in order. Do not start a later phase while an earlier one is open,
stale, unvalidated, or non-terminal. Do not emulate a missing child skill.

## Child skill terminals

- `sam-plan`: only `READY_TO_EXECUTE` advances. `NOT_CONFIDENT` and `BLOCKED`
  stop the workflow as `BLOCKED` with exact residuals.
- `sam-refine-task`: only `HIGH_CONFIDENCE` advances. `NOT_CONFIDENT` requires
  plan or strategy correction then another refine pass within child limits.
  Exhaustion or `BLOCKED` blocks the workflow.
- `sam-work`: only validated `COMPLETE` advances. Inherit its full phase ledger
  and external-write authorization for the delivery portion.
- Closure loop: see [closure-loop.md](closure-loop.md). Terminal `CLEAN` only
  when both review and council gates pass on the same final head with zero open
  material items.

## Authority and inheritance

Invoking `sam-task` authorizes:

1. All plan-directory writes required by `sam-plan`.
2. Read-only refine analysis.
3. Every external write `sam-work` authorizes for delivery (task-branch commit,
   push, proposal create/update, Playwright and demo video publication).
4. In-scope corrections during refine and closure loops, including re-running
   invalidated `sam-work` freshness gates after a post-work fix.

It does **not** authorize merge, deploy, production data access, destructive
cleanup of unrelated user work, or publication of review comments unless a
later explicit user request adds that.

Child “ask / confirm / publish only when authorized” language is overridden for
the duration of the parent run, exactly as in `sam-work`.

## Freshness

Any repository mutation after a proof invalidates later head-tied evidence.
After a closure correction:

1. Re-validate implementation proof for the new head.
2. Re-run every stale `sam-work` gate required for that head (at minimum the
   gates the child marks stale; never skip proposal remote-head equality when a
   proposal exists).
3. Only then start the next review+council pair on the new frozen head.

Planning artifacts live under the plan directory and do not substitute for
implementation receipts.
