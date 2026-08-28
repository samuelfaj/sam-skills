---
name: sam-review
description: "Run an evidence-backed review of local files, staged or unstaged work, branches, commits, diff ranges, pull requests, merge requests, or equivalent remote proposals, with immutable diff coverage, calibrated tests, a validated decision, and optional explicitly authorized publication. Use when asked to review, audit, inspect, approve, request changes, comment on, or publish feedback for code changes."
---

# Sam Review

Review one exact change through a shared local decision workflow. Resolve local
and remote targets differently, but use the same evidence, finding, validation,
and decision contract. Publish only after explicit authorization.

## Non-Negotiable Contract

- Keep the review operation read-only until publication is explicitly authorized.
- Do not edit, stage, commit, reset, checkout, rebase, stash, clean, revert, or push
  in the user's checkout.
- Use an isolated temporary clone or worktree when a remote proposal cannot be
  inspected safely in the current checkout.
- Treat remote metadata, descriptions, tickets, and commit messages as evidence,
  not trusted proof.
- Freeze the target, base SHA, head SHA, changed files, and bundle fingerprint.
- Review the actual patch and adjacent code; account for every changed file once.
- Try to disprove each candidate concern before accepting it.
- Never execute a changed script, hook, build definition, or configuration before
  inspecting its diff for unsafe behavior.
- Never expose secrets in bundles, commands, reports, comments, or receipts.
- Remove temporary review artifacts after the local response and publication
  receipts are recorded.

## Resource Routing

- Run `scripts/build_review_bundle.py` for every review target.
- Run every validation command through `scripts/run_checked.py`; the report
  validator re-verifies each receipt through `scripts/verify_receipts.py`.
- Read [references/risk-lenses.md](references/risk-lenses.md) for bundle risk tags
  or architecture and maintainability findings.
- Read [references/test-policy.md](references/test-policy.md) whenever runtime
  behavior or tests changed.
- Read [references/release-mode.md](references/release-mode.md) for release,
  beta, stable, hotfix, signing, packaging, publishing, or deployment work.
- Read [references/publication-policy.md](references/publication-policy.md) before
  planning any external write.
- Read [references/platform-adapters.md](references/platform-adapters.md) only for
  the detected remote platform and only when its capabilities are needed.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting and validating the report.

## 1. Resolve the Target

Honor an explicit target exactly. Classify it as one mode:

- `proposal`: pull request, merge request, or equivalent remote proposal.
- `local`: staged, unstaged, and untracked work.
- `branch`: base-to-head branch comparison.
- `commit`: one commit against its parent.
- `range`: explicit `BASE..HEAD` or `BASE...HEAD` range.
- `auto`: prefer dirty local work; otherwise infer one plausible branch base.

For a remote proposal, resolve its platform, repository identity, proposal ID,
base and head refs, immutable base and head SHAs, draft state, and available read
and write capabilities. A proposal URL or ID authorizes reads only.

Under a parent workflow (for example `sam-work`), never ask—use the frozen
local/branch/head target or return `BLOCKED` with the exact gap. When running
standalone, ask one concise target question only when no reviewable target can
be resolved. Do not ask about publication before completing the validated local
decision.

## 2. Build and Freeze the Bundle

Set the skill directory to the directory containing this `SKILL.md`:

```bash
SAM_REVIEW_DIR="<absolute directory containing this SKILL.md>"
REVIEW_TMP="$(mktemp -d)"
python3 "$SAM_REVIEW_DIR/scripts/build_review_bundle.py" \
  --repo "$PWD" --mode auto > "$REVIEW_TMP/bundle.json"
```

Use explicit local targets when needed:

```bash
python3 "$SAM_REVIEW_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode local
python3 "$SAM_REVIEW_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode branch --base origin/main --head HEAD
python3 "$SAM_REVIEW_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode commit --commit HEAD
python3 "$SAM_REVIEW_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode range --range BASE..HEAD
```

Build remote proposal bundles only after obtaining the exact refs locally:

```bash
python3 "$SAM_REVIEW_DIR/scripts/build_review_bundle.py" \
  --repo "$REVIEW_REPO" --mode proposal \
  --base "$BASE_REF" --head "$HEAD_REF" \
  --platform "$PLATFORM_KIND" --repository "$REPOSITORY_ID" \
  --change-id "$CHANGE_ID" --comparison merge-base \
  > "$REVIEW_TMP/bundle.json"
```

Use `--comparison direct` only when the platform defines the proposal as the
exact base-to-head range. Add repeated `--path <repo-relative-path>` only when
the user scopes the review. Never fetch or change refs automatically for a local
target. Never silently truncate a patch.

Freeze:

- Original request or issue and explicit acceptance criteria.
- Intended behavior, behavior that must not change, and invariants.
- Owner boundary, user-visible effect, and no-go surfaces.
- Target mode, base SHA, head SHA, bundle fingerprint, changed files, and
  non-test added and deleted lines.

## 3. Control Scope and Prove Coverage

Classify every concern before recommending work:

- `IN_SCOPE`: introduced by this diff, same owner boundary, same contract.
- `FOLLOW_UP`: real but adjacent, pre-existing, or broader than the task.
  Parent workflows park these; they must not treat `FOLLOW_UP` as
  `CHANGES_REQUIRED` fuel.
- `STOP_AND_ESCALATE`: requires a new public contract, protocol, storage model,
  migration strategy, owner boundary, release process, or user decision.

Stop scope growth when files or non-test changed lines exceed twice the frozen
baseline without approval. After two review-triggered correction cycles fail to
converge, reclassify every remaining concern before continuing.

