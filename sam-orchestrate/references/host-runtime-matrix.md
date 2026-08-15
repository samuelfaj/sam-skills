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

Default max parallel execution workers: **2**. Hard cap: **3**. Prefer serial
writes; parallelize only independent scopes with a real ownership boundary.
Never open a graph on `DEEP` — first bind `LIGHT` or `STANDARD` and escalate
only after capability failure or new risk evidence.

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
| `DEEP` / `deep_worker` | `gpt-5.6-luna` | `max` | inherit parent permissions; hard debug / architecture |
| `genius_worker` (rare) | `gpt-5.6-sol` | `high` | final escalation only; never default |
| `REVIEWER` | `gpt-5.6-sol` | `medium` | read-only independent review |
| advisor (optional) | `gpt-5.6-sol` | `max` or `xhigh` | read-only focused second opinion |

Root agent settings when configuring Codex agents: `max_threads = 6`,
`max_depth = 1`. Do not force `model_reasoning_effort = "ultra"`.

## Claude Code

Suggested mapping that mirrors the same ladder on Claude Code aliases. Prefer
aliases (`haiku`, `sonnet`, `opus`) so the host tracks the latest shipped
model; pin a full model ID only when the environment requires it.

| Capability / role | Model alias | Effort | Sandbox / notes |
| --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `haiku` | `high` | read-only tools; narrow search and inventory |
| `STANDARD` / `routine_worker` | `sonnet` | `high` | default implementation and ordinary tests |
| `DEEP` / `deep_worker` | `opus` | `medium` | ambiguous, security, architecture, cross-cutting |
| `genius_worker` (rare) | `opus` | `xhigh` | only after `DEEP` is insufficient |
| `REVIEWER` | `opus` | `high` | read-only / plan-mode independent review |
| advisor (optional) | `fable` when available, else `opus` | `high` | focused advisory question only |

Rationale: Haiku (high effort) for controller / low-context scans, Sonnet for
daily coding quality/cost, Opus medium for DEEP production slices, `xhigh`
reserved for rare genius escalation. Do not default the whole graph to Opus.

## Grok

Fixed model family: `grok-4.6` only. Allowed efforts under this skill:
`medium`, `high`, and `xhigh` (no `low` / `max` for orchestration workers).

| Capability / role | Model | Effort | Sandbox / notes |
| --- | --- | --- | --- |
| `LIGHT` / `fast_scan` | `grok-4.6` | `medium` | prefer read-only discovery |
| `STANDARD` / `routine_worker` | `grok-4.6` | `high` | bounded implementation and validation |
| `DEEP` / `deep_worker` | `grok-4.6` | `xhigh` | hard debug, architecture, high risk |
| `genius_worker` (rare) | `grok-4.6` | `xhigh` | escalate scope/proof; xhigh only for rare genius |
| `REVIEWER` | `grok-4.6` | `high` | independent review; no subagent fan-out |
| advisor (optional) | `grok-4.6` | `xhigh` | focused advisory only |

Invoke Grok workers headless with workspace sandbox and always-approve only when
the node is writable and the parent already authorized those writes.

## Escalation and advisors

- Escalate capability before escalating model cost.
- Prefer a tighter re-prompt at the same tier over jumping tiers.
- Use `genius_worker` only when `DEEP` failed for reasoning/capability reasons
  or residual risk is exceptional.
- Advisors never edit files and never own production nodes.
- On missing model/effort support: pick the nearest cheaper supported effort on
  the same role when safe; otherwise the nearest higher effort on the same
  model family. Record `runtime.fallback_reason`.

## Controller rules

- Keep the main agent controller-only and **thin**: classify, dispatch, check
  proof — do not re-read the full skill pack into every worker prompt.
- Do not put model or host names in owner IDs (`worker-N`, `controller-N`,
  `reviewer-N` only).
- Record the bound runtime on every delegated node before spawn.
- Never ask the user to choose among the matrix rows.
- Reviewer intake is diff/checklist only — not the full matrix document.
