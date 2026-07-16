---
name: sam-pr-description
description: "Create or update an evidence-backed description for a pull request, merge request, or equivalent change proposal using the actual base, immutable branch diff, complete file coverage, verified tests and safety claims, and deterministic validation. Use when asked to draft, rewrite, standardize, or remotely update a proposal description."
---

# Sam PR Description

Generate a concise reviewer-focused description from the actual change. Default
to a local draft and EN-US unless the user explicitly requests another language.
Remain provider-, host-, model-, tool-, and stack-neutral.

## Non-Negotiable Contract

- Never assume the target branch name.
- Never infer implementation, ticket, test, architecture, business-rule, or
  safety claims without evidence.
- Account for every changed file exactly once.
- Distinguish tests changed from commands actually run.
- Use `Not applicable` or `Not verified` instead of filling evidence gaps.
- Do not update a remote proposal unless the user explicitly requests it.
- Re-check the remote head immediately before an authorized update.
- Never expose secrets in context, reports, descriptions, commands, or receipts.

## Resource Routing

- Run `scripts/build_change_context.py` for every draft.
- Read [references/template.md](references/template.md) before writing the body.
- Read [references/output-contract.md](references/output-contract.md) before
  creating the evidence report.
- Run `scripts/validate_description.py` before returning or updating the body.

## 1. Resolve the Exact Base

Resolve in this order:

1. Explicit user-provided target.
2. Target of the existing remote proposal.
3. Repository or remote default branch proved by Git or platform metadata.
4. One concise question when the base remains unknown.

Do not fall back to a conventional branch name. Resolve base and head to
immutable commits before inspecting the change.

## 2. Build the Change Context

Use a safe local checkout containing both refs. Preserve unrelated dirty work;
use an isolated temporary clone or worktree when needed.

```bash
SAM_PR_DESCRIPTION_DIR="<absolute directory containing this SKILL.md>"
DESCRIPTION_TMP="$(mktemp -d)"
python3 "$SAM_PR_DESCRIPTION_DIR/scripts/build_change_context.py" \
  --repo "$DESCRIPTION_REPO" \
  --base "$TARGET_REF" \
  --head "$SOURCE_REF" \
  > "$DESCRIPTION_TMP/context.json"
```

Use `--comparison direct` only when the platform defines an exact base-to-head
range. Never truncate an oversized patch or read a sensitive path into context.

## 3. Reconstruct Scope and Evidence

Read the complete manifest, commits, and relevant changed files. Record:

- Intended outcome and why the change exists.
- Changed modules and every changed path.
- Observable behavior before and after.
- Architecture or ownership changes.
- Business rules actually encoded by the diff.
- Tests added or changed.
- Validation commands run with exact status.
- Compatibility, migration, rollout, rollback, and unresolved risks when
  applicable.
- Ticket or proposal references present in user context, metadata, branch, or
  commits.

Treat reference candidates as candidates, not verified links. A positive claim
must cite one or more evidence IDs in the temporary report.

## 4. Draft the Body

Follow [references/template.md](references/template.md). Keep sections concise
and adapt their content to the actual change:

- Do not invent endpoint or payload fields for non-API work.
- Do not claim an architecture change merely because files moved.
- Do not mark checklist items complete without evidence.
- State unrun or blocked validation explicitly.
- Mention real trade-offs only when supported by context or user evidence.
- Keep reviewer instructions focused on risk and behavior.

The body must be raw Markdown without an outer code fence, placeholders, HTML
comments, or blank template instructions.

## 5. Build and Validate the Evidence Report

Create `report.json` using
[references/output-contract.md](references/output-contract.md). Link concrete
claims to evidence. Map every changed path to one body section.

```bash
python3 "$SAM_PR_DESCRIPTION_DIR/scripts/validate_description.py" \
  --context "$DESCRIPTION_TMP/context.json" \
  "$DESCRIPTION_TMP/report.json"
```

Fix the body or evidence mapping when validation fails. Do not weaken the
validator, omit changed files, or relabel unverified claims to force success.

## 6. Update Remotely Only When Requested

For an explicit update request:

1. Set `remote_update.requested` to true.
2. Re-read the current remote head before the first write.
3. On head drift, set `BLOCKED`, record the error, and update nothing.
4. Use the available platform capability to replace only the description.
5. Record the confirmed receipt. On partial failure, preserve successful
   receipts, set `PARTIAL`, and do not blindly retry.
6. Revalidate the final report.

A local drafting request must remain `NOT_REQUESTED` with no receipts.

## 7. Return

Return only the validated description body when drafting locally. When a remote
update was explicitly requested, return the body plus the confirmed update
status or exact blocker. Remove temporary artifacts after capturing required
receipts.
