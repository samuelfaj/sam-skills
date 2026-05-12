# Sam Skills

Personal Codex skills.

## Skills

- `sam-create-playwright-tests`: map impacted flows, create comprehensive Playwright E2E coverage, record local videos, and attach PR evidence.
- `sam-create-task-demo-video`: create human-paced task demo videos, convert them to `.mp4`, verify playback, upload them, and comment on the GitHub PR or GitLab MR by default.
- `sam-create-test-coverage`: create exhaustive risk-based unit, component, integration, API/contract, and E2E coverage for backend or frontend changes.
- `sam-create-feature`: autonomous feature workflow with requirements discovery, TDD implementation, validation, and PR evidence.
- `sam-fix-bug`: autonomous bugfix workflow with failing tests first, local analysis notes, minimal implementation, validation, and PR evidence.
- `sam-refine-task`: stress-test a strategy, find loopholes, apply proper fixes, and loop until confidence is factual.
- `sam-simplify-task`: review completed work, remove unnecessary complexity, and prove behavior stayed correct.
- `sam-review-code`: rigorous local code review for current workspace changes, returned in Codex without PR/MR comments.
- `sam-review-pr`: rigorous end-to-end GitHub/GitLab PR or MR review with published platform comments.

## Install

Install every skill in this repo:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo samuelfaj/sam-skills \
  --path \
    sam-create-playwright-tests \
    sam-create-task-demo-video \
    sam-create-test-coverage \
    sam-create-feature \
    sam-fix-bug \
    sam-refine-task \
    sam-simplify-task \
    sam-review-code \
    sam-review-pr
```

Restart Codex after installing or updating skills.
