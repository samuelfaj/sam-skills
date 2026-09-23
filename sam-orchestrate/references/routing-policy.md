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

## Proof Cost

Prefer, in order:

1. Scope diff vs writable paths.
2. One focused command (single test file or single target).
3. Summarized failure excerpt, never raw multi-KB logs.

Skip full-suite runs unless the change is cross-cutting or `T3`.
