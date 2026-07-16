# Description Template

Use these sections in order. Replace every instruction with evidence-backed
content or `Not applicable` / `Not verified`.

```markdown
## Description

One short paragraph explaining the outcome and reason.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Other: <specific type>

## Scope

- `<module or path>` — concrete change.

## Behavior and Business Rules

- Expected behavior or `Not applicable`.

## What Was Done

1. Concrete implementation step.

## Architecture and Trade-offs

- Architecture: `None` or supported change.
- Trade-offs: supported decision or `Not applicable`.

## Safety and Risks

- Verified compatibility, recovery, rollout, or risk facts.
- Use `Not verified` when proof is unavailable.

## Validation

- `<command>` — `PASS`, `FAIL`, or `NOT RUN`: reason.

## Tests

- Added or updated: exact paths/scenarios, or `None`.
- Executed: exact commands/status, or `Not run`.

## Author Checklist

- [ ] Scope matches the proposal.
- [ ] Required validation passed.
- [ ] Risks and limitations are documented.
- [ ] No unrelated changes are included.

## Notes for Reviewer

- Highest-value review focus, open question, or `None`.
```

Mark a checkbox only when its claim has evidence. Do not add endpoint, payload,
migration, deployment, or rollback fields unless the change makes them relevant.
Do not wrap the final body in a code fence.
