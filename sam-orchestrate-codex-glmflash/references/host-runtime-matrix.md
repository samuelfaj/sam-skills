# Host Runtime Matrix (Codex–GLM Flash profile)

## Contents

- [Purpose](#purpose)
- [Capability ladder](#capability-ladder)
- [Controller host](#controller-host)
- [Profile bindings](#profile-bindings)
- [Effort policy](#effort-policy)
- [Stall escalation to Sol high](#stall-escalation-to-sol-high)
- [Spawn notes](#spawn-notes)
- [Controller rules](#controller-rules)

## Purpose

Fixed provider map for `sam-orchestrate-codex-glmflash`. Choose the cheapest
matching capability. Never ask the user which model to use. If Codex, the Z.AI
provider, or a required effort is unavailable, stop with a blocker or record
`runtime.fallback_reason` only for an in-matrix nearest supported row — do not
invent out-of-profile hosts.

## Capability ladder

1. Controller (Codex main thread, no worker)
2. `LIGHT` / `fast_scan` — Z.AI `glm-5.3-flash`, max
3. `STANDARD` / `routine_worker` — Z.AI `glm-5.3-flash`, max
4. `DEEP` / `deep_worker` — Z.AI `glm-5.3-flash`, max
5. `genius_worker` — Codex Sol high (rare; stall / multi-round only)
6. Independent `REVIEWER` — Codex Sol medium when the review gate triggers

Default max parallel execution workers: **2**. Hard cap: **3**.

## Controller host

| Field | Value |
| --- | --- |
| `task.active_host` | `codex` (always) |
| Controller work | DAG, reconcile, multi-suite proof re-runs, integration, report |
| Other hosts | not in this profile |

Do not mix out-of-profile producers. Writable work uses Z.AI GLM-5.3-Flash by
default; Codex Sol high is only for genius escalation. REVIEWER is always Codex
Sol medium. Producer and reviewer nodes share the Codex host but use distinct
models and owners.

## Profile bindings

| Capability / role | Host | Model | Effort | Notes |
| --- | --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `codex` | `glm-5.3-flash` | `max` | Mechanical / read-only / T0 micro |
| `STANDARD` / `routine_worker` | `codex` | `glm-5.3-flash` | `max` | Bounded implementation and ordinary tests |
| `DEEP` / `deep_worker` | `codex` | `glm-5.3-flash` | `max` | T3 / risk slice first attempt |
| `REVIEWER` | `codex` | `gpt-5.6-sol` | `medium` | Read-only independent review; distinct model and owner |
| `genius_worker` (rare) | `codex` | `gpt-5.6-sol` | `high` | Unstick only; requires escalation trigger + `fallback_reason` |
| advisor (optional) | `codex` | `gpt-5.6-sol` | `max` | Read-only; never owns production nodes |

For the Z.AI profile, the Codex provider transport must be `wire_api = "responses"`; the local bridge at `127.0.0.1:31415` translates it to Z.AI Chat Completions because the legacy `chat` transport is no longer accepted by current Codex CLI releases.

## Effort policy

All GLM-5.3-Flash producers use `max`, including LIGHT and STANDARD.
Capability labels describe the work; they do not reduce producer effort.
Reviewer and escalation bindings remain those in the table above.

## Stall escalation to Sol high

Escalate a producer to `genius_worker` only when a trigger is met. Record
`runtime.fallback_reason` with the trigger id and evidence reference.

| Trigger | Criterion |
| --- | --- |
| `multi_round_fail` | ≥2 GLM-5.3-Flash attempts on the same objective; TARGET FAIL or capability blocker |
| `stall` | 2× no material progress (empty useful diff or same root-cause loop) |
| `deep_insufficient` | Already DEEP GLM-5.3-Flash-max; slice still unclosed |
| `contradiction` | Worker claims vs controller re-checked proof disagree |

Caps:

- Max **2** GLM-5.3-Flash attempts per objective before Sol-high
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
  "fallback_reason": "multi_round_fail after 2 GLM-5.3-Flash attempts; evidence V4"
}
```

## Spawn notes

- **GLM-5.3-Flash workers:** invoke via `codex exec` with explicit
  `model_provider="zai"`, `model="glm-5.3-flash"`, and effort from this matrix,
  plus an absolute prompt file piped on stdin (`codex exec ... - < prompt-file`).
  Workspace sandbox + always-approve only when the node is writable and the parent
  authorized those writes. Never pass the API key on the command line.
- **Codex REVIEWER:** read-only / ephemeral; diff + checklist intake only.
- **Codex genius:** inherit parent write authorization for the frozen scope only.

## Controller rules

- Keep the main agent controller-only and thin.
- Owner IDs: `worker-N`, `controller-N`, `reviewer-N` only.
- Record bound runtime on every delegated node before spawn.
- Never ask the user to choose among matrix rows.
- Producer and reviewer models share the Codex host; still one producer per writable path.
