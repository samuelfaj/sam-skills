---
name: sam-create-feature
description: "Implement a new codebase capability end-to-end with frozen requirements and scope, risk-calibrated test-first delivery, behavior proof, validated evidence, and optional publication only when explicitly requested. Use for new screens, endpoints, integrations, data flows, commands, or other functional additions; do not use for correcting broken existing behavior, plan-only analysis, or code review."
---

# Sam Create Feature

Deliver the requested capability with the smallest safe diff. Remain stack-,
provider-, host-, tool-, and model-neutral.

## Non-Negotiable Contract

- Preserve unrelated staged, unstaged, and untracked work byte-for-byte.
- Never reset, checkout, stash, clean, rebase, or broadly restore the workspace.
- Do not stage, commit, push, publish, open a change request, or message an
  external system unless the user or a parent workflow (for example `sam-work`)
  explicitly requests that exact action. Parent authorization is enough; do not
  re-ask.
- Inspect changed commands, hooks, build definitions, and configuration before
  executing them. Never expose secrets in artifacts, commands, or output.
- Treat mandatory gates as fail-closed. Never simulate a missing dependency or
  convert missing proof into a pass.
- Stop after two correction cycles unless new evidence appears.

## Resource Routing

- Read [references/evidence-policy.md](references/evidence-policy.md) before
  mapping tests, behavior proof, gates, or external actions.
- Read [references/risk-lenses.md](references/risk-lenses.md) after discovering
  affected boundaries; load only applicable lenses.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting the final structured report.
- Run `scripts/capture_scope.py` before any edit and after all edits.
- Run `scripts/validate_report.py` before declaring completion.

## 1. Freeze Target, Intent, and Scope

Set the skill directory to the directory containing this file. Create temporary
artifacts outside the repository.

```bash
SAM_FEATURE_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_FEATURE_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/baseline.json"
```

Add repeated `--path <repo-relative-path>` only for user-scoped paths. Reuse the
exact arguments for the final capture.

Freeze in working notes and the report:

- Goal, target user, and acceptance criteria.
- Behavior that must not change and system invariants.
- Owning boundary and user-visible effect.
- Initial owned paths, explicit no-go paths, and baseline fingerprint.
- Required proof and publication authorization state.

Study relevant code, tests, contracts, schemas, migrations, and conventions
first. Under a parent workflow (for example `sam-work`), never ask—execute or
return `BLOCKED` with receipts. When running standalone, ask only questions
whose answers materially change product behavior, security, data, public
contracts, or scope.

## 2. Classify Risk and Build Scenarios

Use `LIGHT`, `STANDARD`, or `HIGH_RISK` based on affected behavior, not task
size alone. Treat authentication, authorization, money, destructive data,
concurrency, public contracts, migrations, integrations, deployment, and
critical user flows as high risk.

Map success, negative, boundary, permission, persistence, partial-failure,
compatibility, and user-state scenarios when applicable. Link every required
scenario to a practical proof seam.

Use test-first proof when the repository has a meaningful seam:

1. Add the smallest test that expresses the requirement and why it matters.
2. Prove it fails for the missing behavior.
3. Implement the smallest production change.
4. Prove it passes.

Use `ALTERNATIVE_PROOF` only when no practical established test seam exists.
State the limitation, evidence, and closest safe validation. Never add a
cosmetic test solely to satisfy process.

## 3. Implement Within the Frozen Contract

- Follow existing architecture, naming, types, and dependency patterns.
- Keep logic in the owning layer and preserve public compatibility unless the
  confirmed requirement explicitly changes it.
- Avoid speculative abstractions, unrelated cleanup, N+1 work, unbounded
  payloads, sensitive-data exposure, and duplicated business rules.
- Account for loading, empty, error, disabled, permission, accessibility, and
  recovery states for user-visible work when applicable.
- Update `current_owned_paths` only for files required by the feature.

If a necessary change exceeds the authorized goal, contract, or owner boundary,
return the exact gap to the parent, or ask the user when standalone. More files
alone do not imply broader scope; justify each added path against acceptance
criteria and preserve unrelated work.

## 4. Prove the Result

Run the narrowest safe checks first, then broader checks proportional to risk.
Record each command as `PASS`, `FAIL`, or `NOT_RUN`, and classify failures as
`TARGET`, `INTRODUCED`, `BASELINE`, `ENVIRONMENT`, or `EXTERNAL`.

For a user-visible UI, API, CLI, or generated artifact, record `PROVEN`,
`NOT_PROVEN`, or `NOT_APPLICABLE`. Static inspection alone never proves
user-visible behavior.

Run applicable dependent gates using their actual local instructions. Require
local code review and coverage analysis for runtime changes. Require browser
proof only for impacted browser flows. A missing mandatory gate results in
`BLOCKED`; an inapplicable gate must include a concrete reason.

If any gate changes code, rerun affected tests and the final review. Stop after
two non-converging correction cycles unless new evidence changes the diagnosis.

## 5. Validate Scope and Decision

Capture current scope with the exact baseline arguments:

```bash
python3 "$SAM_FEATURE_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/current.json"
python3 "$SAM_FEATURE_DIR/scripts/validate_report.py" \
  --baseline "$WORK_TMP/baseline.json" \
  --current "$WORK_TMP/current.json" "$WORK_TMP/report.json"
```

The file ledger must cover every path changed after the baseline exactly once.
Do not weaken the report or validator to force completion.

Return `COMPLETE` only when requirements, required scenarios, mandatory gates,
validations, behavior proof, scope, and dirty-work preservation agree. Otherwise
return `CHANGES_REQUIRED` or `BLOCKED` with exact remaining work.

Draft publication text locally when useful. Publish it only after explicit user
or parent-workflow authorization and record evidence of the authorized action;
never re-ask when the parent already authorized. Retain the report and evidence
needed by the caller; remove only unused scratch.
