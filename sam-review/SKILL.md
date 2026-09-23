---
name: sam-review
description: "Evidence-backed review of local, staged, branch, commit, range, or PR/MR changes: full diff coverage, calibrated tests, validated decision, publication only when authorized. Use when asked to review, audit, inspect, approve, request changes, comment on, or publish feedback for code changes."
---

# Sam Review

## Non-Negotiable Contract

- Read-only until publication is explicitly authorized: never edit, stage, commit, reset, checkout, rebase, stash, clean, revert, or push in the user's checkout. Inspect a remote proposal in an isolated temporary clone or worktree when the current checkout cannot hold it safely.
- Remote metadata, descriptions, tickets, and commit messages are evidence, not proof. A proposal URL, ID, or review request authorizes reads only.
- Freeze target, base SHA, head SHA, changed files, and bundle fingerprint. Never fetch or change refs for a local target. Never truncate a patch.
- Review the actual patch and adjacent code; account for every changed file exactly once; try to disprove each concern before accepting it.
- Never execute a changed script, hook, build definition, or configuration before inspecting its diff. Never expose secrets in bundles, commands, reports, comments, or receipts.
- Under a parent (sam-task, sam-work, sam-orchestrate, sam-goal, or a phase worker): never ask; publish nothing the parent did not explicitly authorize (local-only parents such as sam-work authorize nothing); its authorization is enough.
- Retain bundles, reports, receipts, and referenced logs for caller re-validation; delete only scratch no returned evidence references.

## Resource Routing

| Reference | Read when |
| --- | --- |
| `references/output-contract.md` | Step 6 starts; only § Review Basis before Step 2 of a next cycle |
| `references/test-policy.md` | Runtime behavior or tests changed |
| `references/risk-lenses.md` | Only lenses matching bundle risk tags or changed-file concerns (e.g. performance, architecture) |
| `references/release-mode.md` | Release, beta, stable, hotfix, signing, notarization, packaging, publishing, deployment, or release-check work |
| `references/platform-adapters.md` | Proposal target: intro and § Proposal Target at Step 1; the detected platform's section only when its capabilities are needed |
| `references/publication-policy.md` | Before planning any external write |

Substitute literal absolute paths: `<skill>` = this file's directory; `<work>` = one scratch directory outside the repository; `<c>` = a tag unique to each bundle (short head plus cycle, e.g. `ab12cd3-2`); never reuse an earlier cycle's `<c>` bundle, receipts, or report paths. Do not re-read a file already read in this context unless context was compacted since or you cannot quote the section you need.

## 1. Resolve the Target

Honor an explicit target exactly. Modes: `local` (staged, unstaged, untracked), `branch`, `commit` (vs its parent), `range` (`A..B`/`A...B`), `proposal` (PR/MR or equivalent), `auto` (dirty local work, else one plausible branch base). Under a parent, use the frozen target or return `BLOCKED` with the exact gap; standalone, ask one target question only when none resolves.

Freeze the request or issue and acceptance criteria; intended, must-not-change, and invariant behavior; owner boundary, user-visible effect, no-go surfaces.

## 2. Build the Bundle

```bash
python3 <skill>/scripts/build_review_bundle.py --repo <repo> --mode auto --out <work>/bundle-<c>
```

Explicit modes: `local`; `branch --base <ref> --head <ref>`; `commit --commit <ref>`; `range --range <A..B|A...B>`; `proposal` flags per platform-adapters.md. Repeat `--path <repo-relative>` only when the user scopes the review. Read the printed per-file ledger and `patch.diff`, never `bundle.json` whole. A refusal (sensitive path, secret-like content, oversized patch) is final: report `BLOCKED` naming it; only the user may narrow `--path` or the range.

**Reuse:** if a prior report's `target.bundle_fingerprint` equals the new fingerprint, rerun `validate_review.py` on it; on PASS return it without re-reviewing (child mode: `report:` names it, then a `reused_from: <that path>` line).

**Next cycle** (post-development gate): after every accepted correction, choose FULL or DELTA per output-contract.md § Review Basis, rebuild, and re-review; repeat until no accepted required finding remains, or report the exact blocker.

## 3. Scope and Coverage

