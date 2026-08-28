---
name: sam-orchestrate-claude-grok
description: "Claude-controller hybrid orchestration: Grok 4.6 workers for routine and deep slices (medium LIGHT / high STANDARD / xhigh DEEP), Claude opus high independent review, opus xhigh only for stall/multi-round capability escalation, and opus max for optional advisor. Use when the user runs /sam-orchestrate-claude-grok, wants Claude as orchestrator with Grok producers, or cross-host cost-aware multi-agent delivery under this profile."
---

# Sam Orchestrate Claude–Grok

Controller-only orchestration with a **fixed hybrid runtime profile**:

- **Controller host:** Claude Code (long tasks, test re-runs, integration, proof).
- **Default producers:** Grok `grok-4.6` (`medium` LIGHT, `high` STANDARD, `xhigh` DEEP).
- **Independent REVIEWER:** Claude `opus` / `high`.
- **Unstick / genius:** Claude `opus` / `xhigh` only after multi-round Grok failure or stall.
- **Advisor (optional):** Claude `opus` / `max` (read-only).

Do not implement task artifacts on the main thread except controller integration,
proof re-runs, conflict reconciliation, and final reporting.

**Token posture:** thin controller, fat workers, progressive disclosure, cheap
proof, selective review. Spend tokens on artifact verification — not on pasting
this skill into every worker.

**Token Saver inheritance:** when the host provides
`RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1`, every nested worker and advisor must
inherit that content-free receipt and its authorized capability/lane
environment unchanged. The host owns admission; workers must not reconstruct,
widen, or replace those decisions. A missing, malformed, denied, cross-user,
or provider-mismatched receipt is raw fail-open input. Never put Skills,
exact-output commands, prompts, transcripts, secrets, or full advisor
responses into the receipt. Skills and exact-output evidence remain lossless.
Do not claim billing or quota savings.

## Non-Negotiable Contract

- Exclusive top pipeline: if this turn also named `sam-goal`, `sam-task`,
  or `sam-work` as the user request, do not run this controller pipeline;
  that named method owns the turn. Precedence: `sam-goal` > `sam-task` >
  `sam-work` > `sam-orchestrate`.
- Keep the main agent controller-only. Delegate production code, tests, docs,
  migrations, and other task artifacts.
- **Profile is fixed:** `task.active_host` must be `claude-code` (controller).
  Worker `runtime.host` may be `grok` or `claude-code` per
  [references/host-runtime-matrix.md](references/host-runtime-matrix.md).
- Give every worker one owner boundary, writable scope, no-go, dependencies,
  pass criteria, required proof, and a bound runtime receipt.
- Tell every worker that other agents may share the workspace; never revert or
  overwrite unrelated work.
- Treat every returned claim as unverified until the controller checks artifact,
  scope, and proof (diff ⊆ writable paths; one real TARGET proof).
- Bind model/effort **only** from this skill’s matrix. Never invent models,
  never ask the user which model to pick, never put model/host names in owner IDs.
- **Cheap-first:** never open on `DEEP` or `genius_worker`. Escalate only after
  concrete capability failure, stall, or new risk evidence — never because a
  task is large.
- **Equivalence policy:** `grok-4.6` / `high` ≈ `opus` / `medium`. Work at or
  below that quality bar uses Grok. Grok `xhigh` is the DEEP producer bar.
  Opus `high`/`xhigh`/`max` is reserved for review, genius unstick, and advisor.
- Spawn Grok EXECUTION nodes via `sam-grok-worker` with the matrix effort
  (`--effort medium|high|xhigh`). Do not rely on the worker’s default when LIGHT
  needs `medium` or DEEP needs `xhigh`.
- Spawn Claude REVIEWER / genius via Claude Code with the matrix model and
  effort. REVIEWER is read-only.
- If Claude or Grok CLI / auth is unavailable, stop with an evidence-backed
  `EXTERNAL`/`ENVIRONMENT` blocker. No silent host fallback outside this profile.
- Never expose secrets in prompts, reports, commands, or evidence.

## Progressive Disclosure (read only what you need)

| Path | Read now | Defer |
| --- | --- | --- |
| **Micro** (`T0` + certainty `absolute`/`high`) | This SKILL (this section + §1 micro) | full output-contract until report |
| **Single** (`T1`) | + [routing-policy.md](references/routing-policy.md) + [prompt-contract.md](references/prompt-contract.md) | — |
| **Multi** (`T2`) | + [host-runtime-matrix.md](references/host-runtime-matrix.md) | — |
| **Critical** (`T3`) or any stall escalation | + [output-contract.md](references/output-contract.md) + run validator | — |

