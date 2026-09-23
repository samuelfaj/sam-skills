---
name: sam-create-test-coverage
description: "Add risk-based regression tests across unit, component, integration, API/contract, and E2E layers with the smallest reliable proof per behavior. Use when asked to add tests, prove a bug fix, raise coverage or confidence, map acceptance criteria, or close test gaps."
---

# Sam Create Test Coverage

## Non-Negotiable Contract

- Honor the exact repository, path, branch, commit, range, and criteria. Preserve existing work: never reset, checkout, restore, stash, clean, rebase, or rewrite history.
- Inspect changed scripts, hooks, runners, package commands, containers, and CI definitions before executing them.
- Fail closed: real-data E2E only on a verified `local`, `test`, or `dev` environment; never infer a safe database or tenant from a name; never automate production credentials, customer tenants, or private customer data.
- Never expose secrets, credentials, private data, or sensitive paths in bundles, commands, artifacts, reports, or returned evidence.
- Keep artifacts local; publish only on an explicit user or parent-workflow request with a resolved remote target.
- Reject `.only`, `.skip`, retries, broad timeouts, snapshot refreshes, assertion weakening, and mocks that remove the contract under test.
- Report only results backed by a `scripts/run_checked.py` receipt; never edit a receipt or its log.
- Change production code only for the in-scope correction or the smallest test seam a scenario needs. Fix in-scope defects at their owning boundary, never by changing expectations; record unrelated failures separately.
- Register every process, container, port, record, override, environment file, log, and artifact in the cleanup ledger when created, and clean it.
- Under a parent workflow never ask: use the frozen target/environment or return `BLOCKED` with receipts. Standalone, ask one question only when the target or a safety-critical environment cannot be discovered.

## Run Rules

- Use literal absolute paths: `<repo>` the repository root; `<skill>` this directory; `<work>` the parent's phase dir when given, else one `mktemp -d` outside the repository, reused on re-invocation; `<receipts>` is `<work>/receipts-<n>`; `<previous>` this skill's prior report (parent-named, else `<work>/report.json`), if any.
- Do not re-read a file already read in this context unless context was compacted or you cannot quote the section you need.

| Reference | Read when |
| --- | --- |
| [references/output-contract.md](references/output-contract.md) | step 8 or an early `BLOCKED` exit; before step 1 if `<previous>` exists (§ Re-invocation) |

## 1. Resolve and Freeze

```bash
python3 <skill>/scripts/build_test_impact.py --repo <repo> --environment-kind unknown --environment-id unverified --out <work>/baseline
```

Add `--base`, `--head`, and repeated `--path` when given. Read only the one-line stderr summary and `bundle.patch`, never `bundle.json`. Before editing, freeze: target mode, refs, SHAs, fingerprint, changed files; intended behavior, invariants, acceptance criteria, no-go scope; owning boundaries, affected contracts, command definitions; environment kind, identity, UI/API endpoints, database/tenant, proof.

## 2. Behavior and Risk Ledger

IDs look like `AC-001`: `AC` criterion, `B` behavior, `R` risk, `S` scenario, `T` test, `CMD` command, `ART` evidence, `CL` cleanup.

Risk: `CRITICAL` authorization, destructive data, money, secrets, irreversible work; `HIGH` public contract, persistence, cross-service wiring, concurrency, primary flow; `MEDIUM` realistic validation, recovery, compatibility, accessibility; `LOW` contained local behavior. A bundle tagged `security`, `data`, `contract`, or `concurrency` needs a `HIGH`/`CRITICAL` risk.

Cover applicable success, negative, boundary, permission, validation, state-transition, persistence, cache, concurrency, error, recovery, compatibility, and accessibility cases; omit inapplicable classes with a reason. Use equivalence classes from reachable branches; add null, missing, empty, malformed, sentinel, add/update/remove/preserve variants only when they change the contract.

Scenario status: `PLANNED`; `AUTOMATED`; `MANUAL_PROOF` only when automation is less safe or reliable; `REDUNDANT` with the equivalent scenario ID and why; `NOT_COVERED` with exact blocker, residual risk, next action.

## 3. Smallest Reliable Layer

Pick the lowest layer that proves the real contract without replacing its owner: `UNIT` pure rules, parsing, formatting, serializers, validators, reducers, state transitions (never mock the unit under test); `COMPONENT` isolated rendering, form state, interaction, accessibility semantics, client serialization (no network or persistence); `INTEGRATION` coordination of service/repository, storage, cache invalidation, transactions, queue consumers, modules; `API_CONTRACT` exact method, path, query, headers, auth, role, payload, validation, status, body, compatibility on the client's route; `E2E` critical journeys, navigation/auth wiring, browser-only behavior, frontend/backend integration.

