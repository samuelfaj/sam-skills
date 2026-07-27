# Closure Loop

## Contents

1. Purpose
2. Gate pair
3. Pass criteria
4. Correction rules
5. Stop conditions

## Purpose

After `sam-work` reports `COMPLETE`, hunt residual defects with independent
code review and plan/change falsification. Fix what is material. Repeat until
both gates are clean on one final head—or stop fail-closed.

## Gate pair

Each closure iteration runs **both** skills against the same frozen head:

1. `sam-review` — local/branch/head target only; no publication; no questions.
2. `sam-council` — falsify the delivered thesis (frozen goal + plan thesis +
   current diff/receipts). Default profile `fast`; use `full` when council
   triggers fire (security, migration, irreversible, production-critical).

Do not treat one gate as a substitute for the other. Review finds code/diff
defects; council finds weak assumptions, failure modes, and false readiness.

## Pass criteria

An iteration is clean only when all hold:

| Gate | Required terminal | Extra |
| --- | --- | --- |
| Review | `APPROVE` | Zero accepted `BLOCKER`/`IMPORTANT`; no required test gap |
| Council | `TRIAGE_PASS` (fast) or `APPROVED` / `APPROVED_WITH_CONDITIONS` (full) | No open supported blocker/high; conditions owned and closed or explicit owner accept recorded before plan freeze only—post-delivery highs must be mitigated |

`COMMENT_ONLY`, `CHANGES_REQUIRED`, `REVISE`, `ESCALATE_TO_FULL` (unresolved),
`BLOCKED`, and unvalidated reports never close the loop.

`APPROVED_WITH_CONDITIONS` closes only when every condition is mitigated in the
diff with proof, or is non-blocking residual explicitly listed and accepted by
the frozen owner boundary from the original task (not invented mid-loop).

## Correction rules

When either gate fails:

1. Merge findings into a deduplicated material set (by failure mechanism).
2. Apply the smallest in-scope fix via `sam-fix-bug` or `sam-create-feature`
   contracts (match original classification unless the finding proves a bug in
   new code—still keep task ownership).
3. Record correction receipts and re-run validators/tests for the change.
4. Refresh stale `sam-work` gates for the new head (see phase-contract).
5. Start a new closure iteration with a new review bundle and new council run.

Never “approve away” a supported finding to force exit. Suggestions alone do
not force another iteration; blockers and importants do.

## Stop conditions

- **Success:** one iteration where both gates pass on `final_head_sha` →
  closure status `CLEAN`.
- **Cap:** default max `5` closure iterations. Exhaustion without cleanliness →
  workflow `BLOCKED` with open findings ledger.
- **Child stop:** if review or council returns unrecoverable `BLOCKED`, or
  child retry limits exhaust without new evidence → workflow `BLOCKED`.
- **Scope escape:** `STOP_AND_ESCALATE` or out-of-scope redesign → `BLOCKED`
  with the exact decision needed; do not silently expand the task.

## Adversarial ledger pass (contract-only)

Before the first review of a closure iteration (budget ≤1 turn), run a self-check
over structural gap categories and record results in residuals (not a new phase
or terminal):

1. Acceptance criteria without step/proof linkage in the freeze
2. Material assumptions without probe or acceptance reason
3. Open findings without named correction receipts
4. Evidence claims that look like hedges labeled as facts

Skip with an explicit residual reason when cost exceeds value. This pass never
alone changes `CLEAN`; review + council gates still own the terminal.

