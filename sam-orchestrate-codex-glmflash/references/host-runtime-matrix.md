# Host Runtime Matrix (Codex–GLM Flash profile)

Bindings are the SKILL.md §3 table (`task.active_host` and every delegated
`runtime.host` are `codex`; other hosts are not in this profile).

## Spawn note

**GLM-5.3-Flash workers:** invoke via `codex exec` with explicit
`model_provider="zai"`, `model="glm-5.3-flash"`, and effort `max`, plus an
absolute prompt file piped on stdin (`codex exec ... - < prompt-file`).
Workspace sandbox + always-approve only when the node is writable and the parent
authorized those writes. Never pass the API key on the command line.

For the Z.AI profile, the Codex provider transport must be
`wire_api = "responses"`; the local bridge at `127.0.0.1:31415` translates it to
Z.AI Chat Completions because the legacy `chat` transport is no longer accepted
by current Codex CLI releases.

## Fallback

If Codex, the Z.AI provider, or a required effort is unavailable, stop with a
blocker, or record `runtime.fallback_reason` only for an in-matrix nearest
supported row. Never invent out-of-profile hosts.
