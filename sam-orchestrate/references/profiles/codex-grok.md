# Profile: codex-grok

Codex controls (long tasks, test re-runs, integration, proof); Grok `grok-4.6` produces; Codex `gpt-5.6-sol` reviews and unsticks after multi-round Grok failure or stall. Use with `--profile codex-grok` on both report scripts.

- `task.active_host` is `codex`; worker `runtime.host` is `grok` or `codex` per the table.
- Spawn Grok `EXECUTION` nodes via `references/workers/grok.md` with the table effort (`--effort medium|high|xhigh`), never the worker's default. Spawn the Codex REVIEWER and genius via a Codex agent or `codex exec` with the table model and effort; the REVIEWER is read-only.
- If the Codex or Grok CLI or auth is unavailable, stop with an evidence-backed `EXTERNAL`/`ENVIRONMENT` blocker. No silent host fallback outside this profile.

## Bindings

| Capability (role) | Host | Model | Effort | Notes |
| --- | --- | --- | --- | --- |
| `LIGHT` (`fast_scan`) | `grok` | `grok-4.6` | `medium` | mechanical / read-only / `T0` micro |
| `STANDARD` (`routine_worker`) | `grok` | `grok-4.6` | `high` | bounded implementation and ordinary tests |
| `DEEP` (`deep_worker`) | `grok` | `grok-4.6` | `xhigh` | `T3` / risk slice first attempt |
| `REVIEWER` (`reviewer`) | `codex` | `gpt-5.6-sol` | `medium` | read-only / ephemeral; host ≠ Grok producers |
| `genius_worker` (rare) | `codex` | `gpt-5.6-sol` | `high` | unstick only; routing-policy.md trigger + `fallback_reason` |
| advisor (optional) | `codex` | `gpt-5.6-sol` | `max` or `xhigh` | read-only; never owns production nodes |

## Effort policy

- `medium`: `LIGHT` only: `T0` micro mechanical edits, inventory, narrow read-only scans, one-line fixes without design branching.
- `high`: every `STANDARD` Grok producer, including re-prompts after capability failure (Grok `high` until Sol `high`).
- `xhigh`: every `DEEP` Grok producer, including re-prompts after capability failure (Grok `xhigh` until Sol `high`).
- Never lower effort for urgency, cost, or latency.

## Escalation

- Genius trigger counts Grok attempts; `deep_insufficient` means the node already ran `DEEP` Grok `xhigh`.
- At most 2 Grok attempts per objective before Sol `high`, then at most 1 Sol `high` attempt, then `BLOCKED` plus a user decision (or the advisor).
- Never raise REVIEWER effort to `high`; corrections return to Grok producers, or Sol `high` if a trigger is already armed.

## Spawn

- **Grok:** read `references/workers/grok.md` once per run. Per worker run `python3 -B <skill-dir>/scripts/resolve_worker.py --effort <table effort> --prompt-file <abs prompt>`, then run its `command` argv unchanged with stdout to `<run>/<node>.json` and stderr to `<run>/<node>.err`; read only the JSON `.text`. Every Grok node keeps the runbook's prompt requirements (no publish, push, remote proposals, messages, or other external writes unless the frozen request authorizes them; the Output field replaces its report line) and reconcile step.
- The resolver always grants workspace sandbox + always-approve: spawn Grok only where the parent authorized workspace writes, else the controller runs read-only scans itself. A read-only Grok node gets `No-go: any write`, and `--tree` run before and after it must print the same id, else the node fails. Cross-host is intentional; still one producer per writable path.
- **Codex REVIEWER / genius / advisor:** as a Codex agent, or `codex exec ... -o <run>/<node>.last.md - < <run>/<node>.prompt.md > <run>/<node>.log 2>&1`, reading only `<node>.last.md`. The REVIEWER is read-only / ephemeral. Grok workers never self-escalate to Sol.
