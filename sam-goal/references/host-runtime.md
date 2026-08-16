# Host Runtime

## Contents

- [Detection](#detection)
- [Invocation](#invocation)
- [Spawn](#spawn)
- [Shared](#shared)

Detect from **process environment**, never from which clients exist on disk.
Bind exactly one row. Do not mix primitives.

## Detection

`scripts/detect_host.py` inspects `SAM_GOAL_HOST` or `SAM_ACTIVE_HOST`, then
host-unique env keys.

| Host key | Process signals |
| --- | --- |
| `claude-code` | `CLAUDECODE`, `CLAUDE_CODE`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION` |
| `codex` | `CODEX_HOME`, `CODEX_THREAD_ID`, `CODEX_SANDBOX`, `CODEX_CI`, `CODEX_TASK` |
| `grok` | `GROK_AGENT`, `GROK_HOME`, `GROK_SESSION`, `GROK_SESSION_ID` |

`DETECTED` or `OVERRIDE`: use that row. `UNKNOWN` or `CONFLICT`: do not fan
out; walk briefs yourself. Never guess.

## Invocation

Same skill, three slash dialects. All bind this package.

| Host | User invoke | Notes |
| --- | --- | --- |
| `claude-code` | `/sam-goal` | Skill auto-loads from `SKILL.md` |
| `codex` | `$sam-goal` or `@sam-goal` | `agents/openai.yaml` is the interface file |
| `grok` | `/sam-goal` | Skill auto-loads from `SKILL.md` |

Scripts are `python3` stdlib only. They run on every host. Do not wrap them
in another host's plugin, hook, or package.

## Spawn

Coordinator fans out. Workers never spawn.

| Host | Primitive | Parallel | Nesting |
| --- | --- | --- | --- |
| `claude-code` | native Task / Agent tool | yes, independent units | coordinator only |
| `codex` | native agent spawn, fresh thread | yes, independent units | no. `max_depth` is 1 |
| `grok` | native `spawn_subagent` | yes, independent units | no. children do not spawn children |

Each worker brief is the contract plus that unit's gates. Never the parent
transcript. Never another host's scheduler, `/loop`, `ultracode`, or workflow
dialect.

If the bound primitive is missing, walk the briefs yourself. A sequential
ledger still counts. Inventing another host's spawn does not.

## Shared

- Isolation is git worktrees or disjoint files, not a host feature.
- Verification is `check_gates.py` / `check_ledger.py` in this package.
- Record `host.key`, `host.status`, and `host.detected_from` in the report.
