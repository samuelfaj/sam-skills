# Council Output Contract

## Contents

1. Profiles and states
2. Report shape
3. Execution and runtime records
4. Thesis, rounds, and objections
5. Independence and confrontation
6. Decision invariants
7. Validation

## Profiles and states

- `fast`: `TRIAGE_PASS`, `ESCALATE_TO_FULL`, or `BLOCKED`.
- `full`: `APPROVED`, `APPROVED_WITH_CONDITIONS`, `REVISE`, or `BLOCKED`.

`TRIAGE_PASS` means the bounded triage found no reason to escalate. It is never
approval. `ESCALATE_TO_FULL` means a material risk, critical unknown,
specialist trigger, or multi-provider requirement needs the full profile.

## Report shape

Create one UTF-8 JSON object:

```json
{
  "schema_version": 2,
  "profile": "fast",
  "status": "TRIAGE_PASS",
  "execution_policy": {},
  "thesis": {},
  "evidence": [],
  "independence": {},
  "confrontation": null,
  "rounds": [],
  "decision": {},
  "historical_record_limitations": [],
  "blockers": []
}
```

## Execution and runtime records

`execution_policy` contains:

```json
{
  "default_round_limit": 1,
  "hard_round_limit": 1,
  "continuation_authorized": false,
  "max_objections_per_reviewer": 3,
  "max_response_words": 1000,
  "packet_strategy": "RELEVANT_ONLY",
  "parallelism": "MAX_AVAILABLE",
  "initial_effort": "medium",
  "arbiter_effort": "high"
}
```

For `full`, `hard_round_limit` is 3. More than one round requires
`continuation_authorized: true`; the first run never continues automatically.

Each `provider_runtimes` entry contains non-empty `adapter` and `model`,
normalized `reviewer_effort` (`medium` or `host-default`), normalized
`arbiter_effort` (`high` or `host-default`), and positive
`max_parallel_workers`. Model/provider names are unrestricted.

`independence.batch_plan` records ordered waves with `round`, `phase`,
`provider`, and `seat_ids`. Every reviewer and verifier invocation appears
exactly once for its round. Independent seats share a wave up to runtime
capacity; blind reviewers precede verifiers within each round.

## Thesis, rounds, and objections

The thesis retains `id`, `objective`, `problem_frame`, and non-empty `scope`,
`constraints`, `assumptions`, `alternatives`, `steps`, `success_criteria`,
`test_strategy`, `rollout`, `rollback`, `observability`, `residual_risks`, and
`recheck_triggers`. Keep entries concise.

Evidence items contain unique `id`, `kind`, `claim`, and real `locator`.
Assumptions contain `id`, `claim`, `state`, and `evidence_ids`; planned
experiments also name method, owner, and pass threshold.

Each round contains sequential thesis IDs, reviewer IDs/results, objections,
the revised thesis ID, verification results, and the count of new material
objections. Fast has exactly one round. Full has one round by default and at
most three with explicit continuation.

Round one contains every required seat for its profile. Later full rounds may
target open/new mechanisms. Every dispatched seat has exactly one terminal
result.

Each objection contains stable ID, primary and supporting reviewer IDs, claim,
failure mode, severity, confidence, premise/evidence IDs, required proof,
smallest correction, status, and author response. A reviewer owns/supports at
most 3 objections per round. Preserve earlier verdicts unchanged.

## Independence and confrontation

Record:

```json
{
  "mode": "single-host",
  "providers": ["active-host"],
  "provider_runtimes": {
    "active-host": {
      "adapter": "host-native-workers",
      "model": "host-default",
      "reviewer_effort": "medium",
      "arbiter_effort": "high",
      "max_parallel_workers": 4
    }
  },
  "blind_first_pass": true,
  "reviewers_saw_peer_reviews_before_submission": false,
  "reviewer_ids": [],
  "verifier_ids": [],
  "conditional_seat_selection": {},
  "batch_plan": [
    {"round": 1, "phase": "blind", "provider": "active-host", "seat_ids": []},
    {"round": 1, "phase": "verification", "provider": "active-host", "seat_ids": []}
  ],
  "conflicts": []
}
```

Provider keys must be lowercase slugs, but are otherwise open. Multi-provider
requires at least two, profile `full`, namespaced reviewer IDs, confrontation,
and `meta-arbiter`.

Conditional selection lists every conditional seat. In full, use `SELECTED:`
or `NOT_APPLICABLE:` and dispatch selected seats. In fast, use `ESCALATE:` or
`NOT_APPLICABLE:`; any escalation requires `ESCALATE_TO_FULL`.

## Decision invariants

- Fast never returns an approval status; full never returns a triage status.
- `TRIAGE_PASS` requires all fast reviewers, fresh `triage-arbiter`, no open
  blocker/high, no unresolved critical assumption, no new material risk, and no
  conditional escalation.
- `ESCALATE_TO_FULL` requires a material open issue, unresolved assumption,
  new risk, conditional escalation, or multi-provider need.
- Approval requires all full reviewers, applicable specialists, three fresh
  verifiers, complete final closure, no independence conflict, and no open
  blocker/high.
- Never accept a blocker. Accept a high only in
  `APPROVED_WITH_CONDITIONS`, with explicit owner action.
- `APPROVED` requires verified assumptions and complete raw history.
- `REVISE` exposes an actionable material issue after the authorized round.
- `BLOCKED` contains a non-empty blocker list.
- Decision ledgers are exact unordered sets. Never infer a result from counts.

`historical_record_limitations` lists missing raw responses or reconstructed
history. Keep it empty only when scratch evidence proves completeness.

## Validation

Run:

```bash
python3 -B scripts/validate_council_report.py council-report.json
```

Only cite `VALID` as machine proof. Re-run after every report change.
