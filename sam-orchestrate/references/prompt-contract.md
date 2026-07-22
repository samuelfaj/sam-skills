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
- Pass the pre-bound runtime; the worker must not self-select another model.
- Do **not** paste SKILL.md, the full routing policy, or other workers’ reports.
- Do **not** include secrets, hidden context, or a reviewer’s expected answer.
- State assumptions and residual ambiguity in one short bullet list.
- Require inspect-before-edit and surgical changes matching repo conventions.
- Separate proof the worker runs from proof the controller must re-check.
- Never ask the worker to expand scope without returning to the controller.
- Prefer proof: scope diff + one focused command. Summarize logs; never dump them.

## Reviewer prompts

Provide only:

1. Frozen goal + constraints.
2. Combined diff or artifact paths.
3. Changed-file manifest.
4. Available proof IDs/status.
5. Checklist of risks to inspect.

Do **not** provide intended verdict, suspected findings, or other workers’
conclusions. Reviewer stays read-only.
