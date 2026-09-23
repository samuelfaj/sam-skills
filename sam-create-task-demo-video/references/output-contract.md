# Output Contract

`scripts/scaffold_demo_report.py` writes the whole `report.json` skeleton (step 4), one pre-linked id per table. Rerun it after every manifest rebuild; it re-derives only `manifest_fingerprint`, `target`, `command_definitions.changed`, and (with `--media`) the artifact's `path`/`media` from real files. Placeholders (`""`, `null`, `TODO:<enum>`) never validate; the prefilled `[]` in `intent.invariants`/`no_go` and the manifest's environment `kind`/`identity` do, so replace them with the frozen lists and verified values. Fill per this table.

| Field | Rule |
| --- | --- |
| `manifest_fingerprint`, `target.base_sha`, `target.head_sha` | equal the manifest (scaffold) |
| `intent` | non-empty `summary`; `invariants` and `no_go` are lists |
| ids | `AC-`, `R-`, `S-`, `T-`, `CMD-`, `ART-`, `CL-` + ≥3 digits, unique; every table is a non-empty list; references are strings naming existing ids |
| links | reciprocal: scenario↔check (`check_ids`/`scenario_ids`), check↔command (`command_ids`/`check_ids`), scenario↔artifact (`artifact_ids`/`scenario_ids`); risks and scenarios cite `criterion_ids`, scenarios cite `risk_ids` |
| `criteria[]` | non-empty `text` |
| `risks[]` | `level` `LOW`/`MEDIUM`/`HIGH`/`CRITICAL`; non-empty `evidence` or `description` |
| `scenarios[]` | non-empty `initial_state`, `actions`, `proof_moment`, `final_state` |
| `checks[]` | non-empty `assertion` |
| `commands[]` | `status` `PASS`/`FAIL`/`NOT_RUN`; non-empty `command` and `evidence` |
| `artifacts[]` | `status` `LOCAL`/`UPLOADED` (`UPLOADED` adds `receipt` and `readback_verified: true`). Media: path ends `.mp4`; file exists, is non-empty, has an `ftyp` box, and hashes to `media.sha256` (64 lowercase hex); `mime_type` `video/mp4`; `conversion_status` `PASS`; `metadata.has_video` true, `duration_seconds` > 0, integer `width`/`height` > 0; `playback_verified` true; `privacy_review` and `contact_sheet_review` `{status: PASS, evidence}` |
| `cleanup[]` | `status` `CLEANED`/`RETAINED`/`BLOCKED`; non-empty `resource`; non-`CLEANED` needs `reason` |
| `environment` | `kind` `unknown`/`local`/`test`/`dev`/`staging`/`production`; non-empty `identity` and `evidence`; boolean `real_data` (also audited), `true` only with `local`/`test`/`dev` |
| `command_definitions` | `changed` equals whether the manifest lists command definitions; when true, `inspected: true` with `evidence` |
| `plan_audit` | `status` `PASS`/`FAIL` with `evidence` |
| `recording` | booleans `real_ui`, `requires_linked_backend`, `linked_backend`; `real_ui: false` needs `fallback_reason`; `requires_linked_backend: true` needs `linked_backend: true` or `fallback_reason` |
| `authorization` | boolean `publish_requested`; any `UPLOADED` artifact needs `true` |
| `publication.status` | `NOT_REQUESTED` (required when not requested, forbidden when requested); `PUBLISHED` (authorization, `receipt`, `readback_verified: true`); `BLOCKED` (`error` or `reason`) |
| `decision` | `READY_LOCAL`, `PUBLISHED`, `BLOCKED`. Both successes need every command `PASS`, valid media, no `BLOCKED` cleanup, a safe environment, and audit `PASS`. `READY_LOCAL`: publication `NOT_REQUESTED` and nothing uploaded. `PUBLISHED`: publication `PUBLISHED` and ≥1 `UPLOADED` artifact |

Fix from the validator's error lines and patch the report in place; do not read validator source or rewrite the whole report.

## Return

Child mode (a parent or phase worker invoked this skill) — the final message is exactly:

```
RESULT sam-create-task-demo-video <READY_LOCAL|PUBLISHED|BLOCKED>
report: <absolute path>
validator: <exact last line of the validator output>
head: <sha> fingerprint: <manifest fingerprint>
open: <n>
- <one line per open required item, max 10>
```

Standalone: at most 15 lines plus the report path (decision, MP4 path and SHA-256, published location if any, blockers). Never repeat the JSON report.
