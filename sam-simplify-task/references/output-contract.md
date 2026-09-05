# Simplification Report Contract

Write a temporary JSON object with these fields before rendering the response.

## Common Fields

- `schema_version`: `1`.
- `workflow`: `simplification`.
- `target`: `baseline_fingerprint`, `current_fingerprint`,
  `baseline_head_sha`, `current_head_sha`, and exact `paths` from both bundles.
- `intent`: non-empty `goal`, `must_not_change`, `invariants`,
  `owner_boundary`, and boolean `user_visible`.
- `scope`: `initial_owned_paths`, `current_owned_paths`, positive `cycle`,
  boolean `scope_expansion_approved`, and optional `new_evidence`.
- `file_coverage`: one `{path, reason}` entry per post-baseline changed path.
- `evidence`: unique `{id, status, classification, detail}` entries.
- `scenarios`: preserved contracts as `{behavior, status, evidence_ids, reason}`.
- `behavior_proof`: `status`, `evidence_ids`, and `reason` when not proven.
- `gates`: `{name, mandatory, status, evidence_ids, reason}` entries.
- `external_actions`: normally empty; publication requires explicit request and
  passing evidence.

## Simplification Fields

- `candidates`: entries with `opportunity` and one status:
  - `APPLIED` with `complexity_removed` and passing `evidence_ids`.
  - `SKIPPED` with `reason`.
  - `BLOCKED` with `reason`.
- `decision`: `result` and `remaining`. Use
  `SIMPLEST_DEFENSIBLE|NO_CHANGE|BLOCKED`.

## Consistency Rules

- Baseline and current `head_sha` must match. Fingerprints may differ only when
  the captured file ledger has a corresponding delta.
- `SIMPLEST_DEFENSIBLE` requires at least one applied candidate, a real scope
  delta, passing behavior proof, all mandatory gates passed, preserved dirty
  work, and no blocked required candidate.
- `NO_CHANGE` requires no applied candidate and no scope delta.
- `BLOCKED` requires concrete remaining work.
- Every scope delta path must be owned and covered exactly once.
- Keep the report outside the repository and validate it with:

```bash
python3 scripts/validate_report.py \
  --baseline baseline.json --current current.json report.json
```

## Rendered Response

Return decision, candidates applied/skipped/blocked, exact complexity removed,
behavior preserved, validations, files changed, residual risk, and next action.

Scope authorization records changes to the agreed goal or contracts. File and
line counts are evidence, not an automatic approval threshold. Every changed
path must still be in scope and accounted for.
