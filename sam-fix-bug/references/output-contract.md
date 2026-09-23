# Bugfix Report Contract

`--scaffold` derives `schema_version`, `workflow`, `target`, and
`file_coverage` paths; never hand-edit them. "Blocks" means completion is
invalid. PROVEN or PASS needs PASS evidence; every other scenario,
behavior-proof, and gate status needs a concrete reason. A HEAD change, or a
fingerprint change without a file delta, blocks.

| Field | Shape and rules |
|---|---|
| `intent` | goal, owner_boundary: text. must_not_change, invariants: non-empty lists. user_visible: bool; true blocks unless behavior_proof is PROVEN. |
| `scope` | initial_owned_paths, current_owned_paths: repo-relative lists; any changed path outside current_owned_paths blocks, pre-existing dirty work included. cycle: correction cycles so far, from 1; add 1 per in-run correction cycle (`--from` adds 1 itself); above 2 blocks unless new_evidence is true. scope_expansion_approved: bool, true only when the user or parent authorized a change to the frozen goal or contract. |
| `file_coverage` | [{path, reason}]: each delta path once, non-empty reason. |
| `evidence` | Non-empty [{id, status, classification, detail}], unique ids; enums per the evidence policy; FAIL + INTRODUCED blocks; no reused_from. |
| `scenarios` | Non-empty [{behavior, status, evidence_ids, reason}]; statuses per the evidence policy; MISSING_REQUIRED blocks. |
| `behavior_proof` | {status, evidence_ids, reason}; statuses per the evidence policy. |
| `gates` | Non-empty [{name, mandatory (bool), status, evidence_ids, reason}]; PASS/FAIL/NOT_RUN/NOT_APPLICABLE. Mandatory non-PASS blocks, except parent-owned: name `code-review`, `coverage`, or `browser-proof`, NOT_APPLICABLE, reason exactly `owned by parent phase`. |
| `external_actions` | [{kind, requested (bool), status, evidence_ids}]; NOT_REQUESTED/DRAFTED/PUBLISHED/BLOCKED. PUBLISHED needs requested true and PASS evidence; requested false allows only NOT_REQUESTED/DRAFTED. |
| `bug` | observed, expected, root_cause, fix_boundary: text; root_cause_evidence_ids: non-empty. |
| `reproduction` | {status, evidence_ids, reason}; REPRODUCED/PROVEN_BY_CONTRACT need evidence; BLOCKED blocks. |
| `regression_proof` | DIFFERENTIAL: failing_evidence_ids with >= 1 FAIL and no NOT_RUN, all-PASS passing_evidence_ids. ALTERNATIVE_PROOF: reason, PASS evidence_ids. NOT_PROVEN blocks. |
| `decision` | {result, remaining}. COMPLETE needs nothing blocking and empty remaining; CHANGES_REQUIRED/BLOCKED need >= 1 concrete remaining item. |

Fix from the validator's error lines and patch the report in place; do not read
validator source or rewrite the whole report.

## Return

Child mode, exactly:

```
RESULT sam-fix-bug <decision.result>
report: <absolute report path>
validator: <exact last line of the validator output>
head: <target.current_head_sha> fingerprint: <target.current_fingerprint>
open: <count of decision.remaining>
- <one line per remaining item, max 10>
```

Standalone: at most 15 lines (decision, root cause, changed files, key proof,
external actions, residual risk) plus the report path; never repeat the JSON
report or claim unrun proof.
