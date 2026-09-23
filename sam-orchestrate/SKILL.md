---
name: sam-orchestrate
description: "Run complex work as a controller-only orchestrator: cost- and risk-aware routing, owned task dependencies, skeptical proof checks, and an independent review gate. Use when the user asks for delegated execution, parallel agents, controller-only operation, or rigorous multi-agent delivery."
---

# Sam Orchestrate

Stay stack-neutral outside the §3 runtime table.

**Token Saver:** Pass the host's content-free `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` and its capability/lane environment unchanged to every controlled child (nested spawns, retries, resumes, recovery); never reconstruct or widen admission. A missing, malformed, denied, cross-user, or provider-mismatched receipt is raw fail-open input. Never put skills, exact-output commands, prompts, transcripts, secrets, or full responses in it. Skills and exact-output evidence stay lossless; claim no billing or quota savings.

## Non-Negotiable Contract

- Exclusive top pipeline: if this turn also named `sam-goal`, `sam-task`,
  or `sam-work` as the user request, do not run this controller pipeline;
  that named method owns the turn. Precedence: `sam-goal` > `sam-task` > `sam-work` > `sam-orchestrate`.
- Stay controller-only: delegate production code, tests, docs, migrations, and
  other artifacts. Work directly only on decomposition, coordination, result
  inspection, proof reruns, conflict integration, and final reporting.
- Give every worker one owner boundary, writable scope, no-go scope,
  dependencies, pass criteria, required proof, a bound runtime receipt, and the
  warning that other agents share the workspace and their work must not be
  reverted or overwritten.
- Claims are unverified until you check artifact, scope, and proof: diff ⊆
  writable paths and one real TARGET `PASS` proof per proof requirement. Reject
  unrelated changes and unsupported completion claims.
- Pick capability by risk first, then bind model and effort only from §3 for the
  host detected once per run. Never invent models, never ask the user which
  model to pick, never put model or host names in owner IDs.
- Cheap-first: never open on `DEEP` or `genius_worker`; escalate only after
  concrete capability failure or new risk evidence, never because a task is large.
- If delegation is unavailable, stop before execution and report the exact
  blocker; never silently leave controller-only mode.
- Never expose secrets in prompts, reports, commands, or evidence.

## References

Read nothing else up front. Do not re-read a file already read in this context
unless context was compacted since or you cannot quote the section you need.

| File | Read when |
| --- | --- |
| `references/prompt-contract.md` | Before the first worker or reviewer prompt or spawn |
| `references/routing-policy.md` | After a failed or stalled attempt, before any re-prompt or escalation; before proof broader than scope diff + one focused command |
| `references/host-runtime-matrix.md` | A bound model or effort is unavailable, an advisor, Codex agent config, or unclear host detection |
| `references/output-contract.md` | When report authoring starts (§6) |

## Classes and Modes

| Class | Definition | Mode |
| --- | --- | --- |
| `T0` | One mechanical or read-only task, narrow scope, no material runtime, security, data, release, or cross-file risk | **Micro** (certainty `absolute`/`high`; §1) |
| `T1` | One bounded implementation area with ordinary validation | **Single**: one `STANDARD` worker (`LIGHT` if purely mechanical) |
| `T2` | Multiple independent slices, meaningful test work, or cross-file coordination | **Multi**: fewest independent `LIGHT`/`STANDARD` workers; one integration owner |
| `T3` | Production, security, authorization, privacy, payment, secrets, data loss, migration, release, deployment, large refactor, or uncertain cross-repo behavior | **Critical**: `DEEP` only on the risky slice; serialize unsafe writes |

`task.controller_certainty`: `absolute` = zero residual doubt on scope, risk,
ownership, proof (Micro only); `high` = clear single slice, ordinary residual
risk (Micro or Single); `medium` = normal ambiguity or multi-touch, the default
and the value when omitted (Single or Multi); `low` = unclear ownership, risk,
or proof path (Multi or Critical; never skip review). Never invent
`absolute`/`high` to save cost.

Execution producers: ≤ 1 for `T0`/`T1`, ≤ 3 for `T2`/`T3`; default 2
concurrent, hard cap 3. Prefer serial writes; split only on real ownership or
dependency boundaries, never to add agents.

## 1. Freeze

Record before delegation: goal and observable success criteria, constraints and
no-go surfaces, certainty, risk flags, expected artifact classes, an empty
changed-file manifest, and user decisions that must not be inferred. Classify
`T0`–`T3`; pick the cheapest mode that keeps evidence quality. Create a run
directory `<run>` outside the repo `<repo>` (`mktemp -d`) and snapshot the
workspace (literal absolute paths; `<skill-dir>` holds this file):
`python3 <skill-dir>/scripts/scaffold_report.py --freeze-out <run>/freeze.json --repo <repo>`;
note its `tree=` id and run `chmod a-w <run>/freeze.json` (workers may write
under `<run>`).
If `<repo>` is not a git work tree, skip `--freeze-out`/`--freeze`/`--diff-out`/`--tree`
and list changed files in the spec `files` field.

Micro: work directly only for pure controller integration, else one short
slice-only `LIGHT` worker. Proof is the scope diff plus at most one focused
command; no full-suite runs, no raw logs. Skip the formal report only when no
delegated worker ran and proof is one local check.

