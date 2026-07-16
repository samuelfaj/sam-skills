# Scenario Policy

Build scenarios from reachable changed behavior, not from a generic checklist.

## Risk levels

- `CRITICAL`: authorization, destructive data, money, irreversible migration,
  secret exposure, or production delivery.
- `HIGH`: public contract, persistence, cross-service wiring, concurrency, or a
  primary user journey.
- `MEDIUM`: realistic validation, recovery, compatibility, or accessibility risk.
- `LOW`: localized behavior with contained impact.

## Required scenario fields

- Stable ID and concise observable behavior.
- Linked acceptance and risk IDs.
- Preconditions and deterministic data setup.
- Exact user actions and observable assertions.
- Expected method, route, payload, status, response, and visible state when applicable.
- Test IDs, command IDs, artifact IDs, and status.
- Counterfactual proof status and evidence.

## Calibration

Include success, negative, boundary, permission, persistence, error, recovery,
and compatibility variants only when the code path makes them reachable.

Use `REDUNDANT` only when another scenario exercises the same branch and contract;
link that scenario explicitly. Use `MANUAL_PROOF` only when automation is less
reliable or safe and the proof is reproducible. Use `NOT_COVERED` when a real
risk remains, with blocker and residual impact.

Do not duplicate a scenario merely to cover another browser or viewport unless
behavior can differ there.
