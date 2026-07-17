# Playwright Quality

## Real-UI fidelity (default)

Browser tests prove what a user can do in the real product, not what a synthetic
mount can do in isolation.

**Prefer, in order:**

1. Real product route/page already used in local, dev, or test.
2. Real linked backend (or the repo’s supported local stack for that backend).
3. Existing e2e fixtures, page objects, factories, and authenticated sessions.
4. User-visible actions and assertions (`getByRole`, `getByLabel`, `getByText`,
   stable meaningful test IDs already on product UI).
5. Exact browser-requested method, path, query, payload, status, and body.
6. Persistence, cache, permission, and navigation outcomes as the app implements them.

**Do not create for the test alone (unless real UI is blocked):**

- New pages, routes, or components whose only purpose is Playwright.
- Storybook/story mounts, component harness shells, or mini-apps that bypass
  router, layout, providers, auth, or API clients.
- Parallel “test UI” copies of product components.
- Network mocks that replace the integration under test when the real backend can
  run safely on a verified local/test/dev target.

**Fallback is last resort.** Record attempts (boot, auth, seed, ports, backend
link) and the exact blocker. Label the scenario/proof `FALLBACK`. Create the
smallest temporary surface only when those attempts fail; prefer fixing seed,
config, or selector seams on the real product when that unblocks fidelity.

## Prefer

- Existing fixtures, page objects, factories, and authenticated session helpers.
- `getByRole`, `getByLabel`, `getByText`, and stable meaningful test IDs on
  shipping product UI.
- Assertions on visible state, URL, response, persistence, and accessibility state.
- `waitForResponse`, locator assertions, URL assertions, and app readiness signals.
- Exact browser-requested method, path, query, payload, status, and body.
- Console and network evidence for preflight, CORS, opaque failures, and masked errors.

## Reject unless explicitly justified

- `test.only`, `describe.only`, focused runs committed to the suite.
- New skips, fixes, expected failures, broad retries, or increased global timeouts.
- `waitForTimeout`, arbitrary sleeps, execution-order dependencies, shared mutable data.
- Blanket snapshot refreshes or broad snapshots that obscure the contract.
- Assertions weakened to truthiness, existence, or non-throwing behavior.
- Mocks that bypass the route, permission, persistence, or integration under test.
- Assertions of mock call counts when user/API-visible behavior can prove intent.
- New product files (components/pages/routes) introduced only so a test can run
  while the real surface was available.
- Component-level mounts presented as full user-flow e2e without `FALLBACK`
  labeling and blockers.

## Regression discrimination

Prefer safe red/green evidence in an isolated checkout. Otherwise use a focused
mutation or authoritative contract assertion. Record `NOT_PROVEN` rather than
claiming a test protects a regression when discrimination was not established.
