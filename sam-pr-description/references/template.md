# Description Template

Use the repository's proposal template when present. Otherwise start with:

```markdown
## Description

Explain the concrete problem and resulting behavior in one or two sentences.

## Validation

List the relevant checks actually run and their results, or state what was
not verified and why.
```

Add sections only when the change needs them: business rules, compatibility,
migrations, rollout/recovery, material risks, or reviewer focus. Omit empty
sections and checklist boilerplate. Scale detail to the actual change.

Keep complete file coverage and evidence IDs in the structured report. The
published body should explain behavior; it need not enumerate every file or
repeat the report's technical ledger. Keep the Description and Validation
headings for report validation, and map each changed file to the section that
explains its effect. Follow any additional repository template requirements.

Do not invent evidence, fill sections with placeholders, or wrap the final
body in a code fence.
