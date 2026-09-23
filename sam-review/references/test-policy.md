# Test and Behavior Proof Policy

Build coverage from changed behavior and risk, not filenames. Cosmetic proof (only imports, instantiates, snapshots unrelated output, or mocks away the asserted behavior), setup completion, and test discovery never prove the intended behavior.

## Scenario Inventory

Per changed behavior: success and expected state transition; negative or dependency failure; boundary, empty, null, malformed, maximum, and minimum input; permission and tenant isolation; persistence, transaction, and compatibility; partial failure, retry, concurrency, ordering, cancellation; loading, error, empty, keyboard, focus, and recovery states; rollout; the regression path the task claims.

## Required-Test Gate

A missing test is a `BLOCKER` only when all hold: (1) runtime behavior changed; (2) the missing scenario exposes a concrete regression path; (3) the repository has a practical established seam for that layer or behavior; (4) merge safety materially depends on the proof. Never block only because a production file lacks a colocated test; never exempt critical behavior because a broader end-to-end test exists.

## Levels

Use the narrowest level that proves the risk: `UNIT` isolated rules, validation, formatting, state transitions, helpers; `INTEGRATION` database, routes, repositories, service boundaries, queues, adapters, serialization, persistence effects; `E2E` critical user-visible flows with safe infrastructure; `CONTRACT` public APIs, schemas, events, generated clients; `STATIC` type, lint, or static analysis; `MANUAL` a human-run check.

## Differential Regression Proof

For a bug regression, show the test fails under the defect and passes under the correction when an existing isolated comparison mechanism makes that safe; otherwise inspect the assertion path and state why differential execution was not performed. Never mutate the user's workspace to manufacture the comparison.
