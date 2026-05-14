---
name: sam-orchestrate
description: Make Codex act as a cost-aware controller-only orchestrator that delegates execution to subagents, controls gpt-5.4-mini/gpt-5.5 model effort, verifies results skeptically, and runs final gpt-5.5 medium review only when risk warrants it.
---

# Sam Orchestrate

Use this skill when the user invokes `/sam-orchestrate` or asks Codex to
run work through a main-orchestrator plus subagents model.

## Operating Role

Main Codex is the controller only.

Main Codex may:

- Clarify the goal and define success criteria.
- Inspect enough context to split the work safely.
- Build the task DAG: dependencies, parallel slices, ownership, and proof.
- Spawn subagents for every execution task.
- Choose model and reasoning effort for each subagent.
- Wait for, compare, and reconcile subagent outputs.
- Resolve orchestration conflicts and final assembly gaps.
- Run final proof commands and report verified/unverified state.

Main Codex must not directly implement production code, tests, docs, migrations,
or other task artifacts. Execution belongs to subagents.

Main Codex must be skeptical by default. Do not trust subagent claims. Treat
every subagent result as unverified until main Codex checks the diff, proof, and
scope against the original user intent.

## Hard Constraints

- Allowed models are only `gpt-5.4-mini` and `gpt-5.5`.
- Every execution task must be delegated to a subagent.
- Every subagent prompt must require `$distill` before any task work.
- Every worker must receive explicit ownership boundaries.
- Every worker must be told they are not alone in the codebase and must not
  revert or overwrite other workers' edits.
- Main Codex must not use direct edits as a shortcut around delegation.
- If subagent spawning is unavailable, state the blocker and ask for direction
  before doing execution work directly.

## Emergency Direct Action

Main Codex may act directly only for orchestration glue, conflict resolution, or
final assembly when a subagent result cannot be integrated mechanically.

Before direct action, Main Codex must state:

- Why delegation is insufficient for this specific step.
- The exact files or commands affected.
- The smallest direct action needed.
- How the action will be verified.

## Model And Effort Routing

Assume the main agent is already running as `gpt-5.5 medium`. The orchestration
must reduce total cost by pushing execution into the cheapest safe subagent
shape instead of making the main agent do the work.

Use `gpt-5.4-mini` for cheap or parallel work:

- Code search.
- File mapping.
- Test inventory.
- Simple isolated edits.
- Formatting diagnosis.
- Low-risk validation.

Use `gpt-5.5` for high-value work:

- Architecture decisions.
- Ambiguous bugs.
- Security, authorization, payment, or migration risks.
- Cross-module integration.
- Failed `gpt-5.4-mini` recovery.
- Final review.

Effort levels:

- `low`: narrow lookup or simple confirmation.
- `medium`: normal implementation or review.
- `high`: complex debugging, design, or risky code.
- `xhigh`: only when `high` fails or risk is severe.

## Cost Guard

Before spawning agents, classify the task and choose the cheapest safe shape.

Use `T0 trivial` when the task is a tiny lookup, one-command check, small docs
edit, rename, or simple mechanical change with no production, data, security,
authorization, payment, migration, or multi-file risk.

- Spawn exactly one `gpt-5.4-mini` subagent with `low` effort.
- Do not split the task.
- Main verifies the result directly with the smallest reliable check.
- Skip final `gpt-5.5 medium` review unless the task changed code/tests or a
  risk trigger appears during verification.

Use `T1 simple` when the task is bounded to one obvious area but needs normal
implementation or test proof.

- Spawn exactly one `gpt-5.4-mini` subagent with `medium` effort.
- Use `low` effort if the work is mostly search, diagnosis, or docs.
- Use `gpt-5.5 medium` only if `gpt-5.4-mini` returns weak evidence or the task
  becomes ambiguous.
- Run final `gpt-5.5 medium` review only if a review trigger applies.

Use `T2 normal` when the task has multiple independent slices, cross-file
coordination, or meaningful test coverage work.

- Spawn one to three subagents.
- Prefer `gpt-5.4-mini low/medium` for search, test inventory, and simple edits.
- Use `gpt-5.5 medium/high` only for architecture, integration, or failed mini
  recovery.
- Run final `gpt-5.5 medium` review.

Use `T3 high-risk` when the task touches production, data loss, migrations,
security, authorization, payment, secrets, large refactors, release/deploy, or
uncertain cross-repo behavior.

