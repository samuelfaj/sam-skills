# SAM Work output contract

`work-report.json` is the fail-closed completion receipt. `scaffold_work_report.py` writes the mechanical fields from real files; you fill evidence, readback, environments, videos, and `final.result`. Any string starting `SCAFFOLD:` fails validation, including the safety attestations `init` leaves unset.

## Top level

| Field | Rule |
| --- | --- |
| `schema_version` | `2` |
| `workflow_id` | non-empty |
| `request` | `prompt_sha256` (64 lowercase hex), `classification` `BUG`/`FEATURE` (matches the implementation skill), `web_system` boolean, `classification_evidence` (≥1) |
| `authorization` | exactly `{create_or_update_proposal: true, publish_playwright_videos: true, publish_demo_video: true, merge: false, deploy: false}` |
| `target` | `repo_root` absolute, `base_ref`, `base_sha` and `final_head_sha` (40/64 hex), `final_change_fingerprint` = sha256 of the raw `git diff --binary --no-color --no-ext-diff --no-renames <base_sha> <final_head_sha>` output (recomputed by the validator) |
| `phases` | the eight SKILL.md table phases, in order, with that table's skills and final statuses (implementation: `sam-fix-bug` for BUG, `sam-create-feature` for FEATURE) |

## Phases

Non-final iteration statuses, never workflow-terminal: implementation `CHANGES_REQUIRED`; refine `NOT_CONFIDENT`; review `CHANGES_REQUIRED`, `COMMENT_ONLY`; simplify `CHANGES_APPLIED`; coverage and playwright `PARTIAL`; demo `READY_LOCAL`; every phase `BLOCKED`.

Each phase: `id`, `skill`, `applicability` `REQUIRED` (non-web playwright: `NOT_APPLICABLE` plus a concrete `not_applicable_reason`, otherwise null), `status` (= last iteration's), `current: true`, `validated_head_sha` = final head, `report_path` (absolute child report; null only for non-web playwright), `validator_args`, `committed_head_sha` and `carried_forward_from` (null or a revision, below), `evidence`, `validator_receipts`, `iterations` (≥1 each).

`validator_args`: the child validator's arguments before the report, as `--flag <absolute path>` or `--flag=<absolute path>` pairs of only `--baseline --current` (implementation, refine, simplify), `--bundle` (review), `--baseline --bundle` (coverage, playwright), `--context` (proposal), `--manifest` (demo). The validator re-runs the sibling child validator with them; it must pass with its last line equal to the last receipt. A recorded child status (`decision.result`/`decision`/`status`) must equal `status`. Coverage `real_system_proof` `NOT_APPLICABLE` with `delegated to playwright phase` requires playwright `COMPLETE` on the final head.

## Proof anchor

Anchor = `committed_head_sha` if set, else the child report head (`target.current_head_sha`/`target.head_sha`); it equals `validated_head_sha` unless carried forward.

- **Commit** (implementation, refine, simplify): `validator_args` name readable `--baseline`/`--current` captures of `repo_root` whose current head is the child head. A captured delta (differing file records) requires `committed_head_sha`: a descendant of the child head where every delta path holds a blob with the captured `worktree_sha256` (deleted: absent), changing (`git diff --name-only --no-renames`) only delta paths (refine: any captured dirty path, same content check).
- **Carry-forward** (same three): `carried_forward_from` = the anchor, an ancestor of the final head, and `git diff --name-only --no-renames <anchor> <final head>` lists only test paths: a directory segment `test`, `tests`, `__tests__`, `__snapshots__`, `__mocks__`, `testdata`, or a file `test_*.py`, `conftest.py`, `*_test.go`, `*_test.exs`, `*_spec.rb`, `*.{test,spec}.{js,jsx,ts,tsx,mjs,cjs,mts,cts}`. Nothing else is test-only (e.g. a `spec`/`e2e` directory, `AbTest.kt`, `ab_test.py`, `openapi.spec.yaml`, a rename out of production).

## Iterations

Each: `sequence` (contiguous from 1), `input_fingerprint` and `output_fingerprint` (64 hex), `status`, `open_required_items[]`, `correction_receipts[]`, `evidence` (≥1).

- Final iteration: `input_fingerprint` = the child report's input fingerprint (scope, bundle, context, or manifest) when it records one; `output_fingerprint` = sha256 of `report_path`. `record` derives both.
- Open items need correction receipts. An intermediate iteration with no open items names the invalidating change (new head or changed paths) in `correction_receipts`.
- The last iteration has an accepted final status and zero open items. Non-web playwright: one `NOT_APPLICABLE` iteration with a concrete reason and runtime/repository evidence.

## Proposal

`platform`; `url` (HTTPS); `proposal_id`; `created_by_workflow` boolean (false only when an existing task-branch proposal was updated); `description_validated: true`; `description_receipt`; `remote_head_sha` = final head; `rendered_readback_evidence` (≥1); `required_ci_status` `PASS`, or `NOT_CONFIGURED` when no required checks are reported (pending, failed, skipped-required, or unknown checks fail).

## Environments

`environments.demo` always; `environments.playwright` only for web (non-web: null or `{}`). Each: `kind: DEVELOPMENT`, `identity_verified: true`, `identity_evidence` (≥1), `real_data: true`, `dedicated_data: true`, `cleanup_status: COMPLETE`, `privacy_review: PASS`. Production, customer, ambiguous, shared destructive, unverified, or uncleaned data fails.

## Videos

`video_inventory`: `playwright_discovered`, `playwright_uploaded`, `demo_discovered`, `demo_uploaded` (non-negative integers). Web: `playwright_discovered` ≥1 and uploaded = discovered; non-web: both 0. `demo_discovered` ≥1 and uploaded = discovered. Artifact counts per phase = uploaded counts.

`artifacts[]`: `phase` `playwright`/`demo`, `local_path` absolute (demo: `.mp4`), `sha256` (64 hex; `finalize` hashes local files), `uploaded_url` (HTTPS; with native video attachments, the host-issued URL or media markup, verified on the rendered proposal; a repo blob/raw URL or an unread-back upload fails), `upload_receipt`, `player_verified: true`, `readback_evidence` (≥1). No duplicate (path, sha256, URL).

## Final

`result` `COMPLETE` (the only passing value; an interrupted run keeps the schema with `IN_PROGRESS` or `BLOCKED` and exact blockers and is rejected as a completion receipt), `completed_phase_ids` = the eight ids in order, `blockers: []`, `final_head_sha` and `final_change_fingerprint` = `target`.
