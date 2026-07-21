---
name: sam-fix-bug
description: "Diagnose and repair broken existing behavior with exact reproduction, proven root cause, frozen scope, the smallest safe correction, calibrated regression proof, and validated evidence. Use for defects, regressions, crashes, incorrect results, failed user flows, or contract violations; do not use for new capabilities, plan-only analysis, or code review."
---

# Sam Fix Bug

Fix the defect at its owning boundary with the smallest safe diff. Remain
stack-, provider-, host-, tool-, and model-neutral.

## Non-Negotiable Contract

- Preserve unrelated staged, unstaged, and untracked work byte-for-byte.
- Never reset, checkout, stash, clean, rebase, or broadly restore the workspace.
- Do not stage, commit, push, publish, open a change request, or message an
  external system unless the user or a parent workflow (for example `sam-work`)
  explicitly requests that exact action. Parent authorization is enough; do not
  re-ask.
- Do not patch from the reported symptom alone. Prove the reachable failure and
  root cause, or return `BLOCKED`.
- Treat mandatory gates as fail-closed. Never simulate a missing dependency or
  invent proof.
- Stop after two correction cycles unless new evidence appears.

## Resource Routing

- Read [references/evidence-policy.md](references/evidence-policy.md) before
  choosing reproduction and regression proof.
- Read [references/risk-lenses.md](references/risk-lenses.md) after locating the
  failure boundary; load only applicable lenses.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting the structured report.
- Run `scripts/capture_scope.py` before any edit and after all edits.
- Run `scripts/validate_report.py` before declaring completion.

## 1. Freeze Target, Intent, and Scope

Set the skill directory to the directory containing this file. Keep temporary
artifacts outside the repository and remove them before returning.

```bash
SAM_BUG_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_BUG_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/baseline.json"
```

Add repeated `--path <repo-relative-path>` only for explicit user scope and
reuse the exact arguments later.

Freeze:

- Observed behavior, expected behavior, and affected user or system flow.
- Business rule or contract that must hold.
- Behavior that must not change and system invariants.
- Owning boundary, initial owned paths, no-go paths, and fingerprint.
- Required reproduction, regression, behavior, and publication proof.

Inspect relevant callers, routes, handlers, state, persistence, tests, logs,
schemas, and configuration. Under a parent workflow (for example `sam-work`),
never ask—execute or return `BLOCKED` with receipts. When running standalone,
ask only blocking questions after available evidence is exhausted.

## 2. Reproduce and Prove Root Cause

Reproduce at the narrowest layer that still exercises the reported failure.
Trace the causal chain; distinguish root cause from downstream symptoms.

For browser-to-service failures, prove the actual method, URL, route
registration, preflight when applicable, failed-response visibility, and final
user action. A change that only reveals a hidden error is not a complete fix.

Record one reproduction status:

- `REPRODUCED`: observed directly through a meaningful test or runtime path.
- `PROVEN_BY_CONTRACT`: direct execution is unavailable, but code and an
  authoritative contract prove the violation.
- `BLOCKED`: evidence cannot distinguish a defect from environment, data,
  configuration, or external state.

Do not edit production code while root cause remains speculative.

## 3. Build Regression Proof and Fix Minimally

Prefer a differential regression test that fails under defective behavior and
passes after the correction. Use `ALTERNATIVE_PROOF` only when no practical
test seam exists; state why and provide the closest behavior-level evidence.

Implement only at the owning boundary. Preserve public contracts unless the
proven defect is the contract itself. Avoid unrelated refactors, speculative
abstractions, duplicated rules, sensitive-data exposure, N+1 work, and widened
payloads.

Map success, negative, boundary, permission, persistence, partial-failure,
compatibility, and adjacent regression scenarios when applicable. Verify
user-visible loading, empty, error, disabled, accessibility, and recovery states
only when the affected flow reaches them.

If the correction needs more than twice the frozen owned scope or changes a
protocol, storage model, migration strategy, owner boundary, release process, or
destructive behavior: under a parent workflow return `BLOCKED` with the exact
scope breach (do not wait for approval); when standalone, stop and request
approval.

## 4. Validate and Run Gates

Run the narrowest safe checks first, then broader checks proportional to risk.
Inspect changed command definitions before executing them. Record exact command
status and classify failures as `TARGET`, `INTRODUCED`, `BASELINE`,
`ENVIRONMENT`, or `EXTERNAL`.

Record user-visible behavior as `PROVEN`, `NOT_PROVEN`, or `NOT_APPLICABLE`.
Static source review does not prove a user-visible fix.

Run applicable local review and coverage gates for runtime changes. Run browser
proof only for impacted browser flows. A missing mandatory dependency or proof
results in `BLOCKED`; never synthesize a pass. If a gate changes code, rerun the
affected proof. Stop after two non-converging cycles without new evidence.

## 5. Validate Scope and Decision

```bash
python3 "$SAM_BUG_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/current.json"
python3 "$SAM_BUG_DIR/scripts/validate_report.py" \
  --baseline "$WORK_TMP/baseline.json" \
  --current "$WORK_TMP/current.json" "$WORK_TMP/report.json"
```

Follow [references/output-contract.md](references/output-contract.md). Cover
every post-baseline path exactly once. Do not weaken the validator.

Return `COMPLETE` only when reproduction, root cause, regression proof,
required scenarios, validations, mandatory gates, behavior proof, scope, and
dirty-work preservation agree. Otherwise return `CHANGES_REQUIRED` or
`BLOCKED` with exact remaining work.

Draft publication text locally when useful. Publish only after explicit user or
parent-workflow authorization and record the action evidence; never re-ask when
the parent already authorized. Remove temporary artifacts before the final
response.