Always run `scripts/validate_orchestration.py` before declaring completion when
you produced a report JSON (Single/Multi/Critical). Micro may skip the formal
report when no delegated workers ran and proof is a single local check — if you
write a report, validate it.

## Certainty Budget

Record `task.controller_certainty`: `absolute` | `high` | `medium` | `low`.

| Certainty | Meaning | Shape |
| --- | --- | --- |
| `absolute` | Zero residual doubt | Micro (`T0`) only |
| `high` | Clear single-slice; ordinary residual risk | Micro or Single |
| `medium` | Normal ambiguity / multi-touch | Single or Multi |
| `low` | Unclear ownership, risk, or proof | Multi or Critical; do not skip review |

Never invent `absolute`/`high` to save cost.

## Orchestration Modes (T0–T3)

| Mode | When | Shape |
| --- | --- | --- |
| **Micro** | `T0` + certainty `absolute`/`high` | Optional one `LIGHT` Grok worker; no REVIEWER if skip rules hold |
| **Single** | `T1` | One `STANDARD` Grok worker (`LIGHT` if purely mechanical) |
| **Multi** | `T2` | Min independent Grok workers (default parallel **2**, cap **3**); integration owner; review when multi-producer or risk |
| **Critical** | `T3` | `DEEP` Grok only on the risky slice; serialize unsafe writes; **REVIEWER required** (Claude opus high) |

Parallel fan-out: default max **2** concurrent execution workers; hard cap **3**.

## 1. Freeze Goal and Constraints

Record before delegation:

- Goal and observable success criteria.
- Constraints and no-go surfaces.
- Certainty budget.
- Risk flags, expected artifact classes, empty changed-file manifest.
- User decisions that must not be inferred.
- `task.active_host = "claude-code"`.

Classify `T0`–`T3` per [routing-policy.md](references/routing-policy.md).

### Micro path

1. Controller-only only for pure integration; otherwise one short `LIGHT` Grok
   worker (`grok-4.6` / `medium`) with a slice-only prompt.
2. Proof: scope diff + at most one focused command.
3. Skip REVIEWER when absolute/high certainty skip rules hold.
4. Report: one table row or minimal validated JSON.

## 2. Build the Task DAG

Each node needs: stable ID; kind `EXECUTION` | `ORCHESTRATION` | `REVIEW`;
neutral owner (`worker-N` / `controller-N` / `reviewer-N`); capability
`LIGHT` | `STANDARD` | `DEEP` | `REVIEWER`; runtime binding for every delegated
EXECUTION/REVIEW node; dependencies; objective; no-go; proof; writable or
read-only scope; artifact classes; status; evidence IDs.

Caps: `T0`/`T1` → ≤1 execution producer; `T2`/`T3` → ≤3.

`DEEP` only when `T3` or non-empty `risk_flags`.

## 3. Bind Runtime and Delegate

Bind from [host-runtime-matrix.md](references/host-runtime-matrix.md) only:

| Capability | Host | Model | Effort |
| --- | --- | --- | --- |
| `LIGHT` | `grok` | `grok-4.6` | `medium` |
| `STANDARD` | `grok` | `grok-4.6` | `high` |
| `DEEP` | `grok` | `grok-4.6` | `xhigh` |
| `REVIEWER` | `claude-code` | `opus` | `high` |
| `genius_worker` (rare) | `claude-code` | `opus` | `xhigh` |
| advisor (optional) | `claude-code` | `opus` | `max` |

Worker prompts: [prompt-contract.md](references/prompt-contract.md).

### Grok spawn

Use sibling skill `sam-grok-worker` with explicit effort from the matrix and an
absolute `--prompt-file`. Pass only the slice; no full skill paste.

### Claude REVIEWER / genius spawn

Use Claude Code read-only for REVIEWER; writable only for genius when the
controller already authorized those writes. Record runtime receipt before spawn.

### Advisor spawn

Optional read-only second opinion: `opus` / `max`. Never owns production nodes.

Every controlled worker or advisor lifetime must be bracketed by the
provider-neutral telemetry bridge:

