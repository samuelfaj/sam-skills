---
name: sam-create-playwright-tests
description: "Create and validate risk-based Playwright E2E tests with real UI/backend proof, exact route and network assertions, permissions, persistence, and video evidence. Use when asked for Playwright, browser E2E, UI regression, cross-browser, route/CORS checks, or PR/MR test evidence."
---

# Sam Create Playwright Tests

## Non-Negotiable Contract

- Honor the exact repository, path, branch, commit, diff range, and acceptance criteria. Preserve existing work: never reset, checkout, restore, stash, clean, rebase, or rewrite history.
- **Real product UI first.** Drive the real pages and routes users hit, with the app's own auth/session path, real navigation, real network to the intended linked backend, real persistence, and user-visible assertions, not isolated mounts that bypass routing, layout, providers, or API wiring. Never create a page, route or route stub, component, story, mini-app, harness shell, or fixture UI solely to host a test when the real surface can exercise the behavior. `FALLBACK` only after recorded serious attempts (boot, auth, seed, port/config, linked backend) with the exact blocker, never presented as real-UI proof.
- Never use production credentials, services, customer tenants, or private data. Fail closed when real data is requested and the environment is unknown or not a verified `local`, `test`, or `dev` target; never infer safety from a hostname.
- Inspect every changed command definition, hook, script, container file, and test configuration before executing it.
- Never add `.only`, `.skip`, retries, broad timeouts, arbitrary sleeps, snapshot refreshes, weaker assertions (truthiness, existence, or non-throwing checks), or mocks that bypass the contract under test.
- Report only results backed by a `scripts/run_checked.py` receipt; never edit a receipt or its log.
- Change production code only for the in-scope correction or the smallest selector/test seam on the real product UI. Fix in-scope product defects at the owning boundary, never by changing tests; record unrelated defects as follow-up evidence.
- Evidence stays local unless the user or a parent workflow explicitly requests publication and the exact target is known. **Never stage or commit** videos, screenshots, traces, recordings, or reports to the branch, LFS, release assets, or product history.
- Register every process, container, port, record, override, temporary file, and artifact in the cleanup ledger when created; clean it or report the exact retained resource.
- Under a parent workflow never ask; execute or fail closed with receipts. Standalone, ask one question only when the target or a safety-critical environment cannot be discovered; never silently choose a remote, database, or tenant.

## Run Rules

- Use literal absolute paths: `<repo>` the repository root; `<skill>` this directory; `<work>` the parent's phase dir when given, else one `mktemp -d` outside the repository, reused on re-invocation; `<receipts>` is `<work>/receipts-<n>`; `<previous>` this skill's prior report (parent-named, else `<work>/report.json`), if any.
- Do not re-read a file already read in this context unless context was compacted or you cannot quote the section you need.
- When the user or parent explicitly requests video evidence, enable capture before the first run with a temporary config or override outside tracked files. Publish only when the exact target and publication are authorized; in that case, zero videos is a failed publishing run.

| Reference | Read when |
| --- | --- |
| [references/evidence-publishing.md](references/evidence-publishing.md) | step 7, only when publishing |
| [references/output-contract.md](references/output-contract.md) | step 8 or an early `BLOCKED` exit; before step 1 if `<previous>` exists (§ Re-invocation) |

## 1. Resolve and Freeze

```bash
python3 <skill>/scripts/build_e2e_bundle.py --repo <repo> --environment-kind unknown --environment-id unverified --out <work>/baseline
```

Add `--base`, `--head`, and repeated `--path` when given. Read only the one-line stderr summary and `bundle.patch`, never `bundle.json`. Before editing, freeze: base/head SHAs, target mode, fingerprint; intended behavior, invariants, acceptance criteria, no-go surfaces; changed files and command definitions; environment kind, identity, UI URL, API URL, database/tenant identity.

## 2. Traceability Ledger

IDs look like `AC-001`: `AC` criterion, `R` risk, `S` scenario, `T` test, `CMD` command, `ART` artifact, `CL` cleanup.

Risk: `CRITICAL` authorization, destructive data, money, irreversible migration, secret exposure, production delivery; `HIGH` public contract, persistence, cross-service wiring, concurrency, primary user journey; `MEDIUM` realistic validation, recovery, compatibility, accessibility; `LOW` contained local behavior.

Build scenarios from reachable changed behavior: cover success, negative, boundary, permission, validation, persistence, cache, loading, error, recovery, navigation, compatibility, exact browser/API route, and cross-origin cases only where the code path reaches them; omit other classes with a reason and never write checklist-only tests. Do not duplicate a scenario per browser or viewport unless behavior can differ.

Scenario status: `AUTOMATED`; `MANUAL_PROOF` only when automation is less reliable or safe and the proof is reproducible; `REDUNDANT` when another scenario exercises the same branch and contract (link it); `NOT_COVERED` with blocker, residual risk, next action.

## 3. Counterfactual Proof

