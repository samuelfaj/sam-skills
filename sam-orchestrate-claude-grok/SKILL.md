---
name: sam-orchestrate-claude-grok
description: "Claude-controller orchestration with Grok 4.6 workers (medium/high/xhigh by tier), Opus high review, Opus xhigh only on stall or multi-round escalation, Opus max advisor. Use when the user runs /sam-orchestrate-claude-grok or wants Claude orchestrating Grok producers for cross-host multi-agent delivery."
---

# Sam Orchestrate Claude–Grok

Controller-only orchestration with a fixed hybrid profile: Claude Code controls
(long tasks, test re-runs, integration, proof); Grok `grok-4.6` produces; Claude
`opus` reviews, unsticks after multi-round Grok failure or stall, and advises.

**Token Saver:** Pass the host's content-free `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` and its capability/lane environment unchanged to every controlled child (nested spawns, retries, resumes, recovery); never reconstruct or widen admission. A missing, malformed, denied, cross-user, or provider-mismatched receipt is raw fail-open input. Never put skills, exact-output commands, prompts, transcripts, secrets, or full responses in it. Skills and exact-output evidence stay lossless; claim no billing or quota savings.

## Non-Negotiable Contract

- Exclusive top pipeline: if this turn also named `sam-goal`, `sam-task`,
  or `sam-work` as the user request, do not run this controller pipeline;
  that named method owns the turn. Precedence: `sam-goal` > `sam-task` > `sam-work` > `sam-orchestrate`.
- Stay controller-only: delegate production code, tests, docs, migrations, and
  other task artifacts. Never produce task artifacts on the main thread except
  controller integration, proof re-runs, conflict reconciliation, and final
  reporting.
- Profile is fixed: `task.active_host` is `claude-code`; worker `runtime.host`
  is `grok` or `claude-code` per §3.
- Give every worker one owner boundary, writable scope, no-go, dependencies,
  pass criteria, required proof, a bound runtime receipt, and the warning that
  other agents share the workspace and their work must never be reverted or
  overwritten.
- Claims are unverified until the controller checks artifact, scope, and proof
  (diff ⊆ writable paths; one real TARGET proof per requirement).
- Bind model and effort only from §3. Never invent models, never ask the user
  which model to pick, never put model or host names in owner IDs.
- Cheap-first: never open on `DEEP` or `genius_worker`. Escalate only after
  concrete capability failure, stall, or new risk evidence, never because a
  task is large.
- Spawn Grok `EXECUTION` nodes via `sam-grok-worker` with the §3 effort
  (`--effort medium|high|xhigh`), never the worker's default. Spawn the Claude
  REVIEWER and genius via Claude Code with the §3 model and effort; the REVIEWER
  is read-only.
- If the Claude or Grok CLI or auth is unavailable, stop with an evidence-backed
  `EXTERNAL`/`ENVIRONMENT` blocker. No silent host fallback outside this profile.
- Never expose secrets in prompts, reports, commands, or evidence.

## References

Read nothing else up front. Do not re-read a file already read in this context
unless context was compacted since or you cannot quote the section you need.

| File | Read when |
| --- | --- |
| `references/prompt-contract.md` | Before the first worker, reviewer, genius, or advisor prompt or spawn |
| `references/routing-policy.md` | After a failed or stalled attempt, before any re-prompt or escalation; before proof broader than scope diff + one focused command |
| `references/host-runtime-matrix.md` | Only for a fallback or effort-policy doubt |
| `references/output-contract.md` | When report authoring starts (§6) |

## Classes and Modes

| Class | Definition | Mode |
| --- | --- | --- |
| `T0` | Mechanical or read-only, narrow scope, no material runtime, security, or data risk | **Micro** (certainty `absolute`/`high`; §1) |
| `T1` | One bounded implementation area | **Single**: one `STANDARD` Grok worker (`LIGHT` if purely mechanical) |
| `T2` | Multiple independent slices or cross-file coordination | **Multi**: fewest independent Grok workers; integration owner |
| `T3` | Production, security, auth, privacy, payment, secrets, data loss, migration, release, large refactor, or uncertain cross-repo behavior | **Critical**: `DEEP` Grok only on the risky slice; serialize unsafe writes |

`task.controller_certainty`: `absolute` = zero residual doubt (Micro only);
`high` = clear single slice, ordinary residual risk (Micro or Single); `medium`
= normal ambiguity or multi-touch, the default and the value when omitted
(Single or Multi); `low` = unclear ownership, risk, or proof (Multi or Critical;
never skip review). Never invent `absolute`/`high` to save cost.

Execution producers: ≤ 1 for `T0`/`T1`, ≤ 3 for `T2`/`T3`; default 2
concurrent, hard cap 3; split only on real ownership or dependency boundaries.

## 1. Freeze

Record before delegation: goal and observable success criteria, constraints and
no-go surfaces, certainty, risk flags, expected artifact classes, an empty
changed-file manifest, and user decisions that must not be inferred. Classify
`T0`–`T3`. Create a run directory `<run>` outside the repo `<repo>` (`mktemp -d`)
and snapshot the workspace (literal absolute paths; `<skill-dir>` holds this
file):
`python3 <skill-dir>/scripts/scaffold_report.py --freeze-out <run>/freeze.json --repo <repo>`;
note its `tree=` id and run `chmod a-w <run>/freeze.json` (workers may write
under `<run>`).
If `<repo>` is not a git work tree, skip `--freeze-out`/`--freeze`/`--diff-out`/`--tree`
and list changed files in the spec `files` field.

