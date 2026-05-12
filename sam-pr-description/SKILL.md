---
name: sam-pr-description
description: Create a standardized English GitHub PR or GitLab MR description for the current branch, based on branch commits, diff stats, changed files, tests, safety, and business rules.
---

# Sam PR Description

Use this skill when opening, updating, or rewriting a GitHub pull request or GitLab merge request description, or when the user asks for a standardized PR/MR body.

## Goal

Generate a concise English PR/MR description for the current branch.

Default target branch is `main`. If the user or platform context provides a different target branch, use that target.

## Steps

1. Identify target branch:
   - Prefer explicit user-provided target branch.
   - Else use platform PR/MR target branch if available.
   - Else use `main`.
2. Run `git log <target>..HEAD --oneline` to list commits on this branch.
3. Run `git diff <target>...HEAD --stat` to identify files and modules changed.
4. Read relevant changed files to understand scope, intent, tests, architecture, safety, and business rules.
5. If available, inspect linked ticket IDs, PR/MR references, commit messages, and test output.
6. Fill the template below in English.

## Output Contract

- Output ONLY the filled-in template.
- Wrap output in a single markdown code block using ` ```markdown `.
- No prose before or after the code block.
- Keep content concise and reviewer-focused.
- Do not invent tickets, endpoints, payloads, tests, or safety claims.
- If a section lacks evidence, write `Not applicable` or `Not verified` instead of guessing.
- Check the appropriate `Type of Change` box(es) based on what actually changed.

## Template

```markdown
## Description
<!-- Brief summary of what was done and why -->

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Other: ___________

## Scope (Files Changed)
<!-- List the files/modules that SHOULD be changed by this PR/MR -->

## How to Test
- Affected endpoint(s):
- Example payload: {}
- Expected response:
- Error cases to validate:

## What Was Done
<!-- Step-by-step summary of how this was implemented, to guide the reviewer -->
1.
2.
3.

## Architecture Changes
<!-- Describe any structural/architectural changes introduced (new layers, patterns, models, etc.) -->

## Trade-offs
<!-- What alternatives were considered? What did you give up, and why was this the right call? -->

## Why It's Safe
<!-- Explain why this change is safe to merge: backward compatibility, no data loss risk, isolated impact, etc. -->

## System Expected Logic
<!-- Describe the expected behavior end-to-end after this change is live -->

## Business Rules
<!-- List any business rules this change enforces or depends on -->

## Tests
<!-- Describe or link tests added/updated in this PR/MR -->

## Author Checklist
- [ ] Code follows project guidelines
- [ ] Tests were added/updated
- [ ] Changes are within defined scope
- [ ] No commented code or debug logs
- [ ] PR/MR is within size limits

## Notes for Reviewer
<!-- Points of attention, decisions made, open questions -->
```

## Fill Rules

- Write everything in English.
- Use PR or MR wording based on the platform when known; otherwise use `PR/MR`.
- Fill `Scope (Files Changed)` from `git diff <target>...HEAD --stat`, grouped by module when useful.
- For `How to Test`, include affected endpoints, real example payloads, expected responses, and edge/error cases only when evidence exists.
- Link Linear tickets, GitHub issues, GitLab issues, or related PRs/MRs when present in commits, branch names, or user context.
- Keep `Description` to one short paragraph.
- Keep `What Was Done` to concrete implementation steps, not generic process.
- `Architecture Changes` must say `None` when no structural change exists.
- `Trade-offs` must name real alternatives only when evidence exists; otherwise write `Not applicable`.
- `Why It's Safe` must mention only verified safety properties.
- `Tests` must distinguish added/updated tests from commands run manually.
- Do not leave HTML comments in the final output.
