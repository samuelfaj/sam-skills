# Council Output Contract

## Contents

1. Terminal states
2. Report shape
3. Thesis and evidence rules
4. Round and objection rules
5. Independence rules
6. Decision invariants
7. Validation

## Terminal states

- `APPROVED`: fully evidenced and no decision-owner condition remains.
- `APPROVED_WITH_CONDITIONS`: no blocker remains; explicit gated conditions do.
- `REVISE`: actionable material risk or uncertainty remains.
- `BLOCKED`: required capability, evidence, authority, or decision is absent.

## Report shape

Create one UTF-8 JSON object:

```json
{
  "schema_version": 1,
  "status": "APPROVED",
  "thesis": {},
  "evidence": [],
  "independence": {},
  "rounds": [],
  "decision": {},
  "historical_record_limitations": [],
  "blockers": []
}
```

`historical_record_limitations` lists missing raw responses, incomplete
provenance, or reconstructed history. Keep it empty only when the raw scratch
record proves completeness. `APPROVED` requires an empty list; conditional,
revise, and blocked reports must disclose any limitation.

`thesis` must contain:

- `id`, `objective`, and `problem_frame`;
- non-empty `scope`, `constraints`, `assumptions`, `alternatives`, and `steps`;
- non-empty `success_criteria`, `test_strategy`, `rollout`, `rollback`,
  `observability`, `residual_risks`, and `recheck_triggers`.

Each assumption contains `id`, `claim`, `state`, and `evidence_ids`. State is
`VERIFIED`, `EXPERIMENT_PLANNED`, or `UNRESOLVED`. A verified assumption cites
evidence. A planned experiment also contains `experiment`, `owner`, and
`pass_threshold`.

Each evidence item contains unique `id`, `kind`, `claim`, and `locator`. Use
real locators; never write a fabricated source.

## Round shape

Each round contains:

```json
{
  "number": 1,
  "input_thesis_id": "T-001",
  "reviewer_ids": [],
  "reviewer_results": [],
  "objections": [],
  "output_thesis_id": "T-002",
  "verification": [],
  "new_material_objections": 0
}
```

Round numbers must be sequential and cannot exceed three. Round one includes
all six required reviewer IDs. Later rounds may target open or new mechanisms.

Each `reviewer_results` item contains `reviewer_id`, `verdict`,
`search_summary`, `disconfirming_evidence`, and `residual_uncertainty`. Verdict
is `OBJECTIONS`, `NO_MATERIAL_OBJECTION`, or `BLOCKED`. Record exactly one
terminal result for every dispatched seat. An `OBJECTIONS` result must own at
least one objection in that round.

Each objection contains:

```json
{
  "id": "O-R1-001",
  "reviewer_id": "logic",
  "supporting_reviewer_ids": ["logic", "assumptions"],
  "claim": "A falsifiable claim",
  "failure_mode": "Observable consequence",
  "severity": "HIGH",
  "confidence": 85,
  "premise_ids": ["A-001"],
  "evidence_ids": ["E-001"],
  "required_proof": "Proof that would settle the claim",
  "smallest_correction": "Minimum sufficient response",
  "status": "RESOLVED",
  "author_response": {
    "disposition": "ACCEPT",
    "rationale": "Why this treatment is justified",
    "evidence_ids": ["E-001"],
    "change": "Exact thesis change",
    "validation": "How closure was checked",
    "residual_risk": "Declared residual risk or none"
  }
}
```

Allowed objection status: `OPEN`, `RESOLVED`, `MITIGATED`, `ACCEPTED_RISK`, or
`UNSUPPORTED`. Allowed author disposition: `ACCEPT`, `PARTIAL`, `REJECT`,
`INVESTIGATE`, or `ACCEPT_RISK`.

Use `supporting_reviewer_ids` to retain every blind reviewer that independently
found the same failure mechanism. Include the primary `reviewer_id`. A reviewer
with verdict `OBJECTIONS` may support a merged objection instead of owning a
duplicate objection.

Every verification item contains `verifier_id`, `verdict`, `objection_ids`, and
`rationale`. Verdict is `CLOSED`, `STILL_OPEN`, `NEW_RISK`,
`CONDITION_VALIDATED`, or `NO_MATERIAL_OBJECTION`.

Preserve verifier truth at the time of each round. A positive
`new_material_objections` count requires at least one `NEW_RISK` verifier
verdict, and `NEW_RISK` requires a positive count. Earlier open/new verdicts may
be closed by later rounds; never rewrite the earlier record.

## Independence shape

Record:

```json
{
  "blind_first_pass": true,
  "reviewers_saw_peer_reviews_before_submission": false,
  "reviewer_ids": [],
  "verifier_ids": [],
  "conditional_seat_selection": {},
  "conflicts": []
}
```

For approval, include all six distinct required reviewers, at least three fresh
verifiers named `closure-verifier`, `system-verifier`, and `arbiter`, no overlap
between those groups, and no undeclared conflict. The final panel must contain a
terminal result from all three verifiers.

`conditional_seat_selection` contains all conditional seat IDs from
`reviewer-lenses.md`. Each value starts with `SELECTED:` or `NOT_APPLICABLE:`
and gives a system-specific reason. Every selected seat must appear in the
reviewer and round ledgers.

## Decision shape

Record:

```json
{
  "final_thesis_id": "T-002",
  "confidence": 78,
  "basis": "EVIDENCE_AND_RISK",
  "rationale": "Why this status follows from evidence",
  "open_blocker_ids": [],
  "open_high_ids": [],
  "conditions": [],
  "accepted_risk_ids": [],
  "required_experiment_ids": [],
  "change_summary": [],
  "decision_owner_actions": []
}
```

Confidence is an integer from 0 through 100. It communicates calibration; it
does not override a severity gate.

## Decision invariants

- Never approve with an open or accepted blocker.
- Never return `APPROVED` with an open or accepted high risk.
- Permit an accepted high risk only in `APPROVED_WITH_CONDITIONS`, with an
  explicit condition and decision-owner action.
- Require every open blocker/high ID in the decision ledger.
- Treat decision ledgers as unordered sets; ordering has no decision meaning.
- Require `APPROVED` to have only verified assumptions.
- Permit planned experiments only in `APPROVED_WITH_CONDITIONS`, with matching
  required experiment IDs and execution conditions.
- Require the final verification panel to contain no `STILL_OPEN`, `NEW_RISK`,
  or positive `new_material_objections` for approval.
- Require conditional approval to name at least one condition, accepted risk,
  or planned experiment.
- Require `REVISE` to expose at least one open blocker/high, unresolved
  assumption, or material new risk.
- Require `BLOCKED` to contain a non-empty `blockers` list.
- Never infer a decision from reviewer counts.

## Validation

Run:

```bash
python3 -B scripts/validate_council_report.py council-report.json
```

Only cite `VALID` as machine proof. Preserve validator errors in blocked or
in-progress reporting. Do not change the report after validation without
rerunning the command.
