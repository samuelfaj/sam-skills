# Evidence Policy

Use evidence to prove intent, not merely command execution.

## Scenario Mapping

Map each applicable behavior to one status:

- `PROVEN`: passing evidence exercises the behavior.
- `MISSING_REQUIRED`: a concrete unsafe regression path lacks practical proof.
- `OPTIONAL`: useful hardening that does not block safe completion.
- `NOT_APPLICABLE`: the behavior does not apply; state why.

Consider success, negative, boundary, permission, persistence, compatibility,
partial failure, retry, concurrency, ordering, cancellation, and recovery only
when reachable in the changed flow.

## Test Calibration

Require a test when runtime behavior changes, a concrete regression path exists,
the repository has a practical seam, and merge safety depends on it. Prefer the
narrowest layer that proves the rule.

Do not accept import-only, unrelated snapshot, hardcoded, or fully mocked proof
that bypasses the behavior. Do not block solely because a file lacks a direct
test when stronger meaningful proof exists.

Use alternative proof only when the established repository cannot express the
behavior safely. Record the limitation, evidence, and closest supported layer.

## Evidence and Failures

Record each command or observation with `PASS`, `FAIL`, or `NOT_RUN` and one
classification:

- `TARGET`: passing proof for the requested work.
- `INTRODUCED`: failure caused by the work.
- `BASELINE`: independently reproduced pre-existing failure.
- `ENVIRONMENT`: local setup prevents proof.
- `EXTERNAL`: unavailable service or remote state prevents proof.

Never label a failure baseline without evidence. Setup completion and test
discovery are not behavior proof.

## Behavior Proof

Use `PROVEN`, `NOT_PROVEN`, or `NOT_APPLICABLE`. A user-visible UI, API, CLI,
or generated artifact needs runtime or artifact evidence. Static inspection
alone cannot produce `PROVEN`.

## Gates and External Actions

Mark a gate mandatory only when its risk applies. Every mandatory gate must
pass; unavailable mandatory dependencies fail closed. Do not simulate another
skill, tool, review, test, or runtime result.

Draft text locally without external mutation. Record an action as `PUBLISHED`
only when the user explicitly requested that exact action and passing evidence
proves it happened. Remain neutral about host and publication mechanism.
