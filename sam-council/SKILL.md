---
name: sam-council
description: "Falsify, revise, and judge system-development plans through blind specialist reviews, explicit rebuttals, bounded revision rounds, and an evidence-weighted decision record; multi-provider Grok/Claude/Codex confrontation only when the user clearly requests it. Use when planning architecture, features, migrations, incidents, releases, security-sensitive work, expensive changes, or other uncertain and hard-to-reverse technical decisions."
---

# Sam Council

## Purpose

Turn a consequential software plan into a falsifiable thesis, expose its weakest
assumptions through independent adversarial review, revise it, and issue a
traceable decision. Optimize for finding the conditions under which the plan
fails, not for performative criticism or consensus. When the user names multiple
providers, run independent panels on each and confront their claims until the
strongest evidence-backed plan remains. Multi-provider runs only when the user
clearly asks for them.

## Non-Negotiable Contract

Remain read-only in the target system. Use distinct subagents or host workers
for every council seat. Keep the first-pass reviews blind. Answer every
objection explicitly. Decide by evidence and risk, never by vote count or
provider majority. Never report approval while a supported blocker, untreated
high risk, unverified critical assumption, or unvalidated correction remains.
Retain raw blind and verifier responses in scratch space until the final
machine report validates. Never invent a missing provider’s review.
**Default is always `single-host`.** Do not enter multi-provider unless the
user clearly and explicitly requests it.

## Activation and boundaries

- Run the full council when explicitly invoked.
- For implicit use, first confirm that the decision has material cost,
  irreversibility, dependencies, uncertainty, security or money impact, a long
  horizon, or credible competing alternatives.
- For a simple and reversible task, recommend a direct plan unless the user
  still requires the council.
- Produce planning and decision artifacts only. Do not implement, modify target
  files, deploy, publish, approve, or contact external systems.
- Preserve the user's scope, constraints, no-go surfaces, and decision rights.
- Ask only for missing information that would materially change the thesis.
  Otherwise record the gap as an assumption or planned experiment.
- If the runtime cannot create distinct seats for the selected mode, return
  `BLOCKED`. Do not simulate multiple reviewers or providers in one context.

## Required resources

Read these files completely before forming the thesis:

1. [references/reviewer-lenses.md](references/reviewer-lenses.md) for required
   and conditional seats.
2. [references/provider-matrix.md](references/provider-matrix.md) for
   single-host vs multi-provider activation and runtime bindings.
3. [references/prompt-contract.md](references/prompt-contract.md) for blind
   packets, reviewer replies, rebuttals, confrontation, and verification
   prompts.
4. [references/output-contract.md](references/output-contract.md) before
   creating the final report.

## Mode selection

Detect mode before building the seat plan. Prefer the narrower mode.

| Mode | When |
| --- | --- |
| `single-host` | **Default.** Any run that is not a clear multi-provider request |
| `multi-provider` | Only when the user **clearly and explicitly** asks for a multi-host / multi-model council |

**Multi-provider is opt-in only.** Activate it solely when the user intent is
unambiguous, for example:

- “use sam-council with grok, claude and codex”
- “multi-provider council across codex + claude”
- “run the council on all three: grok, claude-code, and codex”
- “confront this plan with grok and codex panels”

**Do not** activate multi-provider from weak or incidental signals, including:

- the controller host merely being Claude, Grok, or Codex;
- casual mention of another model without asking for a multi-host council;
- “get a second opinion” without naming multiple providers as council hosts;
- comparing tools/products in the thesis domain (not council hosts);
- cost, quality, or “be thorough” alone.

If the user names exactly one provider, stay `single-host` on that provider. If
multi-provider intent is ambiguous, stay `single-host` (do not ask to upsell
multi-provider). Provider keys: `grok`, `claude-code`, `codex`. Resolve aliases
via `references/provider-matrix.md`. Bind each selected provider to its fixed
model/effort row. Do not ask which model to use.

## Council topology

Use one main agent as the thesis author and controller.

### Single-host seats

Create one distinct seat for each required blind reviewer:

1. `logic`: attack contradictions and invalid inference.
2. `assumptions`: attack load-bearing premises and missing evidence.
3. `execution`: attack delivery, ownership, dependencies, migration, and
   operations.
4. `adversarial`: make the system fail through abuse, edge cases, security,
   concurrency, and second-order effects.
5. `alternatives`: find a simpler, cheaper, reversible, or existing solution.
6. `problem-frame`: challenge whether the plan solves the right problem.

After revision, use three fresh seats that did not author a blind review:

- `closure-verifier`: test whether each material objection was actually closed.
- `system-verifier`: find displaced problems, regressions, and new complexity.
- `arbiter`: determine which claims have the strongest evidence and issue the
  round verdict.

### Multi-provider seats

For every selected provider, run the full required blind panel under namespaced
IDs `{provider}/{seat}` (example: `codex/logic`, `claude-code/adversarial`,
`grok/alternatives`). First-pass reviews stay blind across seats **and**
providers.

After revision and cross-provider confrontation, require fresh:

