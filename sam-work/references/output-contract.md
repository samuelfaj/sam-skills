# SAM Work output contract

`work-report.json` is the fail-closed receipt for the complete workflow. The validator rejects missing phases, stale evidence, unclosed loops, unsafe environments, proposal drift, incomplete video publication, or unsupported completion.

## Contents

1. [Top-level object](#top-level-object)
2. [Ordered phases](#ordered-phases)
3. [Proposal receipt](#proposal-receipt)
4. [Development environments](#development-environments)
5. [Video inventory and artifacts](#video-inventory-and-artifacts)
6. [Final object](#final-object)

## Top-level object

```json
{
  "schema_version": 1,
  "workflow_id": "stable non-empty identifier",
  "request": {
    "prompt_sha256": "64 lowercase hex characters",
    "classification": "BUG",
    "web_system": true,
    "classification_evidence": ["existing expected behavior and observed break"]
  },
  "authorization": {
    "create_or_update_proposal": true,
    "publish_playwright_videos": true,
    "publish_demo_video": true,
    "merge": false,
    "deploy": false
  },
  "target": {
    "repo_root": "/absolute/repository/path",
    "base_ref": "main",
    "base_sha": "40-or-64-character lowercase hex revision",
    "final_head_sha": "40-or-64-character lowercase hex revision",
    "final_change_fingerprint": "64 lowercase hex characters"
  },
  "phases": [],
  "proposal": {},
  "environments": {},
  "video_inventory": {},
  "artifacts": [],
  "final": {}
}
```

`classification` is `BUG` or `FEATURE`. The selected implementation skill must match it. Authorization is exact: proposal and video writes are true; merge and deploy are false.

## Ordered phases

`phases` contains exactly these entries in this order:

| id | skill | accepted final status |
| --- | --- | --- |
| `implementation` | `sam-fix-bug` for `BUG`; `sam-create-feature` for `FEATURE` | `COMPLETE` |
| `refine` | `sam-refine-task` | `HIGH_CONFIDENCE` |
| `review` | `sam-review` | `APPROVE` |
| `simplify` | `sam-simplify-task` | `SIMPLEST_DEFENSIBLE` or `NO_CHANGE` |
| `coverage` | `sam-create-test-coverage` | `FULL` |
| `proposal` | `sam-pr-description` | `READY` |
| `playwright` | `sam-create-playwright-tests` | `COMPLETE`, or `NOT_APPLICABLE` only for a non-web system |
| `demo` | `sam-create-task-demo-video` | `PUBLISHED` |

Every phase object contains:

```json
{
  "id": "review",
  "skill": "sam-review",
  "applicability": "REQUIRED",
  "status": "APPROVE",
  "current": true,
  "validated_head_sha": "same value as target.final_head_sha",
  "not_applicable_reason": null,
  "evidence": ["immutable bundle and review receipt"],
  "validator_receipts": ["PASS: review report is internally consistent"],
  "iterations": []
}
```

Each phase has at least one iteration. Sequences are contiguous from one. Every iteration contains non-empty input/output fingerprints, a status, evidence, `open_required_items`, and `correction_receipts` arrays.

```json
{
  "sequence": 1,
  "input_fingerprint": "64 lowercase hex characters",
  "output_fingerprint": "64 lowercase hex characters",
  "status": "CHANGES_REQUIRED",
  "open_required_items": ["missing authorization regression"],
  "correction_receipts": ["focused test and implementation receipt"],
  "evidence": ["finding tied to file and line"]
}
```

An intermediate iteration with open items must contain correction receipts. The last iteration must use the phase's accepted final status and have zero open required items. `BLOCKED`, `PARTIAL`, `NOT_CONFIDENT`, `CHANGES_REQUIRED`, `COMMENT_ONLY`, and `CHANGES_APPLIED` are never workflow-terminal states.

For a non-web system, the Playwright phase still has one applicability iteration, `applicability: NOT_APPLICABLE`, status `NOT_APPLICABLE`, a concrete reason, and runtime/repository evidence. All other phases are required.

## Proposal receipt

```json
{
  "platform": "host name or adapter",
  "url": "https://proposal-url",
  "proposal_id": "non-empty platform ID",
  "created_by_workflow": true,
  "description_validated": true,
  "description_receipt": "validator pass receipt",
  "remote_head_sha": "same value as target.final_head_sha",
  "rendered_readback_evidence": ["description and attachment readback"],
  "required_ci_status": "PASS"
}
```

`created_by_workflow` may be false only when an existing task-branch proposal was resolved and updated. `required_ci_status` is `PASS` or `NOT_CONFIGURED`; pending, failed, skipped-required, or unknown checks do not pass.

## Development environments

`environments.demo` is always required. `environments.playwright` is required only for web systems. Each required record contains:

```json
{
  "kind": "DEVELOPMENT",
  "identity_verified": true,
  "identity_evidence": ["effective host, database or tenant identity"],
  "real_data": true,
  "dedicated_data": true,
  "cleanup_status": "COMPLETE",
  "privacy_review": "PASS"
}
```

Production, customer, ambiguous, shared destructive, unverified, or uncleaned data fails the workflow.

## Video inventory and artifacts

```json
{
  "video_inventory": {
    "playwright_discovered": 2,
    "playwright_uploaded": 2,
    "demo_discovered": 1,
    "demo_uploaded": 1
  },
  "artifacts": [
    {
      "phase": "playwright",
      "local_path": "/absolute/path/test.webm",
      "sha256": "64 lowercase hex characters",
      "uploaded_url": "https://rendered-video-attachment",
      "upload_receipt": "platform upload receipt",
      "player_verified": true,
      "readback_evidence": ["rendered proposal contains playable video"]
    }
  ]
}
```

For web systems, at least one Playwright video must be discovered and every discovered video must be uploaded. At least one demo video is always required. Artifact counts must equal inventory counts. Every artifact requires a hash, upload receipt, and rendered inline/native player proof; a downloadable link alone fails.

The demo artifact must be MP4. On a host that supports native video attachments, store the host-issued attachment URL or media markup and verify it on the rendered proposal. A repository blob/raw URL or an upload response without rendered-player readback is insufficient.

## Final object

```json
{
  "result": "COMPLETE",
  "completed_phase_ids": [
    "implementation",
    "refine",
    "review",
    "simplify",
    "coverage",
    "proposal",
    "playwright",
    "demo"
  ],
  "blockers": [],
  "final_head_sha": "same value as target.final_head_sha",
  "final_change_fingerprint": "same value as target.final_change_fingerprint"
}
```

Only `COMPLETE` passes the validator. An interrupted run should keep the same schema, use `IN_PROGRESS` or `BLOCKED`, list exact blockers, and is intentionally rejected as a completion receipt.
