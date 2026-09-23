# Output Contract

Scaffold the report from a spec, then validate; the validator enforces everything here.

## Report

No keys beyond these; `+` marks a non-empty list; lists hold unique non-empty strings.

```json
{"schema_version": 2,
 "task": {"classification": "T0|T1|T2|T3", "goal": "...", "success_criteria": ["+"], "constraints": [], "no_go": ["+"],
  "risk_flags": [], "active_host": "codex|claude-code|grok", "changed_artifacts": ["<class>"],
  "changed_files": [{"path": "src/a.py", "artifact_class": "<class>", "producer_task_id": "E1"}],
  "review_requested": false, "controller_certainty": "absolute|high|medium|low (optional; omitted = medium)"},
 "dag": [{"id": "E1", "kind": "EXECUTION|ORCHESTRATION|REVIEW", "owner": "worker-N|controller-N|reviewer-N",
  "capability": "LIGHT|STANDARD|DEEP|REVIEWER",
  "runtime": {"host": "...", "role": "fast_scan|routine_worker|deep_worker|genius_worker|ultra_worker|reviewer",
   "model": "...", "effort": "...", "fallback_reason": null},
  "depends_on": [], "objective": "...", "no_go": ["+"], "proof_requirements": ["+"], "artifact_classes": ["<class>"],
  "writable_paths": ["src"], "direct_action_reason": null, "status": "PENDING|RUNNING|COMPLETE|BLOCKED",
  "evidence_ids": ["V1"], "blocker": {"kind": "EXTERNAL|AUTHORITY|USER_DECISION|DEPENDENCY", "source": "...", "evidence_ids": ["+"]}}],
 "evidence": [{"id": "V1", "task_id": "E1", "requirement": "<a proof_requirements entry of task_id>",
  "type": "COMMAND|DIFF|FILE|REMOTE|USER|OBSERVATION", "status": "PASS|FAIL|NOT_RUN|INFO",
  "classification": "TARGET|BASELINE|ENVIRONMENT|EXTERNAL", "detail": "short summary (≤ ~500 chars), no raw logs"}],
 "review_gate": {"required": true, "reasons": ["..."], "status": "PASS|FAIL|NOT_RUN|NOT_REQUIRED",
  "review_task_id": "R1", "rounds": 1},
 "decision": {"result": "COMPLETE|BLOCKED|IN_PROGRESS", "remaining_task_ids": []}}
```

`<class>`: `CODE` `TEST` `DOCS` `CONFIG` `DATA` `RELEASE` `OTHER`. Paths are normalized and repo-relative. `runtime` is `null` on `ORCHESTRATION` nodes; `blocker` is `null` unless `BLOCKED`.

## Spec

Write only judgment fields; `scripts/scaffold_report.py` derives the rest.

- `task`: the report `task` without `changed_*`. `active_host` is required; `constraints`, `risk_flags` default `[]`, `review_requested` false.
- `nodes`: `dag` entries without `owner`, `runtime`, `evidence_ids`. `status` defaults `PENDING`; `artifact_classes` defaults to the classes of assigned files; `"genius": true` binds the genius row; `fallback_reason` as needed; `blocker` (`kind`, `source`) only on `BLOCKED` nodes.
- `evidence`: as in the report; omit `requirement` when the node has one.
- `files`: `{"<path>": "<class>" | {"class": "<class>", "producer": "<id>"}}`. With `--freeze`, every path changed after the SKILL.md §1 snapshot is added, each assigned to the one producer whose writable scope holds it; a changed path outside every scope, or a listed path that did not change, is an error. For a changed path no run worker made, follow SKILL.md §4 step 1. Omit a class only when the producer declares one.
- `review_rounds`: completed review rounds; with `--freeze` the scaffold counts `<run>/review-<n>.diff` files and a typed value must match.

## Invariants

- Runtime: `host` = `task.active_host`; role, model, effort = the SKILL.md §3 row for the capability, or the genius row on `STANDARD`/`DEEP`. Codex models match exactly. A non-empty `fallback_reason` allows any model, effort, and role from that host's §3 column (never the advisor rows).
- Owner prefix matches kind; only read-only `REVIEW` nodes use `REVIEWER`.
- `T0`/`T1`: one execution node (`T0` `LIGHT`, `T1` `LIGHT`/`STANDARD`). `T2`/`T3`: 1-3; `T3` needs a `DEEP` one.
- Writable non-review nodes are producers with `artifact_classes`; read-only nodes have none. Writable `ORCHESTRATION` needs `direct_action_reason`, else `null`.
- Dependencies exist and are acyclic; `RUNNING`/`COMPLETE` nodes depend only on `COMPLETE` ones.
- `changed_artifacts` = classes in `changed_files`. Each file is unique, inside its producer's writable scope, with a class that producer declares. A `COMPLETE` producer owns ≥ 1 file; its manifest classes equal its `artifact_classes`.
- Evidence is referenced only by its own task. A `COMPLETE` node proves every requirement with its own `TARGET` `PASS` item.
- Blocker `evidence_ids` are owned by the node and classified `ENVIRONMENT`/`EXTERNAL`. `DEPENDENCY` names a `BLOCKED` direct dependency; other kinds need `COMPLETE` dependencies.
- Gate: required when a `REVIEW` node exists or a SKILL.md §5 trigger fires. Required gates have reasons, are never `NOT_REQUIRED`, and name a `REVIEW` node depending on every producer with a non-producer owner; `PASS` needs it `COMPLETE` with own `TARGET` `PASS` evidence and no unproven `TARGET` evidence. Skip reasons need SKILL.md §5 eligibility; certainty `absolute` only with the absolute skip. Non-required: `NOT_REQUIRED`, `review_task_id` `null`, `rounds` absent or 0.
- Rounds: at most 3; `PASS`/`FAIL` gates record ≥ 1; 3 with `FAIL` enforces the SKILL.md §5 stop.
- Decision: `COMPLETE` only when every node is `COMPLETE`, every completed producer has dedicated `TARGET` `PASS` proof, all `TARGET` evidence is `PASS`, the manifest reconciles, the gate passes or is not required, and no required correction or remaining id is left. Else `remaining_task_ids` = incomplete nodes; `BLOCKED` only with evidence-backed external, authority, user-decision, or dependency provenance: a `BLOCKED` node, nothing runnable (`RUNNING`, or `PENDING` on `COMPLETE` dependencies), every `PENDING` node under blocked work; else `IN_PROGRESS` (something runnable).
