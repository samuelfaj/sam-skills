---
name: sam-plan
description: "Conduct task study and emit a machine freeze plan (goal, thesis, steps, evidence, status) plus a required light-theme HTML pack for humans; assertive investigation first, council only on risk triggers. Use when the user runs /sam-plan, asks for an implementation plan, or needs pre-implementation planning before sam-task/sam-work."
---

# Sam Plan

## Purpose

Turn one planning prompt into a **conducted inquiry + decision freeze**, not a
document factory. Investigate the repo, freeze decisions, and emit:

1. Machine freeze: `plan-report.json` for parents (`sam-task`, validators)
2. **Human plan pack: light-theme HTML** under `$PLAN_DIR` so people can read
   the plan without parsing JSON

Default human presentation is always HTML (light theme). Chat/Markdown may
summarize, but the durable human artifact is the HTML pack.

## Non-Negotiable Contract

Honesty and scope only—presentation form for humans is HTML light pack.

- Do not implement the target system. No production code edits, commits, PRs,
  deploys, or external writes beyond the plan output directory and local
  scratch/report files.
- Separate `FACT`, `ASSUMPTION`, and `UNKNOWN`. Never invent locators or promote
  guesses to facts.
- Always emit a validated machine freeze (`plan-report.json`) **and** a rendered
  light-theme HTML pack (`scripts/render_plan_html.py` + `--require-html`).
- Fail closed: `NOT_CONFIDENT` or `BLOCKED` beats a false `READY_TO_EXECUTE`.
- Council only on risk triggers or explicit user request—not on depth labels.
- Redact secrets and private data from all plan artifacts.
- Prefer the smallest plan that still makes implementation decisions explicit
  ([references/simplicity-rules.md](references/simplicity-rules.md)).

## Machine freeze (always)

For any terminal plan, write `$PLAN_DIR/plan-report.json` with the **hard core**
in [references/output-contract.md](references/output-contract.md):

- Frozen goal, success, invariants, no-go
- `study` receipts: `tools_used`, `surfaces_mapped` (and optional `repo_root`)
- Thesis (approach + rejected alternatives)
- Ordered steps with DoD and proof methods
- Material FACT/ASSUMPTION/UNKNOWN with **real** locators on facts
- `acceptance_trace` mapping each success criterion → steps/proofs
- Status, residuals, blockers, risk flags (include heuristic matches)
- Council policy for risk triggers (run or explicit skip reason)

Chat or Markdown is a **projection** of this freeze. It does not replace it for
`sam-task` or other parents. HTML is the human-readable projection and is
required on every terminal plan.

## Resources (load on demand)

Always:

1. [references/output-contract.md](references/output-contract.md) — freeze + READY invariants
2. [references/simplicity-rules.md](references/simplicity-rules.md)
3. [references/html-shell.md](references/html-shell.md) — required light HTML pack

When classifying effort or risk:

4. [references/complexity-routing.md](references/complexity-routing.md)
5. [references/evidence-policy.md](references/evidence-policy.md)

When risk triggers fire or the user requests council:

6. [references/council-integration.md](references/council-integration.md)
7. `../sam-council/SKILL.md` (full; do not emulate)

When enriching the HTML pack with extra lenses:

8. [references/chapter-taxonomy.md](references/chapter-taxonomy.md) — optional lenses only

Runtime scripts (invoke; do not reimplement):

- `scripts/scaffold_plan_dir.py`
- `scripts/validate_plan_report.py`
- `scripts/render_plan_html.py` (required human pack)

## Study loop (assertive conduct)

Run this **before** drafting the freeze. Ask the user only when a material
unknown blocks planning; otherwise investigate with tools first.

1. **Freeze intent** — goal, non-goals, success criteria, invariants, constraints, no-go from the prompt and explicit owner decisions.
2. **Map surfaces** — locate code, tests, configs, and seams; record them in
   `study.surfaces_mapped` and note tools in `study.tools_used`.