Each new regression test gets one status: `RED_GREEN` (safely observed failure before the correction, pass after); `MUTATION` (a focused reversible mutation fails it); `CONTRACT` (an authoritative boundary and targeted assertion prove discrimination); `NOT_PROVEN` (unsafe or unavailable, with the exact reason; never claim protection without discrimination). Prefer red/green, then mutation, then contract. Never mutate the user's working tree to manufacture proof; use an isolated temporary copy only when safe.

## 4. Start the Real Linked System Safely

Prove each step-1 environment field with evidence; aliases, proxies, tunnels, copied production snapshots, and unknown targets stay unknown until proven. For user-facing behavior:

1. Boot the product UI and intended backend with repository-supported direct, container, or compose workflows and lockfiles; prefer temporary environment overrides outside the repository and unused ports over tracked config changes; confirm the UI calls the intended backend.
2. Authenticate through the app's normal session path or shared auth fixtures that exercise it.
3. Navigate the real route/page that owns the changed behavior.
4. Act as a person would: click, type, submit, open menus.
5. Confirm the browser-requested method, path, payload, response, and visible outcome against the linked backend.

Data: isolated factories, seeds, test accounts, and deterministic identifiers; only records a scenario needs. Never log secrets, cookies, authorization headers, tokens, or private fields. Prove read-after-write before cleanup when persistence is in scope.

Extend an existing e2e on the real page. A fallback sets `behavior_proof` `FALLBACK`; use the thinnest one that still proves useful contract pieces, and apply a temporary local seed or config fix (outside tracked files) or the smallest selector seam instead when that unlocks the real page.

## 5. Implement Without Weakening the Suite

Before changing any spec, capture the runner's own test list as `CMD-900` (`--classification ENVIRONMENT`, step-6 form) unless `<previous>` or an earlier `<receipts>` has one.

- Prefer existing fixtures, page objects, factories, authenticated session helpers, and cleanup conventions on the existing product tree; `getByRole`, `getByLabel`, `getByText`, and stable meaningful test IDs on shipping UI; assertions on visible state, URL, response, persistence, cache, permission, navigation, and accessibility outcomes; `waitForResponse`, locator and URL assertions, and app readiness signals; exact method, path, query, payload, status, and body; console and network evidence for preflight, CORS, opaque failures, and masked errors.
- Reject unless justified: fixmes and expected failures; broad snapshots that obscure the contract; order dependencies and shared mutable records; mocks replacing a backend that can run safely on a verified target; mock call counts where visible behavior can prove intent; framework internals; assertions that repeat fixture literals.

Then rerun the step-1 builder (same target arguments, verified environment) with `--out <work>/final`; the final bundle must include the new specs. Audit it; every finding blocks until disproven from the exact diff:

```bash
python3 <skill>/scripts/audit_test_diff.py <work>/final/bundle.json > <work>/test-diff-audit.json
```

## 6. Run and Classify

```bash
python3 <skill>/scripts/run_checked.py --id CMD-001 --receipts-dir <receipts> --classification TARGET --repeat 3 -- <command and arguments>
```

- Run the narrowest new tests first, then affected tests and broader validation proportional to risk; record each command once. Classify `TARGET`, `BASELINE`, `ENVIRONMENT`, or `EXTERNAL`.
- `TARGET` needs `--repeat` ≥ 2 (prefer 3); differing exit codes, or a fail then pass with nothing fixed, mean `FLAKY`. Never convert flake into green or re-run an id with a `FAIL` receipt: fix the cause (rebuild the final bundle if files changed) and re-run every command but `CMD-900` in the next `<receipts>`, or report the residual risk.
- After the specs exist, capture the test list again as `CMD-901`; read listings from `<receipts>/<id>.run1.log`.
- Cite browser, network, trace, screenshot, or local video evidence for `behavior_proof`.

## 7. Handle Evidence

When publishing, follow `references/evidence-publishing.md`.

## 8. Validate, Clean, and Return

Scaffold, fill the empty fields and decision (never retype derived ones), and validate. Omit `--wiring` when no spec was added (`test_wiring` `NOT_APPLICABLE` with a reason).

```bash
python3 <skill>/scripts/scaffold_report.py --baseline <work>/baseline/bundle.json --bundle <work>/final/bundle.json --receipts-dir <receipts> --wiring CMD-900 CMD-901 --out <work>/report.json
python3 <skill>/scripts/validate_e2e_report.py --baseline <work>/baseline/bundle.json --bundle <work>/final/bundle.json <work>/report.json
```

Fix from the validator's error lines (it runs `scripts/verify_receipts.py`) and patch the report in place; do not read validator source or rewrite the whole report.

Stop only processes and containers this run started; remove created data, temporary environment files, raw recordings that no `ART` record references, and generated runner reports unless the user explicitly asked to retain them; delete only scratch that no returned evidence references; never use broad cleanup commands; update the cleanup ledger and revalidate. Decide by the output-contract gates and return in its § Return format.