- `closure-verifier` and `system-verifier` over the combined ledger;
- `meta-arbiter` that explicitly compares provider claims and forbids majority
  counting.

Conditional specialist seats from `references/reviewer-lenses.md` supplement
required seats; they never replace them. In multi-provider mode, selected
conditional seats run on each selected provider or record provider-specific
`NOT_APPLICABLE`.

Run seats in sequential batches when concurrency is limited. Never merge seats
or providers to save capacity. Record conflicts, shared context, missing seats,
provider outages, or runtime substitutions in the independence ledger.

## Evidence and objection rules

Assign stable identifiers:

- facts and evidence: `E-###`;
- assumptions: `A-###`;
- objections: `O-R<round>-###`;
- thesis versions: `T-###`.

Classify evidence as `VERIFIED`, `OBSERVED`, `INFERRED`, `ASSUMED`, or
`UNKNOWN`. Preserve source locators, commands, code locations, test receipts,
or user constraints. Do not upgrade an inference through repetition.

Require every objection to contain:

- a falsifiable claim and concrete failure mode;
- severity: `BLOCKER`, `HIGH`, `MEDIUM`, `LOW`, or `UNSUPPORTED`;
- confidence from 0 through 100;
- affected assumption IDs and available evidence IDs;
- required proof when current evidence is insufficient;
- the smallest adequate correction or decision needed.

Do not require a reviewer to invent a fault. Permit `NO_MATERIAL_OBJECTION` with
a search summary. Deduplicate objections by failure mechanism, not wording.
Twenty low findings never outweigh one supported blocker.

## Workflow

### 1. Freeze the charter

Record the exact objective, decision to make, target system, current state,
scope, constraints, invariants, no-go surfaces, stakeholders, deadline, and
available evidence. Separate facts from assumptions. Name the decision owner
when known.

Define pass criteria for the council itself. State the maximum of three rounds
and the no-progress rule before review begins. Publish mode (`single-host` or
`multi-provider`), selected providers, runtime bindings, required and
conditional seat count, expected minimum seat invocations, and batching plan.
Never hide the time or compute cost of a full or multi-provider council.

### 2. Write thesis `T-001`

Make the proposal falsifiable. Include:

- problem framing and why action is needed;
- proposed architecture or approach and causal rationale;
- interfaces, data paths, state transitions, and failure boundaries;
- ordered execution steps, dependencies, and ownership gaps;
- assumptions with expected ranges and disconfirming evidence;
- alternatives considered and explicit rejection reasons;
- testing, rollout, rollback, observability, and incident response;
- security, privacy, data, compatibility, capacity, cost, and operational risks;
- measurable success criteria, guardrails, and re-evaluation triggers;
- uncertainties and experiments required before commitment.

Do not hide uncertainty behind generic language. A plan with unknown system
state remains a hypothesis.

### 3. Build one frozen blind-review packet

Include the charter, `T-001`, evidence index, assumption ledger, relevant raw
artifacts, and reviewer-specific mission. Exclude peer reviews, the desired
decision, expected objections, and the author's private diagnosis.

Fingerprint or otherwise identify the exact packet. Give the same frozen core
to every reviewer. Add only role-specific questions.

Preserve each raw terminal reviewer response in scratch space. Do not rely on a
later narrative summary as the only historical record.

### 4. Run blind specialist reviews

Dispatch every seat independently on its bound host runtime. Require each
response to follow `references/prompt-contract.md`. Do not show any peer or
cross-provider response until all blind responses for the pass are terminal.

In multi-provider mode, dispatch each provider’s full required panel against the
same frozen packet. Preserve provider identity on every result
(`provider` field and/or namespaced `reviewer_id`).

Reject vague criticism, style preferences, duplicate mechanisms, and claims
without either evidence or a concrete proof request. Mark them `UNSUPPORTED`;
do not silently discard them.

### 5. Synthesize without voting

Normalize objection IDs, merge true duplicates, preserve disagreements, and
rank by supported severity. Identify the minimum load-bearing set: the smallest
group of objections that can invalidate the thesis.

For every merged mechanism, preserve one primary `reviewer_id` plus every
independent source in `supporting_reviewer_ids` (including other providers).
Never keep duplicate objections only to make each reviewer or provider appear
productive.

Do not count approvals or provider majorities. One demonstrated blocker
controls the round regardless of how many seats or hosts found no issue.

### 5b. Multi-provider confrontation (multi-provider mode only)

After blind synthesis and before or with author cross-examination:

1. Build one position per provider: material objection IDs, preferred
   correction, and provisional stance.
2. Give each provider only the other providers’ material claims. Require
   `ACCEPT`, `REBUT`, or `CONCEDE` with evidence IDs
   (`references/prompt-contract.md`).
3. Drop unsupported claims; keep supported minority blockers.
4. Record the confrontation ledger: positions, disagreements, accepted and
   rejected claims, and evidence-weighted resolution note.
5. Feed the surviving claim set into author cross-examination.

If providers disagree after confrontation, prefer stronger evidence and safer
residual risk. Never declare a winner by 2-of-3 agreement alone.

### 6. Cross-examine the author

