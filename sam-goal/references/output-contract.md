# Output Contract

Write `<goal>/goal-report.json` with the fields marked **you**. `validate_goal_report.py --derive` overwrites the **derive** fields from the gate files, `DELEGATION.md`, and process env, rewrites the file, then validates. Without `--derive`, every field is required as written.

| Field | Source | Rule |
| --- | --- | --- |
| `schema_version`, `workflow` | derive | `1`, `"goal"` |
| `goal` | you | Non-empty text |
| `action` | you | `execute` \| `review` \| `audit` |
| `intensity` | you | `lite` \| `full` \| `ultra` |
| `mode` | you | `solo` \| `delegated`; `delegated` if and only if `units.gate` is `open` |
| `tree_depth` | you | Integer ≥ 1 |
| `goal_dir` | derive | Absolute: the report's directory. A typed `goal_dir` naming another directory is an error |
| `host` | derive | `{key, status, detected_from}` from env. A typed `OVERRIDE` with a listed `key` and `detected_from` `override:<key>` (a `detect_host.py --host` result) is kept, with the env detection added as `env`. `status`: `DETECTED` \| `OVERRIDE` \| `UNKNOWN` \| `CONFLICT` \| `INVALID`. `key`: `claude-code` \| `codex` \| `grok` for `DETECTED`/`OVERRIDE`, else `null`. `detected_from` non-empty |
| `units` | you | `{counted ≥ 1, gate: open \| closed, reason}`; `reason` is the step-3 line |
| `ladder` | you | `{rung 1-7, rationale, skipped[], new_dependencies[], authorized_dependencies[]}`; lists of non-empty strings |
| `gates` | derive | `{path (absolute), total, met, abandoned, unmet[], abandoned_ids[]}`; `met + abandoned + len(unmet) == total`; `abandoned == len(abandoned_ids)`; ids outside `GATES.md` are prefixed `<file>:` |
| `delegation` | derive | `null` in solo. Delegated: `{path (absolute), units ≥ 1, verified, pending, complete: bool}`; `verified + pending ≤ units` |
| `overbuild_review` | you | `{lean_already: bool, net_lines: int, findings: [one entry per cut]}`; `true` forbids findings, `false` needs at least one |
| `checks` | derive | `{gates: {exit_code, summary}, ledger: {exit_code, summary} \| null}`; `gates` required on `execute`; `ledger` `null` in solo |
| `evidence` | you + derive | Non-empty `[{id (unique), status, detail}]`; `status`: `PASS` \| `FAIL` \| `BLOCKED` \| `NOT_RUN` \| `INFO`. Derive replaces `gates-check` and `ledger-check` |
| `decision` | you | `{result: COMPLETE \| IN_PROGRESS \| BLOCKED, remaining[]}` |

## Invariants

- `execute` needs at least one gate; `review` and `audit` may have none.
- `COMPLETE` requires empty `decision.remaining`, empty `gates.unmet`, every `new_dependencies` entry listed in `authorized_dependencies`, and at least one `PASS` evidence item. On `execute` it also requires `checks.gates.exit_code == 0`. Delegated also requires `delegation.complete`, `delegation.verified == delegation.units`, and `checks.ledger.exit_code == 0`.
- `IN_PROGRESS` and `BLOCKED` require a non-empty `remaining` list.
