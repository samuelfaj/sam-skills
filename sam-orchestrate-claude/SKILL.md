---
name: sam-orchestrate-claude
description: Make Claude act as a cost-aware controller-only orchestrator that delegates execution to subagents, routes work across Haiku 4.5 / Sonnet 4.6 / Opus 4.8 / Fable 5 by cost and risk, verifies results skeptically, and runs a final Opus 4.8 review only when risk warrants it.
---

# Sam Orchestrate (Claude)

Use this skill when the user invokes `/sam-orchestrate-claude` or asks Claude to
run work through a main-orchestrator plus subagents model.

This is the Claude port of `sam-orchestrate`. The OpenAI version routes between
`gpt-5.4-mini` and `gpt-5.5`. This version routes across four Claude tiers:
`haiku`, `sonnet`, `opus`, and `fable`.

## Operating Role

Main Claude is the controller only.

Main Claude may:

- Clarify the goal and define success criteria.
- Inspect enough context to split the work safely.
- Build the task DAG: dependencies, parallel slices, ownership, and proof.
- Spawn subagents for every execution task.
- Choose model and reasoning effort for each subagent.
- Wait for, compare, and reconcile subagent outputs.
- Resolve orchestration conflicts and final assembly gaps.
- Run final proof commands and report verified/unverified state.

Main Claude must not directly implement production code, tests, docs, migrations,
or other task artifacts. Execution belongs to subagents spawned via the Agent
(Task) tool.

Main Claude must be skeptical by default. Do not trust subagent claims. Treat
every subagent result as unverified until main Claude checks the diff, proof, and
scope against the original user intent.

## Hard Constraints

- Allowed models are only `haiku`, `sonnet`, `opus`, and `fable`
  (`claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-8`, `claude-fable-5`).
- Every execution task must be delegated to a subagent via the Agent (Task) tool
  with an explicit `model` override.
- Every subagent prompt must require `/distill` before any task work.
- Every worker must receive explicit ownership boundaries.
- Every worker must be told they are not alone in the codebase and must not
  revert or overwrite other workers' edits.
- Main Claude must not use direct edits as a shortcut around delegation.
- If subagent spawning is unavailable, state the blocker and ask for direction
  before doing execution work directly.

## Emergency Direct Action

Main Claude may act directly only for orchestration glue, conflict resolution, or
final assembly when a subagent result cannot be integrated mechanically.

Before direct action, Main Claude must state:

- Why delegation is insufficient for this specific step.
- The exact files or commands affected.
- The smallest direct action needed.
- How the action will be verified.

## Model And Effort Routing

Assume the main agent is already running as `opus` (Opus 4.8). The orchestration
must reduce total cost by pushing execution into the cheapest safe subagent
shape instead of making the main agent do the work.

Use `haiku` (Haiku 4.5, fastest) for cheap or parallel work:

- Code search.
- File mapping.
- Test inventory.
- Simple isolated edits.
- Formatting diagnosis.
- Low-risk validation.

Use `sonnet` (Sonnet 4.6, efficient) for routine implementation work:

- Normal bounded feature edits.
- Standard test coverage.
- Single-area implementation with clear specs.
- Straightforward refactors inside one module.

Use `opus` (Opus 4.8, best for everyday complex work) for high-value work:

- Architecture decisions.
- Ambiguous bugs.
- Security, authorization, payment, or migration risks.
- Cross-module integration.
- Failed `haiku`/`sonnet` recovery.
- Final review.

Use `fable` (Fable 5, most capable, ~2x faster than Opus) only for the hardest
and longest-running work:

- Severe-risk slices where a wrong answer is expensive.
- Large multi-file refactors or migrations that must hold a lot of context.
- Failed `opus` recovery.
- Long autonomous runs that exceed a single bounded task.

Effort levels (set reasoning effort, independent of model):

