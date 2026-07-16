# Feature Report Contract

Write a temporary JSON object with these fields before rendering the response.

## Common Fields

- `schema_version`: `1`.
- `workflow`: `feature`.
- `target`: `baseline_fingerprint`, `current_fingerprint`,
  `baseline_head_sha`, `current_head_sha`, and exact `paths` from both bundles.
- `intent`: non-empty `goal`, `must_not_change`, `invariants`,
  `owner_boundary`, and boolean `user_visible`.
- `scope`: `initial_owned_paths`, `current_owned_paths`, positive `cycle`,
  boolean `scope_expansion_approved`, and optional boolean `new_evidence`.
- `file_coverage`: one `{path, reason}` entry for every path changed after the
  baseline, with no duplicates or omissions.
- `evidence`: unique `{id, status, classification, detail}` entries. Use
  `PASS|FAIL|NOT_RUN` and classifications from the evidence policy.
- `scenarios`: `{behavior, status, evidence_ids, reason}` entries. Include
  `reason` for every status except `PROVEN`.
- `behavior_proof`: `status`, `evidence_ids`, and `reason` when not proven.
- `gates`: `{name, mandatory, status, evidence_ids, reason}` entries.
- `external_actions`: `{kind, requested, status, evidence_ids}` entries. Use
  `NOT_REQUESTED|DRAFTED|PUBLISHED|BLOCKED`.

## Feature Fields

- `requirements`: unique requirements with `id`, `text`, `status`, `material`,
  and `evidence_ids`. Use `CONFIRMED|ASSUMED|BLOCKED`.
- `tdd`: one of:
  - `RED_GREEN` with at least one `FAIL`, no `NOT_RUN`, in
    `red_evidence_ids`, and only passing `green_evidence_ids`.
  - `ALTERNATIVE_PROOF` with `proof_evidence_ids` and `reason`.
  - `NOT_APPLICABLE` with `reason`.
  - `BLOCKED` with `reason`.
- `decision`: `result` and `remaining`. Use
  `COMPLETE|CHANGES_REQUIRED|BLOCKED`.

## Consistency Rules

- Baseline and current `head_sha` must match. Fingerprints may differ only when
  the captured file ledger has a corresponding delta.
- `COMPLETE` requires no remaining work, unresolved material requirement,
  required scenario gap, introduced failure, failed mandatory gate, unproven
  user-visible behavior, scope breach, or dirty-work mutation.
- A non-complete decision requires at least one concrete remaining item.
- `PUBLISHED` requires `requested: true` and passing evidence.
- Keep the report outside the repository and validate it with:

```bash
python3 scripts/validate_report.py \
  --baseline baseline.json --current current.json report.json
```

## Rendered Response

Return requirements and intent, implementation summary, exact files, scenario
and TDD proof, validations, behavior proof, gate results, external-action status,
decision, and remaining risk. Do not claim unrun proof.
