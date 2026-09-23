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
- Grok workers: on capability failure, return evidence to the controller; never
  self-escalate to Opus.

## Spawn

Use `<run>` from SKILL.md §1.

- **Grok:** per worker run the `sam-grok-worker` resolver
  (`python3 -B <sam-grok-worker-dir>/scripts/resolve_worker.py --effort <§3 effort> --prompt-file <abs prompt>`),
  then run its `command` argv unchanged with stdout to `<run>/<node>.json` and
  stderr to `<run>/<node>.err`; read only the JSON `.text`.
- **Claude REVIEWER / genius / advisor:** as a Claude Code subagent, or
  `claude -p --output-format json ... < <run>/<node>.prompt.md > <run>/<node>.json`
  reading only `.result`; only the REVIEWER and advisor add `--add-dir <run>`.
  The REVIEWER is read-only / plan mode. These seats can nest, so
  their prompts add `Nested agents: pass RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1 and its capability/lane environment unchanged; never put content into it`.

Read at most the last 60 stderr/log lines, only on a non-zero exit. Keep prompt
and log files until the report validates, then delete them; keep the report.

## Reviewer prompts (Claude opus high)

Write the diff with
`python3 <skill-dir>/scripts/scaffold_report.py --freeze <run>/freeze.json --diff-out <run>/review-<n>.diff`
and keep its printed `tree=` id. Without `--since`, its `from=` must equal the
FROZE `tree=` id, else stop with an `ENVIRONMENT` blocker. Provide only: frozen
goal and constraints; that diff file or artifact paths; the changed-file
manifest; proof IDs and status; a risk checklist. Never the intended verdict,
suspected findings, or other workers' conclusions.

Round 2+: add `--since <previous round's tree id>` so the diff holds only the
correction delta, and pass every open finding ID. Omit `--since` (full change)
when the delta touches public contracts/APIs/schemas, auth/security/permissions,
persistence/migrations, shared modules used outside the change, or risk-flagged
paths, or is larger than the original change (compare the printed `lines=`). A
prior finding is closed only when the reviewer names it closed.

## Genius prompts (Claude opus xhigh)

Only after the controller records an escalation trigger. Include the prior
attempt count and failed proof IDs, the exact residual failure (not prior
transcripts), and the frozen writable scope and no-go, unchanged from the last
producer.

## Advisor prompts (Claude opus max)

Read-only focused question only; never implementation ownership.
