# Profile: claude-grok

Claude Code controls (long tasks, test re-runs, integration, proof); Grok `grok-4.6` produces; Claude `opus` reviews, unsticks after multi-round Grok failure or stall, and advises. Use with `--profile claude-grok` on both report scripts.

- `task.active_host` is `claude-code`; worker `runtime.host` is `grok` or `claude-code` per the table.
- Spawn Grok `EXECUTION` nodes via `references/workers/grok.md` with the table effort (`--effort medium|high|xhigh`), never the worker's default. Spawn the Claude REVIEWER and genius via Claude Code with the table model and effort; the REVIEWER is read-only.
- If the Claude or Grok CLI or auth is unavailable, stop with an evidence-backed `EXTERNAL`/`ENVIRONMENT` blocker. No silent host fallback outside this profile.

## Bindings

| Capability (role) | Host | Model | Effort | Notes |
| --- | --- | --- | --- | --- |
| `LIGHT` (`fast_scan`) | `grok` | `grok-4.6` | `medium` | mechanical / read-only / `T0` micro |
| `STANDARD` (`routine_worker`) | `grok` | `grok-4.6` | `high` | bounded implementation and ordinary tests |
| `DEEP` (`deep_worker`) | `grok` | `grok-4.6` | `xhigh` | `T3` / risk slice first attempt |
| `REVIEWER` (`reviewer`) | `claude-code` | `opus` | `high` | read-only / plan mode; host ≠ Grok producers |
| `genius_worker` (rare) | `claude-code` | `opus` | `xhigh` | unstick only; routing-policy.md trigger + `fallback_reason` |
| advisor (optional) | `claude-code` | `opus` | `max` | read-only; never owns production nodes |

## Effort policy

- `medium`: `LIGHT` only: `T0` micro mechanical edits, inventory, narrow read-only scans, one-line fixes without design branching.
- `high`: every `STANDARD` Grok producer, including re-prompts after capability failure (Grok `high` until Opus `xhigh`).
- `xhigh`: every `DEEP` Grok producer, including re-prompts after capability failure (Grok `xhigh` until Opus `xhigh`).
- Never lower effort for urgency, cost, or latency.

## Escalation

- Genius trigger counts Grok attempts; `deep_insufficient` means the node already ran `DEEP` Grok `xhigh`.
- At most 2 Grok attempts per objective before Opus `xhigh`, then at most 1 Opus `xhigh` attempt, then `BLOCKED` plus a user decision (or the advisor).
- Never raise REVIEWER effort to `xhigh`/`max`; corrections return to Grok producers, or Opus `xhigh` if a trigger is already armed.

## Spawn

- **Grok:** read `references/workers/grok.md` once per run. Per worker run `python3 -B <skill-dir>/scripts/resolve_worker.py --effort <table effort> --prompt-file <abs prompt>`, then run its `command` argv unchanged with stdout to `<run>/<node>.json` and stderr to `<run>/<node>.err`; read only the JSON `.text`. Every Grok node keeps the runbook's prompt requirements (no publish, push, remote proposals, messages, or other external writes unless the frozen request authorizes them; the Output field replaces its report line) and reconcile step.
- The resolver always grants workspace sandbox + always-approve: spawn Grok only where the parent authorized workspace writes, else the controller runs read-only scans itself. A read-only Grok node gets `No-go: any write`, and `--tree` run before and after it must print the same id, else the node fails. The Claude genius is writable only for the frozen scope the controller already authorized. Cross-host is intentional; still one producer per writable path.
- **Claude REVIEWER / genius / advisor:** as a Claude Code subagent, or `claude -p --output-format json ... < <run>/<node>.prompt.md > <run>/<node>.json` reading only `.result`; only the REVIEWER and advisor add `--add-dir <run>`. The REVIEWER is read-only / plan mode. Grok workers never self-escalate to Opus.
