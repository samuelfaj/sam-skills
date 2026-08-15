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
- Test results are execution receipts, not claims. Validation commands run
  through `run_checked.py`, which captures argv, per-run exit codes, and output
  hashes; report validators recompute those hashes, reject a status that
  disagrees with its receipt, and refuse to close a gate on a flaky run or on a
  test the runner never discovers.
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
- `sam-perceived-performance`: make a requested interaction feel instantaneous
  while the real work continues, under measured feedback and dead-time budgets,
  proven rollback for every optimistic outcome, and a hard ban on faked progress,
  success, or freshness.
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
- `sam-gauntlet-loop`: compile a named, fetchable quality-bar prompt with
  host-detected orchestration tokens and return it for the user to copy,
  edit, and paste. Never starts the loop. Use for `/sam-gauntlet-loop`,
  "gauntlet this", or "loop until it beats a real reference".
- `sam-orchestrate-codex-grok`: hybrid controller/worker orchestration profile —
  Grok 4.6 producers (medium LIGHT / high STANDARD / xhigh DEEP), Sol medium
  independent review, and Sol high only for stall or multi-round unstick.
- `sam-orchestrate-claude-grok`: hybrid controller/worker orchestration profile —
  Grok 4.6 producers (medium LIGHT / high STANDARD / xhigh DEEP), high independent
  review, xhigh only for stall or multi-round unstick, max-effort advisor.
- `sam-plan`: conduct task study and emit a machine freeze plan (goal, thesis,
  steps, evidence, status) plus a required light-theme HTML pack for humans;
  assertive investigation first, council only on risk triggers.
- `sam-task`: run plan → refine → `sam-work` delivery, a closure loop of
  `sam-review` plus `sam-council`, and a proposal-only learning audit that
  captures evidence-backed reusable rules without mutating durable memory.
- `sam-council`: rapidly triage or fully falsify consequential
  system-development plans through portable blind reviews, bounded responses,
  maximum safe parallelism, and evidence-weighted decision gates;
  multi-provider confrontation remains explicit opt-in.
- `sam-codex-advisor`: obtain a bounded read-only second opinion; the calling
  agent binds model and effort from the sam-orchestrate host-runtime-matrix
  advisor row (or an explicit user override).
- `sam-claude-advisor`: obtain a bounded read-only second opinion; the calling
  agent binds model and effort from the sam-orchestrate host-runtime-matrix
  advisor row (or an explicit user override).
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

`sam-task` also ships a provider-neutral behavioral evaluation pack with twelve
versioned scenarios. Run it manually or periodically to compare real task
outcomes, false completions, corrections, latency, token use, and cost across
skill revisions; unavailable host metrics remain `null`.

## Install

Install each complete `sam-*` directory through the target agent host's normal
skill-installation mechanism. Preserve the directory name and all bundled
`agents/`, `references/`, and `scripts/` resources.

After installation, restart or reload the host so it discovers the updated
skills.
