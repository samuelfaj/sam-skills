# Description Template

Write for a reader who did not implement the change. In two minutes, they must
understand why the change exists, what behavior changed, which business rules
apply, what can go wrong, and how the result was verified.

Use these sections in order. Keep each section short. Replace every instruction
with evidence-backed content or `Not applicable` / `Not verified`.

```markdown
## Description

In two to four sentences, explain the problem, the outcome, and why it matters.
Lead with behavior and value, not files or implementation details.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Other: <specific type>

## What Changed

- User-visible change: concise outcome or `None`.
- Internal change: concise implementation summary or `None`.

## Behavior

- Before: previous observable behavior.
- After: new observable behavior.
- Unchanged: important behavior intentionally preserved.

## Business Rules

- Added: new rule or `None`.
- Changed: changed rule or `None`.
- Preserved: rule that must continue to hold.
- Write rules as conditions and outcomes: “When X, the system must Y.”

## Scope and Impact

- In scope: changed components and paths, including every changed file.
- Out of scope: nearby behavior intentionally not changed.
- User impact: who is affected and how, or `None`.
- Technical impact: API, data, configuration, operations, or compatibility, or
  `None`.

## Risks and Mitigations

- Risk: concrete failure mode and affected users or systems.
- Mitigation: prevention, detection, containment, or `None`.
- Remaining risk: what is still uncertain, or `None known`.
- Use `Not verified` when evidence is unavailable.

## Rollout and Recovery

- Rollout: deployment, migration, feature flag, or `Not applicable`.
- Monitoring: signal that confirms healthy behavior, or `Not applicable`.
- Recovery: rollback or corrective action if the change fails, or `Not
  applicable`.

## Validation

- `<command>` — `PASS`, `FAIL`, or `NOT RUN`: concise result or reason.

## Tests

- Scenarios: business and technical behavior covered, or `None`.
- Added or updated: exact test paths, or `None`.
- Executed: exact commands and status, or `Not run`.

## Author Checklist

- [ ] Description explains the problem, outcome, and reason.
- [ ] Before/after behavior and business rules are explicit.
- [ ] Every changed file is represented in scope.
- [ ] Risks, mitigations, and recovery are documented.
- [ ] Tests and validation reflect commands actually run.
- [ ] No unrelated changes are included.

## Notes for Reviewer

- Review first: highest-risk rule, behavior, or file.
- Open questions: unresolved decision or `None`.
```

Mark a checkbox only when its claim has evidence. Prefer behavior and business
language over file-by-file narration. Do not add endpoint, payload, migration,
deployment, or rollback details unless the change makes them relevant. Do not
wrap the final body in a code fence.
