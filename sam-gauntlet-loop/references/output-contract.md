# Output Contract

`scripts/compile_prompt.py` builds and self-validates this report; `--report <path>` saves it outside the repository. After a hand-fix, run `python3 -B <skill>/scripts/validate_gauntlet.py <report>`. Fix from the validator's error lines and patch the report in place; do not read validator source or rewrite the whole report.

Exact keys, no extras: `schema_version`, `goal`, `bar`, `host`, `mode`, `prompt`, `pieces`, `rounds`, `decision`.

| Field | Rule |
| --- | --- |
| `schema_version` | `1` |
| `goal` | Non-empty text |
| `mode` | `PROMPT_ONLY` only; never a `RUN` report |
| `bar` | Exact keys `name`, `locator`, `fetch_method`, `kind`, all strings. `fetch_method`: `screenshot` \| `read` \| `run` \| `open`. `kind`: `visual` \| `writing` \| `code` \| `research` \| `other` |
| `host` | Exact keys `key`, `status`, `detected_from`. `status`: `DETECTED` \| `OVERRIDE` \| `UNKNOWN` \| `CONFLICT` \| `INVALID`. `key`: `claude-code` \| `codex` \| `grok` when `DETECTED` or `OVERRIDE`, else `null`. `detected_from`: non-empty (`env:<KEY>`, `override:<host>`, `user:<host>`, `none`, `conflict`) |
| `prompt` | `PROMPT_READY`: 80-220 words that pass the host token rules. `BLOCKED`: `""` |
| `pieces`, `rounds` | `[]` |
| `decision` | Exact keys `result`, `critic_pick`, `remaining`. `result`: `PROMPT_READY` \| `BLOCKED`. `critic_pick`: `ours` \| `bar` \| `unfetched` \| `null`; `unfetched` requires `BLOCKED`. `remaining`: list of non-empty strings |

`PROMPT_READY` also requires a bar that passes the bar checks and `host.status` `DETECTED` or `OVERRIDE`. `BLOCKED` requires at least one `remaining` item; the compiler writes each as `<code>: <detail>` with code `host_unknown`, `host_conflict`, `host_invalid`, `host_mismatch`, `missing_bar`, `vague_bar`, `compound_bar`, `bad_bar`, `prompt_invalid`, or another named gap.
