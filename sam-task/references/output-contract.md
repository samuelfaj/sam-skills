# Sam Task Output Contract

## Contents

1. Terminal statuses
2. Report shape
3. Phase objects
4. Closure object
5. Learning object
6. Web surface and video evidence
7. Advisor consults
8. Validation

## Terminal statuses

- `COMPLETE`: plan, refine, work, closure, and learning audit are terminal and
  current for one final head; validator returns `VALID`.
- `BLOCKED`: a required child failed, exhausted, or could not produce receipts.
- `IN_PROGRESS`: only for interrupted runs; never claim completion.

## Report shape

Write `task-report.json` (UTF-8 object):

```json
{
  "schema_version": 3,
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
    "final_change_fingerprint": "64 lowercase hex",
    "web_surface": true,
    "web_surface_evidence": ["dev server script and routed pages"]
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
  "learning": {},
  "work_report_path": "/absolute/work-report.json",
  "refine_report_path": "/absolute/plan/refine-report.json",
  "advisor_consults": [],
  "residuals": [],
  "blockers": []
}
```

`classification` is `BUG` or `FEATURE` and must match the path taken inside
`sam-work`.

## Phase objects

`phases` contains exactly these ids in order: `plan`, `refine`, `work`,
`closure`, `learn`.

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
| learn | `LEARNING_AUDITED` |

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

## Learning object

The learning audit runs on the final head and proposes durable knowledge without
writing it:

```json
{
  "status": "LEARNING_AUDITED",
  "write_policy": "PROPOSAL_ONLY",
  "audited_head_sha": "40-or-64 hex",
  "candidates": [
    {
      "id": "L-001",
      "observation": "current-run observation",
      "proposed_rule": "narrow reusable rule",
      "scope": ["where the rule applies"],
      "evidence": ["current-run receipt"],
      "destination": "AGENTS.md",
      "revalidate_when": "condition that may make the rule stale",
      "sensitivity": "INTERNAL",
      "status": "PROPOSED",
      "decision_reason": "why this is or is not durable"
    }
  ],
  "writes_performed": [],
  "evidence": ["learning audit receipt"]
}
```

`destination` is `AGENTS.md|SKILL|MEMORY|NONE`; `sensitivity` is
`PUBLIC|INTERNAL|SENSITIVE`; candidate status is `PROPOSED|REJECTED`.
`candidates: []` is valid and preferable to inventing a lesson.
`writes_performed` must remain empty. Promotion requires a separate explicit
user action.

## Web surface and video evidence

`COMPLETE` requires a boolean `target.web_surface` with at least one
`target.web_surface_evidence` receipt. Decide it from repository evidence: `true`
for any browser-reachable UI; `false` only with concrete evidence of no browser
surface. Unclear or unchecked evidence is `true`.

The validator opens `work_report_path` and checks the child receipt directly. A
`work` phase of `COMPLETE` is not video proof on its own. For `COMPLETE`:

- The work report must exist, load, and record `final.result = COMPLETE`.
- `request.web_system` in the work report must equal `target.web_surface` here.
  A mismatch is `INVALID`—the child cannot silently downgrade a web system.
- `video_inventory.demo_uploaded` must be at least 1 on every run.
- When `web_surface` is `true`, `video_inventory.playwright_uploaded` must be at
  least 1 and must equal `playwright_discovered`.
- When `web_surface` is `false`, Playwright counts must be 0.

## Advisor consults

`advisor_consults` is evidence-only and defaults to `[]`. It never closes a
phase, replaces a validator receipt, or changes a terminal status.

```json
{
  "advisor_consults": [
    {
      "id": "A-001",
      "advisor": "sam-<runtime>-advisor",
      "phase": "refine",
      "model": "advisor model bound by this workflow",
      "effort": "high",
      "effort_source": "MATRIX_DEFAULT",
      "question": "one focused question",
      "status": "ANSWERED",
      "caller_decision": "ACCEPTED",
      "decision_reason": "why the caller accepted or rejected it",
      "failure_reason": null,
      "evidence": ["consult receipt"]
    }
  ]
}
```

- `id` matches `A-###` and is unique.
- `advisor` matches `sam-<runtime>-advisor` (the provider-specific advisor skill
  that was consulted).
- `phase` is `plan`, `refine`, or `closure`. `work` is rejected—that phase is
  owned by the `sam-work` ledger.
- `effort` is `low|medium|high|xhigh|max`; `effort_source` is `MATRIX_DEFAULT` or
  `USER_SPECIFIED`.
- `status` is `ANSWERED` or `FAILED`; `FAILED` requires a `failure_reason` and
  must appear in `residuals`, never in `blockers`.
- `caller_decision` is `ACCEPTED`, `REJECTED`, or `UNRESOLVED`.
- At most 3 consults per run.

## Validation

On `COMPLETE`, the task validator re-opens durable child artifacts:

- `plan.freeze_path` must exist and report `status == READY_TO_EXECUTE`
- `frozen.prompt_hash` must match `request.prompt_sha256`
- `refine_report_path` must exist with `decision.result == HIGH_CONFIDENCE` and empty `remaining`

Bare `validator_receipt` strings are not sufficient.

Closure iterations: a finding present in iteration *N* and absent in *N+1* must be named in iteration *N* `correction_receipts` (normalized substring match).

## Validation

```bash
python3 -B scripts/validate_task_report.py task-report.json
```

Cite only `VALID` as machine proof. Re-run after every report edit.
