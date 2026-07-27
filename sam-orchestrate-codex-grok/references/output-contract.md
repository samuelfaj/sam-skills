# Output Contract (Codex–Grok profile)

## Contents

- Report shape
- Allowed values
- Runtime binding
- Invariants

## Report Shape

Create a temporary JSON report with this shape:

```json
{
  "schema_version": 2,
  "task": {
    "classification": "T2",
    "goal": "Deliver the requested change",
    "success_criteria": ["Focused validation passes"],
    "constraints": [],
    "no_go": ["Do not change unrelated files"],
    "risk_flags": [],
    "active_host": "codex",
    "changed_artifacts": ["CODE", "TEST"],
    "changed_files": [
      {"path": "src/service.py", "artifact_class": "CODE", "producer_task_id": "E1"},
      {"path": "tests/test_service.py", "artifact_class": "TEST", "producer_task_id": "E2"}
    ],
    "review_requested": false,
    "controller_certainty": "medium"
  },
  "dag": [
    {
      "id": "E1",
      "kind": "EXECUTION",
      "owner": "worker-1",
      "capability": "STANDARD",
      "runtime": {
        "host": "grok",
        "role": "routine_worker",
        "model": "grok-4.5",
        "effort": "high",
        "fallback_reason": null
      },
      "depends_on": [],
      "objective": "Implement the bounded service change",
      "no_go": ["Do not edit tests"],
      "proof_requirements": ["Runtime diff matches the assigned scope"],
      "artifact_classes": ["CODE"],
      "writable_paths": ["src/service.py"],
      "direct_action_reason": null,
      "status": "COMPLETE",
      "evidence_ids": ["V1"],
      "blocker": null
    },
    {
      "id": "E2",
      "kind": "EXECUTION",
      "owner": "worker-2",
      "capability": "STANDARD",
      "runtime": {
        "host": "grok",
        "role": "routine_worker",
        "model": "grok-4.5",
        "effort": "high",
        "fallback_reason": null
      },
      "depends_on": [],
      "objective": "Add focused regression coverage",
      "no_go": ["Do not edit runtime code"],
      "proof_requirements": ["Focused regression tests pass"],
      "artifact_classes": ["TEST"],
      "writable_paths": ["tests/test_service.py"],
      "direct_action_reason": null,
      "status": "COMPLETE",
      "evidence_ids": ["V2"],
      "blocker": null
    },
    {
      "id": "R1",
      "kind": "REVIEW",
      "owner": "reviewer-1",
      "capability": "REVIEWER",
      "runtime": {
        "host": "codex",
        "role": "reviewer",
        "model": "gpt-5.6-sol",
        "effort": "medium",
        "fallback_reason": null
      },
      "depends_on": ["E1", "E2"],
      "objective": "Review the combined result independently",
      "no_go": ["Do not modify artifacts"],
      "proof_requirements": ["Independent review finds no required correction"],
      "artifact_classes": [],
      "writable_paths": [],
      "direct_action_reason": null,
      "status": "COMPLETE",
      "evidence_ids": ["V3"],
      "blocker": null
    }
  ],
  "evidence": [
    {
      "id": "V1",
      "task_id": "E1",
      "requirement": "Runtime diff matches the assigned scope",
      "type": "DIFF",
      "status": "PASS",
      "classification": "TARGET",
      "detail": "Inspected service diff stays within the assigned file"
    },
    {
      "id": "V2",
      "task_id": "E2",
      "requirement": "Focused regression tests pass",
      "type": "COMMAND",
      "status": "PASS",
      "classification": "TARGET",
      "detail": "Focused regression command exited successfully"
    },
    {
      "id": "V3",
      "task_id": "R1",
      "requirement": "Independent review finds no required correction",
      "type": "OBSERVATION",
      "status": "PASS",
      "classification": "TARGET",
      "detail": "Read-only reviewer found no required correction"
    }
  ],
  "review_gate": {
    "required": true,
    "reasons": ["Code and tests changed", "Multiple producers contributed"],
    "status": "PASS",
    "review_task_id": "R1"
  },
  "decision": {
    "result": "COMPLETE",
    "remaining_task_ids": []
  }
}
```

Allowed values:

- Task: `T0`, `T1`, `T2`, `T3`.
- `controller_certainty` (optional): `absolute`, `high`, `medium`, `low`.
  Omitted/`null` is treated as `medium` for gate decisions.
