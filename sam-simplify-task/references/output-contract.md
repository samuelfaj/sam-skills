# Simplification Report Contract

`--scaffold` derives `schema_version`, `workflow`, `target`, and
`file_coverage` paths; never hand-edit them. "Blocks" means
completion is invalid. PROVEN or PASS needs PASS evidence; every other
scenario, behavior-proof, and gate status needs a concrete reason. A HEAD
change, or a fingerprint change without a file delta, blocks.

| Field | Shape and rules |
|---|---|
| `intent` | goal, owner_boundary: text. must_not_change, invariants: non-empty lists. user_visible: bool; true blocks unless behavior_proof is PROVEN. |
| `scope` | initial_owned_paths, current_owned_paths: repo-relative lists; any changed path outside current_owned_paths blocks, pre-existing dirty work included. cycle: correction cycles so far, from 1; add 1 per in-run correction cycle (`--from` adds 1 itself); above 2 blocks unless new_evidence is true. scope_expansion_approved: bool, true only when the user or parent authorized a change to the frozen goal or contract. |
| `file_coverage` | [{path, reason}]: each delta path once, non-empty reason. |
| `evidence` | Non-empty [{id, status, classification, detail}], unique ids; enums per the evidence policy; FAIL + INTRODUCED blocks. Optional reused_from (absolute path of a completed simplification/bugfix/feature report whose validator passed, ending at this baseline's head, fingerprint, and paths) + reused_id (a PASS entry there, not itself reused, cited as behavior, scenario, or gate proof), status PASS; after an edit, only a baseline record (never proof). |
| `scenarios` | Preserved contracts: non-empty [{behavior, status, evidence_ids, reason}]; statuses per the evidence policy; MISSING_REQUIRED blocks. |
| `behavior_proof` | {status, evidence_ids, reason}; statuses per the evidence policy. Any delta needs PROVEN, whatever the decision. |
| `gates` | Non-empty [{name, mandatory (bool), status, evidence_ids, reason}]; PASS/FAIL/NOT_RUN/NOT_APPLICABLE. Mandatory non-PASS blocks. |
| `external_actions` | Normally empty. [{kind, requested (bool), status, evidence_ids}]; NOT_REQUESTED/DRAFTED/PUBLISHED/BLOCKED. PUBLISHED needs requested true and PASS evidence; requested false allows only NOT_REQUESTED/DRAFTED. |
| `candidates` | Non-empty [{opportunity, status, complexity_removed, evidence_ids, reason}]. APPLIED: complexity_removed, PASS evidence_ids. SKIPPED: reason. BLOCKED blocks. |
| `decision` | {result, remaining}. Completions SIMPLEST_DEFENSIBLE (needs an applied candidate and a delta) and NO_CHANGE (no edit justified; forbids both) need nothing blocking and empty remaining. BLOCKED (missing proof, access, authorization, or scope expansion) needs >= 1 concrete remaining item. |

Fix from the validator's error lines and patch the report in place; do not read
validator source or rewrite the whole report.

## Return

Child mode, exactly:

```
RESULT sam-simplify-task <decision.result>
report: <absolute report path>
validator: <exact last line of the validator output>
head: <target.current_head_sha> fingerprint: <target.current_fingerprint>
open: <count of decision.remaining>
- <one line per remaining item, max 10>
```

Standalone: at most 15 lines (decision, candidates by status with complexity
removed, preserved behavior and validations, changed files, residual risk, next
action) plus the report path; never repeat the JSON report or claim unrun proof.