Micro: controller-only only for pure integration, else one short slice-only
`LIGHT` Grok worker. Proof is the scope diff plus at most one focused command.
Skip the formal report only when no delegated worker ran and proof is one local
check.

## 2. DAG

Build the smallest useful DAG: one node per owned slice with a stable ID, kind
(`EXECUTION`, `ORCHESTRATION`, or `REVIEW`), capability (`LIGHT`, `STANDARD`,
`DEEP`, or `REVIEWER`), the contract's worker fields, one objective, artifact
classes, status, and evidence IDs. `DEEP` only for `T3` or non-empty
`risk_flags`. Overlapping writes need a dependency edge.

## 3. Bind and Delegate

| Capability (role) | Host | Model | Effort | Notes |
| --- | --- | --- | --- | --- |
| `LIGHT` (`fast_scan`) | `grok` | `grok-4.6` | `medium` | mechanical / read-only / `T0` micro |
| `STANDARD` (`routine_worker`) | `grok` | `grok-4.6` | `high` | bounded implementation and ordinary tests |
| `DEEP` (`deep_worker`) | `grok` | `grok-4.6` | `xhigh` | `T3` / risk slice first attempt |
| `REVIEWER` (`reviewer`) | `claude-code` | `opus` | `high` | read-only / plan mode; host ≠ Grok producers |
| `genius_worker` (rare) | `claude-code` | `opus` | `xhigh` | unstick only; routing-policy.md trigger + `fallback_reason` |
| advisor (optional) | `claude-code` | `opus` | `max` | read-only; never owns production nodes |

Load `sam-grok-worker` once per run; every Grok node keeps its prompt
requirements (no publish, push, remote proposals, messages, or other external
writes unless the frozen request authorizes them; the Output field replaces its
report line) and reconcile step; only re-reading its SKILL.md is skipped. Its
resolver always grants workspace sandbox + always-approve: spawn Grok only
where the parent authorized workspace writes, else the controller runs
read-only scans itself; a read-only Grok node gets `No-go: any write`, and
`--tree` (§4 step 3) run before and after it must print the same id, else the
node fails. The Claude genius is writable only for the frozen scope the
controller already authorized. Cross-host is intentional; still one producer
per writable path.

**Telemetry (lifetime only):** With `T="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"`, bracket each controlled child: `run=$("$T" subagent begin --node <stable-id> </dev/null)` … `"$T" subagent end --run-id "$run" --status completed|failed|cancelled </dev/null`; keep the run id across retries. If the run's first `begin` fails, record one Subagents proof gap and skip brackets for the rest of the run. Telemetry never invents a Done row or receives skill bodies or exact output.

## 4. Track and Reconcile

1. Track node state; reconcile every changed file to one producer and artifact
   class. A changed path no run worker made is never reverted or absorbed by
   widening a scope: stop for a `USER_DECISION`.
2. Re-run the smallest proof instead of re-reading transcripts.
3. Right after each TARGET `PASS`, run
   `python3 <skill-dir>/scripts/scaffold_report.py --tree --repo <repo>` and put
   its `tree=<id>` in that evidence `detail`. Before re-running a node's TARGET
   proof, skip it (reuse its evidence IDs) while `--tree` still prints that id.
   Report-only fixes never re-run proofs or review.
4. Stop for required user decisions that expand scope.

## 5. Review Gate

Require a REVIEWER when: `T3`; non-empty `risk_flags`; `DATA`/`RELEASE`
artifacts; more than one execution producer; TARGET proof missing or not
`PASS`; `review_requested: true`; or `CODE`/`TEST` changed without a certainty
skip. Else record `NOT_REQUIRED` with the exact reason.

A certainty skip needs one producer, empty `risk_flags`, all TARGET proof
`PASS`, and `review_requested` false, plus:

| `controller_certainty` | Class | Capability | Gate reason |
| --- | --- | --- | --- |
| `absolute` | `T0` only | any allowed | `micro_task_absolute_certainty` |
| `high` | `T0` or `T1` | `LIGHT` or `STANDARD` only | `micro_task_high_certainty` |

The REVIEWER has a distinct owner, runs after all producers, gets only the
prompt-contract.md intake, and has its own TARGET `PASS` proof. After
corrections, re-gate on the delta per prompt-contract.md. Never raise REVIEWER
effort to `xhigh`/`max`; corrections return to producers (Grok, or Opus `xhigh`
if a trigger is already armed). Cap: 3 review rounds (initial + 2), recorded in
`review_gate.rounds`; a third failing round stops with the review node `BLOCKED`
on a `USER_DECISION` blocker.

## 6. Report and Validate

For Single/Multi/Critical, and any Micro run that writes a report:

1. Write a judgment-only spec per output-contract.md, then run
   `python3 <skill-dir>/scripts/scaffold_report.py --spec <run>/spec.json --out <run>/report.json --freeze <run>/freeze.json`.
2. Run `python3 <skill-dir>/scripts/validate_orchestration.py <run>/report.json`.
   Fix from the validator's error lines and patch the report in place; do not
   read validator source or rewrite the whole report. Never weaken the validator.

Final response, ≤ 15 lines plus the report path (if written): class, certainty,
mode; decision and remaining IDs; any genius trigger and `fallback_reason`; gate
status and reason; validator last line; only `FAIL` or skipped proofs. Never
repeat the JSON report, unverified claims, or raw logs.
