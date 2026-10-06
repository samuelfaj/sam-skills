# Sam Skills

Reusable agent skills for evidence-backed software delivery, testing, review,
and orchestration.

## Design Principles

- Provider-, model-, host-, and stack-neutral operating contracts.
- Understand the requested outcome, scope, and observable success before editing.
- Select verification by behavior and risk. A test, CI result, remote artifact,
  and live behavior establish different things.
- Specialized report validators and adversarial harnesses remain available
  when a structured audit is requested; ordinary delivery does not require
  their fixed phase counts or artifacts.
- External writes require authorization from the request or prior session.
- No invented evidence, silent scope expansion, test weakening, or unsupported
  completion claims.
- One controller per task. Reuse completed work and evidence instead of
  stacking delivery pipelines. Diagnose a blocker and try a distinct viable
  route; stop repeating attempts that have no new evidence.

## Evidence

Use existing checks first and add focused coverage when needed. Recheck proof
affected by a later edit. For an explicitly requested structured audit, each
skill routes to its own scaffold, receipt validator, and harness. A machine
receipt validates the reported evidence; it does not substitute for observing
the requested behavior.

## Skills

- `sam-task`: complete a software task locally or, with `--deliver pr`, through
  a reviewable PR/MR with accurate remote readback. Frontend work always goes
  through `sam-design`.
- `sam-goal`: finish a broader software goal with adaptive decomposition,
  minimal implementation, and integrated verification.
  Invoke as `/sam-goal`, `$sam-goal`, or `@sam-goal`.
- `sam-pivot`: replan autonomously around blocked methods or stale plans while
  building the best working version of a requested product. Explicit invocation
  only: `/sam-pivot`, `$sam-pivot`, or `@sam-pivot`.
- `sam-create-feature`: deliver a new capability from frozen requirements to
  validated behavior proof.
- `sam-fix-bug`: reproduce, diagnose, minimally repair, and regression-test
  broken existing behavior.
- `sam-simplify-task`: remove proven unnecessary complexity while preserving
  observable behavior.
- `sam-perceived-performance`: make a requested interaction feel instantaneous
  while the real work continues, under measured feedback and dead-time budgets,
  proven rollback for every optimistic outcome, and a hard ban on faked progress,
  success, or freshness.
- `sam-test`: select and implement the smallest reliable mix of unit,
  component, integration, contract, and browser tests; `--layer` picks the
  layer, including risk-based browser coverage with linked UI/backend, route,
  permission, persistence, and cleanup proof.
- `sam-create-task-demo-video`: record and validate a privacy-reviewed local MP4
  tied to acceptance criteria; only when authorized, publish it and verify its
  player embed from the proposal body markup read back through the API.
- `sam-review`: review an immutable local change or remote proposal through one
  evidence-backed decision workflow, re-reviewing corrections as a delta when
  safe; ask before publishing when no action was explicitly authorized.
- `sam-pr-description`: generate a traceable pull/merge-request description from
  the real base, commits, diff, and validation evidence.
- `sam-plan`: conduct task study and emit a machine freeze plan (goal, thesis,
  steps, evidence, status) plus a required light-theme HTML pack for humans;
  assertive investigation first, council only on risk triggers.
- `sam-council`: rapidly triage or fully falsify consequential
  system-development plans through portable blind reviews, bounded responses,
  maximum safe parallelism, and evidence-weighted decision gates;
  `--mode decide|refine` either decides between options or challenges a
  proposed or completed approach through bounded, evidence-backed refinement
  cycles. Multi-provider confrontation remains explicit opt-in.
- `sam-advisor`: obtain a bounded read-only second opinion;
  `--advisor codex|claude [model] [effort]` selects the advisor runtime, model,
  and effort.
- `sam-orchestrate`: coordinate independent work with native delegation by
  default, optional Jev routing in Distill, and verified integration. Presets
  `codex-grok`, `codex-glmflash`, and `claude-grok` select a hybrid
  controller/worker profile; custom `--controller`, `--worker`, and
  `--reviewer` build any other combination.
- `sam-gauntlet-loop`: compile a named, fetchable quality-bar prompt with
  host-detected orchestration tokens and return it for the user to copy,
  edit, and paste. Never starts the loop. Use for `/sam-gauntlet-loop`,
  "gauntlet this", or "loop until it beats a real reference".
- `sam-design`: route frontend and UI design work through all 21 skills from
  `emilkowalski/skills` and `nextlevelbuilder/ui-ux-pro-max-skill`, tracked in a
  coverage ledger; install them with `scripts/install_design_skills.py`.

### Renamed skills

| Old name | New name |
| --- | --- |
| `sam-work` | `sam-task` (`--deliver pr`) |
| `sam-refine-task` | `sam-council --mode refine` |
| `sam-create-test-coverage` | `sam-test` |
| `sam-create-playwright-tests` | `sam-test --layer` |
| `sam-codex-advisor` | `sam-advisor --advisor codex` |
| `sam-claude-advisor` | `sam-advisor --advisor claude` |
| `sam-grok-worker` | `sam-orchestrate` (worker runbook) |
| `sam-orchestrate-codex-grok` | `sam-orchestrate` preset `codex-grok` |
| `sam-orchestrate-codex-glmflash` | `sam-orchestrate` preset `codex-glmflash` |
| `sam-orchestrate-claude-grok` | `sam-orchestrate` preset `claude-grok` |

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

`sam-task` also ships a provider-neutral evaluation pack for its historical
structured receipts. It does not yet measure the adaptive default. Run it
manually or periodically; unavailable host metrics remain `null`.

## Install

Install each complete `sam-*` directory through the target host's skill
mechanism (`~/.grok/skills/` for Distill). Preserve the directory name and all
bundled `agents/`, `references/`, and `scripts/` resources. Structured reports need
their bundled checkers and validators; the adaptive default does not.

`sam-goal` uses the host's skill dialect (`/sam-goal`, `$sam-goal`, or
`@sam-goal`). For optional structured delegation, `SAM_GOAL_HOST` or
`SAM_ACTIVE_HOST` can override an unknown or conflicting host detection.

After installation, restart or reload the host so it discovers the updated
skills.

In Distill, its configured Jev path can shortlist skills and tools and route
eligible model and effort decisions. The adaptive delivery skills leave these
choices to the host when available. Without Jev, they continue with the current
agent and host defaults. Jev supplies typed suggestions; source
inspection and behavior checks remain the evidence for completion. The
[TypeSafe agent skill](https://github.com/typesafe-ai/skills) teaches agents to
build applications with Jev; it does not replace Distill's execution model.