## 2. DAG (Single / Multi / Critical)

Build the smallest useful DAG: one node per owned slice with a stable ID, kind
(`EXECUTION`, `ORCHESTRATION`, or `REVIEW`), capability (`LIGHT`, `STANDARD`,
`DEEP`, or `REVIEWER`), the contract's worker fields, one objective, artifact
classes, status, blocker provenance, and evidence IDs. `DEEP` only for `T3` or
non-empty `risk_flags`. Overlapping writes need a dependency edge.

## 3. Bind and Delegate

Never mix host runtimes in one run unless the user explicitly asks for a
cross-host second opinion; even then keep one producer host for writable work.

| Capability (role) | `codex` | `claude-code` | `grok` | Sandbox |
| --- | --- | --- | --- | --- |
| `LIGHT` (`fast_scan`) | `gpt-5.6-luna` / `medium` | `haiku` / `high` | `grok-4.6` / `medium` | read-only (Grok: prefer read-only) |
| `STANDARD` (`routine_worker`) | `gpt-5.6-luna` / `xhigh` | `sonnet` / `high` | `grok-4.6` / `high` | parent permissions, writable scope only |
| `DEEP` (`deep_worker`) | `gpt-5.6-luna` / `max` | `opus` / `medium` | `grok-4.6` / `xhigh` | as `STANDARD` |
| `genius_worker` (rare) | `gpt-5.6-luna` / `max` | `opus` / `xhigh` | `grok-4.6` / `xhigh` | frozen scope; never a default |
| `REVIEWER` (`reviewer`) | `gpt-6-astra` / `medium` | `opus` / `high` | `grok-4.6` / `high` | read-only / plan mode; Grok: no subagent fan-out |

On Codex, the controller also runs on `gpt-6-astra`; if it cannot be selected,
report that instead of claiming a switch. Run Grok workers headless with
workspace sandbox and always-approve only when the node is writable and the
parent already authorized those writes.

**Telemetry (lifetime only):** With `T="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"`, bracket each controlled child: `run=$("$T" subagent begin --node <stable-id> </dev/null)` … `"$T" subagent end --run-id "$run" --status completed|failed|cancelled </dev/null`; keep the run id across retries. If the run's first `begin` fails, record one Subagents proof gap and skip brackets for the rest of the run. Telemetry never invents a Done row or receives skill bodies or exact output.

## 4. Track and Reconcile

1. Track node state; map every changed file to one producer and artifact class.
   A changed path no run worker made is never reverted or absorbed by widening
   a scope: stop for a `USER_DECISION`.
2. Re-run the smallest proof instead of re-reading transcripts.
3. Right after each TARGET `PASS`, run
   `python3 <skill-dir>/scripts/scaffold_report.py --tree --repo <repo>` and put
   its `tree=<id>` in that evidence `detail`. Before re-running a node's TARGET
   proof, skip it (reuse its evidence IDs) while `--tree` still prints that id.
   Report-only fixes never re-run proofs or review.
4. Stop for required user decisions that expand scope.
5. Fix forward on the existing DAG and task branch: a failed proof, review
   finding, or moved integration ref never authorizes a new worktree or
   discarded producer receipts. Park out-of-scope findings.

## 5. Review Gate

Require a REVIEWER when: class `T3`; non-empty `risk_flags`; `DATA`/`RELEASE`
artifacts; more than one execution producer; TARGET proof missing or not
`PASS`; `review_requested: true`; or `CODE`/`TEST` changed without a certainty
skip. Else record `NOT_REQUIRED` with the exact reason.

A certainty skip needs one producer, empty `risk_flags`, all TARGET proof
`PASS`, and `review_requested` false, plus:

| `controller_certainty` | Class | Capability | Gate reason |
| --- | --- | --- | --- |
| `absolute` | `T0` only | any allowed | `micro_task_absolute_certainty` |
| `high` | `T0` or `T1` | `LIGHT` or `STANDARD` only | `micro_task_high_certainty` |

The REVIEWER has a distinct owner, runs after every producer, gets only the
prompt-contract.md intake, and has its own TARGET `PASS` proof. Corrections
return to producers, then re-gate on the delta per prompt-contract.md. Cap: 3
review rounds (initial + 2), recorded in `review_gate.rounds`; a third failing
round stops with the review node `BLOCKED` on a `USER_DECISION` blocker.

## 6. Report and Validate

For Single/Multi/Critical, and any Micro run that writes a report:

1. Write a judgment-only spec per output-contract.md, then run
   `python3 <skill-dir>/scripts/scaffold_report.py --spec <run>/spec.json --out <run>/report.json --freeze <run>/freeze.json`.
2. Run `python3 <skill-dir>/scripts/validate_orchestration.py <run>/report.json`.
   Fix from the validator's error lines and patch the report in place; do not
   read validator source or rewrite the whole report. Never weaken the validator.

Final response, ≤ 15 lines plus the report path (if written): class, certainty,
mode; decision and remaining IDs; gate status and reason; validator last line;
only `FAIL` or skipped proofs. Never repeat the JSON report, unverified claims,
or raw logs.