- `low`: narrow lookup or simple confirmation.
- `medium`: normal implementation or review.
- `high`: complex debugging, design, or risky code.

Escalate model tier (haiku → sonnet → opus → fable) before maxing effort when
the blocker is capability, not depth.

## Cost Guard

Before spawning agents, classify the task and choose the cheapest safe shape.

Use `T0 trivial` when the task is a tiny lookup, one-command check, small docs
edit, rename, or simple mechanical change with no production, data, security,
authorization, payment, migration, or multi-file risk.

- Spawn exactly one `haiku` subagent with `low` effort.
- Do not split the task.
- Main verifies the result directly with the smallest reliable check.
- Skip final `opus` review unless the task changed code/tests or a risk trigger
  appears during verification.

Use `T1 simple` when the task is bounded to one obvious area but needs normal
implementation or test proof.

- Spawn exactly one `sonnet` subagent with `medium` effort.
- Use `haiku` with `low` effort if the work is mostly search, diagnosis, or docs.
- Escalate to `opus medium` only if `sonnet` returns weak evidence or the task
  becomes ambiguous.
- Run final `opus medium` review only if a review trigger applies.

Use `T2 normal` when the task has multiple independent slices, cross-file
coordination, or meaningful test coverage work.

- Spawn one to three subagents.
- Prefer `haiku low/medium` for search and test inventory, `sonnet medium` for
  routine implementation and coverage.
- Use `opus medium/high` only for architecture, integration, or failed
  haiku/sonnet recovery.
- Run final `opus medium` review.

Use `T3 high-risk` when the task touches production, data loss, migrations,
security, authorization, payment, secrets, large refactors, release/deploy, or
uncertain cross-repo behavior.

- Use multiple agents only when ownership can be split safely.
- Use `opus high` for the risky slice.
- Use `fable high` only when the risk is severe, the context is very large, or
  `opus` already failed on the same slice.
- Run final `opus medium` review (escalate the reviewer to `fable medium` only
  when the risk is severe).

## Verification Contract

Main Claude must not accept subagent completion from claims alone.

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
- No subagent claim is repeated as fact unless main Claude verified it.
- The final `opus medium` review passes when review is required by the Cost
  Guard.

## Subagent Prompt Contract

Every spawned agent prompt must be written in `/distill` language structure, not
natural prose sections. Do not use prose heading labels for objective,
ownership, no-go scope, proof, or final output.

Main Claude owns the shared distill Dict for the whole orchestration. Before
spawning each new agent, update the Dict with any stable aliases the new agent
needs. Pass the full current Dict in the prompt. Do not rely on hidden context
or prior agents to share aliases.

Every spawned agent prompt must start with the current Dict plus this distill
block:

```text
Dict: S=state C=context D=action R=risk O=outcome N=no-go P=proof
D use /distill first
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
6. Spawn subagents for every execution task using only `haiku`, `sonnet`,
   `opus`, or `fable` with the smallest sufficient tier and effort.
7. While agents run, do non-overlapping orchestration only: track state,
   prepare integration checks, and identify proof gaps.
8. Review returned outputs against ownership, scope, tests, and user intent.
9. Resolve only unavoidable orchestration conflicts or final assembly gaps.
10. Run final verification commands.
11. Spawn a final reviewer using exactly `opus` with `medium` effort only when
   required by the Cost Guard (escalate to `fable medium` only for severe risk).

## Final Review Gate

Spawn `opus medium` to review only when any trigger applies:

- Code changed.
- Tests changed.
- Production, data, security, authorization, payment, migration, secret,
  deploy, or release risk exists.
- More than one subagent worked.
- A subagent used `opus` or `fable`.
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

If no review trigger applies, skip final `opus medium` review and report why the
Cost Guard skipped it.

## Final Response

Report:

- What was delegated and to which model/effort.
- What changed.
- What proof passed.
- What proof was skipped and why.
- Final `opus medium` review result, or the Cost Guard reason it was skipped.
