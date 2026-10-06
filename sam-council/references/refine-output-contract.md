# Refinement Report Contract

Cited evidence ids must exist; string lists must not repeat.

| Field | Shape and rules |
| --- | --- |
| `schema_version`, `workflow`, `target` | `1`, `refinement`, and the bundles' `baseline_fingerprint`, `current_fingerprint`, `baseline_head_sha`, `current_head_sha`, `paths` (scaffold) |
| `intent` | Non-empty `goal`, `owner_boundary`, `must_not_change[]`, `invariants[]`; boolean `user_visible` (`true` blocks completion unless `behavior_proof` is `PROVEN`) |
| `scope` | Empty `initial_owned_paths`/`current_owned_paths`; `cycle` >= 1 (> 2 needs `new_evidence: true`); `scope_expansion_approved: false` |
| `file_coverage` | `{path, reason}` per changed path; must equal the baseline-to-current delta, normally `[]`; any delta blocks completion |
| `evidence` | Non-empty, unique-`id` `{id, status PASS\|FAIL\|NOT_RUN, classification TARGET\|INTRODUCED\|BASELINE\|ENVIRONMENT\|EXTERNAL, detail}`; `FAIL`+`INTRODUCED` blocks. Optional `plan_ref` (plan FACT id) + `locator` (its exact locator) needs `PASS` (use classification `TARGET`), top-level absolute `plan_report` (the snapshot), and the locator resolving at the current bundle's head commit or in a changed file whose bytes still match the capture; decision and command locators (`user decision: …`, `command: …`) skip resolution |
| `claims` | Non-empty `{claim, status FACT\|ASSUMPTION\|UNKNOWN, material bool, evidence_ids, probe}`; FACT needs evidence; UNKNOWN needs `probe`; material non-FACT blocks |
| `loopholes` | Non-empty `{loophole, status CLOSED\|REJECTED\|OPEN, evidence_ids}`; `CLOSED`/`REJECTED` need PASS evidence; `OPEN` blocks |
| `verification_plan` | Non-empty `{proof, status, evidence_ids, reason}` (`proof` may cite a plan `V-###`): `PASS` already executed (PASS evidence); `PLANNED` exact proof runnable only after implementation, cites none; `NOT_RUN` unresolved; `BLOCKED`; `NOT_APPLICABLE` concrete reason. Non-PASS needs `reason`; `NOT_RUN`/`BLOCKED` block |
| `scenarios` | May be `[]` (key required); `{behavior, status PROVEN\|MISSING_REQUIRED\|OPTIONAL\|NOT_APPLICABLE, evidence_ids, reason}`; `PROVEN` needs PASS evidence, others `reason`; `MISSING_REQUIRED` blocks |
| `behavior_proof` | `{status PROVEN\|NOT_PROVEN\|NOT_APPLICABLE, evidence_ids, reason}`; normally `NOT_APPLICABLE` with `reason`; `PROVEN` (PASS evidence) only when behavior evidence is part of the refinement |
| `gates` | May be `[]` (key required); read-only `{name, mandatory bool, status PASS\|FAIL\|NOT_RUN\|NOT_APPLICABLE, evidence_ids, reason}`; `PASS` needs PASS evidence, others `reason`; mandatory non-PASS blocks |
| `external_actions` | `[]`; refinement never publishes (validator item: `{kind, requested bool, status NOT_REQUESTED\|DRAFTED\|PUBLISHED\|BLOCKED, evidence_ids}`) |
| `decision` | `result`: `HIGH_CONFIDENCE` only when nothing blocks, with empty `remaining`; else concrete `remaining` work and `BLOCKED` (needs missing access, a user decision, unsafe authorization, or unavailable evidence) or `NOT_CONFIDENT` (required proof remains) |

Completion also fails when the bundles' HEADs differ or the fingerprint changed
without a file delta. Both bundles must be read-only captures of one repository
with identical paths.
