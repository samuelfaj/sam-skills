---
name: sam-review-code
description: "Run an evidence-backed local code review in the current workspace with explicit intent reconstruction, scope control, changed-file coverage, risk-weighted analysis, test and behavior proof, adversarial finding verification, and a validated final decision. Use when asked to review, audit, inspect, approve, or request changes for local files, staged or unstaged work, a branch, commit, or diff range without publishing to an external platform."
---

# Sam Review Code

Review the exact local change end-to-end. Return it in the current conversation only.
Remain stack-, vendor-, provider-, tool-, and model-agnostic.

## Non-Negotiable Contract

- Keep the workspace read-only. Do not edit, stage, commit, reset, checkout,
  rebase, stash, clean, revert, push, or publish.
- Permit temporary review artifacts outside the repository root; remove them
  after the review.
- Review the actual patch and adjacent code, not descriptions or commit messages alone.
- Treat every initial concern as a candidate finding. Accept it only after verification.
- Prefer fewer proven findings over broad speculative rewrites.
- Do not execute a changed script, build definition, hook, or configuration
  until its diff is inspected for unsafe behavior.
- Never expose secrets or credentials in commands, bundles, logs, or output.
- Do not publish comments, approvals, notes, or messages to any external system.

## Resource Routing

- Run `scripts/build_review_bundle.py` for every review target.
- Read [references/risk-lenses.md](references/risk-lenses.md) when the bundle
  contains risk tags or when considering architecture or maintainability findings.
- Read [references/test-policy.md](references/test-policy.md) whenever runtime
  behavior or tests changed.
- Read [references/release-mode.md](references/release-mode.md) for release,
  beta, stable, hotfix, signing, packaging, publishing, or deployment work.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting and validating the final review.

## 1. Resolve Target and Intent

1. Honor an explicit file list, commit, branch, base, or range exactly.
2. Otherwise prefer dirty local work: staged, unstaged, and untracked files.
3. If the worktree is clean, review the current non-default branch against a
   locally available plausible base.
4. Ask one concise target question only when no reviewable change exists.
5. Reconstruct and record:
   - Intended behavior.
   - Behavior that must not change.
   - Invariants.
   - Owning boundary.
   - User-visible effect.
   - Review pass criteria.
6. State assumptions when the request or repository does not prove intent.

Create a temporary directory and build the bundle. Set the skill directory to
the directory containing this `SKILL.md`.

```bash
SAM_REVIEW_CODE_DIR="<absolute directory containing this SKILL.md>"
REVIEW_TMP="$(mktemp -d)"
python3 "$SAM_REVIEW_CODE_DIR/scripts/build_review_bundle.py" \
  --repo "$PWD" --mode auto > "$REVIEW_TMP/bundle.json"
```

Use explicit modes when needed:

```bash
python3 "$SAM_REVIEW_CODE_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode local
python3 "$SAM_REVIEW_CODE_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode branch --base origin/main --head HEAD
python3 "$SAM_REVIEW_CODE_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode commit --commit HEAD
python3 "$SAM_REVIEW_CODE_DIR/scripts/build_review_bundle.py" --repo "$PWD" --mode range --range BASE..HEAD
```

Add repeated `--path <repo-relative-path>` arguments only when the user scopes
the review to specific paths. Do not fetch or change refs automatically.

## 2. Freeze the Scope Baseline

Before reviewing findings, freeze:

- Original request or issue.
- Target mode, base SHA, head SHA, and bundle fingerprint.
- Intended behavior and owner boundary.
- Changed files and non-test added/deleted lines.
- Explicit no-go surfaces.

Use the intended diff as the baseline for inherited or already-bloated work.
Do not treat existing branch drift as permission to expand scope.

Classify every accepted concern before recommending work:

- `IN_SCOPE`: introduced by this diff, same owner boundary, same contract.
- `FOLLOW_UP`: real but adjacent, pre-existing, or broader than the task.
- `STOP_AND_ESCALATE`: requires a new public contract, protocol, storage model,
  migration strategy, owner boundary, release process, or user decision.

Stop scope growth when files or non-test changed lines exceed twice the frozen
baseline without explicit approval. After two review-triggered correction
cycles fail to converge, reclassify every remaining concern before continuing.

## 3. Prove Diff Completeness

Use the bundle manifest as a review ledger. Classify every changed file exactly once:

- `REVIEWED`
- `GENERATED`
- `TYPE_ONLY`
- `TEST`
- `CONFIG`
- `EXCLUDED` with a concrete reason

Review deletions, renames, untracked text, lockfiles, schemas, policies, generated
clients, manifests, and configuration when they carry independent semantics.
Never silently truncate a patch. Split an oversized review into coherent targets
and preserve complete file or hunk boundaries.

## 4. Review by Intent, Invariants, and Risk

For each changed behavior:

