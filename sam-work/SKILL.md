---
name: sam-work
description: "Implement and deliver a software change as a pull or merge request with proportionate verification. Use when the user invokes /sam-work or explicitly asks for PR/MR delivery."
---

# Sam Work

Deliver the requested change to a reviewable PR/MR. This is a delivery guide, not a fixed sequence of eight child workflows.

## Non-Negotiable Contract

- Inspect the repository, request, and relevant code before editing. Define the outcome, acceptance criteria, base, task branch, and unrelated dirty work. Preserve user work.
- A request to use sam-work for PR/MR delivery authorizes task-owned commits, push, and one proposal. It does not authorize merge, deployment, production data changes, unrelated comments, or irreversible cleanup.
- Redact secrets and private data from evidence; verify the target environment before mutating checks.
- Verify claims against the current code and remote head. Do not treat a child report, stale test, CI result, or uploaded media as proof of behavior it did not exercise.
- When another delivery skill is the controller, contribute only the PR/MR steps it needs; reuse its implementation and verification evidence instead of starting another pipeline.
- In Distill, let configured Jev routing help with eligible skill, tool, model, and effort choices. Keep delegated briefs narrow and unpinned unless the user or an observed constraint requires a specific runtime. If Jev is absent, disabled, fails, or defers, use the current agent and host defaults to choose the next step; continue the PR/MR workflow. Verify behavior, CI, and remote state directly in either case.

## Deliver

1. Diagnose a bug or trace a feature's relevant path. Make the smallest task-owned change on the existing task branch or an isolated branch that preserves unrelated work. Choose specialized implementation or review skills only where they add useful evidence.
2. Run relevant existing tests and the smallest additional checks needed for the acceptance criteria and risk. Add regression coverage when meaningful behavior otherwise lacks protection. For a web or device change, exercise the affected interaction when feasible. A video is required only if the user requests one or it is necessary evidence for the stated outcome.
3. Review the diff for scope, correctness, and missing failure paths. Correct material in-scope findings and re-run checks affected by the correction. Do not repeatedly re-run an unchanged review or revalidate unrelated phases.
4. Prepare the proposal from the final diff and actual check results; commit and push only intended paths. Create or update the one PR/MR, then read back its URL, remote head, body, and required CI state. If the request requires all checks green or review approval, wait a practical bounded interval and report any outstanding external gate accurately.

## Unblocking and stopping

Diagnose failed tests, tooling, authentication, CI, and publication separately. Try a distinct safe route when it can still reach the same acceptance criteria. Keep prior valid evidence and the task branch; retry only after a meaningful change or new hypothesis. Continue independent work while an external gate waits. If a required access, owner decision, service, or reviewer action cannot be supplied by this run, identify the exact blocker and leave the completed proposal reviewable. Do not call the requested delivery complete if its required evidence is missing.

## Return

Report the change, relevant checks with their results, proposal URL and remote head when published, and any exact pending or blocked gate. No fixed phase count, media inventory, or machine report is required for an ordinary PR/MR.

## Legacy report tools

For an existing eight-phase report, `references/output-contract.md` explains its historical contract; `scripts/scaffold_work_report.py` and `scripts/validate_work_report.py` rebuild and validate that report. Its fixed requirements, including published media, do not define default PR/MR completion.
