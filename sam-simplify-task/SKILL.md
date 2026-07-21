---
name: sam-simplify-task
description: "Simplify code introduced by a completed task while preserving observable behavior, public contracts, unrelated dirty work, and existing proof. Use after implementation already works when asked to reduce duplication, branching, state, indirection, speculative flexibility, or review complexity; do not use to add features, fix unknown defects, or perform broad cleanup."
---

# Sam Simplify Task

Remove task-introduced complexity without redesigning behavior. Remain stack-,
provider-, host-, tool-, and model-neutral.

## Non-Negotiable Contract

- Never expose secrets, credentials, private data, or sensitive paths in diffs,
  commands, reports, artifacts, or returned evidence.
- Operate only after the primary task and its proof exist.
- Preserve user-visible behavior, public contracts, security, permissions,
  migrations, compatibility handling, and observability.
- Preserve unrelated staged, unstaged, and untracked work byte-for-byte.
- Never reset, checkout, stash, clean, rebase, or broadly restore the workspace.
  Undo only the exact patch introduced by this simplification.
- Do not stage, commit, publish, or message an external system unless the user
  or a parent workflow (for example `sam-work`) explicitly requests it. Parent
  authorization is enough; do not re-ask.
- Stop after two simplification cycles unless new evidence appears.

## Resource Routing

- Read [references/evidence-policy.md](references/evidence-policy.md) before
  deciding whether proof is sufficient to edit.
- Read [references/risk-lenses.md](references/risk-lenses.md) selectively while
  assessing candidates.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting the structured report.
- Run `scripts/capture_scope.py` before and after simplification.
- Run `scripts/validate_report.py` before returning the decision.

## 1. Freeze Completed Work and Invariants

```bash
SAM_SIMPLIFY_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_SIMPLIFY_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/baseline.json"
```

Use repeated `--path <repo-relative-path>` only for explicit scope and reuse the
exact arguments later.

Identify and freeze:

- Task-owned changed paths and unrelated dirty paths.
- Intended behavior, public contracts, invariants, and owner boundary.
- Existing tests, runtime proof, review findings, and known limitations.
- Initial owned paths, no-go paths, and baseline fingerprint.

Under a parent workflow (for example `sam-work`), never ask—if ownership cannot
be reconstructed safely, return `BLOCKED` with receipts. When running
standalone, ask one blocking question only if ownership cannot be reconstructed
safely. Do not claim unrelated code because it is adjacent or untidy.

## 2. Establish the Safety Baseline

Inspect existing proof and run the narrowest relevant passing checks before
editing. Record exact commands and results. If a proposed structural change can
alter behavior and no practical proof can detect it, classify it `BLOCKED` or
`SKIPPED`; do not guess.

Inspect changed command definitions before executing them. Keep all temporary
backups or patch artifacts outside the repository.

## 3. Classify Simplification Candidates

Review every task-owned file and only enough adjacent code to understand it.
Look for removable duplication, branches, derived state stored unnecessarily,
pass-through wrappers, speculative options, mixed abstraction levels, misplaced
logic, brittle test setup, and artifacts made obsolete by the task.

Classify each candidate:

- `APPLIED`: clearly safer or easier to understand, in scope, and provable.
- `SKIPPED`: subjective, churn-heavy, contract-changing, or not worth the risk.
- `BLOCKED`: valuable but requires missing proof, access, or a user decision.

For every applied candidate state what complexity was removed. Prefer deletion
and existing canonical helpers. A move that preserves the same concepts,
branches, modes, or layers is not sufficient evidence of simplification.

## 4. Apply Coherent Changes and Verify

Apply one coherent simplification at a time. Preserve public APIs and external
behavior. Remove only imports, tests, fixtures, or helpers made obsolete by the
current simplification.

After each meaningful change:

1. Inspect the exact diff.
2. Confirm only owned paths changed.
3. Run targeted proof proportional to risk.
4. Undo only that exact patch if behavior changes or complexity merely moves.

If owned scope exceeds twice the frozen initial set or the work crosses an
owner, protocol, storage, migration, or release boundary: under a parent
workflow return `BLOCKED` with the exact breach (do not wait for approval);
when standalone, stop and request approval.

Run a second cycle only when the first exposes new objective simplification.
Stop when remaining opportunities are subjective polish.

## 5. Validate Scope and Decision

```bash
python3 "$SAM_SIMPLIFY_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/current.json"
python3 "$SAM_SIMPLIFY_DIR/scripts/validate_report.py" \
  --baseline "$WORK_TMP/baseline.json" \
  --current "$WORK_TMP/current.json" "$WORK_TMP/report.json"
```

Follow [references/output-contract.md](references/output-contract.md). Cover
every post-baseline path exactly once. Any changed simplification requires
passing behavior proof and mandatory gates.

Return `SIMPLEST_DEFENSIBLE` only when an applied simplification is proven and
no required candidate remains. Return `NO_CHANGE` when no edit is justified.
Return `BLOCKED` when safe simplification requires missing proof, access,
authorization, or scope expansion. Do not weaken the validator. Remove
temporary artifacts before returning.
