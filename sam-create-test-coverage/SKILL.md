---
name: sam-create-test-coverage
description: "Design, implement, and validate risk-based regression coverage across unit, component, integration, API/contract, and browser E2E layers, selecting the smallest reliable proof for each changed behavior. Use when asked to add tests, prove a bug fix, increase confidence or coverage, map acceptance criteria, or close backend or frontend test gaps."
---

# Sam Create Test Coverage

Create the smallest reliable set of tests that proves the changed contract.
Remain stack-, host-, provider-, tool-, and model-agnostic.

## Non-Negotiable Contract

- Honor the exact repository, path, branch, commit, range, and criteria supplied.
- Preserve existing work. Do not reset, checkout, stash, clean, rebase, or rewrite history.
- Freeze base SHA, head SHA, bundle fingerprint, intent, no-go scope, environment
  identity, and cleanup ledger before editing.
- Inspect changed scripts, hooks, test runners, package commands, containers, and
  CI definitions before executing them.
- Fail closed when a real-data E2E target is unknown or is not a verified local,
  test, or development environment.
- Keep artifacts local by default. Publish only when the user or a parent
  workflow (for example `sam-work`) explicitly requests it and the exact remote
  target is resolved. Parent authorization is enough; do not re-ask.
- Never expose secrets, credentials, private data, or sensitive paths in bundles,
  commands, artifacts, reports, or returned evidence.
- Reject `.only`, `.skip`, retries, broad timeouts, snapshot refreshes, assertion
  weakening, and mocks that remove the contract under test.
- Never report a command result that did not come from `scripts/run_checked.py`.
  A status without a verifiable receipt is not evidence.
- Limit production changes to the in-scope correction or smallest test seam
  required by an accepted scenario.
- Record and clean every process, container, port, record, override, and artifact.

## Resource Routing

- Read [references/layer-selection.md](references/layer-selection.md) when mapping
  scenarios to test layers.
- Read [references/scenario-and-risk-policy.md](references/scenario-and-risk-policy.md)
  while building the coverage ledger.
- Read [references/environment-and-data-safety.md](references/environment-and-data-safety.md)
  before starting services or using persistent data.
- Read [references/regression-proof.md](references/regression-proof.md) before
  claiming a new test protects a regression.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting and validating the report.

## 1. Resolve and Freeze the Change

Set the skill directory to the directory containing this file. Build a local
bundle without fetching or modifying refs:

```bash
SAM_COVERAGE_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_COVERAGE_DIR/scripts/build_test_impact.py" \
  --repo "$PWD" --environment-kind unknown \
  --environment-id "unverified" > "$WORK_TMP/baseline-bundle.json"
```

Pass `--base`, `--head`, and repeated `--path` arguments when specified. Rebuild
after verifying a real-data environment.

Freeze:

- Target mode, base/head refs and SHAs, bundle fingerprint, and changed files.
- Intended behavior, invariants, acceptance criteria, and explicit no-go scope.
- Owning boundaries, affected contracts, and command definitions.
- Environment kind, identity, endpoints, database/tenant, and proof.
- Cleanup ledger initialized for all resources the run may create.

Under a parent workflow (for example `sam-work`), never ask—use the frozen
target/environment or return `BLOCKED` with receipts. When running standalone,
ask one concise question only when the target or safety-critical environment
cannot be discovered. Never infer a safe database or tenant from a name alone.

## 2. Build the Behavior and Risk Ledger

Use stable IDs:

- `AC-###`: acceptance criterion.
- `B-###`: changed behavior.
- `R-###`: reachable risk.
- `S-###`: scenario.
- `T-###`: test.
- `CMD-###`: validation command and result.
- `ART-###`: local or explicitly published evidence.
- `CL-###`: cleanup resource.

Link criteria to behaviors, risks, scenarios, tests, commands, results, and
artifacts. Cover applicable success, negative, boundary, permission, validation,
state-transition, persistence, cache, concurrency, error, recovery, compatibility,
and accessibility cases. Omit inapplicable classes with a reason.

Assign each scenario `PLANNED`, `AUTOMATED`, `MANUAL_PROOF`, `REDUNDANT`, or
`NOT_COVERED`. Link `REDUNDANT` to an equivalent scenario. Give `NOT_COVERED` an
exact blocker, residual risk, and next action.

## 3. Select the Smallest Reliable Layer

Apply [references/layer-selection.md](references/layer-selection.md). Prefer:

- Unit for pure rules, mapping, parsing, validation, and state transitions.
- Component for isolated rendering, interaction, and accessibility state.
- Integration for module, storage, cache, queue, or service coordination.
- API/contract for method, route, auth, payload, status, headers, and response.
- E2E for critical real-browser journeys and frontend/backend wiring.

Do not default every case to E2E. Use multiple layers only when each proves a
different boundary. Record why the selected layer is sufficient.

## 4. Plan Counterfactual Regression Proof

Give every new or changed test one proof status:

