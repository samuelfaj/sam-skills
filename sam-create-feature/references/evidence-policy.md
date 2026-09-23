# Evidence Policy

Prove intent, not mere command execution.

## Scenarios

- `PROVEN`: passing evidence exercises the behavior.
- `MISSING_REQUIRED`: a concrete unsafe regression path lacks practical proof.
- `OPTIONAL`: useful hardening; never blocks safe completion.
- `NOT_APPLICABLE`: the behavior does not apply; say why.

Consider success, negative, boundary, permission, persistence, compatibility,
partial failure, retry, concurrency, ordering, cancellation, and recovery only
where the changed flow reaches them.

## Tests

- Require a test when runtime behavior changes, a concrete regression path and
  a practical seam exist, and merge safety depends on it; use the narrowest
  proving layer. A missing direct test is no blocker when stronger meaningful
  proof exists.
- Reject import-only, unrelated snapshot, hardcoded, or fully mocked proof that
  bypasses the behavior.
- Alternative proof only when the repository cannot express the behavior
  safely: record the limitation, evidence, and closest supported layer.

## Evidence and Behavior Proof

Each command or observation is `PASS`, `FAIL`, or `NOT_RUN`, classified
`TARGET` (passing proof for the work), `INTRODUCED` (failure the work caused),
`BASELINE` (independently reproduced pre-existing failure; never assumed),
`ENVIRONMENT` (local setup prevents proof), or `EXTERNAL` (unavailable service
or remote state). Setup completion and test discovery are not behavior proof.

Behavior proof is `PROVEN`, `NOT_PROVEN`, or `NOT_APPLICABLE`. A user-visible
UI, API, CLI, or generated artifact needs runtime or artifact evidence; static
inspection never yields `PROVEN`.

## Gates and External Actions

A gate is mandatory only when its risk applies. Mandatory gates must pass; an
unavailable mandatory dependency fails closed. Never simulate another skill,
tool, review, test, or runtime result. Draft text locally without external
mutation.
