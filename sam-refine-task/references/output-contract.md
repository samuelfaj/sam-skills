# Refinement Report Contract

Write a temporary JSON object with these fields before rendering the response.

## Common Fields

- `schema_version`: `1`.
- `workflow`: `refinement`.
- `target`: `baseline_fingerprint`, `current_fingerprint`,
  `baseline_head_sha`, `current_head_sha`, and exact `paths` from both bundles.
- `intent`: non-empty `goal`, `must_not_change`, `invariants`,
  `owner_boundary`, and boolean `user_visible`.
- `scope`: empty `initial_owned_paths` and `current_owned_paths`, positive
  `cycle`, `scope_expansion_approved: false`, and optional `new_evidence`.
- `file_coverage`: empty unless external workspace drift occurred; then cover
  every changed path while returning a non-confident decision.
- `evidence`: unique `{id, status, classification, detail}` entries.
- `scenarios`: strategy risks as `{behavior, status, evidence_ids, reason}`.
- `behavior_proof`: normally `NOT_APPLICABLE` with reason; use `PROVEN` only
  when behavior evidence is part of the refinement.
- `gates`: read-only evidence gates with `name`, `mandatory`, `status`,
  `evidence_ids`, and `reason`.
- `external_actions`: normally empty. `PUBLISHED` always requires an explicit
  request and passing evidence, but refinement itself must not publish.

## Refinement Fields

- `claims`: `{claim, status, material, evidence_ids}` entries. Use
  `FACT|ASSUMPTION|UNKNOWN`; every fact needs evidence.
- `loopholes`: `{loophole, status, evidence_ids}` entries. Use
  `CLOSED|REJECTED|OPEN`; include at least one adversarial candidate, and give
  closed or rejected entries evidence.
- `verification_plan`: `{proof, status, evidence_ids, reason}` entries. Use
  `PASS|PLANNED|NOT_RUN|BLOCKED|NOT_APPLICABLE`. `PLANNED` means an exact
  executable proof intentionally deferred until implementation; it requires a
  reason and no executed evidence. `NOT_RUN` remains unresolved.
- `decision`: `result` and `remaining`. Use
  `HIGH_CONFIDENCE|NOT_CONFIDENT|BLOCKED`.

## Consistency Rules

- `HIGH_CONFIDENCE` requires no material assumption or unknown, no open
  loophole, no `NOT_RUN` or `BLOCKED` verification, no mandatory-gate failure,
  no scope mutation, and no remaining work. Future proof may be `PLANNED`.
- `NOT_CONFIDENT` or `BLOCKED` requires concrete remaining work.
- Baseline and current `head_sha`, fingerprint, and workspace state must match
  because this workflow is read-only.
- Keep the report outside the repository and validate it with:

```bash
python3 scripts/validate_report.py \
  --baseline baseline.json --current current.json report.json
```

## Rendered Response

Return decision, refined strategy, facts, removed and remaining assumptions,
loopholes, corrections, verification plan, blockers, and residual risk.