- `RED_GREEN`: safely observed failure before correction and pass after it.
- `MUTATION`: focused reversible mutation made the test fail.
- `CONTRACT`: authoritative boundary plus targeted assertion proves discrimination.
- `NOT_PROVEN`: proof was unsafe or unavailable, with reason and residual risk.

**A test linked to a `HIGH` or `CRITICAL` risk requires `RED_GREEN` or
`MUTATION`.** `CONTRACT` is assertable without running anything, so it cannot
close high risk, and `NOT_PROVEN` never can.

Risk level is not a free choice. When the builder tags the diff `security`,
`data`, `contract`, or `concurrency`, at least one declared risk must be `HIGH`
or `CRITICAL`; the validator rejects a report that downgrades a tagged diff.

Never mutate the user's checkout solely to manufacture proof. Use an isolated
temporary copy when safe. Do not claim full confidence with any proof marked
`NOT_PROVEN`.

## 5. Implement Without Gaming Coverage

Use repository frameworks, fixtures, factories, helpers, selectors, and style.
Test observable contracts instead of internal calls when practical. Avoid shared
mutable state, sleeps, execution-order dependencies, hardcoded-literal assertions,
and mocks that bypass ownership boundaries.

Before running the changed suite, rerun the exact builder command with the same
target arguments and verified environment into `$WORK_TMP/bundle.json`. Preserve
`baseline-bundle.json`; the final bundle must include the newly changed tests.
Then audit that final patch:

```bash
python3 "$SAM_COVERAGE_DIR/scripts/audit_test_diff.py" \
  "$WORK_TMP/bundle.json" > "$WORK_TMP/test-diff-audit.json"
```

Treat audit findings as blocking until disproven from the exact diff. Inspect all
changed command definitions before execution.

## 6. Prove the Real System When Required

For browser-facing behavior, start the real UI linked to the intended backend
using safe repository-supported workflows. Confirm the browser uses the frozen
environment. Use isolated deterministic data.

Treat mocked pages, request-only checks, and component shells as fallback proof
only after recording serious direct, container, port/config, and linking attempts.
State the exact blocker and residual risk. Never label fallback proof as real E2E.

## 7. Run and Classify Validation

Every reported result must come from an execution receipt. A typed `PASS` is not
a result. Run each command through the wrapper:

```bash
python3 "$SAM_COVERAGE_DIR/scripts/run_checked.py" \
  --id CMD-001 --receipts-dir "$WORK_TMP/receipts" \
  --classification TARGET --repeat 3 -- <command and arguments>
```

- Run new targeted tests, affected suites, relevant type/lint checks, broader
  suites proportional to risk, then required real-system proof.
- Classify each command `TARGET`, `BASELINE`, `ENVIRONMENT`, or `EXTERNAL`, and
  record its status as `PASS`, `FAIL`, or `NOT_RUN` exactly as the receipt states.
- **`TARGET` commands require `--repeat` of at least 2** (prefer 3). Differing
  exit codes across runs mark the command `FLAKY`; a flaky green is not proof and
  blocks `FULL`. Never "fix" flake by retrying until green—diagnose it or report
  the residual risk.
- Copy `commands[].command` from the receipt argv and set `commands[].receipt` to
  the receipt path. `NOT_RUN` carries a reason and no receipt.
- Never edit a receipt or its log. The validator recomputes both hashes.

Prove that each new test actually runs. A test file that exists but is never
collected proves nothing, so capture the runner's own discovery before and after
adding the test:

```bash
python3 "$SAM_COVERAGE_DIR/scripts/run_checked.py" \
  --id CMD-900 --receipts-dir "$WORK_TMP/receipts" \
  --classification ENVIRONMENT -- <discovery command>   # before the new test
```

Record `test_wiring` with both receipts and the exact new test names. Each name
must be absent from the before-log and present in the after-log.

Do not hide a product defect by changing expectations. Fix only in-scope product
behavior at its owning boundary. Record unrelated failures separately.

## 8. Validate, Clean, and Return

Draft the structured report from
[references/output-contract.md](references/output-contract.md), then run:

```bash
python3 "$SAM_COVERAGE_DIR/scripts/validate_coverage_report.py" \
  --baseline "$WORK_TMP/baseline-bundle.json" \
  --bundle "$WORK_TMP/bundle.json" "$WORK_TMP/report.json"
```

The validator re-verifies every execution receipt through
`scripts/verify_receipts.py`, so it fails when a status disagrees with its
receipt, a log hash does not recompute, a `TARGET` command ran once, or a claimed
new test is not discovered by the runner. Retain the report, bundles,
receipts, and referenced logs at their recorded paths for caller re-validation.
Mark these as retained evidence in the cleanup ledger. Stop only resources
created by this run, remove temporary test data and overrides, update the ledger,
and revalidate. Delete only scratch that no returned evidence references.

Return `FULL` only when all required scenarios and commands pass, required
counterfactual proof exists, real-system proof is honest, the audit passes, and
cleanup succeeds. Return `PARTIAL` for residual gaps. Return `BLOCKED` for unsafe
environment, scope, authorization, or execution conditions.
