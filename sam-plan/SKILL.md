---
name: sam-plan
description: "Produce a case-specific millimetric HTML execution plan from a prompt, auto-scaling from a compact simple pack to a deep multi-chapter plan, with evidence ledgers, simplicity cuts, and sam-council falsification when load-bearing. Use when the user runs /sam-plan, asks for a detailed implementation plan in HTML, or wants pre-implementation planning like a Lacco-style plan pack."
---

# Sam Plan

## Purpose

Turn one planning prompt into a navigable HTML plan pack tailored to that case.
Scale effort to complexity: simple prompts get a short pack; consequential work
gets evidence, council, and gated chapters. Prefer the smallest plan that still
makes implementation decisions explicit.

## Non-Negotiable Contract

- Do not implement the target system. No production code edits, commits, PRs,
  deploys, or external writes beyond the plan output directory and local
  scratch/report files.
- Separate `FACT`, `ASSUMPTION`, and `UNKNOWN`. Never invent locators or treat
  guesses as facts.
- Auto-classify `simple` | `standard` | `deep` and record `complexity_rationale`.
  Do not run a product-scale ceremony for a trivial prompt.
- Use `sam-council` when required by depth or risk. Do not emulate it.
- Bias to simplicity: cut steps and chapters that do not change decisions.
- Emit structured `plan-report.json`, render HTML via the skill scripts, and
  validate before claiming readiness.
- Redact secrets and private data from all plan artifacts.
- Fail closed: `NOT_CONFIDENT` or `BLOCKED` beats a false `READY_TO_EXECUTE`.

## Required resources

Read before planning:

1. [references/complexity-routing.md](references/complexity-routing.md)
2. [references/chapter-taxonomy.md](references/chapter-taxonomy.md)
3. [references/evidence-policy.md](references/evidence-policy.md)
4. [references/simplicity-rules.md](references/simplicity-rules.md)
5. [references/council-integration.md](references/council-integration.md)
6. [references/html-shell.md](references/html-shell.md)
7. [references/output-contract.md](references/output-contract.md)

When council is required, read and follow `../sam-council/SKILL.md` fully.

Runtime scripts (invoke; do not reimplement):

- `scripts/scaffold_plan_dir.py`
- `scripts/render_plan_html.py`
- `scripts/validate_plan_report.py`

## 1. Freeze intent and classify depth

```bash
SAM_PLAN_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
PLAN_DIR="${PLAN_DIR:-$PWD/plan}"
```

Freeze from the user prompt and repo context:

- Goal, non-goals, success criteria, invariants, constraints, no-go
- Case type: `BUG` | `FEATURE` | `PRODUCT` | `MIGRATION` | `OPS` | `SPIKE`
- Prompt hash and short summary
- Depth via complexity-routing (`simple` when the prompt is clearly small)

If the prompt is a one-liner with an obvious local change and no high-risk
signal, choose `simple` and keep the rest of the workflow short.

## 2. Scaffold output

```bash
python3 -B "$SAM_PLAN_DIR/scripts/scaffold_plan_dir.py" --out "$PLAN_DIR"
```

Only the plan directory is a write surface for artifacts. Leave unrelated dirty
work untouched.

## 3. Gather evidence (proportional)

Inspect only what the depth needs. Build evidence, assumptions, and unknowns
with stable IDs and locators. For `simple`, a handful of facts that justify the
steps is enough. For `standard`/`deep`, cover every load-bearing claim.

## 4. Draft thesis, steps, and chapters

Write the plan as structured data first (the report), not free-form HTML.

- Thesis `T-###` with approach and rejected alternatives
- Ordered steps `S-###` with why, deps, surfaces, DoD, proof IDs, and any
  simpler option rejected
- Risks `R-###` and verifications `V-###`
- Chapters per taxonomy for the selected depth only
- Simplicity cuts list

For `simple`, prefer one overview chapter plus steps (or a single merged
`00-plano` chapter). Skip empty risk/council pages.

## 5. Council (when required)

Follow [references/council-integration.md](references/council-integration.md).

- `simple` + no high-risk trigger: skip council; set `council.required=false`
  and a concrete `skip_reason`
- `standard`: at least one `fast` council on the executable thesis
- `deep` or council triggers: escalate per sam-council; fold objections into
  the smallest plan corrections

Store run receipts under `council.runs`. Re-draft affected steps/chapters after
accepted objections.

## 6. Render HTML and validate

Write `$WORK_TMP/plan-report.json` per the output contract, including chapter
bodies as structured sections/blocks.

```bash
python3 -B "$SAM_PLAN_DIR/scripts/validate_plan_report.py" \
  "$WORK_TMP/plan-report.json"
python3 -B "$SAM_PLAN_DIR/scripts/render_plan_html.py" \
  "$WORK_TMP/plan-report.json" --out "$PLAN_DIR"
python3 -B "$SAM_PLAN_DIR/scripts/validate_plan_report.py" \
  "$PLAN_DIR/plan-report.json" --require-html
```

Copy the validated report into `$PLAN_DIR/plan-report.json` if not already
written there by the renderer.

## 7. Return

Report:

1. Terminal status: `READY_TO_EXECUTE` | `NOT_CONFIDENT` | `BLOCKED`
2. Depth, case type, and complexity rationale
3. Absolute plan directory and HTML file list
4. Thesis summary and step count
5. Council skipped (reason) or terminal council result
6. Residuals, blockers, and accepted risks
7. Validator result

Do not claim readiness without a passing validator. Remove scratch outside the
plan directory when done.

## Operating notes

- Locale: match the user's language for HTML prose when practical.
- Visual bar: multi-file sticky-nav HTML similar to a Lacco plan pack, but
  chapter set is case-specific—not a fixed product template.
- Parent workflows may set `PLAN_DIR`. Default is `$PWD/plan`.
- Run `scripts/test_plan_harness.py` only when changing this skill.
