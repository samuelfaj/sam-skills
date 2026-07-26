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
- Keep generated media and reports local until a remote proposal target is
  authorized. Publish only when the user or a parent workflow (for example
  `sam-work`) explicitly requests publication and the exact target is known.
  Parent-workflow authorization is sufficient; do not re-ask the user.
- **Never commit** generated videos, screenshots, traces, or reports to the
  task branch, LFS, or product-tree history.
- When publication is authorized, **always upload** via the host CLI (`gh` /
  `glab` platform uploads) and place media in the PR/MR **description** or a
  **comment/note** using player/image embed markup. Follow
  [references/evidence-publishing.md](references/evidence-publishing.md).
- **Video → inline/native player. Image → inline image. Never a hyperlink.**
  Forbid Markdown download links, “Download MP4” anchors, blob/raw repo URLs,
  and HTML download anchors.
- Never use production credentials, production services, customer tenants, or
  private data for automated browser tests.
- Fail closed when real data is requested and the environment identity is unknown
  or is not a verified local, test, or development target.
- Inspect every changed command definition, hook, script, container file, and test
  configuration before executing it.
- Do not add `.only`, `.skip`, retries, broad timeouts, snapshot refreshes, weaker
  assertions, or mocks that bypass the contract under test.
- **Real product UI first.** Drive the actual application pages, routes, and
  components users hit in production-like local/dev/test. Prefer the real linked
  UI + backend over any substitute.
- **Do not create a new page, route, component, story, harness shell, or fixture
  UI solely to host a browser test** when the real product surface can exercise
  the behavior. Add only the smallest stable selector or test-id seam on the
  existing product UI when needed.
- Tests must be as faithful to reality as possible: real navigation, real
  auth/session helpers already used by the app, real network to the intended
  backend, real persistence, and user-visible assertions—not isolated component
  mounts that bypass routing, layout, providers, or API wiring.
- **Fallback only when the real UI is not reasonably reachable** after serious
  attempts (boot, auth, data seed, port/config, linked backend). Document each
  attempt and blocker, label proof `FALLBACK`, and only then use a minimal
  isolated harness or test-only surface. Never present fallback as real-UI proof.
- Limit production changes to the in-scope correction or the smallest stable
  selector/test seam required by an accepted scenario on the real product UI.
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

Under a parent workflow that already froze the target and environment (for
example `sam-work`), never ask any permission, confirmation, or clarifying
question—execute or fail closed with receipts. When running standalone, ask one
concise question only when the target or a safety-critical environment identity
cannot be discovered. Do not silently choose a remote, database, or tenant.

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

For user-facing behavior, **default and preferred path is the real running app**:

1. Boot the product UI and the intended backend with repo-supported commands.
2. Authenticate through the app’s normal session path (or existing shared auth
   fixtures that exercise that path)—not a test-only fake page.
3. Navigate the real product route/page that owns the changed behavior.
4. Perform the same user actions a person would (click, type, submit, open menus).
5. Confirm browser-requested method, path, payload, response, and visible outcome
   against the linked backend.

**Forbidden as the first choice:** new throwaway components, mini-apps,
Storybook-only mounts, component-test wrappers, or route stubs created only so
Playwright has something to open. Prefer extending an existing e2e against the
real page.

**Fallback** (mocked page, request-only check, component shell, new test-only
surface) is allowed only after recording each serious real-system attempt and
exact blocker. Mark behavior proof `FALLBACK`. Prefer the thinnest fallback that
still proves useful contract pieces; still do not invent product UI permanently
if a temporary local seed or config fix would unlock the real page.

Register every process, container, port, test record, override, and artifact in
the cleanup ledger when it is created.

## 5. Implement Without Weakening the Suite

Follow repository fixtures, factories, selectors, authentication helpers, and
cleanup conventions on the **existing product tree**. Prefer accessible
user-facing locators and observable state on real pages. Avoid sleeps,
execution-order dependencies, shared mutable records, framework internals, and
assertions that merely repeat fixture literals.

When a selector is unstable, add the smallest production-safe test seam on the
real component already shipping in the app. Do not replace that component with a
parallel test-only implementation.

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
the browser, network, trace, screenshot, or local video evidence. `PROVEN`
requires the real product UI and linked backend path. `FALLBACK` requires the
attempt/blocker ledger and must not be reported as full real-UI confidence.

## 7. Handle Evidence Only When Requested

Keep Playwright traces, screenshots, reports, and recordings local and safe by
default. Never `git add` / commit them.

When the user or parent workflow explicitly requests publication—including
`sam-work`, which always requires Playwright video publication for web systems—
enable video capture, run the suite, and publish without asking again. Follow
[references/evidence-publishing.md](references/evidence-publishing.md):

1. Inventory every video (and required screenshots) with path + SHA-256.
2. Upload each file with `glab` (GitLab project uploads) or `gh` (GitHub
   user-attachments / equivalent). Do not commit media.
3. Embed in the PR/MR description or comment:
   - **GitLab video:** `![scenario title](/uploads/<hash>/file.webm)`
   - **GitHub video:** bare `https://github.com/user-attachments/assets/<id>`
     alone on its own line
   - **Images (either host):** host-issued inline image markup with descriptive alt text
4. Forbid Markdown download links, HTML-only download links, and repo blob/raw URLs.
5. Read the remote body back; require a rendered **player** (video) or **image**.
6. Record each as `ART-###` with receipt, markup, and player/image verification.

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
