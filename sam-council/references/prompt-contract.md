# Prompt Contract

## Packet

Write once to `<pkt>/packet.md`: charter, profile, topology, thesis ID; the
exact concise thesis; indexed evidence with precise locators; the assumption
ledger; exact task-local excerpts, diffs, or receipts the lenses need (cite
files the worker can read by path and line range instead of copying them);
the seat mission below, verbatim. Exclude unrelated files, repository dumps,
conversation history, peer reviews, the desired verdict, expected defects,
private reasoning, and duplicated narrative.

## Seat mission

> Try to falsify this system-development thesis within your assigned lens only.
> Find at most three concrete, load-bearing failure mechanisms, most severe and
> best supported first; prefer one causal mechanism over stylistic remarks. Use
> the supplied evidence; separate fact, inference, assumption, and missing
> evidence; name the proof that would settle each uncertainty and the smallest
> sufficient correction. Never approve by deference or vote. Return
> `NO_MATERIAL_OBJECTION` when that is honest. Stay under 1,000 words and stop
> at the cap. Return the response only as your final result; write no files.
> Response fields: `reviewer_id`, `provider`, `thesis_id`, `search_summary`,
> `verdict` (`OBJECTIONS|NO_MATERIAL_OBJECTION|BLOCKED`), `objections` (0-3,
> each `claim` (falsifiable), `failure_mode`, `severity`
> (`BLOCKER|HIGH|MEDIUM|LOW|UNSUPPORTED`), `confidence` (0-100), `premise_ids`,
> `evidence_ids`, `required_proof`, `smallest_correction`),
> `disconfirming_evidence`, `residual_uncertainty`.

Reject a response with more than 3 objections, a missing search, failure
mechanism, or disconfirming evidence, or a blindness violation.

## Author

Give normalized objections without vote counts. Require exactly one response
per objection: `objection_id`, `disposition`
(`ACCEPT|PARTIAL|REJECT|INVESTIGATE|ACCEPT_RISK`), `rationale`,
`evidence_ids`, `change` (exact thesis change), `validation` (validation or
experiment), `residual_risk`, and any decision-owner action. A rejection
without stronger evidence stays open. An investigation names a method, owner,
threshold, and gate.

## Verification

Write once to `<pkt>/verification.md`: prior and revised thesis, material
objections, author responses, evidence, and the traceability map; never the
desired status. Each fresh verifier gets its ID and the path. Response fields:
`verifier_id`, `revised_thesis_id`, objection checks (`objection_id`, verdict
`CLOSED|STILL_OPEN|CONDITION_VALIDATED`, `evidence_ids`, `rationale`),
`new_risks` (0-3: claim, failure mode, suggested severity, evidence IDs or
evidence needed), complexity delta, problem-displacement check, and final
verdict `PASS|REVISE|BLOCKED`.

The `triage-arbiter` combines closure, displacement, and escalation checks and
cannot approve. Convert each material new risk into an objection before any
explicitly authorized later round.
