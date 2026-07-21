# Routing Policy

Choose the cheapest task shape that preserves evidence quality. After selecting
capability, bind the host runtime from
[host-runtime-matrix.md](host-runtime-matrix.md).

## Task Classes

- `T0`: one mechanical or read-only task, narrow scope, no material runtime,
  security, data, release, or cross-file risk. Use one `LIGHT` execution node.
- `T1`: one bounded implementation area with ordinary validation. Use one
  `STANDARD` node, or `LIGHT` when the output is purely mechanical.
- `T2`: multiple independent slices, meaningful test work, or cross-file
  coordination. Use the minimum independent `LIGHT`/`STANDARD` nodes and one
  integration owner.
- `T3`: production, security, authorization, privacy, payment, secrets, data
  loss, migration, release, deployment, large refactor, or uncertain cross-repo
  behavior. Use `DEEP` only for the risky slice and serialize unsafe writes.

## Capability then runtime

1. Classify `T0`–`T3` and pick `LIGHT` / `STANDARD` / `DEEP` / `REVIEWER`.
2. Detect active host: `codex`, `claude-code`, or `grok`.
3. Bind the matrix row for that host and capability. Do not ask the user.
4. Prefer the main controller for simple single-step work before spawning.

## Escalation

Escalate from `LIGHT` to `STANDARD`, or from `STANDARD` to `DEEP`, only when:

- Evidence is missing or contradictory.
- The task crosses an unrecognized owner boundary.
- A worker cannot resolve a concrete ambiguity.
- Risk increases after inspecting the real artifact.
- A previous attempt failed for capability rather than environment reasons.

Escalate to rare `genius_worker` only after `DEEP` is insufficient. On Grok the
model stays `grok-4.5` and effort stays at `high`; escalate proof depth, not a
different model family.

Do not escalate because a task is merely large. Split only along real ownership
or dependency boundaries.

## Review Cost Guard

Use `REVIEWER` only when the review gate triggers. A review must be independent:
do not assign it to the worker that produced the artifact and do not reveal the
expected outcome. Bind the host’s `REVIEWER` matrix row.

Skip the gate only when no trigger applies. Record the reason in the validated
report.
