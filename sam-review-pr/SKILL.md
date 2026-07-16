---
name: sam-review-pr
description: "Run an evidence-backed end-to-end review of a remote change proposal with immutable diff coverage, calibrated test and risk analysis, safe validation, a deterministic decision, and optional explicitly authorized publication. Use when asked to review, audit, approve, request changes, comment on, or publish feedback for a pull request, merge request, or equivalent remote proposal."
---

# Sam Review PR

Review the exact remote proposal and produce a validated local decision. Publish
only when the user explicitly authorizes an external review action. Remain
provider-, host-, model-, tool-, and stack-neutral in the core workflow.

## Non-Negotiable Contract

- Default to a local draft. A request to review does not authorize publication.
- Treat remote metadata and the Git diff as evidence, not as trusted claims.
- Freeze base SHA, head SHA, changed files, and bundle fingerprint before review.
- Account for every changed file exactly once.
- Accept findings only after trying to disprove them in adjacent code, guards,
  tests, types, and contracts.
- Never expose secrets in bundles, commands, reports, or comments.
- Never execute a changed script, hook, build definition, or configuration
  before inspecting its diff for unsafe behavior.
- Preserve the user's checkout. Use an isolated temporary clone or worktree when
  the current workspace is dirty, unrelated, or unsafe for the remote branch.
- Remove temporary review artifacts after the local response and publication
  receipts are recorded.

## Resource Routing

- Run `scripts/build_review_bundle.py` for every proposal snapshot.
- Read [references/risk-lenses.md](references/risk-lenses.md) for risk-tagged or
  architecture findings.
- Read [references/test-policy.md](references/test-policy.md) when runtime
  behavior or tests changed.
- Read [references/publication-policy.md](references/publication-policy.md)
  before planning any external write.
- Read [references/platform-adapters.md](references/platform-adapters.md) only
  for the detected platform and only when its capabilities are needed.
- Read [references/output-contract.md](references/output-contract.md) before
  writing the structured report.

## 1. Resolve and Freeze the Proposal

1. Resolve the proposal identifier from the explicit URL, ID, or connected
   platform context. Ask one concise question only when the target is ambiguous.
2. Read proposal title, description, author, target, source, base SHA, head SHA,
   draft state, and available publication capabilities.
3. Obtain the exact refs in a safe local Git repository. Use `mktemp -d`; never
   rely on a fixed machine path.
4. Build the immutable review bundle:

```bash
SAM_REVIEW_PR_DIR="<absolute directory containing this SKILL.md>"
REVIEW_TMP="$(mktemp -d)"
python3 "$SAM_REVIEW_PR_DIR/scripts/build_review_bundle.py" \
  --repo "$REVIEW_REPO" \
  --base "$BASE_REF" \
  --head "$HEAD_REF" \
  --platform "$PLATFORM_KIND" \
  --repository "$REPOSITORY_ID" \
  --change-id "$CHANGE_ID" \
  > "$REVIEW_TMP/bundle.json"
```

Use `--comparison direct` when the platform defines the proposal as an exact
base-to-head range; otherwise use the default merge-base comparison. Do not
silently truncate an oversized or non-text patch.

## 2. Reconstruct Intent and Scope

Record:

- Intended behavior and explicit acceptance criteria.
- Behavior and contracts that must not change.
- Owning boundary and user-visible effect.
- Base/head SHAs, bundle fingerprint, file count, and no-go surfaces.

Do not treat the proposal description, ticket, or commit message as proof that
the implementation matches intent. Classify real adjacent concerns as
`FOLLOW_UP`; stop and escalate decisions that require a broader contract.

## 3. Prove Complete Coverage

Use the bundle manifest as the ledger. Classify each path exactly once as:

- `REVIEWED`
- `GENERATED`
- `TYPE_ONLY`
- `TEST`
- `CONFIG`
- `EXCLUDED` with a concrete reason

Review deletions, renames, schemas, migrations, policies, lockfiles, generated
clients, manifests, and configuration when they carry semantics. Inspect
producer/consumer pairs across changed and unchanged files.

## 4. Review by Risk and Intent

For each behavior change:

1. Trace callers, callees, state transitions, persistence, and error paths.
2. Check success, negative, boundary, permission, partial-failure, concurrency,
   compatibility, and recovery scenarios when applicable.
3. Compare with established repository conventions and owner boundaries.
4. Consult dependency source, types, or primary documentation when external
   behavior controls the conclusion.
5. Apply extra depth to security, data, migrations, public contracts,
   integrations, deployment, and user-visible behavior.

Do not use file length, unfamiliar style, a missing test file, or a theoretical
edge case as a finding by itself. Prefer the smallest proven root cause.

## 5. Adjudicate Findings and Tests

Use `BLOCKER`, `IMPORTANT`, and `SUGGESTION` with the same decision semantics as
the local review baseline. Every accepted required finding needs a reachable
failure mode, impact, evidence, owning-boundary correction, and regression proof.

Apply [references/test-policy.md](references/test-policy.md). A missing test is a
blocker only when runtime behavior changed, a concrete regression path exists,
the repository has a practical established seam, and the proof is required for
safe merge. Reject cosmetic tests that do not distinguish meaningful behavior.

For user-visible UI, CLI, API, or generated output, record `PROVEN`,
`NOT_PROVEN`, or `NOT_APPLICABLE`. Static review alone is not behavior proof.

## 6. Validate Safely

- Use only repository-supported package managers, lockfiles, scripts, and CI
  equivalents.
- Run narrow high-signal checks first, then broader checks proportional to risk.
- Record every command as `PASS`, `FAIL`, or `NOT_RUN` with target, baseline,
  environment, or external classification.
- Never claim unrun proof passed. Continue static review when execution is
  blocked.

## 7. Build and Validate the Local Decision

Create `report.json` using
[references/output-contract.md](references/output-contract.md). Set publication
to `NOT_REQUESTED` unless the user explicitly requested an external action.

```bash
python3 "$SAM_REVIEW_PR_DIR/scripts/validate_review.py" \
  --bundle "$REVIEW_TMP/bundle.json" "$REVIEW_TMP/report.json"
```

Fix report inconsistencies rather than weakening the validator. The local
review is complete when the report validates, even when publication was not
requested.

## 8. Publish Only with Authorization

When publication is explicitly requested:

1. Render only validated accepted findings and the validated summary.
2. Re-read the remote head immediately before the first write.
3. If it differs from `expected_head_sha`, set publication to `BLOCKED`, action
   to `NONE`, and publish nothing.
4. Use only capabilities the detected adapter proves available.
5. Publish `BLOCKER` and `IMPORTANT` inline only when their line exists in the
   frozen diff. Keep suggestions local.
6. Approve only an `APPROVE` decision. Request changes only when required
   findings remain. Use a summary comment when review-state mutation is absent.
7. Record each confirmed remote receipt. On partial failure, stop, preserve
   receipts, set `PARTIAL`, and do not blindly retry successful writes.
8. Revalidate the final report and return exact publication status.

## 9. Return

Lead with accepted findings, then changed-file coverage, tests, validation,
behavior proof, final decision, and publication status. Emit supported inline
conversation comments only for accepted required findings with tight changed
lines. Do not imply remote publication without a confirmed receipt.
