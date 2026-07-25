# Sam Task Output Contract

## Contents

1. Terminal statuses
2. Report shape
3. Phase objects
4. Closure object
5. Validation

## Terminal statuses

- `COMPLETE`: plan, refine, work, and closure are terminal and current for one
  final head; validator returns `VALID`.
- `BLOCKED`: a required child failed, exhausted, or could not produce receipts.
- `IN_PROGRESS`: only for interrupted runs; never claim completion.

## Report shape

Write `task-report.json` (UTF-8 object):

```json
{
  "schema_version": 1,
  "workflow": "task",
  "workflow_id": "stable-id",
  "status": "COMPLETE",
  "request": {
    "prompt_sha256": "64 lowercase hex",
    "prompt_summary": "short text",
    "classification": "BUG"
  },
  "target": {
    "repo_root": "/absolute/path",
    "base_ref": "main",
    "base_sha": "40-or-64 hex",
    "final_head_sha": "40-or-64 hex",
    "final_change_fingerprint": "64 lowercase hex"
  },
  "plan": {
    "plan_dir": "/absolute/plan",
    "depth": "simple",
    "status": "READY_TO_EXECUTE",
    "validator_receipt": "VALID",
    "freeze_path": "/absolute/plan/plan-report.json"
  },
  "phases": [],
  "closure": {},
  "work_report_path": "/absolute/work-report.json",
  "residuals": [],
  "blockers": []
}
```

`classification` is `BUG` or `FEATURE` and must match the path taken inside
`sam-work`.

## Phase objects

`phases` contains exactly these ids in order: `plan`, `refine`, `work`,
`closure`.

Each phase:

```json
{
  "id": "plan",
  "skill": "sam-plan",
  "status": "READY_TO_EXECUTE",
  "current": true,
  "validated_head_sha": null,
  "evidence": ["..."],
  "validator_receipts": ["VALID"],
  "iterations": []
}
```

- `plan` and `refine` may use `validated_head_sha: null` when no implementation
  head exists yet; once `work` starts, later phases and final target head must
  align.
- `work` and `closure` require `validated_head_sha == target.final_head_sha`
  when status is terminal for `COMPLETE`.
- Iterations are contiguous from 1. Intermediate iterations with open items
  require correction receipts. The last iteration matches phase status and has
  zero open required items for successful terminals.

Accepted phase terminals:

| id | status |
| --- | --- |
| plan | `READY_TO_EXECUTE` |
| refine | `HIGH_CONFIDENCE` |
| work | `COMPLETE` |
| closure | `CLEAN` |

## Closure object

```json
{
  "max_iterations": 5,
  "iterations_used": 1,
  "final_status": "CLEAN",
  "iterations": [
    {
      "sequence": 1,
      "head_sha": "40-or-64 hex",
      "review_status": "APPROVE",
      "council_profile": "fast",
      "council_status": "TRIAGE_PASS",
      "open_findings": [],
      "correction_receipts": [],
      "review_receipt": "VALID",
      "council_receipt": "VALID",
      "evidence": ["..."]
    }
  ]
}
```

For `COMPLETE`, the last closure iteration must have empty `open_findings`,
`review_status=APPROVE`, and an accepted council status
(`TRIAGE_PASS|APPROVED|APPROVED_WITH_CONDITIONS` with conditions closed).

## Validation

```bash
python3 -B scripts/validate_task_report.py task-report.json
```

Cite only `VALID` as machine proof. Re-run after every report edit.
