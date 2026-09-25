---
name: sam-orchestrate
description: "Coordinate independent software work with native delegation, clear ownership, and verified integration. Use when the user explicitly requests orchestration or parallel agents."
---

# Sam Orchestrate

Finish the requested outcome with the fewest useful workers. Start with one execution thread; delegate only independent work that will save more time than briefing, integration, and verification cost.

## Non-Negotiable Contract

- Exclusive top pipeline: when the request names sam-goal, sam-task, or sam-work, that skill controls delivery. Contribute delegation only where it helps; do not run a second complete workflow.
- Inspect the repository and user constraints before splitting work. Preserve unrelated changes, assign one owner per writable path, and keep dependent writes ordered or isolated.
- Give each worker a bounded objective, relevant facts, writable scope, no-go scope, and observable proof. Workers must not overwrite other active work. Reuse their findings and check material claims against the actual artifacts.
- Use the current host's native subagents and default runtime when available. In Distill, leave model and effort unpinned so configured Jev can route eligible choices. If Jev is absent, disabled, fails, or defers, continue with the current agent and host defaults. Pin only for an explicit user choice or a demonstrated task constraint.
- Jev's typed judgments are advisory. The controller owns authorization, acceptance criteria, integration, and verification. Confirm the final behavior with the cheapest reliable checks for its risk; distinguish local tests, CI, publication, and live behavior.
- Pass an existing `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` to a controlled child unchanged when the native path requires it. Never reconstruct or widen it, pass secrets or full transcripts in it, or claim savings without measured accepted-task evidence.

## Execute

1. Identify the smallest set of independent units. Work directly when delegation adds overhead or native subagents are unavailable. For parallel writes, use disjoint paths or isolated worktrees and one integration owner.
2. Launch only useful workers through the current host. Use a separate reviewer when risk or an unresolved finding warrants independent review. Leave model and effort unset when host routing is available. Keep prompts short and source-backed.
3. Integrate results, inspect the actual diff, and rerun only checks affected by integration or later corrections. Challenge unsupported worker claims and fix material in-scope defects. Review depth follows risk, not a fixed round count.
4. Reach the user's requested delivery point and report the exact remaining external gate, if any. Do not infer completion from a child report or a validator alone.

## Unblocking

Fix forward on the current work and evidence. Diagnose whether a failure comes from code, environment, access, or an unmade decision; try a materially different safe route. Repeating the same failed spawn, check, or review without new evidence is not progress. Continue independent work while one dependency waits. Ask for a user decision only when it is genuinely required after inspecting what can be resolved locally.

## Return

State the integrated change, the checks that verify it, and the exact pending or blocked requirement. An ordinary run needs no fixed DAG, model matrix, review count, or JSON report.

## Optional structured report

If the user requests the historical orchestration ledger, read `references/prompt-contract.md`, `references/routing-policy.md`, `references/host-runtime-matrix.md`, and `references/output-contract.md`. Before editing, capture its baseline with `scripts/scaffold_report.py --freeze-out`; then use that script and `scripts/validate_orchestration.py` for the report. Its runtime matrix and validator describe the legacy report format; they do not set the default execution policy. Run `scripts/test_orchestration_harness.py` when changing those report tools.
