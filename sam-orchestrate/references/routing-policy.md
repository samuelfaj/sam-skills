# Routing Policy

## Escalation (cheap-first)

Prefer the controller for simple single-step controller work before spawning.
The first attempt is `LIGHT` (Micro) or `STANDARD` (Single). Escalate `LIGHT` →
`STANDARD` or `STANDARD` → `DEEP` only when:

- Evidence is missing or contradictory after a real attempt.
- The task crosses an unrecognized owner boundary.
- A worker cannot resolve a concrete ambiguity.
- Risk increases after inspecting the real artifact.
- A previous attempt failed for capability, not environment, reasons.

Prefer re-prompting the same tier with a tighter slice. Escalate capability
before model cost. Use `genius_worker` only when `DEEP` failed for reasoning or
capability reasons or residual risk is exceptional; on Grok the model stays
`grok-4.6` / `xhigh`, so escalate scope and proof depth, not model family.

## Genius escalation (profiles with a genius row)

Escalate a `STANDARD`/`DEEP` producer to `genius_worker` only when a trigger
holds; record the trigger id and evidence reference in `runtime.fallback_reason`:

| Trigger | Minimum evidence |
| --- | --- |
| `multi_round_fail` | ≥ 2 worker attempts on the same objective with TARGET `FAIL` or a capability blocker |
| `stall` | 2× no material progress (no useful diff or same root-cause loop) |
| `deep_insufficient` | Node already at the profile's `DEEP` row and still unclosed |
| `contradiction` | Worker claims contradict controller re-checked proof |

At most 2 worker attempts per objective before the genius row, then at most 1
genius attempt, then `BLOCKED` plus a user decision (or the optional read-only
advisor). At most 1 active genius node, serialized. Never escalate for task
size, latency, preference, or env/CLI/auth failure (a blocker, not genius). The
profile file names the genius row and its effort.

## Proof Cost

Prefer, in order:

1. Scope diff vs writable paths.
2. One focused command (single test file or single target).
3. Summarized failure excerpt, never raw multi-KB logs.

Skip full-suite runs unless the change is cross-cutting or `T3`. The controller may re-run multi-suite proofs on the main thread when required.