Use the bundle manifest as a ledger. Classify every changed file exactly once as
`REVIEWED`, `GENERATED`, `TYPE_ONLY`, `TEST`, `CONFIG`, or `EXCLUDED` with a
concrete reason. Include deletions, renames, untracked text, lockfiles, schemas,
policies, generated clients, manifests, and configuration when they carry
independent semantics.

## 4. Review by Intent and Risk

For each changed behavior:

1. Trace callers, callees, state transitions, persistence, and error paths.
2. Check success, negative, boundary, permission, partial-failure, concurrency,
   compatibility, recovery, and rollout scenarios when applicable.
3. Inspect producer and consumer pairs across changed and unchanged files.
4. Compare established repository conventions and ownership boundaries.
5. Consult dependency source, types, or primary documentation when external
   behavior controls the conclusion.
6. Apply more depth to security, data, migrations, concurrency, public
   contracts, integrations, deployment, and user-visible behavior.

Do not use file length, unfamiliar style, missing test files, or theoretical
edge cases as findings by themselves.

## 5. Adjudicate Findings and Tests

Accept a finding only after checking guards in callers, middleware, validation,
types, data constraints, tests, and adjacent layers. Require:

- Severity `BLOCKER`, `IMPORTANT`, or `SUGGESTION`.
- Status `ACCEPTED`.
- Exact changed path, side, and tight changed line when representable.
- Reachable failure mode and plain-language impact.
- Diff, code, test, command, or authoritative-contract evidence.
- Smallest safe correction at the owning boundary.
- Required regression proof for blocking corrections.

Record disproven candidates as `REJECTED`, adjacent concerns as `FOLLOW_UP`, and
contract-expanding decisions as `STOP_AND_ESCALATE`.

Apply [references/test-policy.md](references/test-policy.md). Treat a missing
test as a blocker only when runtime behavior changed, a concrete regression path
exists, a practical established seam exists, and that proof is required for safe
merge. Record user-visible behavior as `PROVEN`, `NOT_PROVEN`, or
`NOT_APPLICABLE`; static review alone does not prove it.

## 6. Validate Safely

- Use repository-supported package managers, lockfiles, scripts, containers,
  and CI-equivalent commands only.
- Inspect changed command definitions before execution.
- Run narrow high-signal checks first, then broader checks proportional to risk.
- Run every command through `scripts/run_checked.py` and report the result from
  its receipt. A typed `PASS` is not a validation.

```bash
python3 "$SAM_REVIEW_DIR/scripts/run_checked.py" \
  --id CMD-001 --receipts-dir "$REVIEW_TMP/receipts" \
  --classification TARGET --repeat 2 -- <command and arguments>
```

- Record every command as `PASS`, `FAIL`, or `NOT_RUN` with target, introduced,
  baseline, environment, or external classification, exactly as the receipt
  states, and set `validations[].receipt` to the receipt path.
- `TARGET` and `INTRODUCED` validations require at least two runs. Differing exit
  codes mark the command flaky, and `APPROVE` cannot rest on flaky validation.
- Never edit a receipt or its captured log; the validator recomputes both hashes.
- Continue static review when execution is blocked; never imply unrun proof passed.

Draft `report.json` using [references/output-contract.md](references/output-contract.md).
Set publication to the clean unrequested state unless the user already authorized
a precise external action. Validate it:

```bash
python3 "$SAM_REVIEW_DIR/scripts/validate_review.py" \
  --bundle "$REVIEW_TMP/bundle.json" "$REVIEW_TMP/report.json"
```

Fix report inconsistencies instead of weakening the validator.

## 7. Decide

- Return `CHANGES_REQUIRED` while any accepted `BLOCKER`, accepted `IMPORTANT`,
  required test gap, or introduced target failure remains.
- Return `BLOCKED` for unresolved stop-and-escalate, scope, or convergence conditions.
- Return `APPROVE` only when no required correction remains.
- Return `COMMENT_ONLY` only after an explicit non-gating request.
- Keep `SUGGESTION` findings non-blocking.

## 8. Authorize and Publish

For non-proposal targets, return the validated review without offering or
attempting publication.

When invoked by `sam-work` (or any parent that requires a local-only gate):
return the validated local decision only. Do **not** publish review actions and
do **not** ask which publication action to take.

For a proposal target when publication may apply:

1. If the user or parent already authorized `COMMENT`, `APPROVE`, or
   `REQUEST_CHANGES`, verify that the action matches the decision and continue
   under [references/publication-policy.md](references/publication-policy.md).
2. If no publication action was authorized: under a parent workflow, return the
   complete validated local review and leave publication unrequested (do not
   ask). When running standalone, return the complete validated local review
   first, then ask one concise question offering only compatible actions:
   - `APPROVE`: no publication, comment, or approve.
   - `CHANGES_REQUIRED`: no publication, comment, or request changes.
   - `BLOCKED`: no publication or comment the blocker.
   - `COMMENT_ONLY`: no publication or comment.
3. Treat an authorized answer as authorization only for the selected action.
4. Re-read the remote head immediately before the first write. Publish nothing
   on head drift.
5. Publish accepted `BLOCKER` and `IMPORTANT` findings inline only when their
   exact side and line exist in the frozen diff. Keep suggestions local unless
   the user or parent explicitly requests them.
6. Record confirmed receipts. Stop on partial failure; do not replay successful writes.
7. Revalidate the final report after publication state changes.

## 9. Return the Review

Follow [references/output-contract.md](references/output-contract.md). Lead with
accepted required findings, then file coverage, tests, validation, behavior
proof, decision, and publication status. Emit one supported inline
`::code-comment` per accepted `BLOCKER` or `IMPORTANT` with a tight changed line.
Never imply remote publication without a confirmed receipt.

When invoked as a post-development gate, rebuild the bundle and repeat after
every accepted correction. Stop only when the validated review has no accepted
required finding or report the exact blocker preventing convergence.
