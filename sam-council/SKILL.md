---
name: sam-council
description: "Rapidly triage or fully falsify consequential system-development plans through blind specialist reviews, explicit rebuttals, bounded revision rounds, and evidence-weighted decisions. Use for architecture, features, migrations, incidents, releases, security-sensitive work, expensive changes, or uncertain and hard-to-reverse technical decisions on any agent platform; use multi-provider confrontation only when explicitly requested."
---

# Sam Council

## Purpose

Turn a consequential software plan into a falsifiable thesis, expose its weakest
assumptions through independent review, and issue a traceable result. Optimize
for decisive evidence per model call. Remain independent of any vendor, model,
CLI, agent API, or fixed concurrency limit.

## Non-Negotiable Contract

Remain read-only in the target system. Use distinct workers for every seat and
keep first-pass reviews blind. Answer every objection explicitly. Decide by
evidence and risk, never by vote count. Never report full approval while a
supported blocker, untreated high risk, unverified critical assumption, or
unvalidated correction remains. Retain raw responses in scratch space until the
machine report validates. Never invent an unavailable worker or provider.

`fast` is a triage profile, not a weaker approval path. It may return only
`TRIAGE_PASS`, `ESCALATE_TO_FULL`, or `BLOCKED`. Only `full` may return
`APPROVED`, `APPROVED_WITH_CONDITIONS`, `REVISE`, or `BLOCKED`.

**Token Saver inheritance:** when the host provides
`RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1`, every controlled seat and verifier must
inherit that content-free receipt and its authorized capability/lane
environment unchanged. Never reconstruct or widen admission. A missing,
malformed, denied, cross-user, or provider-mismatched receipt is raw fail-open
input. Never put Skills, exact-output commands, prompts, transcripts, secrets,
or full reviewer responses into the receipt. Skills and exact-output evidence
remain lossless. Do not claim billing or quota savings.

Every controlled seat/verifier lifetime must be bracketed by the
provider-neutral telemetry bridge:

```bash
telemetry_command="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"
child_run="$("$telemetry_command" subagent begin --node '<stable-seat-id>')"
# run the seat or verifier
"$telemetry_command" subagent end --run-id "$child_run" --status completed
```

Use `failed` or `cancelled` on the corresponding terminal path. Preserve the
host receipt and returned child run id through retries. Bridge unavailability
means raw execution plus an explicit Subagents proof gap — never invent a Done
row. Do not require Distill to process Skill bodies or exact output; the bridge
is lifetime telemetry only.

## Required resources

Read these files completely before running the council:

1. [references/reviewer-lenses.md](references/reviewer-lenses.md) for profile
   seats and conditional specialists.
2. [references/provider-matrix.md](references/provider-matrix.md) for portable
   runtime discovery, topology, effort, and scheduling.
3. [references/prompt-contract.md](references/prompt-contract.md) for compact
   packets and response limits.
4. [references/output-contract.md](references/output-contract.md) before writing
   the report.

## Select profile and topology

Choose the smallest valid profile before forming the thesis.

| Profile | Use when | First pass | Verification | Rounds |
| --- | --- | --- | --- | --- |
| `fast` | Reversible, bounded work without a triggered specialist domain | 3 composite seats | 1 fresh triage arbiter | exactly 1 |
| `full` | Explicitly requested, costly, irreversible, production-critical, security/privacy, migration, compliance, or cross-provider | 6 required seats plus applicable specialists | 3 fresh verifiers | 1 by default, at most 3 |

Default an explicit `sam-council` request to `fast` only when every full trigger
is absent. Escalate before dispatch when uncertain. A `fast` result that finds a
blocker, high risk, critical unknown, displaced material risk, or applicable
conditional specialist returns `ESCALATE_TO_FULL`; do not imply approval.

Topology is independent of profile:

- `single-host` is always the default and uses the active host runtime.
- `multi-provider` is explicit opt-in only, requires at least two independent
  providers, and forces `full`.
- Provider identifiers are runtime-supplied lowercase slugs. Examples include
  `codex`, `claude-code`, and `grok`; they are not an allowlist.
- If exactly one provider is named, stay `single-host` on it.

## Portable execution policy

Discover and record the host's actual adapter, model label, supported effort
controls, and maximum safe parallel workers. Never require a named model or
vendor-specific command.

- Request the host's closest available `medium` tier for blind reviewers,
  conditional specialists, closure verification, and system verification.
- Request the closest available `high` tier only for the arbiter or
  meta-arbiter. If effort is not configurable, use `host-default` and record it.
- Dispatch independent seats concurrently up to the discovered safe capacity.
  Run one wave when capacity covers all seats; otherwise use the minimum number
  of batches. Never serialize independent seats unnecessarily.
- Evaluate conditional-seat applicability once in the controller. In `fast`,
  any applicable specialist triggers escalation rather than another seat. In
  `full`, dispatch every applicable specialist.
