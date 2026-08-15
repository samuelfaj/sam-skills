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
- `mode`: `PROMPT_ONLY` | `RUN`
- `decision.result`: `PROMPT_READY` | `WON` | `STOPPED` | `BLOCKED` | `STALLED`
- `decision.critic_pick`: `ours` | `bar` | `unfetched` | `null`

## Invariants

- `PROMPT_ONLY` may only return `PROMPT_READY` or `BLOCKED`.
- `RUN` may only return `WON`, `STOPPED`, `BLOCKED`, or `STALLED`.
- `WON` requires `critic_pick=ours`, a fetched bar, and no remaining gaps.
- `STALLED` requires two consecutive rounds with the same gap fingerprint.
- `BLOCKED` requires a concrete remaining item (`host_unknown`,
  `host_conflict`, `bar_unfetched`, `vague_bar`, or a named gap).
- The stored `prompt` must pass the host token rules in
  [prompt-contract.md](prompt-contract.md).
- `pieces` and `rounds` stay empty on `PROMPT_ONLY`. On `RUN`, every piece has
  a latest critic pick.

## Rendered return

- Prompt-only: the compiled prompt, the bound host, and the offer to run.
- After a run: result, bar, host, piece picks, remaining gap, and whether the
  bar was actually fetched.
