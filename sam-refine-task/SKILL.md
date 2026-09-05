---
name: sam-refine-task
description: "Stress-test and revise a technical strategy without implementing it, using an exact evidence baseline, fact and assumption ledgers, bounded loophole analysis, verification mapping, and a validated confidence decision. Use for implementation plans, debugging hypotheses, migrations, rollouts, releases, test strategies, or architecture approaches that need hardening before execution."
---

# Sam Refine Task

Produce an executable, factually defensible strategy. Remain read-only and
stack-, provider-, host-, tool-, and model-neutral.

## Non-Negotiable Contract

- Never expose secrets, credentials, private data, or sensitive paths in plans,
  commands, reports, or returned evidence.
- Do not edit, stage, commit, reset, checkout, stash, clean, publish, deploy, or
  mutate any local or external state.
- Preserve unrelated dirty work byte-for-byte.
- Separate facts, assumptions, and unknowns. Never promote confidence because a
  plan sounds plausible.
- Keep risk analysis inside the stated goal unless an adjacent risk directly
  invalidates the strategy.
- Stop after two refinement passes unless new evidence appears.

## Resource Routing

- Read [references/evidence-policy.md](references/evidence-policy.md) before
  classifying claims or proof.
- Read [references/risk-lenses.md](references/risk-lenses.md) selectively for
  applicable boundaries.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting the structured report.
- Run `scripts/capture_scope.py` before analysis and immediately before return.
- Run `scripts/validate_report.py` before returning the confidence decision.

## 1. Freeze Target and Intent

```bash
SAM_REFINE_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_REFINE_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/baseline.json"
```

Use repeated `--path <repo-relative-path>` only for explicit scope and reuse the
exact arguments later.

Freeze:

- Goal, non-goals, proposed steps, expected outcome, and success criteria.
- Behavior and contracts that must not change.
- Invariants, owner boundary, constraints, and no-go scope.
- Required evidence and unresolved decisions.
- Baseline fingerprint with empty owned paths; refinement must not alter files.

Under a parent workflow (for example `sam-work`), never ask—evaluate from
available evidence or return `BLOCKED` / `NOT_CONFIDENT` with exact unknowns.
When running standalone, ask a concise blocking question only when the strategy
is too ambiguous to evaluate and repository evidence cannot resolve it.

## 2. Build the Evidence Ledger

Create explicit claims and classify each as:

- `FACT`: supported by code, tests, logs, runtime evidence, authoritative docs,
  or a recorded user decision.
- `ASSUMPTION`: plausible but unverified.
- `UNKNOWN`: evidence is missing or contradictory.

Mark material claims. Link every fact to evidence. `HIGH_CONFIDENCE` cannot
contain a material assumption or unknown.

Inspect only sources needed to test the strategy: code, tests, configuration,
schemas, deployment definitions, issue text, review history, and safe runtime
evidence. Do not use unavailable external state as if it were known.

## 3. Find and Close Material Loopholes

Apply only relevant lenses. Check requirements, ownership, security, data,
contracts, concurrency, failure handling, environment drift, test seams,
observability, compatibility, rollout, rollback, and operational dependencies.

For each loophole record:

- Concrete failure mode and evidence.
- Impact on the stated goal.
- Smallest strategy correction.
- Verification required.
- `CLOSED`, `REJECTED`, or `OPEN` status.

Prefer deleting unnecessary steps, branches, modes, abstractions, or manual
coordination. Do not add speculative process that closes no proven loophole.
Treat repository conventions and actual ownership as stronger than arbitrary
size thresholds.

## 4. Map Verification and Repeat Once

Map every material strategy claim to a proof command, test, runtime check,
artifact, rollback exercise, or explicit user decision. Use `NOT_APPLICABLE`
only with a concrete reason.

Mark already executed proof `PASS`. Mark an exact proof that is executable only
after implementation as `PLANNED`, with the deferral reason and no executed
evidence. Use `NOT_RUN` only when proof remains unresolved; it blocks
`HIGH_CONFIDENCE`.

Run a second pass only if the first materially changes the strategy or new
evidence appears. Recheck facts, loopholes, scope, recovery, and proof mapping.

Return:

- `HIGH_CONFIDENCE` when every material claim is factual, every material
  loophole is closed or disproven, and every verification is `PASS`, `PLANNED`,
  or concretely `NOT_APPLICABLE`.
- `NOT_CONFIDENT` when the strategy can be improved but required proof remains.
- `BLOCKED` when progress requires missing access, a user decision, unsafe
  authorization, or unavailable evidence.

## 5. Validate Read-Only Integrity and Decision

```bash
python3 "$SAM_REFINE_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/current.json"
python3 "$SAM_REFINE_DIR/scripts/validate_report.py" \
  --baseline "$WORK_TMP/baseline.json" \
  --current "$WORK_TMP/current.json" "$WORK_TMP/report.json"
```

The baseline and current file state must match. Follow
[references/output-contract.md](references/output-contract.md). Do not weaken
the validator to force confidence.

When invoked under `sam-task` (or any parent that needs durable receipts), copy
the validated report to `$PLAN_DIR/refine-report.json` (or another absolute path
the parent records as `refine_report_path`) before cleaning temp artifacts.

Retain the report and referenced evidence for caller re-validation; remove only
unused scratch.