3. **Ledger** — material FACT / ASSUMPTION / UNKNOWN with stable IDs; FACT needs a
   locator that exists in the repo (`path` or `path:line`) or `user decision: …`.
4. **Thesis** — falsifiable approach plus at least one simpler path rejected with reason.
5. **Steps** — ordered work with why, surfaces, DoD, and proof method IDs.
6. **Gates** — risks, risk flags (do not under-flag migration/auth/etc.),
   `acceptance_trace`, residuals; what must be true for `READY_TO_EXECUTE`.

Decision points that must appear in the freeze (not empty template pages):

- Chosen approach and rejected alternatives
- Risks accepted or mitigated
- Open material unknowns (if any → not READY)
- Council required vs skipped with concrete reason

## Workflow

```bash
SAM_PLAN_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
PLAN_DIR="${PLAN_DIR:-$PWD/plan}"
```

### 1. Scaffold

```bash
python3 -B "$SAM_PLAN_DIR/scripts/scaffold_plan_dir.py" --out "$PLAN_DIR"
```

Only the plan directory is a write surface for artifacts.

### 2. Study, then draft freeze

Build `plan-report.json` from the study loop. Record depth signal
(`simple` | `standard` | `deep`) as rationale only—it does **not** force a
chapter matrix or automatic council.

Set `risk_flags` from [references/council-integration.md](references/council-integration.md).
If any risk trigger is present, run `sam-council` and record the run; do not
require council merely because depth is `standard`.

### 3. Validate freeze (hard core)

Prefer resolving locators against the target repo:

```bash
REPO_ROOT="${REPO_ROOT:-$PWD}"
python3 -B "$SAM_PLAN_DIR/scripts/validate_plan_report.py" \
  "$WORK_TMP/plan-report.json" \
  --repo-root "$REPO_ROOT"
```

`--repo-root` enables path/line checks for FACT locators. Omit only when the
target tree is unavailable (`BLOCKED` / `NOT_CONFIDENT` is better than fake
paths). Copy the validated report to `$PLAN_DIR/plan-report.json`.

### 4. Required HTML pack (light theme, for humans)

Always render a human-readable light-theme HTML pack after a valid freeze:

- Optionally attach `chapters[]` (lenses from the taxonomy catalog—not a required set).
- If `chapters` is empty, the renderer synthesizes a single compact page from the freeze.
- Theme is light (soft page background, white cards)—never emit a dark-only pack.

```bash
python3 -B "$SAM_PLAN_DIR/scripts/render_plan_html.py" \
  "$PLAN_DIR/plan-report.json" --out "$PLAN_DIR"
python3 -B "$SAM_PLAN_DIR/scripts/validate_plan_report.py" \
  "$PLAN_DIR/plan-report.json" --require-html
```

Open the primary HTML file (e.g. `00-plano.html` or the first entry in
`output.html_files`) as the human plan. Parents still consume `plan-report.json`.

### 5. Return

Report:

1. Terminal status: `READY_TO_EXECUTE` | `NOT_CONFIDENT` | `BLOCKED`
2. Depth signal and complexity rationale
3. Absolute `PLAN_DIR`, primary HTML path(s), and freeze path
4. Thesis summary and step count
5. Council skipped (reason) or terminal council result
6. Residuals, blockers, risk flags
7. Validator result (`VALID` with HTML on disk required before claiming a finished plan)

Do not claim a finished plan without a passing freeze validator **and** rendered
HTML under `$PLAN_DIR`. Remove scratch outside the plan directory when done.

## Operating notes

- Locale: match the user's language for prose projections and HTML body when practical.
- Parent workflows may set `PLAN_DIR`. Default is `$PWD/plan`.
- `sam-task` advances on validated freeze core (`plan-report.json`); HTML is the
  required human artifact of this skill, not the parent machine gate.
- Run `scripts/test_plan_harness.py` only when changing this skill.
