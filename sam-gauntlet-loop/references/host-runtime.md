# Host Runtime

## Contents

- [Detection](#detection)
- [Shared runner rules](#shared-runner-rules)
- [claude-code](#claude-code)
- [codex](#codex)
- [grok](#grok)

Detect the host from **process environment**, never from which clients exist on
disk. Bind exactly one row. Do not mix primitives.

## Detection

`scripts/detect_host.py` inspects override vars, then host-unique env keys.

| Host key | Process signals |
| --- | --- |
| `claude-code` | `CLAUDECODE`, `CLAUDE_CODE`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_CODE_ENTRYPOINT` |
| `codex` | `CODEX_HOME`, `CODEX_THREAD_ID`, `CODEX_SANDBOX`, `CODEX_CI` |
| `grok` | `GROK_AGENT`, `GROK_HOME`, `GROK_SESSION`, `GROK_SESSION_ID` |

Override: `SAM_GAUNTLET_HOST` or `SAM_ACTIVE_HOST`. Override wins. Two families
at once without an override is `CONFLICT`. None is `UNKNOWN`.

## Shared runner rules

- Lead owns the loop. Depth-1 hosts cannot let a builder spawn its critic.
- Critic spawn: new agent, no resume, no builder transcript.
- Critic intake: bar locator, fetch method, output paths, binary pick contract.
- Parallelize builder and critic per piece when the host allows it.
- Progress: the host's native run view if it has one; otherwise a short note.
- Never invent a primitive the host does not expose.

## claude-code

Allowed in the compiled prompt: `/loop` as a quality retry, and `ultracode` to
opt the turn into a dynamic workflow.

- Fan-out with native subagents / Task. Nesting is allowed on this host.
- `/loop` here means keep retrying a piece until the critic picks `ours`.
- `ultracode` writes and runs a workflow script. Use it for the run.
- Watch the host workflow / task panel. A live progress page is welcome.
- Do not substitute another host's scheduler or workflow dialect.

## codex

Forbidden in the compiled prompt: `/loop`, `ultracode`.

- Spawn builders and critics as distinct agents with fresh threads.
- `max_depth` is 1. The lead loops; children do not spawn children.
- Keep looping in the lead turn until the critic picks `ours` or the user stops.
- Slash `/loop` is not a quality retry on this host. Do not invoke it.
- Use the host's native spawn / agent tool only. Do not write a workflow script
  from another product.

## grok

Forbidden in the compiled prompt: `/loop`, `ultracode`.

- Orchestrate with the host `workflow` tool (`agent`, `parallel`, `phase`) or
  with top-level `spawn_subagent`. Children cannot spawn children.
- Slash `/loop` is a recurring scheduler, not a quality retry. Never emit it.
- There is no `ultracode` setting. The workflow tool is the orchestration.
- Watch `/workflows`. Scratch progress is enough; do not require an HTML page.
- `/goal` is a weaker fallback (independent review, no bar A/B). Prefer the
  workflow loop when the run is requested.