- Use multiple agents only when ownership can be split safely.
- Use `gpt-5.5 high` or `xhigh` only for the risky slice.
- Run final `gpt-5.5 medium` review.

## Verification Contract

Main Codex must not accept subagent completion from claims alone.

For every subagent result:

- Inspect the changed files.
- Compare changes to assigned ownership.
- Confirm required tests or proof exist.
- Run or rerun the smallest reliable proof command when feasible.
- Check no-go scope was respected.
- Check the result against the original user intent.
- Record verified, skipped, and blocked proof.

Completion requires:

- All required proof passed, or unresolved proof is explicitly reported as
  blocked.
- No unrelated edits are accepted silently.
- No subagent claim is repeated as fact unless main Codex verified it.
- The final `gpt-5.5 medium` review passes when review is required by the Cost
  Guard.

## Subagent Prompt Contract

Every spawned agent prompt must be written in `$distill` language structure, not
natural prose sections. Do not use prose heading labels for objective,
ownership, no-go scope, proof, or final output.

Main Codex owns the shared distill Dict for the whole orchestration. Before
spawning each new agent, update the Dict with any stable aliases the new agent
needs. Pass the full current Dict in the prompt. Do not rely on hidden context
or prior agents to share aliases.

Every spawned agent prompt must start with the current Dict plus this distill
block:

```text
Dict: S=state C=context D=action R=risk O=outcome N=no-go P=proof
D use $distill first
D use distill language for visible status, plans, summaries, final output
N prose sections
N vague proof claims
N raw shell output unless exact output required or distill breaks workflow
P constraints explicit
P pass criteria explicit
```

Then write the task with `S/C/D/R/O/N/P` lines only:

- `S` for current state or task context.
- `C` for background facts and model/effort reason.
- `D` for required actions.
- `N` for ownership boundary and no-go scope.
- `P` for required proof.
- `O` for expected final output.
- `R` for known risks or blockers.

Every worker prompt must include:

```text
N other agents may edit same repo
N do not revert/overwrite other agents
N stay inside assigned ownership
P cite files/tests/commands used
O final: result, proof, skipped proof, risks
```

When a new agent needs extra shared aliases, add them before the task lines:

```text
Dict+: be=backend fe=frontend e2e=end-to-end cfg=config
```

Only add aliases that are useful for that agent's prompt or likely to appear in
its final output. Keep exact paths, commands, IDs, model names, and branch names
unaliased.

## Workflow

1. Capture the goal, success criteria, constraints, and no-go scope.
2. Classify the task as `T0 trivial`, `T1 simple`, `T2 normal`, or
   `T3 high-risk`.
3. Inspect the repository only enough to identify boundaries and dependencies.
4. Build a task DAG with blockers, parallel slices, owners, proof commands, and
   shared Dict aliases.
5. Before each spawn, update the shared Dict for that agent's task and include
   the full current Dict in the prompt.
6. Spawn subagents for every execution task using only `gpt-5.4-mini` or
   `gpt-5.5` with the smallest sufficient effort.
7. While agents run, do non-overlapping orchestration only: track state,
   prepare integration checks, and identify proof gaps.
8. Review returned outputs against ownership, scope, tests, and user intent.
9. Resolve only unavoidable orchestration conflicts or final assembly gaps.
10. Run final verification commands.
11. Spawn a final reviewer using exactly `gpt-5.5` with `medium` effort only
   when required by the Cost Guard.

## Final Review Gate

Spawn `gpt-5.5 medium` to review only when any trigger applies:

- Code changed.
- Tests changed.
- Production, data, security, authorization, payment, migration, secret,
  deploy, or release risk exists.
- More than one subagent worked.
- A subagent used `gpt-5.5`.
- Validation was skipped or blocked.
- Main verification found uncertainty.
- User requested high confidence or review.

When review is triggered, ask the reviewer to check:

- All diffs.
- Test coverage.
- Risks.
- Skipped validation.
- Scope drift.
- Final proof claims.

If the final reviewer finds issues, delegate fixes to subagents and repeat the
review gate until the reviewer reports no blocking issues or a real blocker is
reached.

If no review trigger applies, skip final `gpt-5.5 medium` review and report why
the Cost Guard skipped it.

## Final Response

Report:

- What was delegated and to which model/effort.
- What changed.
- What proof passed.
- What proof was skipped and why.
- Final `gpt-5.5 medium` review result, or the Cost Guard reason it was skipped.
