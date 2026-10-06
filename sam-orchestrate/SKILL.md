---
name: sam-orchestrate
description: "Coordinate independent software work with native delegation, clear ownership, and verified integration; optionally pin controller, worker, and reviewer models via a preset or flags. Use when the user explicitly requests orchestration or parallel agents."
---

# Sam Orchestrate

Finish the requested outcome with the fewest useful workers. Start with one execution thread; delegate only independent work that will save more time than briefing, integration, and verification cost.

## Non-Negotiable Contract

- Exclusive top pipeline: when the request names sam-goal or sam-task, that skill controls delivery. Contribute delegation only where it helps; do not run a second complete workflow.
- Inspect the repository and user constraints before splitting work. Preserve unrelated changes, assign one owner per writable path, and keep dependent writes ordered or isolated.
- Give each worker a bounded objective, relevant facts, writable scope, no-go scope, and observable proof. Workers must not overwrite other active work. Reuse their findings and check material claims against the actual artifacts.
- Use the current host's native subagents and default runtime when available. In Distill, leave model and effort unpinned so configured Jev can route eligible choices. If Jev is absent, disabled, fails, or defers, continue with the current agent and host defaults. Pin only for an explicit user choice or a demonstrated task constraint.
- Jev's typed judgments are advisory. The controller owns authorization, acceptance criteria, integration, and verification. Confirm the final behavior with the cheapest reliable checks for its risk; distinguish local tests, CI, publication, and live behavior.
- Pass an existing `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` to a controlled child unchanged when the native path requires it. Never reconstruct or widen it, pass secrets or full transcripts in it, or claim savings without measured accepted-task evidence.

## Execute

1. Identify the smallest set of independent units. Work directly when delegation adds overhead or native subagents are unavailable. For parallel writes, use disjoint paths or isolated worktrees and one integration owner.
2. Launch only useful workers through the current host. Use a separate reviewer when risk or an unresolved finding warrants independent review. Leave model and effort unset when host routing is available. Keep prompts short and source-backed.
3. Integrate results, inspect the actual diff, and rerun only checks affected by integration or later corrections. Challenge unsupported worker claims and fix material in-scope defects. Review depth follows risk, not a fixed round count.
4. Reach the user's requested delivery point and report the exact remaining external gate, if any. Do not infer completion from a child report or a validator alone.

## Unblocking

Fix forward on the current work and evidence. Diagnose whether a failure comes from code, environment, access, or an unmade decision; try a materially different safe route. Repeating the same failed spawn, check, or review without new evidence is not progress. Continue independent work while one dependency waits. Ask for a user decision only when it is genuinely required after inspecting what can be resolved locally.

## Return

State the integrated change, the checks that verify it, and the exact pending or blocked requirement. An ordinary run needs no fixed DAG, model matrix, review count, or JSON report.

## Choosing models

Read this section only when the user names models. Otherwise run the native flow above.

| Form | Invocation | Behavior |
| --- | --- | --- |
| Native (default) | no argument | Host-native subagents; in Distill, Jev routes; nothing pinned. |
| Preset | `/sam-orchestrate <preset>` | Read `references/profiles/<preset>.md` and run the pinned pipeline below. Presets: `codex-grok`, `codex-glmflash`, `claude-grok`. |
| Custom | `--controller <host> --worker <model[:effort]> --reviewer <model[:effort]>` | Overrides the same fields of a preset, or pins those seats alone. Fields not given fall back to the preset, else to native routing. |

Profile files: `references/profiles/codex-grok.md`, `references/profiles/codex-glmflash.md`, `references/profiles/claude-grok.md`. Profiles with Grok workers also point to `references/workers/grok.md`, which runs `scripts/resolve_worker.py`. Profile files are read only when a preset or custom pin is given. Never ask the user which model to pick; pin only what was named. A custom pin outside a preset's table is recorded through `runtime.fallback_reason`; `scripts/validate_orchestration.py` checks it only against `--profile native`.

## Pinned pipeline

Applies only after a preset or custom pin. The profile file supplies controller, worker, reviewer, genius, and advisor bindings per tier, spawn forms, and provider setup.

- Stay controller-only: delegate production code, tests, docs, migrations, and other task artifacts. The main thread only integrates, re-runs proof, reconciles conflicts, and reports.
- Bind model and effort only from the profile table; never put model or host names in owner IDs.
- Cheap-first: open on `LIGHT` or `STANDARD`; never open on `DEEP` or the genius row. Escalate only after concrete capability failure, stall, or new risk evidence, per `references/routing-policy.md`.
- If a pinned CLI or its auth is unavailable, stop with an evidence-backed `EXTERNAL`/`ENVIRONMENT` blocker; no silent fallback outside the pin.
- Give every worker one owner boundary, writable scope, no-go, dependencies, pass criteria, required proof, the bound runtime, and the warning that other agents share the workspace. Read `references/prompt-contract.md` before the first spawn.
- Claims are unverified until the controller checks artifact, scope, and proof (diff within writable paths; one real `TARGET` proof per requirement). Never expose secrets in prompts, reports, commands, or evidence.

