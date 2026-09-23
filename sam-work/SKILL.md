---
name: sam-work
description: "Deliver a software task end-to-end with no permission prompts: bug/feature implementation, refinement, review, simplification, coverage, PR/MR, browser proof, and demo video, with fresh proof after every change. Use when the user wants complete verified delivery with a created or updated PR/MR."
---

# SAM Work

Deliver one request as a pull/merge request through fail-closed gates.

## Non-Negotiable Contract

- Exclusive top pipeline: if this turn also named `sam-goal` or `sam-task` as a user request, do not start this pipeline as the top method; that named parent owns the turn. `sam-task` may still run this ledger. Precedence: `sam-goal` > `sam-task` > `sam-work` > `sam-orchestrate`.
- Invoking this skill **is** the explicit user request for every required action and authorizes only: commit task-owned work on the task branch, push it, create or update its one proposal, and publish the required Playwright and demo videos there. Never merge, deploy, approve reviews, post unrelated comments, destructively clean user work, or touch production data.
- Autonomy: never ask for permission or confirmation, or pause for OS screen-recording permission. Child "ask", "stop for approval", or "publish only when authorized" rules become: execute in frozen scope or return `BLOCKED` with receipts. Resolve routine choices from the frozen request and repo evidence; if a required target, permission, tool, or decision is missing, continue independent safe work and report the exact blocker. Never infer scope or authority from a child. Respect host permissions.
- Prove all eight phases; never `COMPLETE` with one missing, stale, non-terminal, unvalidated, or silently skipped. Only Playwright may be `NOT_APPLICABLE`, only for a proven non-web system.
- Freeze prompt hash, repo root, base, branch, acceptance, invariants, no-go surfaces, and initial change fingerprint. Never reset, overwrite, or bundle unrelated user work.
- A child is done only through its terminal plus a stored validator receipt, never because it was invoked or narrated. A missing required child is `BLOCKED`, never emulated. Child retry limits stay; exhaustion is `BLOCKED`, never confidence.
- A loop ends only on its accepted terminal with zero open required items; findings need correction receipts before the next iteration. `FOLLOW_UP` and `SUGGESTION` items are parked and never reopen a loop.
- Freshness: a task-branch mutation invalidates proofs tied to the old head, except proof that `finalize` re-anchors (output contract § Proof anchor); re-run affected gates on the new commit of the same branch until all eight phases are current for one final head. Never reset, rebase, or replace the branch or worktree because a gate failed or the base moved.
- Verified development environments and dedicated data only; never production, customer, or ambiguous targets. Record environment identity before auth or mutation; keep dedicated identities, a mutation ledger, cleanup receipts, redaction proof, and artifact hashes.
- Never claim "all tests", "simplest possible", or "no issues" without the child terminal plus current-head evidence. Screenshots or text never substitute for a required video.

## Start

1. Classify `BUG` (→ `sam-fix-bug`) only when expected existing behavior is broken or regressed, else `FEATURE` (→ `sam-create-feature`), from concrete evidence, never labels. Decide web applicability from repo/runtime evidence (under `sam-task`: its `web_surface`).
2. State one line (classification + evidence, target head, "writes authorized per contract"; under `sam-task`, the freeze path) and continue.
3. `WORK_DIR` is absolute and outside the repo, or gitignored, in every mode (`mktemp -d`; under `sam-task`, `<RUN_DIR>/work`). Use literal absolute paths; `<SAM_WORK_DIR>` is this skill's directory. Run `python3 -B <SAM_WORK_DIR>/scripts/scaffold_work_report.py init --out <WORK_DIR>/work-report.json --repo <repo> --base-ref <ref> --base-sha <frozen base> --classification BUG|FEATURE --web-system true|false --prompt-sha256 <hash> --workflow-id <id>`.

## Phase isolation