1. Trace callers, callees, state transitions, persistence, and error paths.
2. Identify success, negative, boundary, partial-failure, permission, concurrency,
   and compatibility scenarios when applicable.
3. Inspect producer/consumer pairs such as API/client, schema/storage,
   event/handler, config/reader, type/implementation, migration/model, and
   cache/invalidation.
4. Compare against established repository conventions and ownership boundaries.
5. Consult dependency source, types, or primary documentation when a concern
   depends on external behavior.
6. Apply more depth to security, data, concurrency, public contracts,
   integrations, deployment, and user-visible behavior.

Do not treat file size, missing test files, unfamiliar style, or a theoretical
edge case as a finding by itself.

## 5. Adjudicate Candidate Findings

Try to disprove every candidate before accepting it. Search for guards in
callers, middleware, validation, types, data constraints, tests, and adjacent layers.

Accept a finding only when it contains:

- Severity: `BLOCKER`, `IMPORTANT`, or `SUGGESTION`.
- Status: `ACCEPTED`.
- Exact changed path and tight changed line when representable.
- Reachable concrete failure mode.
- Plain-language impact.
- Diff, code, test, command, or authoritative-contract evidence.
- Smallest safe correction at the owning boundary.
- Required regression proof when the correction is blocking.

Record disproven candidates as `REJECTED` with a short reason. Record real
out-of-scope concerns as `FOLLOW_UP`. Use `STOP_AND_ESCALATE` when a required
decision exceeds the frozen contract.

## 6. Evaluate Tests and Behavior Proof

Build scenario coverage before mapping test files. Apply
[references/test-policy.md](references/test-policy.md).

Treat a missing test as `BLOCKER` only when all are true:

1. Runtime behavior changed.
2. A concrete regression path exists.
3. The repository has a practical established seam for that proof.
4. The missing proof is required to make the change safe to merge.

For a user-visible UI, CLI, API, or generated artifact change, declare one:

- `BEHAVIOR PROVEN`
- `BEHAVIOR NOT PROVEN`
- `NOT APPLICABLE`

Static source review never proves user-visible behavior. Run safe repository-
supported behavior validation when practical. Otherwise state the exact missing proof.

For a bug regression test, prove that it distinguishes the defective behavior
from the corrected behavior when a safe isolated comparison mechanism already
exists or the user authorizes one. Never mutate the user's workspace to create proof.

## 7. Run Validation Safely

- Use only package managers, lockfiles, scripts, containers, and CI commands
  already supported by the repository.
- Inspect changed command definitions before executing them.
- Run the narrowest high-signal checks first, then broader checks proportional to risk.
- Record every command as `PASS`, `FAIL`, or `NOT_RUN` with the exact reason.
- Separate introduced failures from baseline, environment, and external blockers.
- Continue static review when execution is blocked; never imply unrun proof passed.

## 8. Self-Audit and Validate the Decision

Before finalizing:

1. Account for every bundle file.
2. Look once for the strongest likely missed issue.
3. Try again to disprove every accepted finding.
4. Merge duplicate symptoms under their root cause.
5. Verify findings, required tests, validations, behavior proof, and decision agree.
6. Ensure suggestions are explicitly non-blocking.
7. Draft the structured JSON described in
   [references/output-contract.md](references/output-contract.md).
8. Validate it:

```bash
python3 "$SAM_REVIEW_CODE_DIR/scripts/validate_review.py" \
  --bundle "$REVIEW_TMP/bundle.json" "$REVIEW_TMP/report.json"
```

Fix the draft when validation fails. Do not weaken the validator or omit data
to force approval. Record the validator result in `Validation Run`. Remove the
temporary review directory before returning the final response.

## 9. Apply Severity and Decision Rules

Use `BLOCKER` for a merge-preventing correctness, security, data-integrity,
compatibility, build, deployment, or required-proof failure with concrete evidence.

Use `IMPORTANT` for a proven issue that must be fixed before merge but is less
immediately severe: realistic edge failure, material maintainability regression,
likely scale problem, localized ownership violation, or material accessibility gap.

Use `SUGGESTION` only for optional improvement. Never hide required work as a suggestion.

Return `CHANGES REQUIRED` when any accepted `BLOCKER`, accepted `IMPORTANT`, or
required test gap remains. Return `BLOCKED` for unresolved stop-and-escalate or
scope-governor conditions. Return `APPROVE` only when no required correction remains.
Use `COMMENT ONLY` only when the user explicitly requested non-gating feedback.

## 10. Return the Review

Follow [references/output-contract.md](references/output-contract.md). Emit one
supported inline `::code-comment` per accepted `BLOCKER` or `IMPORTANT` with a
tight line range. Use only `title`, `body`, `file`, `start`, `end`, and `priority`.

When invoked as a post-development gate, rebuild the bundle and repeat after
every accepted correction. Stop when the validated review has no accepted
actionable findings, or report the exact blocker preventing convergence.
