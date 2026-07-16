# Playwright Quality

## Prefer

- Existing fixtures, page objects, factories, and authenticated session helpers.
- `getByRole`, `getByLabel`, `getByText`, and stable meaningful test IDs.
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

## Regression discrimination

Prefer safe red/green evidence in an isolated checkout. Otherwise use a focused
mutation or authoritative contract assertion. Record `NOT_PROVEN` rather than
claiming a test protects a regression when discrimination was not established.
