# Host Runtime Matrix

Execution and review bindings are the SKILL.md §3 table. sam-task and the
advisor skills read the advisor rows here.

## Host detection

Detect the active controller host once per run:

| Host key | Detection signals |
| --- | --- |
| `codex` | Running under Codex CLI / Codex-backed session |
| `claude-code` | Running under Claude Code (`claude` CLI / Claude Code session) |
| `grok` | Running under Grok CLI / Grok Build session |

## Fallback

If a bound model or effort is unavailable, use the nearest supported fallback
for that role: the nearest cheaper supported effort on the same role when safe,
otherwise the nearest higher effort on the same model family. Record
`runtime.fallback_reason`. Codex fallbacks may adjust effort but must keep
`gpt-5.6-luna` for execution and `gpt-6-astra` for review; if the required model
is unavailable, report the blocked role.

## Host notes

- **Codex:** keep the current controller effort unless the task requires a
  change; do not force maximum reasoning. When configuring Codex agents, set
  root `max_threads = 6` and `max_depth = 1`; do not force
  `model_reasoning_effort = "ultra"`. Agent files may name `genius_worker` as
  `ultra_worker` when the installed agents require it.
- **Claude Code:** prefer the aliases `haiku`, `sonnet`, `opus` so the host
  tracks the latest shipped model; pin a full model ID only when the
  environment requires it. Do not default the whole graph to `opus`.
- **Grok:** model family `grok-4.6` only; orchestration workers use `medium`,
  `high`, or `xhigh` (never `low` or `max`).

## Advisor rows

Optional, read-only, one focused question. Advisors never edit files and never
own production nodes.

| Host | Advisor model | Effort | Notes |
| --- | --- | --- | --- |
| `codex` | `gpt-6-astra` | `max` or `xhigh` | read-only focused second opinion |
| `claude-code` | `fable` when available, else `opus` | `high` | focused advisory question only |
| `grok` | `grok-4.6` | `xhigh` | focused advisory only |
