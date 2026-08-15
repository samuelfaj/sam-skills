# Routing Policy (Claude–Grok profile)

Choose the cheapest task shape that preserves evidence quality. After selecting
capability, bind runtime from
[host-runtime-matrix.md](host-runtime-matrix.md).

## Contents

1. Task classes
2. Certainty budget
3. Capability then hybrid runtime
4. Fan-out
5. Escalation and stall
6. Review cost
7. Proof cost

## Task Classes

- `T0`: mechanical or read-only, narrow scope, no material runtime/security/data
  risk. Micro: one `LIGHT` Grok node max (or controller-only).
- `T1`: one bounded implementation area. Single: one `STANDARD` Grok node, or
  `LIGHT` when purely mechanical.
- `T2`: multiple independent slices or cross-file coordination. Multi: min
  independent Grok nodes (default parallel 2, hard cap 3) + integration owner.
- `T3`: production, security, auth, privacy, payment, secrets, data loss,
  migration, release, large refactor, uncertain cross-repo. Critical: `DEEP`
  Grok on the risky slice; serialize unsafe writes; REVIEWER required (Claude
  opus high).

## Certainty Budget

| Value | Use when |
| --- | --- |
| `absolute` | T0 micro, zero residual doubt |
| `high` | Clear single slice; ordinary residual risk only |
| `medium` | Default when not sure enough for high/absolute |
| `low` | Unclear ownership, risk, or proof path |

## Capability then hybrid runtime

1. Classify `T0`–`T3` and set certainty.
2. Pick mode: Micro / Single / Multi / Critical.
3. Set `task.active_host` to `claude-code` (controller).
4. Bind profile matrix row for the capability (Grok or Claude per matrix).
5. Prefer the main controller for simple single-step controller work before spawn.
6. **Never open on DEEP or genius.** First attempt is LIGHT (Micro) or STANDARD.

## Fan-out caps

| Class | Max execution producers | Default parallel |
| --- | --- | --- |
| T0 | 1 | 1 |
| T1 | 1 | 1 |
| T2 | 3 | 2 |
| T3 | 3 | 2 |

Split only along real ownership or dependency boundaries.

## Escalation and stall (cheap-first)

Escalate `LIGHT` → `STANDARD` → `DEEP` only when:

- Evidence is missing or contradictory after a real attempt.
- Unrecognized owner boundary.
- Worker cannot resolve a concrete ambiguity.
- Risk increases after inspecting the real artifact.
- Previous attempt failed for **capability**, not environment.

Prefer: re-prompt the same tier with a tighter slice before escalating.

### Genius / Opus xhigh (unstick)

Escalate to `genius_worker` (`claude-code` / `opus` / `xhigh`) only after:

| Trigger | Minimum |
| --- | --- |
| `multi_round_fail` | ≥2 Grok attempts on same objective with FAIL/capability blocker |
| `stall` | 2× no material progress |
| `deep_insufficient` | Already DEEP Grok-xhigh, still unclosed |
| `contradiction` | Claims vs controller proof disagree |

Caps: 2 Grok attempts/objective → at most 1 Opus-xhigh → then BLOCKED/user
(or optional advisor `opus` / `max`). Record trigger in
`runtime.fallback_reason`. Never escalate because a task is merely large.
Env/CLI failures are blockers, not genius.

`DEEP` is invalid unless classification is `T3` or `risk_flags` is non-empty.

## Review Cost Guard

Use `REVIEWER` only when the review gate triggers. Bind Claude `opus` / `high`.
Independent: different owner; no expected outcome leaked. Feed
**diff + checklist + frozen scope + proof refs** only.

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

Never invent certainty to save cost. Do not raise REVIEWER to Opus xhigh/max.

## Proof Cost Guard

Prefer, in order:

1. Scope diff vs writable paths.
2. One focused command (single test file / single target).
3. Summarized failure excerpt — never raw multi-KB logs.

Skip full-suite runs unless the change is cross-cutting or T3. Controller may
re-run multi-suite proofs on Claude main thread when required.
