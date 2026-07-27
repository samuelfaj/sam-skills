# Worker Prompt Contract

Every worker prompt must include these semantic fields. Keep the whole prompt
**short** (target ≤ 40 lines). Pass only the slice the worker needs.

```text
State: 3–6 task-local facts (no full transcript)
Objective: one bounded outcome
Ownership: exact writable paths or read-only surface
Runtime: host, role, model, effort (matrix-bound; do not rechoose)
No-go: forbidden paths, mutations, unrelated cleanup
Dependencies: completed task IDs only
Actions: ordered steps
Proof: exact commands/artifacts (prefer one focused check)
Output: result, changed files, proof, skipped proof, blockers, runtime used
Coordination: other agents may share the workspace; never revert their work
```

## Slice-only rules

- Pass exact paths and immutable refs when available.
- Pass the pre-bound runtime; the worker must not self-select another model or host.
- Do **not** paste SKILL.md, the full routing policy, or other workers’ reports.
- Do **not** include secrets, hidden context, or a reviewer’s expected answer.
- State assumptions and residual ambiguity in one short bullet list.
- Require inspect-before-edit and surgical changes matching repo conventions.
- Separate proof the worker runs from proof the controller must re-check.
- Never ask the worker to expand scope without returning to the controller.
- Prefer proof: scope diff + one focused command. Summarize logs; never dump them.
- Repeat the host’s distill / token-saver rules for any nested workers; never
  assume inheritance.

## Grok workers

- Effort must match the matrix (`medium` for LIGHT, `high` for STANDARD/DEEP).
- Invoke through the Grok worker path with absolute prompt file.
- On capability failure, return evidence to the controller; do not self-escalate
  to Sol.

## Reviewer prompts (Codex Sol medium)

Provide only:

1. Frozen goal + constraints.
2. Combined diff or artifact paths.
3. Changed-file manifest.
4. Available proof IDs/status.
5. Checklist of risks to inspect.

Do **not** provide intended verdict, suspected findings, or other workers’
conclusions. Reviewer stays read-only.

## Genius prompts (Codex Sol high)

Only after controller records an escalation trigger. Include:

- Prior attempt count and failed proof IDs.
- Exact residual failure (not full prior transcripts).
- Frozen writable scope and no-go (unchanged from last producer).
