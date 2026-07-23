# Plan Output Contract

## Contents

1. Terminal statuses
2. Report shape
3. Depth invariants
4. Validation
5. Human response

## Terminal statuses

- `READY_TO_EXECUTE`: material claims are factual or explicitly accepted;
  steps have DoD and verification mapping; no open blocker; simplicity cuts
  recorded; council policy for the depth is satisfied.
- `NOT_CONFIDENT`: useful plan exists, but material unknowns, unaccepted
  assumptions, or `NOT_RUN` proofs remain.
- `BLOCKED`: missing access, owner decision, unsafe scope, or council/runtime
  capability prevents a defensible plan.

## Report shape

Write `plan-report.json` (UTF-8 object) with:

- `schema_version`: `1`
- `workflow`: `plan`
- `status`, `depth` (`simple|standard|deep`), `case_type`
- `complexity_rationale` (non-empty)
- `frozen`: `prompt_hash`, `prompt_summary`, `goal`, `non_goals`,
  `success_criteria`, `invariants`, `constraints`, `no_go`
- `output`: `plan_dir`, `html_files` (non-empty list of basenames)
- `evidence[]`: `id`, `kind`, `classification` (`FACT|ASSUMPTION|UNKNOWN`),
  `claim`, `locator`
- `assumptions[]`, `unknowns[]`
- `thesis`: `id`, `summary`, `approach`, `rejected_alternatives`
- `steps[]`: `id`, `title`, `why`, `depends_on`, `surfaces`, `dod`,
  `proof_ids`, `simpler_rejected`
- `risks[]`, `verifications[]` (`PASS|PLANNED|NOT_RUN|BLOCKED|NOT_APPLICABLE`)
- `chapters[]`: `id`, `slug`, `title`, `summary`, `sections[]`
  with `heading` and `blocks[]` (`type` + `text` or `rows`)
- `council`: `required`, `skip_reason`, `runs[]`
- `simplicity`: `cuts`, `retained_complexity_justifications`
- `residuals[]`, `blockers[]`

IDs must be unique within their series (`E-###`, `A-###`, `U-###`, `T-###`,
`S-###`, `R-###`, `V-###`).

## Depth invariants

- `simple`: ≤3 chapters; council may be skipped with reason; ≥1 step.
- `standard`/`deep`: core planning fields populated; if `council.required`,
  at least one run with terminal status is present.
- `READY_TO_EXECUTE` forbids material `UNKNOWN`, open blockers, and verification
  `NOT_RUN`/`BLOCKED` on required proofs. `PLANNED` is allowed for post-implement
  checks with exact method text.

## Validation

```bash
python3 -B scripts/validate_plan_report.py plan-report.json
python3 -B scripts/render_plan_html.py plan-report.json --out "$PLAN_DIR"
```

Re-validate after any report edit. Cite only a validator `VALID` result as
machine proof.

## Human response

Return status, depth, plan directory path, chapter list, thesis summary,
open residuals/blockers, and council skip or result. Do not claim readiness
when the validator fails.
