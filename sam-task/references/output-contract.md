# Sam Task Output Contract

`task-report.json` (UTF-8 object). `scaffold_task_report.py` derives every field marked *derived* from the cited files; strings starting `SCAFFOLD:` fail validation.

## Top level

| Field | Rule |
| --- | --- |
| `schema_version` | `3` |
| `workflow` | `"task"` |
| `workflow_id` | non-empty |
| `status` | `COMPLETE` (per SKILL.md § Non-Negotiable Contract), `BLOCKED` (a child failed, exhausted, or lacks receipts; needs `residuals` or `blockers`), `IN_PROGRESS` (interrupted only) |
| `request` | *derived*: `prompt_sha256` (64 lowercase hex, = freeze `frozen.prompt_hash`), `prompt_summary`, `classification` `BUG`/`FEATURE` (the path taken in `sam-work`) |
| `target` | *derived* from the work report: `repo_root` (absolute), `base_ref`, `base_sha` and `final_head_sha` (40/64 hex), `final_change_fingerprint` (64 hex); plus `web_surface` (boolean, required for `COMPLETE`) and `web_surface_evidence` (≥1) |
| `plan` | *derived*: `plan_dir` (absolute), `depth` `simple`/`standard`/`deep`, `status` (`READY_TO_EXECUTE` for `COMPLETE`), `validator_receipt` (= the plan phase's last receipt), `freeze_path` (absolute; required for `COMPLETE`) |
| `refine_report_path`, `work_report_path` | absolute; required for `COMPLETE` |
| `refine_validator_args` | *derived*: exactly `--baseline` and `--current`, each `<absolute path>` or `=<absolute path>` |
| `phases` | exactly `plan`, `refine`, `work`, `closure`, `learn`, in order |
| `advisor_consults` | fields and enums in SKILL.md § Advisors; at most 3 |
| `residuals`, `blockers` | string arrays; `COMPLETE` needs `blockers: []` |

## Phases

Each: `id`; `skill` as in the SKILL.md table; `status` (= last iteration's); `current` (true for `COMPLETE`); `validated_head_sha` (`plan`/`refine`: null or a revision; `work`/`closure`/`learn`: `target.final_head_sha` for `COMPLETE`); `evidence`, `validator_receipts`, `iterations` (≥1 each). `COMPLETE` needs each phase's accepted terminal (SKILL.md table).

Iteration: `sequence` (contiguous from 1), `input_fingerprint` and `output_fingerprint` (64 hex), `status`, `open_required_items[]`, `correction_receipts[]`, `evidence` (≥1). Iteration statuses: plan `READY_TO_EXECUTE`/`NOT_CONFIDENT`/`BLOCKED`; refine `HIGH_CONFIDENCE`/`NOT_CONFIDENT`/`BLOCKED`; work `COMPLETE`/`BLOCKED`/`IN_PROGRESS`; closure `CLEAN`/`OPEN`/`BLOCKED`; learn `LEARNING_AUDITED`/`BLOCKED`. An intermediate iteration with open items needs correction receipts; a terminal last iteration has none. Fingerprints are *derived* (input → output): plan `prompt_sha256` → freeze sha256; refine freeze → refine report sha256; work refine report → work report sha256; closure iterations mirror `closure.iterations` (input: cited review report sha256); learn mirrors `learning`.

## Closure object

`max_iterations` (positive, default 5), `iterations_used` (= length, ≤ max), `final_status` `CLEAN`/`OPEN`/`BLOCKED`, `iterations[]`:

| Field | Rule |
| --- | --- |
| `sequence` | contiguous from 1 |
| `head_sha` | revision (*derived* from the review report) |
| `review_status` | `APPROVE`/`CHANGES_REQUIRED`/`COMMENT_ONLY`/`BLOCKED` (*derived*) |
| `review_report_path` / `review_reused_from` | exactly one, absolute: a fresh review, or the `sam-work` review phase `report_path` cited under an identical key |
| `review_validator_args` | fresh review: exactly `--bundle <absolute path>` (*derived* from `validator-args.json` beside it) |
| `review_receipt` | non-empty (*derived*) |
| `review_report_sha256` | *derived*: sha256 of the cited review, pinned while the iteration is last; a superseded iteration's file must keep it |
| `council_status` | `NOT_RUN` unless review is `APPROVE` on this head; else the council status (*derived*) |
| `council_profile`, `council_receipt` | required when council ran (*derived*) |
| `council_report_path` | absolute when council ran, else null |
| `open_findings`, `correction_receipts` | string arrays; intermediate open findings need receipts; a finding that disappears must be named in the previous iteration's receipts |
| `evidence` | ≥1 |

`COMPLETE` needs `final_status: CLEAN` and a last iteration with no open findings, `review_status: APPROVE`, council `TRIAGE_PASS`/`APPROVED`/`APPROVED_WITH_CONDITIONS` (conditions closed), and `head_sha` = final head. A `BLOCKED` report cannot claim `CLEAN` without iterations.

## Learning object

`status` `LEARNING_AUDITED`/`BLOCKED` (`COMPLETE` needs `LEARNING_AUDITED`), `write_policy: PROPOSAL_ONLY`, `audited_head_sha` = final head, `writes_performed: []`, `evidence` (≥1), `candidates[]` (`[]` is valid). Candidate: `id` (`L-###`, unique), `observation`, `proposed_rule`, `scope` (≥1), `evidence` (≥1), `destination` `AGENTS.md`/`SKILL`/`MEMORY`/`NONE`, `revalidate_when`, `sensitivity` `PUBLIC`/`INTERNAL`/`SENSITIVE`, `status` `PROPOSED`/`REJECTED`, `decision_reason`.

## What `COMPLETE` re-checks on disk

- Freeze `READY_TO_EXECUTE` with `frozen.prompt_hash` = `request.prompt_sha256`; refine `HIGH_CONFIDENCE`, empty `remaining`; plan/refine/work output fingerprints = file sha256.
- Fresh validator runs (plan freeze and council with no arguments, refine with `refine_validator_args`, work, fresh review with `review_validator_args`) that pass, with the last line = the recorded receipt.
- Work report: `final.result: COMPLETE`; `request.prompt_sha256`, `request.web_system` (= `target.web_surface`), and `target` `repo_root`/`base_sha`/`final_head_sha`/`final_change_fingerprint` equal this report's; `video_inventory.demo_uploaded` ≥1; web: `playwright_uploaded` ≥1 and = `playwright_discovered`; non-web: Playwright counts 0.
- Last closure iteration: a reused review is the work report's review `report_path` (branch mode, same head and base, its receipt); a fresh review matches `head_sha`, `review_status`, branch mode, and `target.base_sha`; the council report matches `council_status` and `packet_head` = `head_sha`.
- Superseded closure iterations: the cited review still holds the recorded `head_sha` and `review_status`.
