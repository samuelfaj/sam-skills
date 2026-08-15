# Host Runtime Matrix (Claude–Grok profile)

## Contents

- [Purpose](#purpose)
- [Capability ladder](#capability-ladder)
- [Controller host](#controller-host)
- [Profile bindings](#profile-bindings)
- [Effort policy (Grok medium / high / xhigh)](#effort-policy-grok-medium--high--xhigh)
- [Stall escalation to Opus xhigh](#stall-escalation-to-opus-xhigh)
- [Spawn notes](#spawn-notes)
- [Controller rules](#controller-rules)

## Purpose

Fixed hybrid map for `sam-orchestrate-claude-grok`. Choose the cheapest matching
capability. Never ask the user which model to use. If a preferred model or
effort is unavailable, stop with a blocker or record `runtime.fallback_reason`
only for an in-matrix nearest supported row — do not invent out-of-profile hosts.

**Equivalence policy:** `grok-4.6` / `high` ≈ `opus` / `medium`. Work at or
below that bar binds to Grok. Grok `xhigh` is the DEEP producer bar. Opus
`high` / `xhigh` / `max` is review, genius unstick, and advisor only.

## Capability ladder

1. Controller (Claude main thread, no worker)
2. `LIGHT` / `fast_scan` — Grok medium
3. `STANDARD` / `routine_worker` — Grok high
4. `DEEP` / `deep_worker` — Grok xhigh
5. `genius_worker` — Claude opus xhigh (rare; stall / multi-round only)
6. Independent `REVIEWER` — Claude opus high when the review gate triggers
7. Advisor (optional) — Claude opus max, read-only

Default max parallel execution workers: **2**. Hard cap: **3**.

## Controller host

| Field | Value |
| --- | --- |
| `task.active_host` | `claude-code` (always) |
| Controller work | DAG, reconcile, multi-suite proof re-runs, integration, report |
| Other hosts | not in this profile |

Do not mix out-of-profile producers. Writable work uses Grok by default; Claude
opus xhigh only for genius escalation. REVIEWER is always Claude opus high.

## Profile bindings

| Capability / role | Host | Model | Effort | Notes |
| --- | --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `grok` | `grok-4.6` | `medium` | Mechanical / read-only / T0 micro |
| `STANDARD` / `routine_worker` | `grok` | `grok-4.6` | `high` | Bounded implementation and ordinary tests |
| `DEEP` / `deep_worker` | `grok` | `grok-4.6` | `xhigh` | T3 / risk slice first attempt |
| `REVIEWER` | `claude-code` | `opus` | `high` | Read-only independent review; host ≠ Grok producers |
| `genius_worker` (rare) | `claude-code` | `opus` | `xhigh` | Unstick only; requires escalation trigger + `fallback_reason` |
| advisor (optional) | `claude-code` | `opus` | `max` | Read-only; never owns production nodes |

## Effort policy (Grok medium / high / xhigh)

### Use `medium`

- `LIGHT` capability only
- T0 micro mechanical edits, inventory, narrow read-only scans
- Purely mechanical one-line fixes without design branching (prefer LIGHT)

### Use `high`

- All `STANDARD` Grok producers
- Any STANDARD re-prompt after capability failure (still Grok high until Opus-xhigh)
- Never lower effort for urgency, cost, or latency

### Use `xhigh`

- All `DEEP` Grok producers
- Any DEEP re-prompt after capability failure (still Grok xhigh until Opus-xhigh)

## Stall escalation to Opus xhigh

Escalate a producer to `genius_worker` only when a trigger is met. Record
`runtime.fallback_reason` with the trigger id and evidence reference.

| Trigger | Criterion |
| --- | --- |
| `multi_round_fail` | ≥2 Grok attempts on the same objective; TARGET FAIL or capability blocker |
| `stall` | 2× no material progress (empty useful diff or same root-cause loop) |
| `deep_insufficient` | Already DEEP Grok-xhigh; slice still unclosed |
| `contradiction` | Worker claims vs controller re-checked proof disagree |

Caps:

- Max **2** Grok attempts per objective before Opus-xhigh
- Max **1** Opus-xhigh attempt per objective
- Max **1** active genius node; serialize
- Prefer one tighter same-tier re-prompt before escalating
- No Opus-xhigh for env/CLI/auth failures (blocker, not genius)
- REVIEWER stays Opus **high**; never auto-raise reviewer to xhigh/max

Example genius runtime receipt:

```json
{
  "host": "claude-code",
  "role": "genius_worker",
  "model": "opus",
  "effort": "xhigh",
  "fallback_reason": "multi_round_fail after 2 grok attempts; evidence V4"
}
```

## Spawn notes

- **Grok workers:** invoke via `sam-grok-worker` with explicit `--effort` from
  this matrix and absolute `--prompt-file`. Workspace sandbox + always-approve
  only when the node is writable and the parent authorized those writes.
- **Claude REVIEWER:** read-only / plan-mode; diff + checklist intake only.
- **Claude genius:** inherit parent write authorization for the frozen scope only.
- **Advisor:** `opus` / `max`, read-only, focused question only.

## Controller rules

- Keep the main agent controller-only and thin.
- Owner IDs: `worker-N`, `controller-N`, `reviewer-N` only.
- Record bound runtime on every delegated node before spawn.
- Never ask the user to choose among matrix rows.
- Cross-host is intentional in this profile; still one producer per writable path.
