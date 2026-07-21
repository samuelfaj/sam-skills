# Sam Skills

Reusable agent skills for evidence-backed software delivery, testing, review,
and orchestration.

## Design Principles

- Provider-, model-, host-, and stack-neutral operating contracts.
- Exact target, intent, scope, invariants, and no-go surfaces before execution.
- Risk-calibrated proof with explicit `PASS`, `FAIL`, `BLOCKED`, and `NOT_RUN`
  states.
- Deterministic validators and adversarial harnesses for every executable
  workflow.
- Local artifacts by default. Publishing, comments, uploads, pushes, and other
  external writes require explicit user authorization.
- No invented evidence, silent scope expansion, test weakening, or unsupported
  completion claims.

## Skills

- `sam-work`: deliver a bug or feature through mandatory implementation,
  refinement, review, simplification, coverage, proposal, browser-proof, and
  published demo-video gates with fresh-head receipts.
- `sam-create-feature`: deliver a new capability from frozen requirements to
  validated behavior proof.
- `sam-fix-bug`: reproduce, diagnose, minimally repair, and regression-test
  broken existing behavior.
- `sam-refine-task`: challenge a proposed or completed approach through bounded,
  evidence-backed refinement cycles.
- `sam-simplify-task`: remove proven unnecessary complexity while preserving
  observable behavior.
- `sam-create-playwright-tests`: build risk-based browser coverage with linked
  UI/backend, route, permission, persistence, and cleanup proof.
- `sam-create-test-coverage`: select and implement the smallest reliable mix of
  unit, component, integration, contract, and browser tests.
- `sam-create-task-demo-video`: record and validate a privacy-reviewed local MP4
  tied to acceptance criteria.
- `sam-review`: review an immutable local change or remote proposal through one
  evidence-backed decision workflow; ask before publishing when no action was
  explicitly authorized.
- `sam-pr-description`: generate a traceable pull/merge-request description from
  the real base, commits, diff, and validation evidence.
- `sam-orchestrate`: coordinate complex work through capability- and risk-based
  delegation, skeptical verification, and an independent review gate.
- `sam-council`: falsify and revise consequential system-development plans
  through blind specialist reviews, cross-examination, and evidence-weighted
  decision gates.
- `sam-codex-advisor`: obtain a bounded read-only second opinion through a
  fixed-model advisor with explicit effort routing.
- `sam-fable-advisor`: obtain a bounded read-only second opinion through a
  fixed-model advisor with explicit effort routing.
- `sam-grok-worker`: delegate a bounded implementation task to a fixed worker
  runtime under workspace sandbox and headless execution.

## Repository Quality Gate

Run the complete deterministic suite from the repository root:

```bash
python3 -B scripts/validate_skill_suite.py .
python3 -B scripts/run_skill_harnesses.py
```

The first command checks package structure, metadata, resource routing,
portability, executable permissions, and forbidden operational coupling. The
second discovers and runs every skill harness, including adversarial failure
fixtures.

## Install

Install each complete `sam-*` directory through the target agent host's normal
skill-installation mechanism. Preserve the directory name and all bundled
`agents/`, `references/`, and `scripts/` resources.

After installation, restart or reload the host so it discovers the updated
skills.