Never default to E2E or repeat a branch a lower layer already proves; use several layers only for different failure boundaries. Coverage percentage is diagnostic, never sufficient.

Delegation: under a parent that runs `sam-create-playwright-tests` on the same head, record browser journeys as `PLANNED` `E2E` scenarios, prove lower layers here, and set `real_system_proof` `NOT_APPLICABLE` with `reason` exactly `delegated to playwright phase`.

## 4. Counterfactual Regression Proof

Each new or changed test gets one status: `RED_GREEN` (fails on a safely available defective state, passes on the corrected one); `MUTATION` (one focused reversible change, touching nothing unrelated, fails it for the expected reason); `CONTRACT` (asserts an authoritative local schema, invariant, route, type, or requirement boundary); `NOT_PROVEN` (unsafe or unavailable; reason and residual risk). `HIGH`/`CRITICAL`-linked tests need `RED_GREEN` or `MUTATION`.

Record the exact command and observed failure for red/green and mutation; never mutate the user's checkout to manufacture proof (use an isolated copy when safe). Reject tests that pass on defective and corrected code alike, assert only fixture literals, or check mock calls while the user-visible contract stays untested.

## 5. Implement Without Gaming Coverage

Before changing any test, capture the runner's discovery listing as `CMD-900` (`--classification ENVIRONMENT`, step-7 form) unless `<previous>` or an earlier `<receipts>` has one. Use repository frameworks, fixtures, factories, helpers, selectors, and style; test observable contracts over internals; avoid shared mutable state, sleeps, and order dependencies.

Then rerun the step-1 builder (same target arguments, verified environment) with `--out <work>/final`; the final bundle must include the new tests. Audit it; findings block until disproven from the exact diff:

```bash
python3 <skill>/scripts/audit_test_diff.py <work>/final/bundle.json > <work>/test-diff-audit.json
```

## 6. Environment and Real System

Before starting services or touching persistent data, prove the step-1 environment fields with evidence; aliases, tunnels, proxies, and copied snapshots stay unknown until proven. Prefer existing lockfiles and repository commands, temporary overrides outside the repository, and unused ports; confirm every client points to the frozen backend.

For browser-facing behavior not delegated, start the real UI linked to the intended backend with isolated deterministic data. Mocked pages, request-only checks, and component shells are `FALLBACK`, allowed only after recorded serious direct, container, port/config, and linking attempts with exact blocker and residual risk; never call them real E2E.

## 7. Run and Classify

```bash
python3 <skill>/scripts/run_checked.py --id CMD-001 --receipts-dir <receipts> --classification TARGET --repeat 3 -- <command and arguments>
```

- Run new targeted tests, affected suites, relevant type/lint checks, broader suites proportional to risk, then required real-system proof.
- Classify `TARGET`, `BASELINE`, `ENVIRONMENT`, or `EXTERNAL`.
- `TARGET` needs `--repeat` ≥ 2 (prefer 3); differing exit codes, or a fail then pass with nothing fixed, mean `FLAKY`. Never re-run an id with a `FAIL` receipt: fix the cause (rebuild the final bundle if files changed) and re-run every command but `CMD-900` in the next `<receipts>`, or report the residual risk.
- After the tests exist, capture discovery again as `CMD-901`; read listings from `<receipts>/<id>.run1.log`.

## 8. Validate, Clean, and Return

Scaffold, fill the empty fields and decision (never retype derived ones), and validate. Omit `--wiring` when no test was added (`test_wiring` `NOT_APPLICABLE` with a reason).

```bash
python3 <skill>/scripts/scaffold_report.py --baseline <work>/baseline/bundle.json --bundle <work>/final/bundle.json --receipts-dir <receipts> --wiring CMD-900 CMD-901 --out <work>/report.json
python3 <skill>/scripts/validate_coverage_report.py --baseline <work>/baseline/bundle.json --bundle <work>/final/bundle.json <work>/report.json
```

Fix from the validator's error lines (it runs `scripts/verify_receipts.py`) and patch the report in place; do not read validator source or rewrite the whole report.

Mark explicitly requested safe artifacts `RETAINED` with exact path and reason. Stop only resources this run created, remove temporary data and overrides, delete only scratch that no returned evidence references, update the cleanup ledger, and revalidate. Decide by the output-contract gates and return in its § Return format.
