# Council Output Contract

`init` writes this skeleton; `TODO`, empty values, and a zero `max_parallel_workers` fail
validation until replaced. `finalize` derives the fields marked `derived`; do not hand-edit them.

## Skeleton

```jsonc
{
  "schema_version": 2, "profile": "fast|full",
  "status": "TRIAGE_PASS|ESCALATE_TO_FULL|APPROVED|APPROVED_WITH_CONDITIONS|REVISE|BLOCKED",
  "packet_path": "<abs>", "packet_head": "<full commit SHA|none>", "packet_scope": "FULL|DELTA",
  "packet_fingerprint": "<init; absent if dirty or outside a repo>", "base_report": "<DELTA only>",
  "execution_policy": {"default_round_limit": 1, "hard_round_limit": 1, // full: 3
    "continuation_authorized": false, "max_objections_per_reviewer": 3,
    "max_response_words": 1000, "packet_strategy": "RELEVANT_ONLY",
    "parallelism": "MAX_AVAILABLE", "initial_effort": "medium", "arbiter_effort": "high"},
  "thesis": {"id": "T-###", "objective": "", "problem_frame": "", "scope": [""],
    "constraints": [""], "alternatives": [""], "steps": [""], "success_criteria": [""],
    "test_strategy": [""], "rollout": [""], "rollback": [""], "observability": [""],
    "residual_risks": [""], "recheck_triggers": [""], // all non-empty, assumptions too
    "assumptions": [{"id": "A-###", "claim": "", "state": "VERIFIED|EXPERIMENT_PLANNED|UNRESOLVED",
      "evidence_ids": ["E-###"], // required if VERIFIED
      "experiment": "", "owner": "", "pass_threshold": ""}]}, // EXPERIMENT_PLANNED only
  "evidence": [{"id": "E-###", "kind": "", "claim": "", "locator": ""}],
  "independence": {"mode": "single-host|multi-provider", "providers": ["<slug>"],
    "provider_runtimes": {"<slug>": {"adapter": "", "model": "",
      "reviewer_effort": "medium|host-default", "arbiter_effort": "high|host-default",
      "max_parallel_workers": 1}}, // capacity actually used; init fills only the first provider (others: placeholders)
    "blind_first_pass": true, "reviewers_saw_peer_reviews_before_submission": false,
    "reviewer_ids": [], "verifier_ids": [], // derived
    "batch_plan": [{"round": 1, "phase": "blind|verification", "provider": "<slug>",
      "seat_ids": []}], // derived: planned minimum schedule at max_parallel_workers
    "conditional_seat_selection": {"<seat>": "<PREFIX>: <system-specific reason>"}, "conflicts": []},
  "confrontation": null, // multi-provider: see provider-matrix.md
  "rounds": [{"number": 1, "input_thesis_id": "T-001", "output_thesis_id": "T-002",
    "reviewer_ids": [""], "reviewer_results": [{"reviewer_id": "", "provider": "<multi-provider>",
      "verdict": "OBJECTIONS|NO_MATERIAL_OBJECTION|BLOCKED", "search_summary": "",
      "disconfirming_evidence": "", "residual_uncertainty": ""}],
    "objections": [{"id": "O-R<round>-###", "reviewer_id": "", "supporting_reviewer_ids": [""],
      "claim": "", "failure_mode": "", "severity": "BLOCKER|HIGH|MEDIUM|LOW|UNSUPPORTED",
      "confidence": 0, "premise_ids": ["A-###"], "evidence_ids": ["E-###"],
      "required_proof": "", "smallest_correction": "",
      "status": "OPEN|RESOLVED|MITIGATED|ACCEPTED_RISK|UNSUPPORTED",
      "author_response": {"disposition": "ACCEPT|PARTIAL|REJECT|INVESTIGATE|ACCEPT_RISK",
        "rationale": "", "evidence_ids": [], "change": "", "validation": "",
        "residual_risk": ""}}],
    "verification": [{"verifier_id": "", "objection_ids": [], "rationale": "",
      "verdict": "CLOSED|STILL_OPEN|NEW_RISK|CONDITION_VALIDATED|NO_MATERIAL_OBJECTION"}],
    "new_material_objections": 0}],
  "decision": {"final_thesis_id": "", "open_blocker_ids": [], "open_high_ids": [],
    "accepted_risk_ids": [], "required_experiment_ids": [], // derived (all five)
    "confidence": 0, "basis": "EVIDENCE_AND_RISK", "rationale": "",
    "conditions": [], "change_summary": [], "decision_owner_actions": []},
  "historical_record_limitations": [], "blockers": []}
```

