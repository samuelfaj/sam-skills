# Scenario and Risk Policy

## Risk levels

- `CRITICAL`: authorization, destructive data, money, secrets, irreversible work.
- `HIGH`: public contract, persistence, cross-service wiring, concurrency, primary flow.
- `MEDIUM`: realistic validation, recovery, compatibility, accessibility.
- `LOW`: localized behavior with contained impact.

## Traceability

Link each `AC-###` to `B-###`, `R-###`, `S-###`, `T-###`, `CMD-###`, and
when produced, `ART-###`. Every reference must resolve in the same report.

For each scenario record preconditions, setup, action, observable assertion,
selected layer, sufficiency reason, failure mode, and proof status.

## Calibration

Build equivalence classes from reachable branches and boundaries. Include null,
missing, empty, malformed, sentinel, add, update, remove, and preserve variants
only when they change the contract.

Use `REDUNDANT` only with an equivalent scenario ID and explanation. Use
`MANUAL_PROOF` only when automation would be less safe or reliable. Use
`NOT_COVERED` for a real remaining risk with blocker, residual impact, and next action.

Coverage percentage is diagnostic data, never sufficient evidence by itself.
