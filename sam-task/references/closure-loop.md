# Closure Loop

After `sam-work` is `COMPLETE`, iterate until both gates are clean on one final head, or stop fail-closed. Neither gate substitutes for the other.

## Iteration (one frozen head)

1. **Adversarial ledger pass** (≤1 turn, contract-only): check acceptance criteria without step/proof linkage in the freeze, material assumptions without probe or acceptance reason, open findings without named correction receipts, and evidence hedges labeled as facts. Record results in residuals; skip with an explicit residual reason when cost exceeds value. It is not a phase or terminal and never alone changes `CLEAN`.
2. **Review:** `sam-review`, branch mode against the frozen base, local-only. When the `sam-work` ledger's review report has the identical key (`sam-review`, branch mode, frozen base, this head), as in iteration 1 and after every fix's ledger refresh, cite it as `review_reused_from` and re-run only its validator. Any key difference means a fresh review (`review_report_path`) in `<RUN_DIR>/closure-<n>/review/`.
3. **Council:** only after review `APPROVE` on that head; otherwise record `council_status: NOT_RUN`. `sam-council` falsifies the delivered thesis (frozen goal, plan thesis, current diff and receipts), profile `fast` by default, `full` when council triggers fire (security, migration, irreversible, production-critical). Its report's `packet_head` must be this iteration's head.

## Pass criteria

| Gate | Required terminal | Extra |
| --- | --- | --- |
| Review | `APPROVE` | Zero accepted `BLOCKER`/`IMPORTANT`; no required test gap |
| Council | `TRIAGE_PASS` (fast) or `APPROVED` / `APPROVED_WITH_CONDITIONS` (full) | No open supported blocker/high; post-delivery highs must be mitigated |

`COMMENT_ONLY`, `CHANGES_REQUIRED`, `REVISE`, unresolved `ESCALATE_TO_FULL`, `BLOCKED`, and unvalidated reports never close the loop. `APPROVED_WITH_CONDITIONS` closes only when every condition is owned and mitigated in the diff with proof, or is a non-blocking residual explicitly listed and accepted by the frozen owner boundary of the original task, recorded before plan freeze (never invented mid-loop).

## Corrections

Only accepted in-scope `BLOCKER`/`IMPORTANT` findings on the frozen goal, or council-supported blockers/highs that break frozen acceptance, force a fix. `FOLLOW_UP`, suggestions, and newly discovered items outside frozen acceptance are parked on the findings ledger and never start another iteration. Never "approve away" a supported in-scope finding to force exit.

When a gate fails:

1. Merge findings into a deduplicated material set (by failure mechanism).
2. Apply the smallest in-scope fix through the `sam-fix-bug` or `sam-create-feature` contract (keep the original classification unless the finding proves a bug in new code; keep task ownership).
3. Record correction receipts and re-run validators/tests for the change. A finding open in iteration N and absent in N+1 must be named in iteration N `correction_receipts` (normalized substring match).
4. Refresh the `sam-work` ledger for the new head: record the fix's implementation report (`finalize` anchors it at the fix commit) and re-run every stale gate per `sam-work` § Completion (never skip proposal remote-head equality when a proposal exists). The refreshed review is the next iteration's cited review.
5. Only then start the next iteration on the new frozen head.

Fix forward on the same task branch: keep the branch and prior receipts for unchanged files; never create a new worktree, discard the delivered head, or rebuild from a moved integration ref because a gate failed or the base moved.

## Stop conditions

- **Success:** one iteration where both gates pass on `final_head_sha` → closure `CLEAN`.
- **Cap:** max 5 iterations; exhaustion without cleanliness → workflow `BLOCKED` with the open findings ledger.
- **Child stop:** unrecoverable review or council `BLOCKED`, or child retry limits exhausted without new evidence → `BLOCKED`.
- **Scope escape:** `STOP_AND_ESCALATE` or out-of-scope redesign → `BLOCKED` with the exact decision needed; never silently expand the task.
