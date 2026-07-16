---
name: sam-create-playwright-tests
description: "Create and validate risk-based Playwright browser tests for changed or reported user flows, including real linked UI/backend proof, exact route and network assertions, permissions, persistence, and optional local video evidence. Use when asked for Playwright, browser E2E, UI regression tests, cross-browser flows, route or CORS verification, or explicitly requested PR/MR test evidence."
---

# Sam Create Playwright Tests

Create browser tests that prove the intended user and API contract. Keep the
workflow stack-, host-, provider-, and model-agnostic except for Playwright itself.

## Non-Negotiable Contract

- Honor the exact repository, path, branch, commit, diff range, and acceptance
  criteria supplied by the user.
- Preserve existing work. Do not reset, checkout, stash, clean, rebase, or rewrite history.
- Keep generated media and reports local by default. Publish only when the user
  explicitly requests publication and the exact target is known.
- Never use production credentials, production services, customer tenants, or
  private data for automated browser tests.
- Fail closed when real data is requested and the environment identity is unknown
  or is not a verified local, test, or development target.
- Inspect every changed command definition, hook, script, container file, and test
  configuration before executing it.
- Do not add `.only`, `.skip`, retries, broad timeouts, snapshot refreshes, weaker
  assertions, or mocks that bypass the contract under test.
- Limit production changes to the in-scope correction or the smallest stable
  selector/test seam required by an accepted scenario.
- Track all started processes, containers, ports, data, overrides, and temporary
  files. Clean them before completion or report the exact retained resource.

## Resource Routing

- Read [references/environment-safety.md](references/environment-safety.md)
  before starting services or using persistent data.
- Read [references/scenario-policy.md](references/scenario-policy.md) while
  building the scenario ledger.
- Read [references/playwright-quality.md](references/playwright-quality.md)
  before implementing or changing browser tests.
- Read [references/evidence-publishing.md](references/evidence-publishing.md)
  only when video or external publication is explicitly requested.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting the final report.

## 1. Resolve and Freeze the Target

Set the skill directory to the directory containing this file. Build the bundle
without fetching or changing refs:

```bash
SAM_PLAYWRIGHT_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_PLAYWRIGHT_DIR/scripts/build_e2e_bundle.py" \
  --repo "$PWD" --environment-kind unknown \
  --environment-id "unverified" > "$WORK_TMP/baseline-bundle.json"
```

Pass `--base`, `--head`, and repeated `--path` arguments when the user specifies
them. Rebuild with the verified environment identity before using real data.

Freeze these fields before editing:

- Base SHA, head SHA, target mode, and bundle fingerprint.
- Intended behavior, invariants, acceptance criteria, and explicit no-go surfaces.
- Changed-file ledger and command definitions.
- Environment kind, identity, endpoints, database/tenant identity, and evidence.
- Cleanup ledger initialized with every resource that may be created.

Ask one concise question only when the target or a safety-critical environment
identity cannot be discovered. Do not silently choose a remote, database, or tenant.

## 2. Build the Traceability Ledger

Use stable IDs throughout the run:

- `AC-###`: acceptance criterion.
- `R-###`: reachable risk linked to one or more criteria.
- `S-###`: scenario linked to criteria and risks.
- `T-###`: test linked to scenarios.
- `CMD-###`: command linked to tests and results.
- `ART-###`: local or explicitly published artifact linked to scenarios.
- `CL-###`: cleanup resource.

For each changed behavior, cover applicable success, negative, boundary,
permission, validation, persistence, cache, loading, error, recovery, navigation,
compatibility, exact browser/API route, and cross-origin cases. Mark irrelevant
classes as omitted with a reason; do not create checklist-only tests.

Assign each scenario one status: `AUTOMATED`, `MANUAL_PROOF`, `REDUNDANT`, or
`NOT_COVERED`. Give `REDUNDANT` an equivalent scenario and `NOT_COVERED` a
blocker, residual risk, and next action.

## 3. Plan Counterfactual Proof

For every new regression test, record one proof status:

- `RED_GREEN`: safely observed failure before the correction and pass after it.
- `MUTATION`: a focused reversible mutation made the test fail.
- `CONTRACT`: an authoritative boundary and targeted assertion prove discrimination.
- `NOT_PROVEN`: counterfactual proof was unsafe or unavailable, with the exact reason.

Never mutate the user's working tree solely to manufacture proof. Use an isolated
temporary copy only when safe. Do not claim complete confidence while required
high-risk regression proof remains `NOT_PROVEN`.

## 4. Start the Real Linked System Safely

Inspect changed command definitions first. Then use repository-supported direct,
container, or compose workflows. Prefer temporary environment overrides and
unused ports over tracked configuration changes.

For user-facing behavior, drive the real running UI linked to the intended
backend. Confirm the browser-requested method, path, payload, response, and
visible outcome. Treat mocked pages, request-only checks, and component shells as
fallback evidence only after recording each serious real-system attempt and blocker.

Register every process, container, port, test record, override, and artifact in
the cleanup ledger when it is created.

## 5. Implement Without Weakening the Suite

Follow repository fixtures, factories, selectors, authentication helpers, and
cleanup conventions. Prefer accessible user-facing locators and observable state.
Avoid sleeps, execution-order dependencies, shared mutable records, framework
internals, and assertions that merely repeat fixture literals.

Rerun the exact builder command with the same target arguments and verified
environment into `$WORK_TMP/bundle.json`. Preserve `baseline-bundle.json`; the
final bundle must include the newly changed tests. Audit that final patch:

```bash
python3 "$SAM_PLAYWRIGHT_DIR/scripts/audit_test_diff.py" \
  "$WORK_TMP/bundle.json" > "$WORK_TMP/test-diff-audit.json"
```

Treat every audit finding as blocking until disproven from the exact diff.

## 6. Run and Classify Validation

Run the narrowest new tests first, then affected tests and broader validation
proportional to risk. Record each command exactly once as `PASS`, `FAIL`, or
`NOT_RUN`, classified as `TARGET`, `BASELINE`, `ENVIRONMENT`, or `EXTERNAL`.

Do not hide product failures by changing tests. Fix an in-scope product defect
only at its owning boundary. Record unrelated defects as follow-up evidence.

For user-visible behavior, declare `PROVEN`, `NOT_PROVEN`, or `FALLBACK` and cite
the browser, network, trace, screenshot, or local video evidence.

## 7. Handle Evidence Only When Requested

Keep Playwright traces, screenshots, reports, and recordings local and safe.
When the user explicitly requests publication, follow
[references/evidence-publishing.md](references/evidence-publishing.md), verify the
remote receipt by reading it back, and record it as an `ART-###` entry.

## 8. Validate, Clean, and Return

Draft `report.json` using [references/output-contract.md](references/output-contract.md),
then validate it:

```bash
python3 "$SAM_PLAYWRIGHT_DIR/scripts/validate_e2e_report.py" \
  --baseline "$WORK_TMP/baseline-bundle.json" \
  --bundle "$WORK_TMP/bundle.json" "$WORK_TMP/report.json"
```

Do not weaken the report to force completion. Stop services, containers, and
temporary overrides; remove temporary data and artifacts not explicitly retained.
Update every `CL-###` entry, revalidate, then remove `WORK_TMP`.

Return `COMPLETE` only when all required scenarios and validations pass, required
counterfactual proof exists, behavior is proven, and cleanup succeeds. Return
`PARTIAL` for honest residual gaps. Return `BLOCKED` for unsafe environment,
scope, authorization, or execution conditions.
