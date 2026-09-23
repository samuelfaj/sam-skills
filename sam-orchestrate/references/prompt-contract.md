# Worker Prompt Contract

## Prompt

Keep each prompt ≤ 40 lines and slice-only, written to a file in the run
directory, with these fields:

```text
State: 3-6 task-local facts (no transcript)
Objective: one bounded outcome
Ownership: exact writable paths or read-only surface
Runtime: host, role, model, effort (matrix-bound; worker must not rechoose)
No-go: forbidden paths, mutations, unrelated cleanup
Dependencies: completed task IDs only
Actions: ordered steps
Proof: exact commands/artifacts (prefer one focused check)
Output: at most 15 lines: result, changed paths, each proof command with exit code, skipped proof, blockers, runtime used; never paste diffs or logs
Coordination: other agents may share the workspace; never revert their work
```

- Pass exact paths, immutable refs, and diff files; never paste file bodies or diffs.
- Never include SKILL.md, references, other workers' reports, secrets, hidden
  context, or a reviewer's expected answer.
- State assumptions and residual ambiguity in one short bullet list.
- Require inspect-before-edit and surgical changes matching repo conventions.
- Separate proof the worker runs from proof the controller must re-check.
- Scope expansion always returns to the controller.

## Spawn

Use `<run>` from SKILL.md §1. Redirect CLI output to files and read only the
final message:

| CLI | Redirect | Read |
| --- | --- | --- |
| Codex | `codex exec ... -o <run>/<node>.last.md - < <run>/<node>.prompt.md > <run>/<node>.log 2>&1` | `<node>.last.md` |
| Claude Code | `claude -p --output-format json ... < <run>/<node>.prompt.md > <run>/<node>.json` | `.result` |
| Grok | `... --output-format json > <run>/<node>.json 2> <run>/<node>.err` | `.text` |

Only read-only REVIEWER/advisor `claude -p` seats add `--add-dir <run>`.
Read at most the last 60 log/stderr lines, only on a non-zero exit. Keep prompt
and log files until the report validates, then delete them; keep the report.

## Reviewer prompts

Write the diff with
`python3 <skill-dir>/scripts/scaffold_report.py --freeze <run>/freeze.json --diff-out <run>/review-<n>.diff`
and keep its printed `tree=` id. Without `--since`, its `from=` must equal the
FROZE `tree=` id, else stop with an `ENVIRONMENT` blocker. Provide only: frozen
goal and constraints; that diff file or artifact paths; the changed-file
manifest; proof IDs and status; a risk checklist. Never the intended verdict,
suspected findings, or other workers' conclusions; no full-repo re-read unless
`T3` risk demands it.

Round 2+: add `--since <previous round's tree id>` so the diff holds only the
correction delta, and pass every open finding ID. Omit `--since` (full change)
when the delta touches public contracts/APIs/schemas, auth/security/permissions,
persistence/migrations, shared modules used outside the change, or risk-flagged
paths, or is larger than the original change (compare the printed `lines=`). A
prior finding is closed only when the reviewer names it closed.