- With subagents, dispatch each phase to a fresh worker, one at a time; workers never spawn, so parallel seats (`sam-council`) run at controller level. Without subagents, or with nesting exhausted, run the phase inline under the same contract.
- Every phase run gets a new `<phase dir>` (for this skill's phases `<WORK_DIR>/<phase>-<k>/`, k = that phase's run count). Never overwrite a cited report or its validator inputs; a DELTA review keeps its base review and uses a fresh receipts directory.
- Before dispatch write `<phase dir>/handoff.json`: the frozen ledger with current head and fingerprint, authorization scope, prior report paths, open items, and report path (`<phase dir>/report.json` unless the child fixes it).
- The worker (or you, inline) reads only the child's `../<child>/SKILL.md` and needed refs when the phase starts, runs it in child mode, writes the report, its validator inputs, and `validator-args.json` (JSON array of the child validator's arguments before the report, e.g. `["--bundle", "/abs/bundle.json"]`) into the phase dir, and validates; a worker returns only its `RESULT` block. Child cleanup never deletes the report or its validator inputs (captures, bundles, contexts, manifests, logs, final media) before the parent's final validation.
- Never read the worker transcript; re-run the child validator for your receipt: `python3 -B <SAM_WORK_DIR>/scripts/scaffold_work_report.py record <WORK_DIR>/work-report.json --phase <id> --child <report>`.
- Re-read a file already read in this context only after compaction or when you cannot quote the needed section; suite-enforced byte-identical sibling copies (shared scripts; `evidence-policy.md` and `risk-lenses.md` among sam-fix-bug, sam-create-feature, sam-refine-task, sam-simplify-task) count as read.
- **Token Saver:** Pass the host's content-free `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` and its capability/lane environment unchanged to every controlled child (nested spawns, retries, resumes, recovery); never reconstruct or widen admission. A missing, malformed, denied, cross-user, or provider-mismatched receipt is raw fail-open input. Never put skills, exact-output commands, prompts, transcripts, secrets, or full responses in it. Skills and exact-output evidence stay lossless; claim no billing or quota savings.
- **Telemetry (lifetime only):** With `T="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"`, bracket each controlled child: `run=$("$T" subagent begin --node <stable-id> </dev/null)` … `"$T" subagent end --run-id "$run" --status completed|failed|cancelled </dev/null`; keep the run id across retries. If the run's first `begin` fails, record one Subagents proof gap and skip brackets for the rest of the run. Telemetry never invents a Done row or receives skill bodies or exact output.

## Phases

Canonical order; a correction may rewind gates. Only the selected path's children are required. Child `BLOCKED` blocks the workflow.

| # | id | child | closes on |
| --- | --- | --- | --- |
| 1 | `implementation` | `sam-fix-bug` / `sam-create-feature` | `COMPLETE` with acceptance, validation, scope evidence |
| 2 | `refine` | `sam-refine-task` (implemented strategy + diff) | `HIGH_CONFIDENCE`, no open item |
| 3 | `review` | `sam-review`, branch mode vs frozen base, local-only (never publish or offer publication) | `APPROVE`, no actionable in-scope finding |
| 4 | `simplify` | `sam-simplify-task` | `SIMPLEST_DEFENSIBLE` or `NO_CHANGE`, nothing open |
| 5 | `coverage` | `sam-create-test-coverage` (acceptance, risks, seams, tests) | `FULL`, no uncovered required risk |
| 6 | `proposal` | `sam-pr-description` | `READY` (validated description) |
| 7 | `playwright` | `sam-create-playwright-tests` | `COMPLETE` |
| 8 | `demo` | `sam-create-task-demo-video` | `PUBLISHED` |