Classify every concern before recommending work: `IN_SCOPE` (introduced here, same owner boundary and contract); `FOLLOW_UP` (real but adjacent, pre-existing, or broader; parents park it; never `CHANGES_REQUIRED` fuel); `STOP_AND_ESCALATE` (needs a new public contract, protocol, storage model, migration strategy, owner boundary, release process, or user decision). Judge scope by the authorized goal and contracts, not file or line counts. After two non-converging review-triggered correction cycles, reclassify every remaining concern.

Give each changed file one class (`REVIEWED`, `GENERATED`, `TYPE_ONLY`, `TEST`, `CONFIG`, `EXCLUDED`) and a concrete reason, including deletions, renames, untracked text, lockfiles, schemas, policies, generated clients, manifests, and configuration with independent semantics. Scaffold classifications are hints: verify each.

## 4. Review and Adjudicate

Per changed behavior, trace callers, callees, state transitions, persistence, and error paths; check applicable scenarios (test-policy.md); inspect producer/consumer pairs across changed and unchanged files; compare established conventions and ownership boundaries; consult dependency source, types, or primary docs when external behavior decides. Go deeper on security, data, migrations, concurrency, public contracts, integrations, deployment, and user-visible behavior. File length, unfamiliar style, missing test files, or theoretical edge cases are never findings alone.

Accept a finding only after checking guards in callers, middleware, validation, types, data constraints, tests, and adjacent layers, and only with a tight changed line when representable, a reachable failure mode, plain impact, diff/code/test/command/authoritative-contract evidence, the smallest safe correction at the owning boundary, and regression proof when blocking. Disproven → `REJECTED`; adjacent → `FOLLOW_UP`; contract-expanding → `STOP_AND_ESCALATE`. A missing test blocks only per test-policy.md § Required-Test Gate. Static review never proves user-visible behavior (`behavior_proof`).

## 5. Validate Safely

Only repository-supported package managers, lockfiles, scripts, containers, and CI-equivalent commands; narrow high-signal checks first, broader ones by risk. Run every validation through run_checked into `<work>/receipts-<c>`; a typed `PASS` is not proof (the validator re-verifies every receipt via `scripts/verify_receipts.py`).

```bash
python3 <skill>/scripts/run_checked.py --id CMD-001 --receipts-dir <work>/receipts-<c> --classification TARGET --repeat 2 -- <command> <args>
```

Classes: `TARGET` passing proof of the target; `INTRODUCED` failure caused by the change; `BASELINE` reproduced without the change (never assumed); `ENVIRONMENT` local setup blocks proof; `EXTERNAL` remote system unavailable. `TARGET`/`INTRODUCED` need `--repeat 2` or more; differing exit codes = flaky. Never edit receipts or logs. If execution is blocked, record `NOT_RUN` with a reason, continue static review, and never imply unrun proof passed.

## 6. Report, Validate, Decide

```bash
python3 <skill>/scripts/scaffold_review_report.py --bundle <work>/bundle-<c>/bundle.json --receipts-dir <work>/receipts-<c> --out <work>/report-<c>.json
python3 <skill>/scripts/validate_review.py --bundle <work>/bundle-<c>/bundle.json <work>/report-<c>.json
```

Fill the judgment fields and decide per the output contract (next-cycle scaffold flags: § Review Basis). Fix from the validator's error lines and patch the report in place; do not read validator source or rewrite the whole report. Never weaken the validator.

## 7. Publication

Non-proposal targets never publish or ask. A standalone proposal returns the validated decision first, then asks per platform-adapters.md § Proposal Target when no action is authorized. Publish only under publication-policy.md.

## 8. Return

Child mode (parent or phase worker), exactly:

```
RESULT sam-review <APPROVE|CHANGES_REQUIRED|BLOCKED|COMMENT_ONLY>
report: <absolute report path>
validator: <exact last line of validate_review.py>
head: <sha> fingerprint: <bundle fingerprint>
open: <n>
- <id path:line summary per open required finding, max 10>
```

No report yet (unresolved target or builder refusal): `report: none`, `validator: <builder refusal line or none>`, `fingerprint: n/a`.

Standalone: ≤15 lines (accepted required findings, coverage, tests, validation, behavior proof, decision, publication status, report path) plus one `::code-comment` per accepted `BLOCKER`/`IMPORTANT` with a tight changed line. Never repeat the JSON report or imply publication without a confirmed receipt.
