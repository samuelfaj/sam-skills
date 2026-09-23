# Host Runtime Matrix (Claude–Grok profile)

Bindings are the SKILL.md §3 table (`task.active_host` is always `claude-code`;
other hosts are not in this profile).

## Fallback

If a preferred model or effort is unavailable, stop with a blocker, or record
`runtime.fallback_reason` only for an in-matrix nearest supported row. Never
invent out-of-profile hosts.

## Effort policy

- `medium`: `LIGHT` only: `T0` micro mechanical edits, inventory, narrow
  read-only scans, purely mechanical one-line fixes without design branching.
- `high`: every `STANDARD` Grok producer, including re-prompts after capability
  failure (Grok `high` until Opus `xhigh`).
- `xhigh`: every `DEEP` Grok producer, including re-prompts after capability
  failure (Grok `xhigh` until Opus `xhigh`).
- Never lower effort for urgency, cost, or latency.
