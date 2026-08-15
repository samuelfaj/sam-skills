# Output Contract

Write a temporary JSON report, then validate it with
`scripts/validate_gauntlet.py`. Keep it outside the repository.

```json
{
  "schema_version": 1,
  "goal": "Landing page for a running brand",
  "bar": {
    "name": "Nike current running campaign page",
    "locator": "https://www.nike.com/running",
    "fetch_method": "screenshot",
    "kind": "visual"
  },
  "host": {
    "key": "grok",
    "status": "DETECTED",
    "detected_from": "env:GROK_AGENT"
  },
  "mode": "PROMPT_ONLY",
  "prompt": "Build a landing page...",
  "pieces": [],
  "rounds": [],
  "decision": {
    "result": "PROMPT_READY",
    "critic_pick": null,
    "remaining": []
  }
}
```

## Allowed values

- `host.key`: `claude-code` | `codex` | `grok`
- `host.status`: `DETECTED` | `OVERRIDE`
- `bar.fetch_method`: `screenshot` | `read` | `run` | `open`
- `bar.kind`: `visual` | `writing` | `code` | `research` | `other`
- `mode`: `PROMPT_ONLY`
- `decision.result`: `PROMPT_READY` | `BLOCKED`
- `decision.critic_pick`: `ours` | `bar` | `unfetched` | `null`

## Invariants

- This skill only returns `PROMPT_ONLY`. Never emit a `RUN` report.
- `PROMPT_ONLY` may only return `PROMPT_READY` or `BLOCKED`.
- `pieces` and `rounds` stay empty.
- `BLOCKED` requires a concrete remaining item (`host_unknown`,
  `host_conflict`, `vague_bar`, or a named gap).
- The stored `prompt` must pass the host token rules in
  [prompt-contract.md](prompt-contract.md).

## Rendered return

The compiled prompt as one fenced block the user can copy, edit, and paste.
Name the bound host and the bar on one line under the block. Do not offer to
run it. Do not start it.
