---
name: sam-orchestrate
description: "Coordinate complex work as a controller-only orchestrator using cost- and risk-aware capability routing, explicit task dependencies and ownership, skeptical proof verification, and an independent review gate. Use when the user asks for delegated execution, parallel agents, controller-only operation, or rigorous multi-agent delivery."
---

# Sam Orchestrate

Coordinate execution without implementing task artifacts directly. Route work by
capability and risk, then bind each delegated node to the active host’s fixed
runtime matrix (Codex, Claude Code, or Grok). Remain stack-neutral outside that
matrix.

**Token posture:** thin controller, fat workers, progressive disclosure, cheap
proof, selective review. Spend tokens on verification of artifacts — not on
re-reading this skill or re-prompting full history into every worker.

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

- Keep the main agent controller-only. Delegate production code, tests,
  documentation, migrations, and other task artifacts.
- Permit direct main-agent work only for task decomposition, agent coordination,
  result inspection, proof reruns, conflict integration, and final reporting.
- Give every worker one explicit owner boundary, writable scope, no-go scope,
  dependencies, pass criteria, required proof, and a bound runtime receipt.
- Tell every worker that other agents may share the workspace and that it must
  not revert or overwrite unrelated work.
- Treat every returned claim as unverified until the controller checks its
  artifact, scope, and proof (diff vs writable paths; one real TARGET proof).
- Select capability by task risk first. Bind model/effort only from
  [references/host-runtime-matrix.md](references/host-runtime-matrix.md) for the
  active host. Never invent models, never ask the user which model to pick, and
  never put model or host names into owner IDs.
- **Cheap-first:** never open on `DEEP` or `genius_worker`. Escalate only after
  concrete capability failure or new risk evidence — never because a task is large.
- If delegation is unavailable, stop before execution and report the exact
  blocker. Do not silently abandon controller-only mode.
- Never expose secrets in prompts, reports, commands, or evidence.

## Progressive Disclosure (read only what you need)

Do **not** load every reference on every turn.

| Path | Read now | Defer |
| --- | --- | --- |
| **Micro** (`T0` + certainty `absolute`/`high`) | This SKILL (this section + §1 micro) | matrix full tables, output-contract, validator until report |
| **Single** (`T1`) | + [routing-policy.md](references/routing-policy.md) + [prompt-contract.md](references/prompt-contract.md) | full output-contract until drafting report |
| **Multi** (`T2`) | + [host-runtime-matrix.md](references/host-runtime-matrix.md) | — |
| **Critical** (`T3`) | + [output-contract.md](references/output-contract.md) + run validator | — |

Always run `scripts/validate_orchestration.py` before declaring completion when
you produced a report JSON (Single/Multi/Critical). Micro path may skip the
formal report when no delegated workers ran and proof is a single local check —
if you write a report, validate it.

## Certainty Budget

Record `task.controller_certainty` as one of: `absolute` | `high` | `medium` |
`low`.

| Certainty | Meaning | Orchestration shape |
| --- | --- | --- |
| `absolute` | Zero residual doubt on scope, risk, ownership, proof | Micro path only (`T0`) |
| `high` | Clear single-slice work; ordinary residual risk only | Micro or Single |
| `medium` | Normal ambiguity or multi-touch | Single or Multi |
| `low` | Unclear ownership, risk, or proof path | Multi or Critical; do not skip review |

Never invent `absolute`/`high` to save cost.

## Orchestration Modes (T0–T3)

| Mode | When | Shape |
| --- | --- | --- |
| **Micro** | `T0` and certainty `absolute` or `high` | No subagent required; optional one `LIGHT` worker; **no REVIEWER** if absolute-certainty (or high) skip rules hold; no formal DAG theater |
| **Single** | `T1` | One `STANDARD` worker (or `LIGHT` if purely mechanical); review only if triggers fire and skip rules fail |
| **Multi** | `T2` | Minimum independent workers (default parallel **2**, hard cap **3**); one integration owner; review when multi-producer or risk |
| **Critical** | `T3` | `DEEP` only on the risky slice; serialize unsafe writes; **REVIEWER required** |

Parallel fan-out: default max **2** concurrent execution workers; hard cap **3**.
Split only on real ownership/dependency boundaries — never to increase agent count.

## 1. Freeze Goal and Constraints

Record before delegation:

- Goal and observable success criteria.
- Explicit constraints and no-go surfaces.
- Certainty budget (`absolute`/`high`/`medium`/`low`).
- Risk flags, expected artifact classes, empty changed-file manifest.
- User decisions that must not be inferred.

Classify `T0`–`T3` per [routing-policy.md](references/routing-policy.md). Pick the
**cheapest** mode that still preserves evidence quality.

### Micro path (token-efficient)

When mode is Micro:

1. Do the work yourself only if it is pure controller integration; otherwise one
   short `LIGHT` worker with a **slice-only** prompt (see prompt-contract).
2. Proof: scope diff + at most one focused command. No full-suite runs. No raw
   log dumps — summary + failing excerpt only.
3. Skip REVIEWER when absolute/high certainty skip rules hold.
4. Report: one table row (node / model / proof / status) or a minimal validated
   JSON report. No narrative essay.

