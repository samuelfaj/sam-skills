# Host Runtime Matrix (Codex–Grok profile)

## Contents

- [Purpose](#purpose)
- [Capability ladder](#capability-ladder)
- [Controller host](#controller-host)
- [Profile bindings](#profile-bindings)
- [Effort policy (Grok medium vs high)](#effort-policy-grok-medium-vs-high)
- [Stall escalation to Sol high](#stall-escalation-to-sol-high)
- [Spawn notes](#spawn-notes)
- [Controller rules](#controller-rules)

## Purpose

Fixed hybrid map for `sam-orchestrate-codex-grok`. Choose the cheapest matching
capability. Never ask the user which model to use. If a preferred model or
effort is unavailable, stop with a blocker or record `runtime.fallback_reason`
only for an in-matrix nearest supported row — do not invent out-of-profile hosts.

**Equivalence policy:** `grok-4.5` / `high` ≈ `gpt-5.6-sol` / `medium`. Work at
or below that bar binds to Grok. Sol `high` is genius unstick only.

## Capability ladder

1. Controller (Codex main thread, no worker)
2. `LIGHT` / `fast_scan` — Grok medium
3. `STANDARD` / `routine_worker` — Grok high
4. `DEEP` / `deep_worker` — Grok high
5. `genius_worker` — Codex Sol high (rare; stall / multi-round only)
6. Independent `REVIEWER` — Codex Sol medium when the review gate triggers

Default max parallel execution workers: **2**. Hard cap: **3**.

## Controller host

| Field | Value |
| --- | --- |
| `task.active_host` | `codex` (always) |
| Controller work | DAG, reconcile, multi-suite proof re-runs, integration, report |
| Other hosts | not in this profile |

Do not mix out-of-profile producers. Writable work uses Grok by default; Codex Sol high
only for genius escalation. REVIEWER is always Codex Sol medium.

## Profile bindings

| Capability / role | Host | Model | Effort | Notes |
| --- | --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `grok` | `grok-4.5` | `medium` | Mechanical / read-only / T0 micro |
| `STANDARD` / `routine_worker` | `grok` | `grok-4.5` | `high` | Bounded implementation and ordinary tests |
| `DEEP` / `deep_worker` | `grok` | `grok-4.5` | `high` | T3 / risk slice first attempt |
| `REVIEWER` | `codex` | `gpt-5.6-sol` | `medium` | Read-only independent review; host ≠ Grok producers |
| `genius_worker` (rare) | `codex` | `gpt-5.6-sol` | `high` | Unstick only; requires escalation trigger + `fallback_reason` |
| advisor (optional) | `codex` | `gpt-5.6-sol` | `max` or `xhigh` | Read-only; never owns production nodes |

## Effort policy (Grok medium vs high)

### Use `medium`

- `LIGHT` capability only
- T0 micro mechanical edits, inventory, narrow read-only scans
- Purely mechanical one-line fixes without design branching (prefer LIGHT, not STANDARD medium)

### Use `high`

- All `STANDARD` and `DEEP` Grok producers
- Any Grok re-prompt after capability failure (still Grok high until Sol-high trigger)
- Never lower effort for urgency, cost, or latency

## Stall escalation to Sol high

Escalate a producer to `genius_worker` only when a trigger is met. Record
`runtime.fallback_reason` with the trigger id and evidence reference.

| Trigger | Criterion |
| --- | --- |
| `multi_round_fail` | ≥2 Grok attempts on the same objective; TARGET FAIL or capability blocker |
| `stall` | 2× no material progress (empty useful diff or same root-cause loop) |
| `deep_insufficient` | Already DEEP Grok-high; slice still unclosed |
| `contradiction` | Worker claims vs controller re-checked proof disagree |

Caps:

- Max **2** Grok attempts per objective before Sol-high
- Max **1** Sol-high attempt per objective
- Max **1** active genius node; serialize
- Prefer one tighter same-tier re-prompt before escalating
- No Sol-high for env/CLI/auth failures (blocker, not genius)
- REVIEWER stays Sol **medium**; never auto-raise reviewer to high

Example genius runtime receipt:

```json
{
  "host": "codex",
  "role": "genius_worker",
  "model": "gpt-5.6-sol",
  "effort": "high",
  "fallback_reason": "multi_round_fail after 2 grok attempts; evidence V4"
}
```

## Spawn notes

- **Grok workers:** invoke via `sam-grok-worker` with explicit `--effort` from
  this matrix and absolute `--prompt-file`. Workspace sandbox + always-approve
  only when the node is writable and the parent authorized those writes.
- **Codex REVIEWER:** read-only / ephemeral; diff + checklist intake only.
- **Codex genius:** inherit parent write authorization for the frozen scope only.

## Controller rules

- Keep the main agent controller-only and thin.
- Owner IDs: `worker-N`, `controller-N`, `reviewer-N` only.
- Record bound runtime on every delegated node before spawn.
- Never ask the user to choose among matrix rows.
- Cross-host is intentional in this profile; still one producer per writable path.
