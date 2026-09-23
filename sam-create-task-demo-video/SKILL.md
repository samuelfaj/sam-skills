---
name: sam-create-task-demo-video
description: "Record and validate a human-paced MP4 walkthrough of a finished task, feature, or bug fix in the real UI, with criterion traceability, privacy checks, and media validation. Use when asked for a demo or proof video, walkthrough, screen recording, MP4, or PR/MR video attachment."
---

# Sam Create Task Demo Video

Create a human-reviewable demo; never present it as automated test coverage. Stay host-, provider-, tool-, and model-agnostic.

## Non-Negotiable Contract

- Honor the exact repository, change, behavior, and acceptance criteria supplied; keep the demo scoped to linked criteria.
- Never reset, checkout, stash, clean, or rewrite history. Inspect changed scripts, hooks, package commands, command definitions, containers, CI definitions, and browser config before executing them.
- **Real UI.** Record the real product pages, routes, and flows linked to the intended backend: real boot, auth (or an existing demo/test account), navigation, actions, and visible outcomes. While the real surface can show the behavior, build no demo-only page, route, component, story mount, component shell, mock screen bypassing router/layout/providers/auth/API clients, or parallel "demo UI" copy; prefer config or seed fixes.
- **Fallback** only after recording each real-system attempt and blocker (boot, auth, seed, ports/config, backend link): thinnest temporary surface that still proves useful visible behavior, artifact and proof labeled `FALLBACK`, `recording.real_ui=false` with an exact `fallback_reason`, never described as a real linked walkthrough.
- Real data only on a verified `local`, `test`, or `dev` target; fail closed when unknown. Never capture, show on screen, or expose production credentials, customer tenants, private customer data, secrets, tokens, cookies, internal URLs, emails, internal identifiers, or sensitive production information.
- **Publication.** All media stays local, with no upload or comment, unless the user or a parent workflow (e.g. `sam-work`) explicitly requests publication to a known target. Parent authorization is enough; never re-ask. Never infer it from a PR, MR, branch, or CLI login.
- **Never commit** videos, screenshots, contact sheets, traces, or recordings (branch, LFS, product tree, release assets); upload through the host platform as an inline player or image, never a hyperlink, download anchor, or blob/raw URL.
- Register every process, container, port, record, override, raw video, contact sheet, and temp file at creation; clean every one this run created and nothing else, except `report.json`, `manifest.json`, and the final MP4, which stay `RETAINED` for caller re-validation.

## Paths and Reads

Write literal absolute paths in every command (shell variables do not persist): `<skill>` = this file's directory, `<tmp>` = one scratch directory outside the repository (`mktemp -d` once), `<repo>` = the repository root.

| Read | Read when |
| --- | --- |
| [references/output-contract.md](references/output-contract.md) | step 4, before scaffolding the report |
| [references/evidence-publishing.md](references/evidence-publishing.md) | step 6, only when publication is authorized |

Do not re-read a file already read in this context unless context was compacted since or you cannot quote the section you need.

## 1. Freeze the Target

```bash
python3 <skill>/scripts/build_demo_manifest.py --repo <repo> \
  --environment-kind unknown --environment-id unverified > <tmp>/manifest.json
```

Add `--base`, `--head`, and repeated `--path` when specified; refs are never fetched or changed. Rebuild with the verified kind and identity once a real-data environment is verified. Read changed paths and the fingerprint from its stderr summary. **Never open or print manifest.json** (it embeds the full patch); the scaffold copies its fields. When the summary shows `more=N`, list every path with: `python3 -c 'import json,sys;[print(f["path"]) for f in json.load(open(sys.argv[1]))["files"]]' <tmp>/manifest.json`.

Freeze before recording: target mode, refs/SHAs, changed files, fingerprint; intended visible behavior, invariants, criteria, risks, no-go surfaces; environment kind, identity, UI/API endpoints, database/tenant, evidence; the local output path; whether publication was explicitly requested; the cleanup ledger.