| Class | Definition | Mode |
| --- | --- | --- |
| `T0` | Mechanical or read-only, narrow scope, no material runtime, security, or data risk | Micro (certainty `absolute`/`high`) |
| `T1` | One bounded implementation area | Single: one `STANDARD` worker (`LIGHT` if purely mechanical) |
| `T2` | Multiple independent slices or cross-file coordination | Multi: fewest independent workers; integration owner |
| `T3` | Production, security, auth, privacy, payment, secrets, data loss, migration, release, large refactor, uncertain cross-repo behavior | Critical: `DEEP` only on the risky slice; serialize unsafe writes |

`task.controller_certainty`: `absolute` = zero residual doubt (Micro only); `high` = clear single slice (Micro or Single); `medium` = default (Single or Multi); `low` = unclear ownership, risk, or proof (Multi or Critical; never skip review). Never invent `absolute`/`high` to save cost. Execution producers: at most 1 for `T0`/`T1`, at most 3 for `T2`/`T3`; default 2 concurrent.

1. **Freeze.** Record goal, success criteria, constraints, no-go surfaces, certainty, risk flags, and user decisions not to infer. Classify `T0`–`T3`. Make `<run>` outside the repo (`mktemp -d`) and snapshot: `python3 <skill-dir>/scripts/scaffold_report.py --freeze-out <run>/freeze.json --repo <repo>`; note its `tree=` id and `chmod a-w <run>/freeze.json`. In a non-git directory skip `--freeze-out`/`--freeze`/`--diff-out`/`--tree` and list changed files in the spec `files` field. Micro uses the controller for pure integration, else one short `LIGHT` worker; skip the report only when no worker ran and proof is one local check.
2. **DAG.** One node per owned slice: stable ID, kind (`EXECUTION`, `ORCHESTRATION`, `REVIEW`), capability (`LIGHT`, `STANDARD`, `DEEP`, `REVIEWER`), one objective, artifact classes, status, evidence IDs. `DEEP` only for `T3` or non-empty `risk_flags`. Overlapping writes need a dependency edge.
3. **Bind and delegate.** Use the profile table. The genius row is writable only for the scope the controller already authorized; still one producer per writable path. Telemetry (lifetime only): with `T="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"`, bracket each controlled child: `run=$("$T" subagent begin --node <stable-id> </dev/null)` … `"$T" subagent end --run-id "$run" --status completed|failed|cancelled </dev/null`; keep the run id across retries. If the first `begin` fails, record one Subagents proof gap and skip brackets. Telemetry never receives skill bodies or exact output.
4. **Track and reconcile.** Reconcile every changed file to one producer and artifact class. A changed path no run worker made is never reverted or absorbed by widening a scope: stop for a `USER_DECISION`. Re-run the smallest proof. After each `TARGET` `PASS`, run `python3 <skill-dir>/scripts/scaffold_report.py --tree --repo <repo>` and put `tree=<id>` in that evidence `detail`; skip a re-run while `--tree` prints that id. Stop for user decisions that expand scope.
5. **Review gate.** Require a `REVIEWER` when: `T3`; non-empty `risk_flags`; `DATA`/`RELEASE` artifacts; more than one producer; `TARGET` proof missing or not `PASS`; `review_requested: true`; or `CODE`/`TEST` changed without a certainty skip. A certainty skip needs one producer, empty `risk_flags`, all `TARGET` proof `PASS`, `review_requested` false, and either `absolute` on `T0` (`micro_task_absolute_certainty`) or `high` on `T0`/`T1` with `LIGHT`/`STANDARD` (`micro_task_high_certainty`). The `REVIEWER` has a distinct owner, is read-only, runs after all producers, gets only the prompt-contract.md intake, and has its own `TARGET` `PASS` proof. Never raise reviewer effort for corrections; they return to producers (or the genius row if a trigger is armed). Cap: 3 review rounds, recorded in `review_gate.rounds`; a third failing round stops with the review node `BLOCKED` on a `USER_DECISION` blocker.
6. **Report and validate.** Write a judgment-only spec per `references/output-contract.md`, then `python3 <skill-dir>/scripts/scaffold_report.py --profile <preset> --spec <run>/spec.json --out <run>/report.json --freeze <run>/freeze.json` and `python3 <skill-dir>/scripts/validate_orchestration.py --profile <preset> <run>/report.json`. Fix from the validator's error lines and patch the report in place; never weaken the validator. Final response: at most 15 lines plus the report path: class, certainty, mode; decision and remaining IDs; any genius trigger and `fallback_reason`; gate status and reason; validator last line; only `FAIL` or skipped proofs.

## Optional structured report

If the user requests the historical orchestration ledger, read `references/prompt-contract.md`, `references/routing-policy.md`, `references/host-runtime-matrix.md`, and `references/output-contract.md`. Before editing, capture its baseline with `scripts/scaffold_report.py --freeze-out`; then use that script and `scripts/validate_orchestration.py` for the report. Its runtime matrix and validator describe the legacy report format; they do not set the default execution policy. Pass `--profile <preset>` to both scripts under a preset (default `native`). Run `scripts/test_orchestration_harness.py` when changing those report tools, and `scripts/test_worker_harness.py` when changing the Grok resolver.