- Use a relevant-only packet. Prefer exact file ranges, diffs, receipts, and
  user constraints; exclude unrelated repository or conversation history.
- Cap each reviewer at 3 material objections and 1,000 words. Prefer fewer
  load-bearing objections. A reviewer may return `NO_MATERIAL_OBJECTION`.
- Do not run the report validator or skill harness inside reviewer workers.

Record the policy and actual runtime in the report. A host limitation is not a
reason to fabricate compliance: use the nearest supported capability and make
the deviation explicit.

## Seats

### Fast

Create three blind workers:

1. `frame-evidence`: problem frame, logic, and load-bearing assumptions.
2. `delivery-failure`: execution, operations, abuse, edge cases, and failure.
3. `simplification`: cheaper, smaller, reversible, or existing alternatives.

After revision, use one fresh `triage-arbiter`. It checks closure and displaced
risk, but cannot grant full approval.

### Full

Create six blind workers: `logic`, `assumptions`, `execution`, `adversarial`,
`alternatives`, and `problem-frame`. Add every applicable conditional seat from
`references/reviewer-lenses.md`.

After revision, use fresh `closure-verifier`, `system-verifier`, and `arbiter`.
In multi-provider mode, run the required blind panel per provider with
`{provider}/{seat}` IDs and replace `arbiter` with `meta-arbiter`.

## Evidence rules

Assign stable IDs: evidence `E-###`, assumptions `A-###`, objections
`O-R<round>-###`, and theses `T-###`. Classify evidence as `VERIFIED`,
`OBSERVED`, `INFERRED`, `ASSUMED`, or `UNKNOWN`; repetition never upgrades it.

Every objection must state a falsifiable claim, failure mode, severity,
confidence, premise/evidence IDs, required proof, and smallest correction.
Deduplicate by failure mechanism while preserving all
`supporting_reviewer_ids`. A supported blocker outweighs any number of passes.

## Workflow

1. Freeze the objective, decision, scope, invariants, constraints, no-go
   surfaces, owner, evidence, assumptions, selected profile/topology, execution
   policy, runtime capability, seat count, and batch plan.
2. Write `T-001` as a concise falsifiable thesis with approach, interfaces,
   state/failure boundaries, steps, alternatives, tests, rollout/recovery,
   observability, risks, measurable success, and recheck triggers.
3. Build one frozen relevant-only packet. Give every worker the same core plus
   only its lens. Preserve each raw response.
4. Dispatch blind seats at maximum safe concurrency. Do not reveal peer output
   until every seat in the pass is terminal.
5. Normalize and deduplicate objections without voting. Preserve unsupported
   claims as `UNSUPPORTED` rather than silently dropping them.
6. In explicit multi-provider runs, confront provider claims as described in
   `references/provider-matrix.md`.
7. Cross-examine the author. Use exactly one disposition per objection:
   `ACCEPT`, `PARTIAL`, `REJECT`, `INVESTIGATE`, or `ACCEPT_RISK`.
8. Publish the revised thesis and map every objection to its response, change,
   validation, and status.
9. Run the fresh verification panel at maximum safe concurrency.
10. Stop after round one by default. Return a terminal result instead of
    automatically starting another round. Continue to round two or three only
    when the user explicitly asks to validate a revised thesis. Never exceed
    three rounds; stop after two rounds without material progress.
11. Validate the scratch report with
    `python3 -B scripts/validate_council_report.py council-report.json`.

## Decision rules

For `fast`:

- `TRIAGE_PASS`: no supported blocker/high, no critical unknown, no specialist
  trigger, and the fresh triage arbiter found no material displaced risk.
- `ESCALATE_TO_FULL`: any blocker/high, critical unknown, specialist trigger,
  multi-provider requirement, or material new risk exists.
- `BLOCKED`: distinct workers, evidence, runtime capability, or authority is
  unavailable.

For `full`:

- `APPROVED`: no supported blocker/high remains; critical assumptions and
  corrections are verified.
- `APPROVED_WITH_CONDITIONS`: no blocker remains; every high is mitigated or
  explicitly accepted by the decision owner, with owned gated conditions.
- `REVISE`: an actionable material objection or unknown remains after the
  current authorized round.
- `BLOCKED`: required evidence, independence, authority, provider, or runtime
  capability is unavailable.

Never treat `TRIAGE_PASS` as approval. Never accept a blocker as residual risk
or a high risk on the user's behalf.

## Output

Follow [references/output-contract.md](references/output-contract.md). Report
the terminal result, confidence, profile, topology, providers, actual runtime
bindings, batch plan, thesis, evidence, objections, responses, verification,
conditions, residual uncertainty, and validator result. Disclose missing raw
history in `historical_record_limitations`.

Run `scripts/test_council_harness.py` only when changing this skill. Never call
a blocked or invalid result approved.
