# Routing Policy (Codex–Grok profile)

## Escalation (cheap-first)

Prefer the main controller for simple single-step controller work before
spawning. The first attempt is `LIGHT` (Micro) or `STANDARD`. Escalate `LIGHT`
→ `STANDARD` → `DEEP` only when:

- Evidence is missing or contradictory after a real attempt.
- The task crosses an unrecognized owner boundary.
- A worker cannot resolve a concrete ambiguity.
- Risk increases after inspecting the real artifact.
- A previous attempt failed for capability, not environment, reasons.

Prefer re-prompting the same tier with a tighter slice.

## Genius escalation

Escalate a `STANDARD`/`DEEP` producer to `genius_worker` only when a trigger
holds; record the trigger id and evidence reference in `runtime.fallback_reason`:

| Trigger | Minimum evidence |
| --- | --- |
| `multi_round_fail` | ≥ 2 Grok attempts on the same objective with TARGET `FAIL` or a capability blocker |
| `stall` | 2× no material progress (no useful diff or same root-cause loop) |
| `deep_insufficient` | Node already `DEEP` Grok `xhigh` and still unclosed |
| `contradiction` | Worker claims contradict controller re-checked proof |

Caps: at most 2 Grok attempts per objective before Sol `high`, then at most 1
Sol `high` attempt, then `BLOCKED` plus a user decision (or the optional
read-only advisor). At most 1 active genius node, serialized. Never escalate for
task size, latency, preference, or env/CLI/auth failure (a blocker, not genius).

## Proof Cost

Prefer, in order:

1. Scope diff vs writable paths.
2. One focused command (single test file or single target).
3. Summarized failure excerpt, never raw multi-KB logs.

Skip full-suite runs unless the change is cross-cutting or `T3`. The controller
may re-run multi-suite proofs on the Codex main thread when required.
