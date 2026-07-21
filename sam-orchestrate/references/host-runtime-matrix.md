# Host Runtime Matrix

## Contents

- [Purpose](#purpose)
- [Capability ladder](#capability-ladder)
- [Active host selection](#active-host-selection)
- [Codex](#codex)
- [Claude Code](#claude-code)
- [Grok](#grok)
- [Escalation and advisors](#escalation-and-advisors)
- [Controller rules](#controller-rules)

## Purpose

Map each capability class to an exact host role, model, and effort. Choose the
cheapest matching role. Never ask the user which model to use. If a preferred
model or effort is unavailable, use the nearest supported fallback for that
role and record the fallback in the node runtime receipt.

## Capability ladder

Escalate only after evidence of capability failure:

1. Controller (main thread, no worker)
2. `LIGHT` / `fast_scan`
3. `STANDARD` / `routine_worker`
4. `DEEP` / `deep_worker`
5. `genius_worker` (rare single-agent escalation)
6. Independent `REVIEWER` when the review gate triggers

Default max parallel workers: 3. Hard cap: 6. Prefer serial writes; parallelize
only independent read-only partitions.

## Active host selection

Detect the active controller host once per run:

| Host key | Detection signals |
| --- | --- |
| `codex` | Running under Codex CLI / Codex-backed session |
| `claude-code` | Running under Claude Code (`claude` CLI / Claude Code session) |
| `grok` | Running under Grok CLI / Grok Build session |

Bind every delegated node with that host’s row for the node’s capability. Do not
mix host runtimes inside one orchestration unless the user explicitly requests a
cross-host second opinion; even then, keep one producer host for writable work.

## Codex

Based on the local Codex multi-agent cost ladder (Luna for cheap work, Sol for
deep reasoning). Agent file names may use `ultra_worker` as an alias for
`genius_worker` when the installed Codex agents require that name.

| Capability / role | Model | Effort | Sandbox / notes |
| --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `gpt-5.6-luna` | `medium` | read-only; narrow search and evidence only |
| `STANDARD` / `routine_worker` | `gpt-5.6-luna` | `xhigh` | inherit parent permissions; bounded implementation |
| `DEEP` / `deep_worker` | `gpt-5.6-sol` | `high` | inherit parent permissions; hard debug / architecture |
| `genius_worker` (rare) | `gpt-5.6-sol` | `xhigh` | final escalation only; never default |
| `REVIEWER` | `gpt-5.6-sol` | `high` | read-only independent review |
| advisor (optional) | `gpt-5.6-sol` | `max` or `xhigh` | read-only focused second opinion |

Root agent settings when configuring Codex agents: `max_threads = 6`,
`max_depth = 1`. Do not force `model_reasoning_effort = "ultra"`.

## Claude Code

Suggested mapping that mirrors the same ladder on Claude Code aliases. Prefer
aliases (`haiku`, `sonnet`, `opus`) so the host tracks the latest shipped
model; pin a full model ID only when the environment requires it.

| Capability / role | Model alias | Effort | Sandbox / notes |
| --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `haiku` | `medium` | read-only tools; narrow search and inventory |
| `STANDARD` / `routine_worker` | `sonnet` | `high` | default implementation and ordinary tests |
| `DEEP` / `deep_worker` | `opus` | `high` | ambiguous, security, architecture, cross-cutting |
| `genius_worker` (rare) | `opus` | `xhigh` | only after `DEEP` is insufficient |
| `REVIEWER` | `opus` | `high` | read-only / plan-mode independent review |
| advisor (optional) | `fable` when available, else `opus` | `high` | focused advisory question only |

Rationale: Haiku for low-context scans, Sonnet for daily coding quality/cost,
Opus for hard reasoning and independent review, `xhigh` reserved for rare
escalation. Do not default the whole graph to Opus.

## Grok

Fixed model family: `grok-4.5` only. Allowed efforts under this skill: `medium`
and `high` (no `low` / `xhigh` / `max` for orchestration workers).

| Capability / role | Model | Effort | Sandbox / notes |
| --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `grok-4.5` | `medium` | prefer read-only discovery |
| `STANDARD` / `routine_worker` | `grok-4.5` | `medium` | bounded implementation and validation |
| `DEEP` / `deep_worker` | `grok-4.5` | `high` | hard debug, architecture, high risk |
| `genius_worker` (rare) | `grok-4.5` | `high` | same ceiling as DEEP; escalate scope/proof, not model family |
| `REVIEWER` | `grok-4.5` | `high` | independent review; no subagent fan-out |
| advisor (optional) | `grok-4.5` | `high` | focused advisory only |

Invoke Grok workers headless with workspace sandbox and always-approve only when
the node is writable and the parent already authorized those writes.

## Escalation and advisors

- Escalate capability before escalating model cost.
- Use `genius_worker` only when `DEEP` failed for reasoning/capability reasons
  or residual risk is exceptional.
- Advisors never edit files and never own production nodes.
- On missing model/effort support: pick the nearest cheaper supported effort on
  the same role when safe; otherwise the nearest higher effort on the same
  model family. Record `runtime.fallback_reason`.

## Controller rules

- Keep the main agent controller-only.
- Do not put model or host names in owner IDs (`worker-N`, `controller-N`,
  `reviewer-N` only).
- Record the bound runtime on every delegated node before spawn.
- Never ask the user to choose among the matrix rows.
