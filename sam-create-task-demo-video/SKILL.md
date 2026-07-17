---
name: sam-create-task-demo-video
description: "Record and validate a human-paced MP4 walkthrough of a completed task, feature, or bug fix using the real runnable UI, with acceptance-criterion traceability, privacy checks, deterministic media validation, and optional external publication. Use when asked for a demo video, proof video, walkthrough, screen recording, MP4, or explicitly requested PR/MR video attachment."
---

# Sam Create Task Demo Video

Create a human-reviewable demo artifact. Do not present a demo as automated test
coverage. Remain host-, provider-, tool-, and model-agnostic.

## Non-Negotiable Contract

- Honor the exact repository, change, behavior, and acceptance criteria supplied.
- Freeze base SHA, head SHA, manifest fingerprint, intent, no-go scope,
  environment identity, and cleanup ledger before recording.
- Preserve existing work. Do not reset, checkout, stash, clean, or rewrite history.
- Inspect changed scripts, hooks, command definitions, containers, and browser
  configuration before executing them.
- Use the real linked UI by default. Label mocked or isolated recording honestly
  as fallback after documenting real-system attempts and blockers.
- Fail closed when real data is requested and the environment is unknown or is
  not a verified local, test, or development target.
- Keep final and intermediate media local until a remote proposal target is
  authorized. Publish only when the user (or parent workflow) explicitly
  requests it and the exact remote target is known.
- **Never commit** generated videos, screenshots, contact sheets, or recordings
  to the task branch, LFS, or product-tree history.
- When publication is authorized, **always upload** via the host CLI (`gh` /
  `glab` platform uploads) and place the media in the PR/MR **description** or
  a **comment/note** using player/image embed markup. Follow
  [references/evidence-publishing.md](references/evidence-publishing.md).
- **Video → inline/native player. Image → inline image. Never a hyperlink**
  (`[label](url)`, “Download MP4”, blob/raw repo URLs, or HTML download anchors).
- Never expose secrets, tokens, credentials, private customer data, internal
  identifiers, or sensitive production information.
- Record and clean every process, container, port, record, override, raw video,
  contact sheet, and temporary file.

## Resource Routing

- Read [references/recording-policy.md](references/recording-policy.md) before
  starting services or recording.
- Read [references/media-validation.md](references/media-validation.md) before
  conversion and playback checks.
- Read [references/evidence-publishing.md](references/evidence-publishing.md)
  only after explicit publication authorization.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting and validating the report.

## 1. Resolve and Freeze the Demo Target

Set the skill directory to the directory containing this file. Build the manifest
without fetching or changing refs:

```bash
SAM_DEMO_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_DEMO_DIR/scripts/build_demo_manifest.py" \
  --repo "$PWD" --environment-kind unknown \
  --environment-id "unverified" > "$WORK_TMP/manifest.json"
```

Pass `--base`, `--head`, and repeated `--path` when specified. Rebuild after
verifying a real-data environment.

Freeze:

- Target mode, base/head refs and SHAs, changed files, and manifest fingerprint.
- Intended visible behavior, invariants, criteria, risks, and no-go surfaces.
- Environment kind, identity, UI/API endpoints, database/tenant, and evidence.
- Exact local output path and whether publication was explicitly requested.
- Cleanup ledger initialized for every resource the run may create.

Ask one concise question only when a safety-critical target cannot be discovered.
Do not infer authorization from the presence of a PR, MR, branch, or CLI login.

## 2. Build the Proof Storyboard

Use stable traceability IDs:

- `AC-###`: acceptance criterion.
- `R-###`: visible or operational risk.
- `S-###`: demo scenario.
- `T-###`: proof check linked to a scenario; this is not a coverage claim.
- `CMD-###`: recording, conversion, inspection, or validation command and result.
- `ART-###`: local or explicitly published artifact.
- `CL-###`: cleanup resource.

