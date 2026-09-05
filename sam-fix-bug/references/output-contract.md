# Bugfix Report Contract

Write a temporary JSON object with these fields before rendering the response.

## Common Fields

- `schema_version`: `1`.
- `workflow`: `bugfix`.
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
- `scenarios`: `{behavior, status, evidence_ids, reason}` entries.
- `behavior_proof`: `status`, `evidence_ids`, and `reason` when not proven.
- `gates`: `{name, mandatory, status, evidence_ids, reason}` entries.
- `external_actions`: `{kind, requested, status, evidence_ids}` entries. Use
  `NOT_REQUESTED|DRAFTED|PUBLISHED|BLOCKED`.

## Bugfix Fields

- `bug`: non-empty `observed`, `expected`, `root_cause`, `fix_boundary`, and
  `root_cause_evidence_ids`.
- `reproduction`: `status`, `evidence_ids`, and `reason`. Use
  `REPRODUCED|PROVEN_BY_CONTRACT|BLOCKED`.
- `regression_proof`: one of:
  - `DIFFERENTIAL` with at least one `FAIL`, no `NOT_RUN`, in
    `failing_evidence_ids`, and only passing `passing_evidence_ids`.
  - `ALTERNATIVE_PROOF` with passing `evidence_ids` and `reason`.
  - `NOT_PROVEN` with `reason`.
- `decision`: `result` and `remaining`. Use
  `COMPLETE|CHANGES_REQUIRED|BLOCKED`.

## Consistency Rules

- Baseline and current `head_sha` must match. Fingerprints may differ only when
  the captured file ledger has a corresponding delta.
- `COMPLETE` requires proven reproduction or contract violation, root-cause
  evidence, regression proof, no required scenario gap, no introduced failure,
  all mandatory gates passed, required behavior proof, safe scope, and preserved
  dirty work.
- A non-complete decision requires at least one concrete remaining item.
- `PUBLISHED` requires `requested: true` and passing evidence.
- Keep the report outside the repository and validate it with:

```bash
python3 scripts/validate_report.py \
  --baseline baseline.json --current current.json report.json
```

## Rendered Response

Return observed versus expected behavior, reproduction, root cause, correction,
exact files, regression scenarios, validations, behavior proof, gates,
external-action status, decision, and residual risk.

Scope authorization records changes to the agreed goal or contracts. File and
line counts are evidence, not an automatic approval threshold. Every changed
path must still be in scope and accounted for.
