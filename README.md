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
- One top delivery method per turn. If several of `sam-goal`, `sam-task`,
  `sam-work`, and `sam-orchestrate` are named, run only the highest-precedence
  winner (`sam-goal` > `sam-task` > `sam-work` > `sam-orchestrate`). Failures
  fix forward on the same branch; they do not restart from a moving base.

## Shared Mechanisms

- **Child mode.** Under a parent (`sam-task`, `sam-work`, `sam-orchestrate`,
  `sam-goal`, or a phase worker) a skill never asks and ends with a six-line
  `RESULT <skill> <TERMINAL>` block: report path, the validator's last line,
  head and fingerprint, and at most ten open items. Standalone runs answer in
  15 lines or fewer plus the report path, never the JSON report.
  Implementation children leave review, coverage, and browser proof to the
  parent's own phases.
- **Phase isolation.** `sam-task` and `sam-work` dispatch each phase to a fresh
  worker, or run it inline when the host has no subagents. Phases run one at a
  time, every run writes to its own directory, and the controller re-runs the
  child validator for its receipt instead of reading the worker transcript.
- **Reuse and delta review.** Identical input reuses a prior valid report after
  re-running only its validator. Carrying proof to a new head needs a
  mechanical check that the phase's inputs did not change, such as a test-only
  delta. `sam-review` re-reviews corrections as a delta against a valid base
  review, and runs a full review when the delta touches contracts, security,
  persistence, shared modules, or risk paths, or outgrows the original change.
- **Scaffolds.** Skills with large reports ship a scaffold that fills hashes,
  heads, fingerprints, receipts, file coverage, and fail-closed placeholders
  from real files. Validators recompute derived fields where cheap and reject
  typed values that disagree.
- **Compact script output.** Captures and builders print a one-line summary
  (`--out` writes the full bundle and patch). `run_checked.py` prints one JSON
  line and, on failure, a capped, best-effort redacted log tail. Validators
  print `VALID`/`PASS` or error lines, and reports are fixed in place from
  those lines.

## Skills

- `sam-work`: deliver a bug or feature through mandatory implementation,
  refinement, review, simplification, coverage, proposal, browser-proof, and
  published demo-video gates with fresh-head receipts.
- `sam-goal`: finish a software goal completely with the smallest correct
  change. Write checkable gates first, split independent units onto workers
  when the unit gate opens, verify every unit yourself, and add no new
  dependency. Stdlib-only checkers, host-detected spawn, no other skill.
  Invoke as `/sam-goal`, `$sam-goal`, or `@sam-goal`.
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
  tied to acceptance criteria; only when authorized, publish it and verify its
  player embed from the proposal body markup read back through the API.
- `sam-review`: review an immutable local change or remote proposal through one
  evidence-backed decision workflow, re-reviewing corrections as a delta when
  safe; ask before publishing when no action was explicitly authorized.
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
- `sam-orchestrate-codex-glmflash`: controller with GLM-5.3-Flash producers via
  the configured Z.AI provider, independent Sol medium review,
  and Sol high only for stall or multi-round unstick.
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
portability, executable permissions, byte-identical shared copies, and
forbidden operational coupling. The second discovers and runs every skill
harness, including adversarial failure fixtures, and prints only failures plus
a summary line (`--verbose` lists every harness).

`sam-task` also ships a provider-neutral behavioral evaluation pack with twelve
versioned scenarios. Run it manually or periodically to compare real task
outcomes, false completions, corrections, latency, token use, and cost across
skill revisions; unavailable host metrics remain `null`.

## Install

Install each complete `sam-*` directory through the target agent host's normal
skill-installation mechanism. Preserve the directory name and all bundled
`agents/`, `references/`, and `scripts/` resources. A host-specific subset of
the tree will fail closed: the checkers and report validator live in
`scripts/` and are part of the contract.

`sam-goal` uses the host's skill dialect (`/sam-goal`, `$sam-goal`, or
`@sam-goal`). Override the bound host with `SAM_GOAL_HOST` or
`SAM_ACTIVE_HOST` when process detection is `UNKNOWN` or `CONFLICT`.

After installation, restart or reload the host so it discovers the updated
skills.
