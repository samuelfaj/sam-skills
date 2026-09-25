---
name: sam-task
description: "Complete a software task from diagnosis through the delivery point the user requested, with evidence proportional to risk. Use when the user invokes /sam-task or asks for end-to-end task execution."
---

# Sam Task

Finish the requested task with the smallest correct change and enough evidence to trust the result. The delivery point comes from the request: it may be a local fix, a proposal, or a verified deployment.

## Non-Negotiable Contract

- Inspect the relevant code and current state before changing it. State the outcome, scope, and observable acceptance criteria briefly. Preserve unrelated work and follow repository instructions.
- Do not invent evidence, weaken tests to obtain a pass, conceal an unmet criterion, or declare an external gate complete from a local result. A plan, green CI, published artifact, and live behavior are different evidence.
- Obtain confirmation for genuinely irreversible actions. Publishing, pushing, deploying, or messaging requires authorization from the user's request or earlier session context; invoking this skill alone does not expand that scope.
- Redact secrets and private data from evidence. Run mutating verification only in an environment whose identity and safety have been established.
- If several delivery skills are named, use one controller and reuse work already done. Do not nest entire pipelines or restart from a moving base just to satisfy a method. For a broad multi-unit goal, sam-goal may be the controller; for an explicitly requested PR/MR, use the relevant sam-work delivery guidance.
- In Distill, let configured Jev routing help choose eligible models, effort, skills, and tools. Keep task and child briefs concrete and bounded; do not pin a model or repeat a host decision with a separate Jev call. If Jev is absent, disabled, fails, or defers, continue with the current agent, ordinary tools, and source-backed judgment. Do not block delivery or relax verification. Treat any Jev suggestion as advisory.

## Execute

1. Trace the behavior or decision path that matters. Reproduce a reported failure when practical, identify its cause, and choose a short implementation path. A plan artifact is useful only when the task's complexity or the user's request warrants it.
2. Implement in small, reviewable changes. Use a specialized skill such as sam-fix-bug, sam-create-feature, sam-review, or sam-council only when its specific method improves this task. Delegate independent work when doing so is faster after coordination and verification; otherwise work directly.
3. Verify the changed behavior with the cheapest reliable evidence for its risk: relevant existing tests first, then a focused new test only if needed; build, browser/device behavior, CI, and post-deploy checks when they are part of the requested outcome. Review the final diff and recheck evidence invalidated by later edits.
4. Reach the requested delivery point. If it includes a proposal, use the existing branch and review the exact remote head and required checks. Record which checks are complete, pending, or externally blocked. Do not require a video, council, HTML plan, learning audit, or phase report merely because this skill was invoked.

## Unblocking and stopping

When a step fails, determine whether the cause is code, environment, access, an external dependency, or an unmade decision. Try a materially different safe route when it can still satisfy the acceptance criteria: inspect another source of truth, isolate the environment, use an existing equivalent tool, narrow to a reproducible case, or fix the newly discovered cause. Repeating the same command or review without new evidence is not progress.

Continue independent work while a dependent step waits. Ask a concise question when a user decision is genuinely required; do not turn routine implementation choices into questions. Stop the blocked path when no credible in-scope route remains. Explain the exact blocker and what would unblock it. Never mark the whole task complete while a requested criterion remains unverified.

## Return

Report the change, the evidence that verifies the requested outcome, the delivery state, and any exact remaining blocker. Keep external approval or release state separate from implementation proof. No fixed report format or validator is required for an ordinary task.

## Legacy report tools

For an existing five-phase report, `references/closure-loop.md` and `references/output-contract.md` explain its historical contract; `scripts/scaffold_task_report.py` and `scripts/validate_task_report.py` rebuild and validate that report. Its COMPLETE applies to that report, not the adaptive task workflow. For archived comparative runs, read `references/behavior-evals.md` and use `scripts/validate_behavior_eval.py` with `assets/behavior-eval-scenarios.json`.
