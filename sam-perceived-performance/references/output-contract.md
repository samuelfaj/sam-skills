# Output Contract

`scripts/scaffold_perceived_report.py` writes the complete `report.json` skeleton (`schema_version: 1`, `workflow: "perceived-performance"`, one pre-linked `I-001`/`T-001`). It copies `target`, each receipt's `id`/`classification`/`status`/`command`/`receipt`, the `file_coverage` paths (the scope delta), and the four gate names. Every other field is a placeholder: `""`, `null`, and `TODO:<enum>` never validate, but some `[]` can (owned paths, `remaining`), so fill every list deliberately. Owned paths come from the step-1 freeze, never from the delta. Fill per these tables.

| Field | Rule |
| --- | --- |
| bundles | `baseline`/`current` are read-only captures of the same repository and `paths`; `target.baseline_fingerprint`, `target.current_fingerprint`, `target.paths` equal them; differing HEAD blocks |
| `intent` | non-empty `goal`, `owner_boundary`; non-empty lists `must_not_change`, `invariants` (include honesty invariants) |
| `environment` | `kind` `unknown`/`local`/`test`/`dev`/`staging`/`production`; non-empty `identity`, `device_profile` (CPU throttle, viewport, cache state), `network_profile` (bandwidth, latency) |
| ids | `E-`, `I-`, `T-` + ≥3 digits, unique; `evidence` and `interactions` non-empty; `interactions[].technique_ids` ↔ `techniques[].interaction_ids` reciprocal and known |
| `evidence[]` | `kind` `MEASUREMENT`/`TEST`/`INSPECTION`; `status` `PASS`/`FAIL`/`NOT_RUN` (`NOT_RUN` needs `reason` and no receipt); `classification` `BASELINE`/`TARGET`/`INTRODUCED`/`ENVIRONMENT`/`EXTERNAL`; non-empty `detail` (e.g. "median of 7 samples"). `MEASUREMENT`/`TEST` need an absolute `receipt` whose hash, logs, id, status, classification, and argv text recompute; `TARGET`/`INTRODUCED` need ≥2 runs. `INSPECTION` cites no receipt and never closes a proof. An `INTRODUCED` `FAIL` blocks |
| `interactions[]` | non-empty `name`, `entry_point` (`path:line`), `trigger`, `blocking_work`; `status` `IMPROVED` (needs an applied technique and `after.feedback_ms` < `baseline.feedback_ms`), `UNCHANGED` (needs `reason`, no applied technique), or `BLOCKED` (needs `reason`, omits metric blocks, blocks the decision) |
| `baseline`, `after` | integer ms `feedback_ms`, `meaningful_ms`, `settled_ms`, `dead_time_ms` in physical order; `samples` ≥ 5; `evidence_ids` cite passing `MEASUREMENT`/`TEST`, including ≥1 `BASELINE` item for `baseline` and ≥1 `TARGET` item for `after`. `after` must meet its class budget; a `settled_ms` increase over `max(25, 5% of baseline)` blocks |
| `techniques[]` | non-empty `name`; `status` `APPLIED`, `REJECTED`, or `BLOCKED` (non-applied need `reason`; `BLOCKED` blocks); booleans `optimistic`, `irreversible_effect`; `progress_signal` `REAL`/`SYNTHETIC`/`NONE`; `progress_presentation` `DETERMINATE` (needs `REAL`), `INDETERMINATE`, or `NONE` (required when the signal is `NONE`); integer `added_delay_ms` ≤ 200, with `added_delay_reason` when > 0 |
| `APPLIED` technique | repository-relative `paths`, each changed and inside `scope.current_owned_paths`; non-empty `accessibility` (announcement and reduced motion); passing `evidence_ids`. If `optimistic`: `reversible: true`, `irreversible_effect: false`, non-empty `failure_mode`, `rollback`, `on_failure_ui`, and passing `failure_path_evidence_ids` |
| `file_coverage` | every scope-delta path exactly once, each with a non-empty `reason`; a changed workspace needs ≥1 `APPLIED` technique |
| `scope` | repository-relative `initial_owned_paths`, `current_owned_paths`; a change outside `current_owned_paths` or to pre-existing dirty work blocks; boolean `scope_expansion_approved`; integer `cycle` ≥ 1, and `cycle` > 2 needs `new_evidence: true` |

Scope authorization records changes to the agreed goal or contracts; file and line counts are evidence, not an approval threshold.

## Gates

All four are listed with `mandatory: true`; applicability is derived from the change and cannot be waived. `PASS` cites passing `MEASUREMENT`/`TEST` evidence (≥1 `TARGET` item for the two latency gates); any other status needs `reason`; `FAIL` or `NOT_RUN` blocks.

| Gate | Proven by | `NOT_APPLICABLE` allowed |
| --- | --- | --- |
| `honest-feedback` | the `TARGET` measurement cited by `after` | never |
| `real-latency-non-regression` | the same measurement; the validator recomputes the budget | never |
| `failure-path-proof` | passing failure-path test | only with no applied optimistic technique |
| `accessibility-announcement` | passing announcement test | only with no applied technique |

## Decisions

| `decision.result` | When |
| --- | --- |
| `PERCEIVED_INSTANT` | ≥1 `IMPROVED` interaction and every one is instant, none is `BLOCKED`, all gates pass; the only status claiming instant feel |
| `IMPROVED` | ≥1 `IMPROVED` interaction, all gates pass, but pending time remains; say what remains in the final response (the illusion's boundary), not in `remaining` |
| `NO_CHANGE` | no delta, nothing applied or improved, and every interaction's `after` already meets its class budget |
| `BLOCKED` | measurement, authorization, or a safe technique is unavailable; an interaction that misses its budget with no honest technique is `BLOCKED` and `remaining` names the real latency |

`PERCEIVED_INSTANT` and `IMPROVED` also need no `FLAKY` receipt. A completed decision (the first three) lists no `remaining` and contradicts any blocker; `BLOCKED` lists what is needed in `remaining`.

Fix from the validator's error lines and patch the report in place; do not read validator source or rewrite the whole report.

## Return

Child mode (a parent or phase worker invoked this skill) — the final message is exactly:

```
RESULT sam-perceived-performance <PERCEIVED_INSTANT|IMPROVED|NO_CHANGE|BLOCKED>
report: <absolute path>
validator: <exact last line of the validator output>
head: <sha> fingerprint: <current scope fingerprint>
open: <n>
- <one line per open required item, max 10>
```

Standalone: at most 15 lines plus the report path, never the JSON: the decision; per interaction `feedback_ms` and `dead_time_ms` before → after with the class of its real latency; each applied technique, what it makes feel instant, and what happens when the work fails; techniques rejected for honesty and why (an unshipped optimistic path on an irreversible action is a result); real `settled_ms` before → after, including any in-budget regression; blockers and what unblocks them; the illusion's boundary — what shows immediately versus what still settles.
