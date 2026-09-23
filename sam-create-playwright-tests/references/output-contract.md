# Output Contract

`scripts/scaffold_report.py` writes every key and derives fingerprints, `target`, `command_definitions.changed`, `commands[]` (not `test_ids`), wiring receipts, and `test_diff_audit`. `+` = non-empty; `*_ids` = resolving string IDs.

| Field | Contents |
| --- | --- |
| intent | summary+, invariants list, no_go list |
| environment | kind unknown/local/test/dev/staging/production, identity+, real_data bool, evidence+ (identity proof plus the exact boot, auth, and seed commands, without secrets; the demo phase reuses them) |
| authorization | publish_requested bool (true for any UPLOADED artifact) |
| command_definitions | inspected true and evidence+ when changed |
| criteria | id, text+ |
| risks | id, criterion_ids, level (step 2), evidence+ or description+ |
| scenarios | id, criterion_ids, risk_ids, status (step 2), test_ids, artifact_ids, reason |
| tests | id, scenario_ids, command_ids, path+, name+, regression_proof {status (step 3), evidence+} |
| commands | id, test_ids, command+, status, classification, receipt, evidence+ |
| artifacts | id, scenario_ids, status LOCAL/UPLOADED/NOT_CREATED, safety_review true, receipt and readback_verified true when UPLOADED |
| cleanup | id, resource+, status CLEANED/RETAINED/BLOCKED, reason unless CLEANED |
| test_diff_audit | status PASS/FAIL, evidence+, disproven [{id, kind, path, reason+}] |
| test_wiring | status PROVEN/NOT_PROVEN/NOT_APPLICABLE, before_receipt, after_receipt, discovered_tests, reason unless PROVEN |
| behavior_proof | status PROVEN/NOT_PROVEN/FALLBACK, evidence+ |
| decision | COMPLETE/PARTIAL/BLOCKED |

- IDs are unique report-wide. Every ledger from criteria to cleanup is non-empty (nothing produced: one `NOT_CREATED` artifact linked to a scenario). Every `*_ids` list is non-empty except scenario `artifact_ids`, and scenario `test_ids` unless `AUTOMATED`. Reciprocal links: scenario/test, test/command, scenario/artifact. `MANUAL_PROOF`/`REDUNDANT`/`NOT_COVERED` need `reason` or `evidence`.
- `behavior_proof` `PROVEN` means the real product UI and linked backend path.
- Commands: `PASS`/`FAIL` match their cited absolute receipt, whose hashes and exit codes are recomputed; `NOT_RUN` has a reason and no receipt.
- Wiring `PROVEN`: non-empty `discovered_tests`, each absent from the before log and present in the after log.
- Audit: `PASS` over findings needs a `disproven` entry matching each finding's `id`, `kind`, and `path`.

## Decision

`COMPLETE` requires: no `NOT_COVERED` scenario; no `NOT_PROVEN` test; every `TARGET` `PASS`; no `FLAKY` command; audit `PASS`; wiring `PROVEN` or `NOT_APPLICABLE`; `behavior_proof` `PROVEN`; no `BLOCKED` cleanup; when publication was requested, every uploaded video or image in host player/image markup with passing readback (never hyperlink-only or committed media).

`PARTIAL`: honest residual gaps. `BLOCKED`: unsafe environment, scope, authorization, or execution conditions.

## Re-invocation

Rebuild the final bundle. Same head and fingerprint: keep `<receipts>` and run only missing or `NOT_RUN` commands (a `FAIL` only per the step-6 rule); if none remain, re-run only the validator. Otherwise rebuild both bundles, take the next `<receipts>`, re-establish each test's regression proof, and re-run every `PASS`/`FAIL` command, including every `TARGET` spec with video capture. Scaffold with `--previous <previous>`.

## Return

Child mode (invoked by a parent or phase worker): the final message is exactly this block. Standalone: at most 15 lines plus the report path; never repeat the report.

```
RESULT sam-create-playwright-tests <COMPLETE|PARTIAL|BLOCKED>
report: <absolute path>
validator: <exact last line of the validator output>
head: <sha> fingerprint: <final bundle fingerprint>
open: <n>
- <one line per open required item, max 10>
```
