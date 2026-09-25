---
name: sam-goal
description: "Finish a multi-step software goal with adaptive decomposition, minimal implementation, and direct verification. Use when the user invokes /sam-goal or asks to complete a broader engineering outcome."
---

# Sam Goal

Finish every outcome the user asked for with the smallest sound implementation. Treat the goal as complete when its acceptance criteria have current evidence, rather than when a prescribed number of files, workers, or reports exists.

## Non-Negotiable Contract

- Understand the request and trace the relevant implementation before changing it. Identify observable outcomes and constraints; preserve unrelated work and follow repository instructions.
- Do not claim that a worker's report, a passing unit test, a plan, or a published artifact proves behavior it did not exercise. Verify the integrated result yourself where practical.
- Do not add speculative dependencies, layers, or configuration. A new dependency is acceptable when it is necessary for the current goal and the existing code or platform cannot reasonably do the job; explain why.
- Respect authorization and reversibility. Ask before genuinely irreversible actions, and perform external writes only when the request or session authorizes them.
- Protect secrets and private data in evidence; verify the target environment before any mutating check.
- Use one controller if multiple workflow skills are named. Reuse completed evidence; do not run a second full pipeline over the same work.
- In Distill, let configured Jev routing help with eligible skill, tool, model, and effort choices. Give native workers bounded outcomes and evidence without pinning a model or effort unless the user or a concrete requirement calls for it. If Jev is absent, disabled, fails, or defers, make those choices from the task and repository evidence using the current agent and host defaults; keep working. Verify the integrated outcome regardless of how it was routed.

## Work

1. Break the goal into the fewest meaningful outcomes. Order dependent work; delegate only independent units when the expected time saved exceeds briefing, merge, and verification cost. Work directly when that is simpler.
2. For each outcome, inspect the code path and, for a bug, correct the owning cause across affected callers. Choose the smallest correct change, implement it, and verify its behavior. Use existing tests first. Add a focused test only for meaningful behavior that existing checks miss. Apply additional review, browser/device checks, security checks, or production proof when the outcome's risk warrants them.
3. Integrate the units and check the final state against the original goal. Recheck only proofs affected by later changes. Resolve in-scope defects found during review; park unrelated findings with a clear note.

## Unblocking and stopping

Classify a failure before retrying. Seek a different evidence-backed route when possible: inspect a caller or authoritative system, isolate a broken toolchain, use an existing equivalent capability, reduce the reproduction, or correct the actual defect. Retry only when something material changed or a distinct hypothesis is being tested. If no credible in-scope route remains, keep completed independent outcomes and report the exact remaining dependency or decision. Ask for a required user choice after inspecting what can be resolved autonomously.

Finish when the requested outcomes are verified at the requested delivery point. If a human approval, unavailable service, or other external gate remains, distinguish the completed work from that gate; do not loop indefinitely or call it fulfilled.

## Return

State what changed, what evidence verifies each requested outcome, and the exact remaining work, if any. An ordinary run needs no gate files or JSON report.

## Optional structured ledger

When the user explicitly wants a machine-readable gate ledger or a large delegation needs durable coordination, read `references/gates.md`, `references/orchestration.md`, and `references/output-contract.md`; use `scripts/scaffold_goal_dir.py`, `scripts/check_gates.py`, `scripts/check_ledger.py`, `scripts/detect_host.py`, and `scripts/validate_goal_report.py` as applicable. `references/ladder.md` and `references/method.md` describe the older fixed method; consult them only for an explicitly requested tree/intensity run. The ledger's validator proves its own format, not the broader goal by itself.