## Rules

- Text is non-empty, lists unique, `confidence` 0-100, and every ID reference
  resolves. Provider slugs match `^[a-z0-9]+(-[a-z0-9]+)*$`.
- A present `packet_fingerprint` must recompute from the `packet_path` bytes,
  profile, providers, and `packet_head`.
- `conditional_seat_selection` holds exactly the nine specialists of
  reviewer-lenses.md, prefixed `SELECTED: ` or `NOT_APPLICABLE: ` (full) or
  `ESCALATE: ` or `NOT_APPLICABLE: ` (fast); every `SELECTED` seat is
  dispatched.
- Rounds: more than 1 needs `continuation_authorized: true`. Each
  `input_thesis_id` equals the prior output. Round 1 holds every required
  seat; later rounds may be limited to open or new mechanisms.
- The zero-objection fast pass (SKILL step 7) has `verification: []` and
  `output_thesis_id` equal to `input_thesis_id`; no other round has equal IDs,
  nor empty `verification` unless the report is `BLOCKED`.
- One result per round reviewer; `OBJECTIONS` needs an objection it supports; a
  reviewer supports at most 3 per round, and `reviewer_id` is in `supporting_reviewer_ids`.
- `BLOCKER` is never `ACCEPTED_RISK`; `ACCEPTED_RISK` needs `ACCEPT_RISK`;
  status `UNSUPPORTED` needs `REJECT`. Preserve earlier rounds' verdicts.
- Each verifier response becomes one entry per check verdict (with its
  `objection_ids`), one `NEW_RISK` per material new risk, else one
  `NO_MATERIAL_OBJECTION`. `new_material_objections` is positive exactly when
  a verdict is `NEW_RISK`.
- `thesis.id` equals the last `output_thesis_id`. Never infer a result from counts.
- `blockers` is non-empty exactly for `BLOCKED`, which may leave providers, runtimes, and
  conditional seats out and `rounds` as `[]`.
- `historical_record_limitations` lists missing raw responses or reconstructed
  history; empty only when every raw response is retained (file or locator).
- `DELTA`: `base_report` (absolute or report-relative) is VALID with its own chain,
  passing (`TRIAGE_PASS`, `APPROVED`, or `APPROVED_WITH_CONDITIONS`), with the same
  profile and `thesis.objective`, and a `final_thesis_id` equal to round 1
  `input_thesis_id`; heads are distinct commit SHAs, the base's an ancestor in the
  target repo (checked by `finalize --repo`).
- Fast non-`BLOCKED` and approval: no `BLOCKED` reviewer. Approval also: blind,
  no peer leak, no `conflicts` or `UNRESOLVED` assumption; at least 3
  verifiers, disjoint from reviewers, every required one in the final panel;
  final verdicts without `STILL_OPEN`/`NEW_RISK`; non-empty `change_summary`.
- `APPROVED`: empty `historical_record_limitations`, no `EXPERIMENT_PLANNED`, no accepted
  `HIGH`, no `conditions`. `APPROVED_WITH_CONDITIONS`: a condition, accepted risk, or
  planned experiment; an accepted `HIGH` or planned experiment needs `conditions`; an
  accepted `HIGH` needs `decision_owner_actions`.