- Active host (controller): **`codex` only** for this profile.
- Artifact: `CODE`, `TEST`, `DOCS`, `CONFIG`, `DATA`, `RELEASE`, `OTHER`.
- Kind: `EXECUTION`, `ORCHESTRATION`, `REVIEW`.
- Capability: `LIGHT`, `STANDARD`, `DEEP`, `REVIEWER`.
- Runtime role: `fast_scan`, `routine_worker`, `deep_worker`, `genius_worker`,
  `reviewer`.
- Runtime host: `grok` (LIGHT/STANDARD/DEEP) or `codex` (REVIEWER / genius).
- Node status: `PENDING`, `RUNNING`, `COMPLETE`, `BLOCKED`.
- Blocker kind: `EXTERNAL`, `AUTHORITY`, `USER_DECISION`, `DEPENDENCY`.
- Evidence type: `COMMAND`, `DIFF`, `FILE`, `REMOTE`, `USER`, `OBSERVATION`.
- Evidence status: `PASS`, `FAIL`, `NOT_RUN`, `INFO`.
- Evidence classification: `TARGET`, `BASELINE`, `ENVIRONMENT`, `EXTERNAL`.
- Gate status: `PASS`, `FAIL`, `NOT_RUN`, `NOT_REQUIRED`.
- Gate skip reasons: `micro_task_absolute_certainty`,
  `micro_task_high_certainty`, or a short non-trigger explanation.
- Decision: `COMPLETE`, `BLOCKED`, `IN_PROGRESS`.

## Fan-out and DEEP invariants

- Execution producers: max 1 for `T0`/`T1`; max 3 for `T2`/`T3`.
- `DEEP` capability only when `classification` is `T3` or `risk_flags` is
  non-empty.
- Evidence `detail` should be a short summary (prefer under ~500 characters for
  COMMAND logs); do not paste multi-KB raw logs into the report.

## Runtime binding

`task.active_host` is required and must be `codex`. Every delegated `EXECUTION`
and `REVIEW` node requires a `runtime` object matching
[host-runtime-matrix.md](host-runtime-matrix.md) for the node capability.

Standard Grok producer:

```json
{
  "host": "grok",
  "role": "routine_worker",
  "model": "grok-4.5",
  "effort": "high",
  "fallback_reason": null
}
```

Codex REVIEWER:

```json
{
  "host": "codex",
  "role": "reviewer",
  "model": "gpt-5.6-sol",
  "effort": "medium",
  "fallback_reason": null
}
```

Rare genius unstick (STANDARD or DEEP capability nodes only):

```json
{
  "host": "codex",
  "role": "genius_worker",
  "model": "gpt-5.6-sol",
  "effort": "high",
  "fallback_reason": "stall after 2 grok attempts; evidence V4"
}
```

`fallback_reason` is a non-empty string when the preferred Grok row was replaced
by genius escalation or another in-matrix fallback; otherwise null.
Controller-only `ORCHESTRATION` nodes may set `runtime` to null.

## Invariants

- Owner IDs are role-only: `worker-N`, `controller-N`, or `reviewer-N`.
- Runtime bindings live only in structured `runtime` fields.
- Cross-host is allowed: producers may be `grok` while `active_host` is `codex`
  and REVIEWER/genius may be `codex`.
- Every writable non-review node is a producer. A completed producer owns at
  least one changed-file entry; manifest classes match `artifact_classes`.
- `task.changed_artifacts` equals the distinct classes in `changed_files`.
  Every changed path lies inside its producer's writable scope.
- Every completed node proves every `proof_requirements` entry with dedicated
  TARGET/`PASS` evidence.
- `RUNNING` and `COMPLETE` nodes have only `COMPLETE` dependencies.
- A `BLOCKED` node has a blocker object with source and evidence IDs.
- Review gate follows the routing-policy cost guard.
- Lean final user report: table of nodes/proof/review/decision — no essay.
- A required reviewer is read-only, independent, depends on every producer, and
  has dedicated passing target evidence.

The validator checks the full schema, producer derivation, changed-file
reconciliation, state transitions, blocker provenance, dependency acyclicity,
overlapping writes, proof ownership, review triggers, hybrid runtime matrix
binding, owner-identity hygiene, and decision consistency. Report validator
`PASS` or its exact errors in the final response.
