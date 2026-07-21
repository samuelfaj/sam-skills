# Worker Prompt Contract

Every worker prompt must include these semantic fields. The active conversation
style may change their formatting, but not their meaning.

```text
State: current task-local facts and dependency state
Objective: one bounded outcome
Ownership: exact writable paths or read-only surface
Runtime: host, role, model, effort (from host-runtime-matrix; do not rechoose)
No-go: forbidden paths, mutations, and unrelated cleanup
Dependencies: task IDs that are already satisfied
Actions: required work in execution order
Proof: exact artifacts, tests, commands, or observations required
Output: result, changed files, proof, skipped proof, blockers, runtime used
Coordination: other agents may share the workspace; never revert their work
```

Prompt rules:

- Pass exact paths and immutable refs when available.
- Pass the pre-bound runtime; the worker must not self-select another model.
- State assumptions and unresolved ambiguity.
- Require the worker to inspect before editing.
- Require repository conventions and surgical changes.
- Separate proof performed by the worker from proof that the controller must
  rerun.
- Never include secrets, hidden context, or another reviewer's expected answer.
- Never ask the worker to expand scope without returning to the controller.

For an independent reviewer, provide the request, frozen scope, combined
artifact or diff, and available proof. Do not provide the intended verdict or a
list of suspected findings.
