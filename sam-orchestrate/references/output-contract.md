# Output Contract

## Contents

- Report shape
- Allowed values
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
    "changed_artifacts": ["CODE", "TEST"],
    "changed_files": [
      {"path": "src/service.py", "artifact_class": "CODE", "producer_task_id": "E1"},
      {"path": "tests/test_service.py", "artifact_class": "TEST", "producer_task_id": "E2"}
    ],
    "review_requested": false
  },
  "dag": [
    {
      "id": "E1",
      "kind": "EXECUTION",
      "owner": "worker-1",
      "capability": "STANDARD",
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
- Artifact: `CODE`, `TEST`, `DOCS`, `CONFIG`, `DATA`, `RELEASE`, `OTHER`.
- Kind: `EXECUTION`, `ORCHESTRATION`, `REVIEW`.
- Capability: `LIGHT`, `STANDARD`, `DEEP`, `REVIEWER`.
- Node status: `PENDING`, `RUNNING`, `COMPLETE`, `BLOCKED`.
- Blocker kind: `EXTERNAL`, `AUTHORITY`, `USER_DECISION`, `DEPENDENCY`.
- Evidence type: `COMMAND`, `DIFF`, `FILE`, `REMOTE`, `USER`, `OBSERVATION`.
- Evidence status: `PASS`, `FAIL`, `NOT_RUN`, `INFO`.
- Evidence classification: `TARGET`, `BASELINE`, `ENVIRONMENT`, `EXTERNAL`.
- Gate status: `PASS`, `FAIL`, `NOT_RUN`, `NOT_REQUIRED`.
- Decision: `COMPLETE`, `BLOCKED`, `IN_PROGRESS`.

## Invariants

- Owner IDs are role-only: `worker-N`, `controller-N`, or `reviewer-N` according
  to node kind. Named routing identities are invalid.
- Every writable non-review node is a producer. A completed producer owns at
  least one changed-file entry, and its manifest classes exactly match its
  `artifact_classes`.
- `task.changed_artifacts` equals the distinct classes in `changed_files`.
  Every changed path lies inside its producer's writable scope.
- Every completed node proves every `proof_requirements` entry with evidence
  dedicated by `task_id`, classified `TARGET`, and marked `PASS`.
- `RUNNING` and `COMPLETE` nodes have only `COMPLETE` dependencies.
- A `BLOCKED` node has a blocker object with source and evidence IDs. A
  dependency blocker names a directly blocked dependency; other blockers begin
  only after dependencies complete. Blocker evidence is classified
  `ENVIRONMENT` or `EXTERNAL`.
- `BLOCKED` is terminal only when no runnable node remains and all pending work
  descends from blocked work. Otherwise the decision is `IN_PROGRESS`.
- A required reviewer is read-only, independent, depends on every producer, and
  has dedicated passing target evidence.

The validator checks the full schema, producer derivation, changed-file
reconciliation, state transitions, blocker provenance, dependency acyclicity,
overlapping writes, proof ownership, review triggers, package neutrality, and
decision consistency. Report validator `PASS` or its exact errors in the final
response.
