# Test and Behavior Proof Policy

Build coverage from changed behavior and risk, not from filenames alone.

## Scenario Inventory

For each changed behavior, identify applicable scenarios:

- Success and expected state transition.
- Negative or dependency failure.
- Boundary, empty, null, malformed, maximum, and minimum input.
- Permission and tenant isolation.
- Persistence, transaction, and compatibility behavior.
- Partial failure, retry, concurrency, ordering, or cancellation.
- Loading, error, empty, keyboard, focus, and recovery states.
- Regression path claimed by the task.

## Coverage Mapping

Map each scenario to one of:

- `COVERED`: a meaningful existing or changed test proves it.
- `MISSING_REQUIRED`: all required-test gates below are satisfied.
- `OPTIONAL`: useful hardening without merge-blocking risk.
- `NOT_SUPPORTED`: the repository lacks that test level; name the closest safe proof.
- `NOT_APPLICABLE`: explain why the scenario does not apply.

Reject cosmetic proof that only imports, instantiates, snapshots unrelated output,
or mocks away the behavior being asserted.

## Required-Test Gate

Mark a missing test `BLOCKER` only when all are true:

1. Runtime behavior changed.
2. The missing scenario exposes a concrete regression path.
3. The repository has a practical established seam for that layer or behavior.
4. Merge safety materially depends on the missing proof.

Do not block solely because a production file lacks a colocated direct test.
Do not exempt critical behavior merely because a broader end-to-end test exists.
Choose the narrowest meaningful level that proves the risk.

## Test Levels

- Use unit tests for isolated rules, validation, formatting, state transitions, and helpers.
- Use integration tests for database behavior, routes, repositories, service boundaries,
  queues, adapters, serialization, and persistence effects.
- Use end-to-end tests for critical user-visible flows when safe infrastructure exists.
- Use contract or compatibility tests for public APIs, schemas, events, and generated clients.

## Differential Regression Proof

For a bug regression, verify that the test would fail under the defective behavior
and pass under the correction when an existing isolated comparison mechanism makes
that safe. Otherwise inspect the assertion path and state why differential execution
was not performed. Never mutate the user's workspace to manufacture the comparison.

## Validation Failures

Classify each failure as:

- `INTRODUCED`: caused by the reviewed change.
- `BASELINE`: reproducible outside the reviewed change.
- `ENVIRONMENT`: local setup or missing dependency prevents proof.
- `EXTERNAL`: remote system or unavailable service prevents proof.

Use `TARGET` for a passing validation of the reviewed target.

Never report an unverified baseline assumption as fact. Never treat setup completion
or test discovery as proof that the intended behavior works.