## 2. Build the Task DAG (Single / Multi / Critical)

Create the **smallest** useful DAG. Each node must contain:

- Stable task ID and kind: `EXECUTION`, `ORCHESTRATION`, or `REVIEW`.
- Neutral owner ID and capability: `LIGHT`, `STANDARD`, `DEEP`, or `REVIEWER`.
- Runtime binding for every delegated `EXECUTION` and `REVIEW` node.
- Dependencies, one objective, no-go, proof requirements.
- Writable paths or explicitly read-only scope; artifact classes.
- Status, blocker provenance, evidence IDs.

Owner IDs: `worker-N`, `controller-N`, `reviewer-N` only.

Caps by class: `T0`/`T1` → at most **1** execution producer; `T2`/`T3` → at most
**3** execution producers.

`DEEP` only when classification is `T3` or `risk_flags` is non-empty. Prefer a
better `LIGHT`/`STANDARD` re-prompt over escalating model tier.

## 3. Bind Runtime and Delegate

Detect host once (`codex`, `claude-code`, `grok`). Bind matrix rows from
[host-runtime-matrix.md](references/host-runtime-matrix.md).

| Capability | Codex | Claude Code | Grok |
| --- | --- | --- | --- |
| `LIGHT` | `gpt-5.6-luna` / `medium` | `haiku` / `high` | `grok-4.6` / `medium` |
| `STANDARD` | `gpt-5.6-luna` / `xhigh` | `sonnet` / `high` | `grok-4.6` / `high` |
| `DEEP` | `gpt-5.6-luna` / `max` | `opus` / `medium` | `grok-4.6` / `xhigh` |
| rare escalate | `gpt-5.6-sol` / `high` | `opus` / `xhigh` | `grok-4.6` / `xhigh` |
| `REVIEWER` | `gpt-5.6-sol` / `medium` | `opus` / `high` | `grok-4.6` / `high` |

Worker prompts: [prompt-contract.md](references/prompt-contract.md) — **slice-only**,
no full skill paste, no other workers’ conclusions into independent review.

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

## 4. Track and Reconcile (cheap skepticism)

1. Track node state; prevent overlapping writes without a dependency edge.
2. Reconcile every changed file to one producer + artifact class.
3. **Before accepting claims:** check diff ⊆ writable_paths; require one real
   TARGET proof per proof requirement.
4. Prefer re-running the smallest proof over re-reading whole transcripts.
5. Reject unrelated changes and unsupported completion claims.
6. Escalate capability only after capability failure or new risk evidence.
7. Stop for required user decisions that expand scope.

## 5. Review Gate

### Require REVIEWER when

- Classification `T3`, or non-empty `risk_flags`, or `DATA`/`RELEASE` artifacts.
- More than one execution producer.
- TARGET proof missing or not `PASS`.
- User set `review_requested: true`.
- `CODE`/`TEST` changed **and** certainty skip does not apply.

### Certainty skip (no REVIEWER)

| | Absolute | High |
| --- | --- | --- |
| Class | `T0` only | `T0` or `T1` |
| Producers | 1 | 1 |
| Capability | any allowed | `LIGHT` or `STANDARD` only |
| risk_flags | empty | empty |
| TARGET proof | all PASS | all PASS |
| review_requested | false | false |
| Record | `controller_certainty: "absolute"` | `controller_certainty: "high"` |
| Gate reason | `micro_task_absolute_certainty` | `micro_task_high_certainty` |

### Reviewer efficiency

- Read-only; distinct neutral owner; after all producers.
- Feed **combined diff/artifact + checklist + frozen scope + proof IDs** — not
  this entire SKILL and not expected findings.
- Dedicated TARGET/`PASS` proof for the review node.
- Corrections → re-gate until pass or concrete blocker.

When skip applies or no trigger fires: `NOT_REQUIRED` + exact reason.

## 6. Validate Completion

For Single/Multi/Critical (and any Micro that wrote a report), write JSON per
[output-contract.md](references/output-contract.md), then:

```bash
SAM_ORCHESTRATE_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_ORCHESTRATE_DIR/scripts/validate_orchestration.py" \
  "$ORCHESTRATION_TMP/report.json"
```

Do not weaken the validator. Remove temp artifacts after validation.

`COMPLETE` only when DAG + review gate satisfy the contract, every completed
producer has dedicated TARGET/`PASS` proof, manifest reconciles, and no required
correction remains. `BLOCKED` only with evidence-backed external/authority/
user-decision/dependency provenance. Else `IN_PROGRESS`.

## 7. Report (lean)

Return a **table**, not an essay:

| Field | Content |
| --- | --- |
| Class / certainty / mode | `T*`, certainty, micro/single/multi/critical |
| Nodes | id · capability · model · effort · status |
| Manifest | path · class · producer |
| Proof | id · requirement · PASS/FAIL |
| Review | required? reason / skip reason |
| Decision | COMPLETE / BLOCKED / IN_PROGRESS + remaining IDs |

Do not repeat unverified agent claims. Do not dump raw logs.
