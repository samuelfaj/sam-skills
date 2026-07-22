# Routing Policy

Choose the cheapest task shape that preserves evidence quality. After selecting
capability, bind the host runtime from
[host-runtime-matrix.md](host-runtime-matrix.md).

## Task Classes

- `T0`: one mechanical or read-only task, narrow scope, no material runtime,
  security, data, release, or cross-file risk. Use Micro path: one `LIGHT`
  execution node max (or controller-only if no delegation needed).
- `T1`: one bounded implementation area with ordinary validation. Use Single
  path: one `STANDARD` node, or `LIGHT` when the output is purely mechanical.
- `T2`: multiple independent slices, meaningful test work, or cross-file
  coordination. Use Multi path: minimum independent `LIGHT`/`STANDARD` nodes
  (default parallel 2, hard cap 3) and one integration owner.
- `T3`: production, security, authorization, privacy, payment, secrets, data
  loss, migration, release, deployment, large refactor, or uncertain cross-repo
  behavior. Use Critical path: `DEEP` only for the risky slice; serialize unsafe
  writes; REVIEWER required.

## Certainty Budget

Record `controller_certainty`:

| Value | Use when |
| --- | --- |
| `absolute` | T0 micro-task, zero residual doubt |
| `high` | Clear single slice; ordinary residual risk only |
| `medium` | Default when not sure enough for high/absolute |
| `low` | Unclear ownership, risk, or proof path |

## Capability then runtime

1. Classify `T0`–`T3` and set certainty.
2. Pick mode: Micro / Single / Multi / Critical.
3. Detect active host: `codex`, `claude-code`, or `grok`.
4. Bind matrix row for that host and capability. Do not ask the user.
5. Prefer the main controller for simple single-step work before spawning.
6. **Never open on DEEP.** First attempt is LIGHT (Micro) or STANDARD (Single).

## Fan-out caps

| Class | Max execution producers | Default parallel |
| --- | --- | --- |
| T0 | 1 | 1 |
| T1 | 1 | 1 |
| T2 | 3 | 2 |
| T3 | 3 | 2 |

Split only along real ownership or dependency boundaries.

## Escalation (cheap-first)

Escalate from `LIGHT` → `STANDARD`, or `STANDARD` → `DEEP`, only when:

- Evidence is missing or contradictory after a real attempt.
- The task crosses an unrecognized owner boundary.
- A worker cannot resolve a concrete ambiguity.
- Risk increases after inspecting the real artifact.
- A previous attempt failed for **capability** rather than environment reasons.

Prefer: re-prompt the same tier with a tighter slice before escalating.

Escalate to rare `genius_worker` only after `DEEP` is insufficient. On Grok the
model stays `grok-4.5`; escalate proof depth, not a different model family.

Do not escalate because a task is merely large.

`DEEP` is invalid unless classification is `T3` or `risk_flags` is non-empty.

## Review Cost Guard

Use `REVIEWER` only when the review gate triggers. Independent review only:
different owner; no expected outcome leaked. Bind the host `REVIEWER` row.

Feed the reviewer **diff + checklist + frozen scope + proof refs** — never the
full skill pack and never other workers’ conclusions.

### Require review when

- `T3`, non-empty `risk_flags`, or `DATA`/`RELEASE` artifacts.
- More than one execution producer.
- TARGET proof missing or not PASS.
- `review_requested: true`.
- `CODE`/`TEST` changed and certainty skip does not apply.

### Certainty skip (no REVIEWER)

| | Absolute | High |
| --- | --- | --- |
| Class | `T0` | `T0` or `T1` |
| Producers | 1 | 1 |
| Caps | — | producers only `LIGHT`/`STANDARD` |
| risk_flags | empty | empty |
| TARGET proof | all PASS | all PASS |
| review_requested | false | false |
| Gate reason | `micro_task_absolute_certainty` | `micro_task_high_certainty` |

Never invent certainty to save cost.

### Reviewer efficiency

- Diff-only / artifact-only intake.
- One TARGET proof for the review node.
- No full-repo re-read unless T3 risk demands it.

## Proof Cost Guard

Prefer, in order:

1. Scope diff vs writable paths.
2. One focused command (single test file / single target).
3. Summarized failure excerpt — never raw multi-KB logs.

Skip full-suite runs unless the change is cross-cutting or T3.
