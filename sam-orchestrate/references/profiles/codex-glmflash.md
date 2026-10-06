# Profile: codex-glmflash

Codex controls (long tasks, test re-runs, integration, proof); Z.AI `glm-5.3-flash` produces; Codex `gpt-5.6-sol` reviews and unsticks after multi-round GLM-5.3-Flash failure or stall. Use with `--profile codex-glmflash` on both report scripts.

- `task.active_host` and every delegated `runtime.host` are `codex`; the producer model is selected through provider `zai`. Producer and reviewer share the host but use distinct models, roles, owners, and read/write boundaries.
- Effort policy: GLM-5.3-Flash always uses `max`, including `LIGHT` and `STANDARD`; capability labels describe the work, not producer effort. Sol `high` is reserved for genius unstick after GLM-5.3-Flash is exhausted. Never lower effort for urgency, cost, or latency.
- If Codex, the Z.AI provider, or GLM-5.3-Flash auth is unavailable, stop with an evidence-backed `EXTERNAL`/`ENVIRONMENT` blocker. No silent host fallback outside this profile.

## Bindings

| Capability (role) | Host | Model | Effort | Notes |
| --- | --- | --- | --- | --- |
| `LIGHT` (`fast_scan`) | `codex` | `glm-5.3-flash` | `max` | mechanical / read-only / `T0` micro |
| `STANDARD` (`routine_worker`) | `codex` | `glm-5.3-flash` | `max` | bounded implementation and ordinary tests |
| `DEEP` (`deep_worker`) | `codex` | `glm-5.3-flash` | `max` | `T3` / risk slice first attempt |
| `REVIEWER` (`reviewer`) | `codex` | `gpt-5.6-sol` | `medium` | read-only / ephemeral; distinct model and owner |
| `genius_worker` (rare) | `codex` | `gpt-5.6-sol` | `high` | unstick only; routing-policy.md trigger + `fallback_reason` |
| advisor (optional) | `codex` | `gpt-5.6-sol` | `max` | read-only; never owns production nodes |

## Escalation

- Genius trigger counts GLM-5.3-Flash attempts; `deep_insufficient` means the node already ran `DEEP` GLM-5.3-Flash `max`.
- At most 2 GLM-5.3-Flash attempts per objective before Sol `high`, then at most 1 Sol `high` attempt, then `BLOCKED` plus a user decision (or the advisor).
- Never raise REVIEWER effort to `high`; corrections return to producers, or Sol `high` if a trigger is already armed.

## Provider setup and spawn

- **GLM-5.3-Flash workers:** invoke via `codex exec` with explicit `model_provider="zai"`, `model="glm-5.3-flash"`, and effort `max`, plus an absolute prompt file piped on stdin (`codex exec ... -o <run>/<node>.last.md - < <prompt-file> > <run>/<node>.log 2>&1`); read only `<node>.last.md`. Workspace sandbox + always-approve only when the node is writable and the parent authorized those writes.
- Never pass the API key on the command line or in a prompt; rely on the configured `ZAI_API_KEY` environment variable. Never include `ZAI_API_KEY` in a worker prompt.
- The Codex provider transport must be `wire_api = "responses"`; the local bridge at `127.0.0.1:31415` translates it to Z.AI Chat Completions because the legacy `chat` transport is no longer accepted by current Codex CLI releases.
- **Codex REVIEWER / genius / advisor:** as a Codex agent or the same `codex exec` form with the table model and effort; the REVIEWER is read-only / ephemeral. GLM-5.3-Flash workers never self-escalate to Sol.
- The Codex genius is writable only for the frozen scope the controller already authorized; still one producer per writable path.