Under a parent workflow ask nothing: record, convert, publish when authorized, or fail closed with receipts. Standalone, ask one concise question only when a safety-critical target cannot be discovered.

## 2. Storyboard

IDs: `AC-###` criterion, `R-###` risk, `S-###` scenario, `T-###` proof check, `CMD-###` recording, conversion, inspection, or validation command and result, `ART-###` artifact, `CL-###` cleanup resource.

Per scenario: the real entry route that owns the changed behavior, initial state, exact human actions on the controls users use, visible proof moment, stable final state, linked AC/R/T, and expected artifact. Show before/after only when the defective state is safely available.

## 3. Prepare the Real Linked System

Reuse a parent's `sam-create-playwright-tests` environment only when its report has `decision` `COMPLETE`, `target.head_sha` equal to the manifest head, and a validator `PASS` (handoff receipt or rerun): copy `environment` `kind`/`identity`/`real_data`, cite the report path in `environment.evidence`, skip identity re-verification, and restart only what stopped, using the boot, auth, and seed steps in its `environment.evidence` and `cleanup[]`, or the repository workflows in the next paragraph when it records none.

Otherwise boot with repository-supported direct, container, or compose workflows, supported lockfiles and commands, temporary overrides, and unused ports, and use deterministic seed data or a dedicated demo account on the linked backend, never in-browser-only fake state while the backend is available. Either way, after any (re)start confirm the browser reaches the frozen product UI and backend, not a harness URL invented for the video.

## 4. Scaffold, Audit, Record

```bash
python3 <skill>/scripts/scaffold_demo_report.py --manifest <tmp>/manifest.json \
  --report <tmp>/report.json --publish-requested <true|false>
python3 <skill>/scripts/audit_demo_plan.py --manifest <tmp>/manifest.json <tmp>/report.json
```

Before the audit, fill `environment` (`kind`, `identity`, `real_data`, `evidence`), `command_definitions`, `recording`, and the storyboard tables. Resolve every audit finding before recording. Use a stable viewport, human-readable pacing, and waits on visible readiness or network completion, never fixed timers. Pause on the opening, key action, proof moment, and final state. Keep captions short and inject them only in the browser session, never into product files. Use the real navigation path when it is part of the proof story.

## 5. Convert and Validate Media

```bash
python3 <skill>/scripts/media_tools.py convert --input <tmp>/raw.webm --output <tmp>/demo.mp4
python3 <skill>/scripts/media_tools.py inspect --input <tmp>/demo.mp4 > <tmp>/media.json
python3 <skill>/scripts/media_tools.py contact-sheet --input <tmp>/demo.mp4 --output <tmp>/contact-sheet.png
python3 <skill>/scripts/scaffold_demo_report.py --manifest <tmp>/manifest.json \
  --report <tmp>/report.json --media <tmp>/media.json
```

The deliverable is MP4 unless the user explicitly changes the request; raw WebM never substitutes. Missing tooling (probe with `media_tools.py capabilities`) is a blocker. Play the final file and review the contact sheet (spans the full duration): initial state, actions, proof moment, final state, readable pacing, no secrets or private data. A metadata-only check proves neither content nor privacy.

## 6. Publish Only When Authorized

When authorized (including `sam-work` requiring `PUBLISHED`), upload, embed, and verify with `scripts/count_embeds.py` per references/evidence-publishing.md.

## 7. Validate, Clean, Return

```bash
python3 <skill>/scripts/validate_demo_report.py --manifest <tmp>/manifest.json <tmp>/report.json
```

If a local output path was frozen, move the MP4 there, rerun `inspect` on it, and rerun the scaffold with `--media`. Clean every other registered resource, including raw media, temporary captions, and logs, unless explicitly retained. Update every `CL-###`, revalidate, then delete only scratch that no retained file references.

Decide `READY_LOCAL` (validated local MP4), `PUBLISHED` (verified remote readback), or `BLOCKED` (safety, conversion, playback, privacy, authorization, drift, or cleanup prevents an honest deliverable); return per references/output-contract.md.