- **1:** the child records its `code-review`, `coverage`, and `browser-proof` gates `NOT_APPLICABLE`, reason `owned by parent phase`.
- **1 and 4**, and every correction through the implementation contract: after the child validates, commit exactly its captured delta (never pre-existing dirty work) before the next phase.
- **2:** `NOT_CONFIDENT` → corrections through the implementation contract, fresh validation, refine again.
- **3:** `CHANGES_REQUIRED` → fix accepted in-scope `BLOCKER`/`IMPORTANT` only through the implementation contract, then review the new head.
- **4:** applied simplifications need focused validation plus fresh refine and review proof.
- **5:** `PARTIAL` → add justified coverage, validate, re-run; commit and push test changes. When phase 7 applies, coverage records `real_system_proof = NOT_APPLICABLE`, reason `delegated to playwright phase`. Production testability changes rewind implementation, refine, review, simplify; test-only changes rewind review and any proof whose bundle changed. Before the proposal, run `finalize` (Completion 1) and re-run and `record` each phase 1-5 it marks stale.
- **6:** resolve any open proposal for the task branch; run the child on the real base, commits, diff, and proofs; validate the description before any platform write. Create exactly one proposal if none exists, else update it. Push the exact reviewed head, read back per Completion 2-4, and store create/update and readback receipts.
- **7:** always record applicability; non-web needs repo/runtime evidence. Web: real linked development UI/backend, verified real development data, `COMPLETE`, cleanup, current-head proof. Record video wherever the runner supports it; hash and upload every video to the proposal, each rendering as an inline/native player (a file link fails). On a recording, capture, conversion, or upload failure, finish remaining attempts and cleanup, then report the exact failure. A repo change here: commit, push, refresh the description, and re-run invalidated gates first.
- **8:** reuse phase 7's environment receipt (identity, boot, auth, seed) when it verified this head; otherwise verify before recording. Require a validated MP4, privacy proof, cleanup, upload receipt, and rendered-player readback. No honest runnable demo after the child's fallbacks, or tooling/OS capture denied: `BLOCKED` with the attempt ledger.

## Completion

After the last repository mutation:

1. `python3 -B <SAM_WORK_DIR>/scripts/scaffold_work_report.py finalize <WORK_DIR>/work-report.json` derives the final head and change fingerprint, commit anchors, carry-forward, and local video hashes; re-run and `record` every phase it marks stale.
2. Push; the proposal remote head must equal the final local head.
3. Every existing required check must pass. Wait in one blocking call bounded by the host tool timeout (or in the background), never polling turn by turn: `gh pr checks <id> --required --watch --fail-fast --interval 30 > <WORK_DIR>/ci.log 2>&1; echo "exit=$?"; tail -n 15 <WORK_DIR>/ci.log` (or the platform's equivalent).
4. Read back the validated description and every expected player from the body markup via the platform API (`gh pr view <id> --json body -q .body > <WORK_DIR>/body.md`); per Playwright and demo upload run `python3 -B <SAM_WORK_DIR>/../sam-create-task-demo-video/scripts/count_embeds.py <WORK_DIR>/body.md --video-url <url>` and record its `PASS` line. No screenshots.
5. Read `references/output-contract.md`, fill the remaining `SCAFFOLD:` fields, set `final.result`, and run `python3 -B <SAM_WORK_DIR>/scripts/validate_work_report.py <WORK_DIR>/work-report.json`. Fix from the validator's error lines and patch the report in place; do not read validator source or rewrite the whole report.

`COMPLETE` only when the validator passes; else `BLOCKED` or `IN_PROGRESS` with exact remaining work and receipts obtained.

## Final response

Under a parent, exactly these lines: `RESULT sam-work <COMPLETE|BLOCKED|IN_PROGRESS>`, `report: <absolute path>`, `validator: <exact last line>`, `head: <sha> fingerprint: <final change fingerprint>`, `open: <n>`, then ≤10 open-item lines. Standalone: ≤15 lines plus the report path, never the JSON: terminal; classification/implementation skill; phase ledger (terminal, iterations), final head, validator line; tests and required CI; proposal URL, remote head; environment identity, cleanup; video hashes, uploads, player readback; exact blockers or remaining work. Never hide a skipped or stale phase.
