---
name: sam-pr-description
description: "Write or update a pull/merge request description from the real base and immutable diff, covering every file and only verified test and safety claims. Use when asked to draft, rewrite, standardize, or remotely update a proposal description."
---

# Sam PR Description

Concise and reviewer-focused; provider-, host-, model-, tool-, and stack-neutral.

## Non-Negotiable Contract

- Never assume the target branch name.
- Never make an implementation, ticket, test, architecture, business-rule, or safety claim without evidence; write `Not applicable` or `Not verified` instead of filling gaps; distinguish tests changed from commands actually run.
- Account for every changed file exactly once.
- Draft locally; update a remote proposal only on an explicit user or parent (e.g. sam-work) request, which is enough: never re-ask.
- Never truncate the patch, read a sensitive path into context, or expose secrets in context, reports, descriptions, commands, or receipts.
- Retain report, context, body, and referenced evidence for caller re-validation; remove only unused scratch.

## Resource Routing

| Reference | Read when |
| --- | --- |
| `references/output-contract.md` | Step 4 starts (body and report) |

Substitute literal absolute paths: `<skill>` = this file's directory; `<work>` = one scratch directory outside the repository. Do not re-read a file already read in this context unless context was compacted since or you cannot quote the section you need.

## 1. Resolve the Exact Base

In order: explicit user or parent target; the existing remote proposal's target; the repository or remote default branch proved by Git or platform metadata. Still unknown: `BLOCKED` with the exact gap under a parent, one concise question standalone. Resolve base and head to immutable commits before inspecting.

## 2. Build the Context

Use a safe local checkout holding both refs, preserving unrelated dirty work (isolated temporary clone or worktree when needed):

```bash
python3 <skill>/scripts/build_change_context.py --repo <repo> --base <target-ref> --head <source-ref> --out <work>/desc-<short-head>
```

Add `--comparison direct` only when the platform defines an exact base-to-head range. Read the printed per-file summary and `patch.diff`, never `context.json` whole; `--out` also writes the `report.json` scaffold. A refusal (sensitive path, secret-like content, oversized patch) is final: report `BLOCKED`.

## 3. Reconstruct Scope and Evidence

Reuse a sam-review report as the ledger only if `python3 <skill>/../sam-review/scripts/validate_review.py --bundle <its bundle.json> <report>` passes now, that bundle has no `path_filters`, and its `target.merge_base_sha`..`head_sha` equals the context's `base_sha`..`head_sha`: take its intent, `file_coverage` reasons, and receipt-backed validations, and read only the `patch.diff` hunks the body details. Otherwise read `patch.diff`, commits, and relevant changed files. Establish what applies: problem, outcome, rationale, beneficiaries; behavior before/after/unchanged; business rules added/changed/preserved; user, API, data, configuration, operational, compatibility impact; failure modes, mitigations, residual risk, rollout, monitoring, recovery; tests changed; commands run with exact status; reference candidates from user context, metadata, branch, and commits (treat them as candidates, not verified links).

## 4. Draft the Body

Write it once to `body.md` beside the scaffold (its `body_file`). Follow the repository's proposal template and its requirements when present, but always keep `## Description` (the concrete problem and resulting behavior, one or two sentences) and `## Validation` (checks actually run and results, or what was not verified and why). Add sections only when needed (business rules, compatibility, migrations, rollout/recovery, material risks, reviewer focus); omit empty sections and checklist boilerplate; scale detail to the change. Write for a reader who did not implement it: problem, outcome, and observable behavior first; business rules as conditions and outcomes; each material risk with its mitigation or "none proven"; reviewer notes on risk and behavior. Never invent endpoint or payload fields for non-API work, narrate files where a behavior summary is clearer, or check checklist items without evidence. Coverage and evidence IDs stay in the report.

## 5. Report and Validate

Complete `report.json` per the output contract, then:

```bash
python3 <skill>/scripts/validate_description.py --context <work>/desc-<short-head>/context.json <work>/desc-<short-head>/report.json
```

Fix from the validator's error lines and patch the report or body in place; do not read validator source or rewrite the whole report. Never weaken the validator, omit changed files, or relabel unverified claims.

## 6. Update Remotely Only When Requested

Set `remote_update.requested: true`; re-read the remote head immediately before the first write and write nothing on drift; replace only the description, from the validated `body.md` (the platform's body-from-file option); record the confirmed receipt; on partial failure keep successful receipts and never blindly retry; revalidate.

## 7. Return

Child mode (parent or phase worker), exactly:

```
RESULT sam-pr-description <READY|PARTIAL|BLOCKED>
report: <absolute report path>
validator: <exact last line of validate_description.py>
head: <sha> fingerprint: <context fingerprint>
open: <n>
- <one line per open item, max 10>
```

No report yet (unresolved base or builder refusal): `report: none`, `validator: <builder refusal line or none>`, `fingerprint: n/a`.

`READY` = validator PASS with `remote_update` `NOT_REQUESTED` or `UPDATED`; the parent reads the body from `body_file`. Standalone: the validated body from `body.md`, the report path, and, for a requested update, the confirmed status or exact blocker. Never repeat the JSON report.
