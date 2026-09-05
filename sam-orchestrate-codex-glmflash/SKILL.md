---
name: sam-orchestrate-codex-glmflash
description: "Codex-controller orchestration with GLM-5.3-Flash workers via Z.AI (always max effort), Codex gpt-5.6-sol independent review, and Sol high only for stall or multi-round capability escalation. Use when the user runs /sam-orchestrate-codex-glmflash or wants Codex to coordinate work through the configured Z.AI GLM provider."
---

# Sam Orchestrate Codex–GLM Flash

Controller-only orchestration with a **fixed Z.AI runtime profile**:

- **Controller host:** Codex (long tasks, test re-runs, integration, proof).
- **Default producers:** Z.AI `glm-5.3-flash` at `max` effort for LIGHT, STANDARD, and DEEP.
- **Independent REVIEWER:** Codex `gpt-5.6-sol` / `medium`.
- **Unstick / genius:** Codex `gpt-5.6-sol` / `high` only after multi-round GLM-5.3-Flash failure or stall.

Do not implement task artifacts on the main thread except controller integration,
proof re-runs, conflict reconciliation, and final reporting.

**Token posture:** thin controller, fat workers, progressive disclosure, cheap
proof, selective review. Spend tokens on artifact verification — not on pasting
this skill into every worker.

**Token Saver inheritance:** when the host provides
`RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1`, every nested worker must inherit that
content-free receipt and its lane/capability environment unchanged. The host
owns admission, Graphify, Distill, managed-wrapper PATH, recovery scope, and
provider attribution; workers must not reconstruct, widen, or replace those
decisions. A missing, malformed, denied, cross-user, or provider-mismatched
receipt is raw fail-open input. Never put prompts, transcripts, tool output, or
secrets into the receipt. Exact-output commands and Skills remain lossless.

## Non-Negotiable Contract

- Exclusive top pipeline: if this turn also named `sam-goal`, `sam-task`,
  or `sam-work` as the user request, do not run this controller pipeline;
  that named method owns the turn. Precedence: `sam-goal` > `sam-task` >
  `sam-work` > `sam-orchestrate`.
- Keep the main agent controller-only. Delegate production code, tests, docs,
  migrations, and other task artifacts.
- **Profile is fixed:** `task.active_host` and every delegated `runtime.host` are
  `codex`; the producer model is selected through provider `zai` per
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
- **Effort policy:** GLM-5.3-Flash always uses `max`, including LIGHT and STANDARD.
  Sol `high` is reserved for genius unstick after GLM-5.3-Flash is exhausted.
- Spawn GLM-5.3-Flash EXECUTION nodes via `codex exec` with explicit provider `zai`,
  model `glm-5.3-flash`, and the matrix effort (`max`). Never pass the
  API key on the command line; rely on the configured `ZAI_API_KEY` environment variable.
- Spawn Codex REVIEWER / genius via Codex agent/`codex exec` with the matrix
  model and effort. REVIEWER is read-only.
- If Codex, the Z.AI provider, or GLM-5.3-Flash auth is unavailable, stop with an evidence-backed
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
| **Micro** | `T0` + certainty `absolute`/`high` | Optional one `LIGHT` GLM-5.3-Flash worker; no REVIEWER if skip rules hold |
| **Single** | `T1` | One `STANDARD` GLM-5.3-Flash worker (`LIGHT` if purely mechanical) |
| **Multi** | `T2` | Min independent GLM-5.3-Flash workers (default parallel **2**, cap **3**); integration owner; review when multi-producer or risk |
| **Critical** | `T3` | `DEEP` GLM-5.3-Flash only on the risky slice; serialize unsafe writes; **REVIEWER required** (Codex Sol medium) |

Parallel fan-out: default max **2** concurrent execution workers; hard cap **3**.

## 1. Freeze Goal and Constraints

Record before delegation:

- Goal and observable success criteria.
- Constraints and no-go surfaces.
- Certainty budget.
- Risk flags, expected artifact classes, empty changed-file manifest.
- User decisions that must not be inferred.
- `task.active_host = "codex"`.

Classify `T0`–`T3` per [routing-policy.md](references/routing-policy.md).

### Micro path

1. Controller-only only for pure integration; otherwise one short `LIGHT` GLM-5.3-Flash
   worker (`glm-5.3-flash` / `max`) with a slice-only prompt.
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
| `LIGHT` | `codex` | `glm-5.3-flash` | `max` |
| `STANDARD` | `codex` | `glm-5.3-flash` | `max` |
| `DEEP` | `codex` | `glm-5.3-flash` | `max` |
| `REVIEWER` | `codex` | `gpt-5.6-sol` | `medium` |
| `genius_worker` (rare) | `codex` | `gpt-5.6-sol` | `high` |

Worker prompts: [prompt-contract.md](references/prompt-contract.md).

### GLM-5.3-Flash spawn

Use `codex exec` with the provider, model, and effort bound by the matrix, and
pipe an absolute prompt file on stdin (`codex exec ... - < prompt-file`).

Pass only the slice; no full skill paste and no API key.

### Codex REVIEWER / genius spawn

Use Codex read-only for REVIEWER; writable only for genius when the controller
already authorized those writes. Record runtime receipt before spawn.

Every real delegated node must be bracketed by the provider-neutral telemetry
bridge (`${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill} subagent begin
--node <stable-id>` / matching `subagent end --run-id <id> --status
<completed|failed|cancelled>`). Preserve the host receipt and returned child id
through retries and recovery; if the bridge is unavailable, keep the worker raw
and record the Subagents proof gap.

## 4. Track, Reconcile, Escalate

1. Track node state; no overlapping writes without a dependency edge.
2. Reconcile every changed file to one producer + artifact class.
3. Before accepting claims: diff ⊆ writable_paths; one TARGET proof per
   requirement.
4. Prefer re-running the smallest proof over re-reading transcripts.
5. Escalate capability only after capability failure, stall, or new risk evidence.
6. Stop for required user decisions that expand scope.

### Stall / multi-round → Sol high

Escalate a STANDARD/DEEP producer to `genius_worker` (`codex` /
`gpt-5.6-sol` / `high`) only when **any** trigger holds (record in
`runtime.fallback_reason`):

| Trigger | Minimum evidence |
| --- | --- |
| `multi_round_fail` | ≥2 GLM-5.3-Flash attempts on the same objective with TARGET `FAIL` or capability blocker |
| `stall` | 2× no material progress (no useful diff / same root cause loop) |
| `deep_insufficient` | Node already `DEEP` GLM-5.3-Flash-max and still unclosed |
| `contradiction` | Worker claims contradict controller re-checked proof |

**Caps:** max **2** GLM-5.3-Flash attempts per objective before Sol-high; max **1**
Sol-high attempt per objective; then `BLOCKED` + user decision (or optional
read-only advisor). Max **1** active genius node; serial. Prefer one tighter
re-prompt at the same tier before escalating.

Do **not** escalate for task size, latency, preference, or CLI/auth failure.

Do **not** raise REVIEWER effort to `high`; corrections return to producers
(GLM-5.3-Flash, or Sol-high if trigger already armed).

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

- Codex Sol medium; read-only; distinct owner; after all producers.
- Feed combined diff/artifact + checklist + frozen scope + proof IDs only.
- Dedicated TARGET/`PASS` proof for the review node.

## 6. Validate Completion

Write JSON per [output-contract.md](references/output-contract.md), then:

```bash
SAM_ORCHESTRATE_CODEX_GLMFLASH_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_ORCHESTRATE_CODEX_GLMFLASH_DIR/scripts/validate_orchestration.py" \
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