```bash
telemetry_command="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"
child_run="$("$telemetry_command" subagent begin --node '<stable-id>')"
# run the delegated worker or advisor
"$telemetry_command" subagent end --run-id "$child_run" --status completed
```

Use `failed` or `cancelled` on the corresponding terminal path. Preserve the
host Token Saver receipt and the returned child run id through retries and
recovery. Bridge unavailability means raw execution plus an explicit Subagents
proof gap — never invent a Done row. Do not require Distill to process Skill
bodies or exact output; the bridge is lifetime telemetry only.

## 4. Track, Reconcile, Escalate

1. Track node state; no overlapping writes without a dependency edge.
2. Reconcile every changed file to one producer + artifact class.
3. Before accepting claims: diff ⊆ writable_paths; one TARGET proof per
   requirement.
4. Prefer re-running the smallest proof over re-reading transcripts.
5. Escalate capability only after capability failure, stall, or new risk evidence.
6. Stop for required user decisions that expand scope.

### Stall / multi-round → Opus xhigh

Escalate a STANDARD/DEEP producer to `genius_worker` (`claude-code` /
`opus` / `xhigh`) only when **any** trigger holds (record in
`runtime.fallback_reason`):

| Trigger | Minimum evidence |
| --- | --- |
| `multi_round_fail` | ≥2 Grok attempts on the same objective with TARGET `FAIL` or capability blocker |
| `stall` | 2× no material progress (no useful diff / same root cause loop) |
| `deep_insufficient` | Node already `DEEP` Grok-xhigh and still unclosed |
| `contradiction` | Worker claims contradict controller re-checked proof |

**Caps:** max **2** Grok attempts per objective before Opus-xhigh; max **1**
Opus-xhigh attempt per objective; then `BLOCKED` + user decision (or optional
read-only advisor at `opus` / `max`). Max **1** active genius node; serial.
Prefer one tighter re-prompt at the same tier before escalating.

Do **not** escalate for task size, latency, preference, or CLI/auth failure.

Do **not** raise REVIEWER effort to `xhigh`/`max`; corrections return to
producers (Grok, or Opus-xhigh if trigger already armed).

## 5. Review Gate

### Require REVIEWER when

- `T3`, non-empty `risk_flags`, or `DATA`/`RELEASE` artifacts.
- More than one execution producer.
- TARGET proof missing or not `PASS`.
- `review_requested: true`.
- `CODE`/`TEST` changed and certainty skip does not apply.

### Certainty skip (no REVIEWER)

| | Absolute | High |
| --- | --- | --- |
| Class | `T0` only | `T0` or `T1` |
| Producers | 1 | 1 |
| Capability | any allowed | `LIGHT` or `STANDARD` only |
| risk_flags | empty | empty |
| TARGET proof | all PASS | all PASS |
| review_requested | false | false |
| Gate reason | `micro_task_absolute_certainty` | `micro_task_high_certainty` |

### Reviewer efficiency

- Claude opus high; read-only; distinct owner; after all producers.
- Feed combined diff/artifact + checklist + frozen scope + proof IDs only.
- Dedicated TARGET/`PASS` proof for the review node.

## 6. Validate Completion

Write JSON per [output-contract.md](references/output-contract.md), then:

```bash
SAM_ORCHESTRATE_CLAUDE_GROK_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_ORCHESTRATE_CLAUDE_GROK_DIR/scripts/validate_orchestration.py" \
  "$ORCHESTRATION_TMP/report.json"
```

Do not weaken the validator. Remove temp artifacts after validation.

`COMPLETE` only when DAG + review gate satisfy the contract, every completed
producer has dedicated TARGET/`PASS` proof, manifest reconciles, and no required
correction remains. `BLOCKED` only with evidence-backed external/authority/
user-decision/dependency provenance. Else `IN_PROGRESS`.

## 7. Report (lean)

| Field | Content |
| --- | --- |
| Class / certainty / mode | `T*`, certainty, micro/single/multi/critical |
| Nodes | id · capability · host · model · effort · status |
| Manifest | path · class · producer |
| Proof | id · requirement · PASS/FAIL |
| Escalation | any genius trigger + fallback_reason |
| Review | required? reason / skip reason |
| Decision | COMPLETE / BLOCKED / IN_PROGRESS + remaining IDs |

Do not repeat unverified agent claims. Do not dump raw logs.