For each scenario define initial state, exact human actions, visible proof moment,
final stable state, linked criteria/risks/checks, and expected artifact. Keep the
story focused. Use before/after only when the defective state is safely available.

## 3. Prepare the Real Linked System

Inspect changed command definitions first. Start the app with repository-supported
direct, container, or compose workflows. Prefer temporary overrides and unused
ports. Confirm the browser reaches the frozen UI and backend.

Use deterministic seed data or a dedicated demo account. Use real data only on a
verified local, test, or dev target. Register every created resource immediately.

If the real UI cannot run after serious direct, container, port/config, and
linking attempts, record the exact attempts and blocker. Continue only with an
honestly labeled fallback that still proves useful visible behavior.

## 4. Audit and Record

Draft the manifest-linked recording plan, then run:

```bash
python3 "$SAM_DEMO_DIR/scripts/audit_demo_plan.py" \
  --manifest "$WORK_TMP/manifest.json" "$WORK_TMP/report.json"
```

Resolve every audit finding before recording. Record with a stable viewport,
human-readable pacing, visible readiness waits, deterministic state, and pauses
on the opening, key action, proof moment, and ending. Inject captions only in the
browser session; do not modify product files for captions.

## 5. Convert and Validate Media

Keep raw media temporary. Produce MP4 using the conditional media helper:

```bash
python3 "$SAM_DEMO_DIR/scripts/media_tools.py" convert \
  --input "$WORK_TMP/raw.webm" --output "$WORK_TMP/demo.mp4"
python3 "$SAM_DEMO_DIR/scripts/media_tools.py" inspect \
  --input "$WORK_TMP/demo.mp4" > "$WORK_TMP/media.json"
python3 "$SAM_DEMO_DIR/scripts/media_tools.py" contact-sheet \
  --input "$WORK_TMP/demo.mp4" --output "$WORK_TMP/contact-sheet.png"
```

Follow [references/media-validation.md](references/media-validation.md). Verify
playback, start/action/proof/end content, duration, video stream, codec, dimensions,
hash, and contact-sheet privacy. Report missing media tooling as a blocker; do not
pretend raw WebM is the requested MP4.

## 6. Publish Only When Explicitly Requested

Without explicit authorization, retain only the safe local MP4 requested by the
user. Do not upload or comment. Never `git add` / commit the MP4.

When publication is explicit, follow
[references/evidence-publishing.md](references/evidence-publishing.md):

1. Reconfirm host, repository, proposal ID, and head SHA.
2. Upload the exact validated MP4 with `glab` (GitLab project uploads) or `gh`
   (GitHub user-attachments / equivalent). Do not commit media.
3. Embed in the PR/MR description or comment:
   - **GitLab video:** `![scenario title](/uploads/<hash>/file.mp4)`
   - **GitHub video:** bare `https://github.com/user-attachments/assets/<id>`
     alone on its own line
   - **Images (either host):** `![descriptive alt](<upload-url>)`
4. Forbid `[Download](url)`, HTML-only download links, and repo blob/raw URLs.
5. Read the remote body back; require a rendered **player** (video) or **image**.
6. Record receipt, markup, and `player_verified` under `ART-###`. Stop on drift
   or link-only readback.

## 7. Validate, Clean, and Return

Complete `report.json` using [references/output-contract.md](references/output-contract.md),
then run:

```bash
python3 "$SAM_DEMO_DIR/scripts/validate_demo_report.py" \
  --manifest "$WORK_TMP/manifest.json" "$WORK_TMP/report.json"
```

Stop only resources created by this run. Remove raw media, temporary captions,
contact sheets, data, overrides, and logs unless explicitly retained. Update every
`CL-###` entry, revalidate, then remove `WORK_TMP` except for an explicitly retained
final artifact outside it.

Return `READY_LOCAL` for a validated local MP4, `PUBLISHED` only with verified
remote readback, and `BLOCKED` when safety, conversion, playback, privacy,
authorization, target drift, or cleanup prevents an honest deliverable.