Respond to every objection with exactly one disposition:

- `ACCEPT`: concede and change the thesis.
- `PARTIAL`: concede the supported part and bound the rest.
- `REJECT`: rebut with stronger evidence or mark proof still needed.
- `INVESTIGATE`: define an experiment with owner, method, threshold, and gate.
- `ACCEPT_RISK`: preserve a non-blocking risk for the decision owner.

Include rationale, evidence IDs, exact thesis change, validation method, and
residual risk. Never accept a `BLOCKER` as residual risk. Never accept a `HIGH`
risk on the user's behalf without explicit authority; otherwise make it a
condition or return `REVISE`.

### 7. Publish the revised thesis

Create the next thesis version. Add a traceability map from every objection to
its response, changed section, validation, and current status: `OPEN`,
`RESOLVED`, `MITIGATED`, `ACCEPTED_RISK`, or `UNSUPPORTED`.

Recheck internal consistency. A correction that adds a queue, cache, retry,
permission, migration, dependency, or manual operation must also add its new
failure modes, tests, observability, rollout, and rollback treatment.

### 8. Run the fresh verification panel

Give the panel the frozen prior thesis, objections, author responses, revised
thesis, evidence, confrontation ledger when present, and traceability map. Do
not provide the desired verdict.

Require the panel to determine:

- whether each material objection is closed rather than renamed;
- whether the correction moved the problem elsewhere;
- whether complexity or operational burden grew disproportionately;
- whether evidence supports the author's rebuttal;
- whether new risks require new objection IDs;
- whether the problem framing still matches the user's objective;
- in multi-provider mode, whether any provider disagreement on blockers/highs
  remains unresolved by evidence.

Require the arbiter (or `meta-arbiter` in multi-provider mode) to explain the
evidence basis. It cannot erase a supported objection; it may only confirm
closure, keep it open, downgrade it with evidence, or classify it unsupported.

### 9. Iterate with bounded convergence

Start another round when the panel finds an open blocker, untreated high risk,
new material objection, invalid correction, or load-bearing unknown. Use the
revised thesis as the next frozen thesis and keep prior IDs traceable.

Preserve each round's verdict as it existed at that time. Never rewrite an
earlier `STILL_OPEN` or `NEW_RISK` to match a later closure. Let the final round
and current objection ledger determine the terminal decision.

Stop after at most three rounds. Stop earlier after two consecutive rounds with
no material reduction in open blocker/high risk and no new decisive evidence.
Return `BLOCKED` or `REVISE`; do not manufacture convergence.

## System-development approval gates

Before approval, require all applicable gates:

- scope and interfaces are explicit;
- main flows and failure paths are modeled;
- data ownership, schema evolution, migration, and backward compatibility are
  addressed;
- authentication, authorization, secrets, privacy, abuse, and dependency risk
  are addressed;
- concurrency, idempotency, retry, timeout, partial failure, and recovery are
  addressed;
- capacity, latency, reliability, and cost assumptions are bounded;
- tests map to acceptance criteria and material risks;
- rollout is staged and observable;
- rollback or forward-recovery is executable and has a trigger;
- alerts, dashboards, logs, traces, and on-call ownership are sufficient;
- operational maintenance and decommissioning are owned;
- critical assumptions are verified or have gated experiments;
- success, guardrail, and re-evaluation thresholds are measurable.

Mark a gate `NOT_APPLICABLE` only with a system-specific reason.

## Decision rules

Return one terminal status:

- `APPROVED`: no supported blocker/high remains; every critical assumption is
  verified; all corrections are validated; no decision-owner condition remains.
- `APPROVED_WITH_CONDITIONS`: no blocker remains; every high is mitigated or
  explicitly accepted by the decision owner; planned experiments and conditions
  have owners, thresholds, and execution gates.
- `REVISE`: material objections or unknowns remain actionable within scope.
- `BLOCKED`: required evidence, reviewer independence, authority, runtime
  capability, or external decision is unavailable.

Approval also requires zero new material objection in the final verification
panel, measurable criteria, executable recovery, and declared residual risk.

## Validation and final response

Create the machine-checkable report in scratch space unless the user authorizes
a persistent planning artifact. Validate it with:

```bash
python3 -B scripts/validate_council_report.py council-report.json
```

Do not weaken the validator to force approval. Run
`scripts/test_council_harness.py` only when changing this skill.

Record any missing transcript, incomplete provenance, or reconstructed history
in `historical_record_limitations`. Never infer unpreserved reviewer support.

Report:

1. terminal status and calibrated confidence;
2. mode, providers, and runtime bindings used;
3. final thesis and decision rationale;
4. round, reviewer, independence, and confrontation ledgers;
5. material objections with responses and closure proof;
6. how cross-provider disagreements were resolved (if multi-provider);
7. changes made to the thesis after review;
8. conditions, experiments, accepted risks, and decision-owner actions;
9. rollout, rollback, observability, tests, and re-evaluation triggers;
10. exact blockers or residual uncertainty;
11. validator result.

Never summarize a blocked or unvalidated council as “plan approved.”
