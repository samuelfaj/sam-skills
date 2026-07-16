---
name: sam-orchestrate
description: "Coordinate complex work as a controller-only orchestrator using cost- and risk-aware capability routing, explicit task dependencies and ownership, skeptical proof verification, and an independent review gate. Use when the user asks for delegated execution, parallel agents, controller-only operation, or rigorous multi-agent delivery."
---

# Sam Orchestrate

Coordinate execution without implementing task artifacts directly. Remain
provider-, model-, host-, and stack-neutral.

## Non-Negotiable Contract

- Keep the main agent controller-only. Delegate production code, tests,
  documentation, migrations, and other task artifacts.
- Permit direct main-agent work only for task decomposition, agent coordination,
  result inspection, proof reruns, conflict integration, and final reporting.
- Give every worker one explicit owner boundary, writable scope, no-go scope,
  dependencies, pass criteria, and required proof.
- Tell every worker that other agents may share the workspace and that it must
  not revert or overwrite unrelated work.
- Treat every returned claim as unverified until the controller checks its
  artifact, scope, and proof.
- Never route by a named provider or model. Route by capability and task risk.
- If delegation is unavailable, stop before execution and report the exact
  blocker. Do not silently abandon controller-only mode.
- Never expose secrets in prompts, reports, commands, or evidence.

## Resource Routing

- Read [references/routing-policy.md](references/routing-policy.md) before
  classifying work or selecting a capability class.
- Read [references/prompt-contract.md](references/prompt-contract.md) before
  spawning the first worker.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting the orchestration report.
- Run `scripts/validate_orchestration.py` before declaring completion.

## 1. Freeze Goal and Constraints

Record before delegation:

- Goal and observable success criteria.
- Explicit constraints and no-go surfaces.
- Repository or system boundaries.
- Required evidence and unsafe operations.
- User decisions that must not be inferred.

Classify the task as `T0`, `T1`, `T2`, or `T3` using the routing policy. Record
risk flags, expected artifact classes, and an initially empty changed-file
manifest before building the task graph.

## 2. Build the Task DAG

Create the smallest useful directed acyclic graph. Each node must contain:

- Stable task ID and kind: `EXECUTION`, `ORCHESTRATION`, or `REVIEW`.
- Neutral owner ID and capability: `LIGHT`, `STANDARD`, `DEEP`, or `REVIEWER`.
- Dependencies.
- One objective, explicit no-go items, and proof requirements.
- Writable paths or an explicitly read-only scope.
- Artifact classes for writable work.
- A direct-action reason only for controller-owned writable integration work.
- Status, blocker provenance, and evidence IDs.

Use neutral owner IDs: `worker-N` for execution, `controller-N` for
orchestration, and `reviewer-N` for review. Never put a provider, model, host,
vendor, or agent product name in an owner identity.

Every writable non-review node is a producer, regardless of node kind. Record
each changed file with exactly one producer ID and artifact class. Keep the
task-level artifact list equal to the classes in that manifest.

Use parallel workers only for independent scopes. Serialize overlapping writes
with a dependency edge. Do not split a cohesive task merely to increase agent
count. Keep one controller-owned integration point for cross-slice contracts.

## 3. Delegate with Exact Contracts

Construct every worker prompt from
[references/prompt-contract.md](references/prompt-contract.md). Pass only the
context needed for that task. Do not leak expected findings or another worker's
conclusion into an independent review.

Use capability classes as requirements, not implementation names:

- `LIGHT`: narrow discovery, inventory, or mechanical low-risk work.
- `STANDARD`: bounded implementation and ordinary validation.
- `DEEP`: ambiguous, cross-boundary, or high-risk reasoning and execution.
- `REVIEWER`: independent adversarial review.

When the execution environment cannot select capability explicitly, keep the
classification in the task contract and compensate with narrower scope,
stronger proof, or an independent reviewer.

## 4. Track and Reconcile

While workers run:

1. Track node state and newly discovered dependencies.
2. Prevent overlapping edits without ordering.
3. Reconcile every changed file to one producer scope and artifact class.
4. Inspect returned files and diffs before accepting claims.
5. Re-run the smallest reliable proof when safe and practical.
6. Reject unrelated changes and unsupported completion claims.
7. Escalate capability only after a concrete evidence or reasoning failure.
8. Stop and request direction when a required user decision expands scope.

Use direct action only for unavoidable integration glue. State why delegation
cannot solve that step, the exact affected surface, and its proof before acting.

Advance a node to `RUNNING` or `COMPLETE` only after every dependency is
`COMPLETE`. Mark a node `BLOCKED` only with evidence-backed external,
authority, user-decision, or blocked-dependency provenance. Otherwise leave
unfinished runnable work `PENDING` or `RUNNING` and report `IN_PROGRESS`.

## 5. Apply the Review Gate

Require an independent `REVIEWER` node when any trigger applies:

- Code or tests changed.
- Security, authorization, privacy, data, migration, payment, secret, release,
  deployment, or production risk exists.
- More than one execution worker contributed.
- Target validation failed or was not run.
- Integration produced uncertainty.
- The user requested review or high confidence.

The reviewer must be read-only, have a distinct neutral owner, run after every
producer, and inspect the actual combined diff or artifact, changed-file
manifest, test coverage, scope, validation evidence, and unresolved risks. Its
own proof must be dedicated `TARGET` evidence with `PASS` status. Do not pass
prior conclusions as expected answers. Delegate corrections and repeat the gate
until it passes or a concrete blocker remains.

When no trigger applies, record `NOT_REQUIRED` and the reason.

## 6. Validate Completion

Write a temporary JSON report following
[references/output-contract.md](references/output-contract.md), then run:

```bash
SAM_ORCHESTRATE_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_ORCHESTRATE_DIR/scripts/validate_orchestration.py" \
  "$ORCHESTRATION_TMP/report.json"
```

Fix the report when validation fails. Do not weaken the validator or omit state
to force completion. Remove temporary orchestration artifacts after validation.

Return `COMPLETE` only when required DAG nodes and the review gate are complete,
every completed producer has dedicated passing target proof for every declared
proof requirement, the changed-file manifest reconciles, and no required
correction remains. Return `BLOCKED` only when no runnable work remains and the
unfinished graph traces to evidence-backed external, authority, user-decision,
or blocked-dependency provenance. Otherwise keep the run `IN_PROGRESS`.

## 7. Report

Return:

- Task classification and delegated slices by capability.
- Changed-file manifest, artifact classes, and producer ownership.
- Passed, failed, skipped, and blocked proof.
- Exact blocker provenance for blocked nodes.
- Review-gate result or exact reason it was not required.
- Final result and remaining task IDs.

Do not repeat agent claims that the controller did not verify.
