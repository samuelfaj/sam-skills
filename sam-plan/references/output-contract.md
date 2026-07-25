# Plan Output Contract

## Contents

1. Terminal statuses
2. Hard freeze core
3. Study and acceptance
4. Optional presentation
5. READY invariants
6. Validation
7. Human response

## Terminal statuses

- `READY_TO_EXECUTE`: material claims are factual or explicitly accepted;
  steps have DoD and verification mapping; no open blocker; study receipts
  present; council policy for risk triggers is satisfied.
- `NOT_CONFIDENT`: useful plan exists, but material unknowns, unaccepted
  assumptions, or `NOT_RUN` proofs remain.
- `BLOCKED`: missing access, owner decision, unsafe scope, or council/runtime
  capability prevents a defensible plan.

## Hard freeze core

Write `plan-report.json` (UTF-8 object) with:

- `schema_version`: `1`
- `workflow`: `plan`
- `status`, `depth` (`simple|standard|deep` as **signal only**), `case_type`
- `complexity_rationale` (non-empty)
- `risk_flags[]` (from the council trigger catalog; may be empty)
- `study`: see below
- `frozen`: `prompt_hash`, `prompt_summary`, `goal`, `non_goals`,
  `success_criteria`, `invariants`, `constraints`, `no_go`
- `output`: `plan_dir` (absolute); `html_files` (may be empty when no pack)
- `evidence[]`: `id`, `kind`, `classification` (`FACT|ASSUMPTION|UNKNOWN`),
  `claim`, `locator` (required when classification is `FACT`)
- `assumptions[]`, `unknowns[]` (`material` bool on unknowns)
- `thesis`: `id`, `summary`, `approach`, `rejected_alternatives`
- `steps[]`: `id`, `title`, `why`, `depends_on`, `surfaces`, `dod`,
  `proof_ids`, optional `simpler_rejected`
- `risks[]`, `verifications[]` (`PASS|PLANNED|NOT_RUN|BLOCKED|NOT_APPLICABLE`)
- `acceptance_trace[]`: map success criteria to steps/proofs
- `council`: `required`, `skip_reason`, `runs[]`
- `simplicity`: `cuts`, `retained_complexity_justifications`
- `residuals[]`, `blockers[]`

IDs should be unique within their series (`E-###`, `A-###`, `U-###`, `T-###`,
`S-###`, `R-###`, `V-###`). Prefer that shape; the hard fail is uniqueness and
reference integrity, not ceremony.

Optional: `chapters[]` for HTML pack bodies. Empty chapters are valid for
compact freeze-only plans.

## Study and acceptance

### `study` (required for READY)

```json
{
  "tools_used": ["graphify query …", "rg InvoiceDetail"],
  "surfaces_mapped": ["src/views/InvoiceDetail.tsx"],
  "prompt_ambiguities": [],
  "repo_root": "/absolute/target/repo"
}
```

- `tools_used` and `surfaces_mapped` must be non-empty for READY except
  `case_type=SPIKE`.
- `repo_root` optional in the file; pass `--repo-root` on validate when possible.

### FACT locators

Prefer repo paths: `path`, `path:line`, or `path:line:col`. Exempt forms:

- `user decision: …` / `decision: …`
- `command: …`

With `--repo-root`, path locators must exist; line numbers must be in range.

### `acceptance_trace` (required for READY when success_criteria set)

Each `frozen.success_criteria` entry must appear as `criterion` with
`step_ids` / `proof_ids` that exist in the freeze.

## Optional presentation

| Mode | When | Artifacts |
| --- | --- | --- |
| Compact (default) | Most plans | `plan-report.json` + chat/MD projection |
| Pack | User asks or handoff risk | Same freeze + HTML via renderer |

Never treat HTML as the success criterion. Parents consume the freeze file.

## READY invariants

`READY_TO_EXECUTE` hard-fails when any of these hold:

1. Non-empty `blockers`
2. Material `unknowns`
3. Open risks with severity `high` or `blocker`
4. Verification status `NOT_RUN` or `BLOCKED`
5. Assumptions in state `UNVERIFIED`
6. Empty `thesis.rejected_alternatives`
7. No FACT evidence with a non-empty locator
8. A step with empty `dod`
9. `council.required` true without at least one run, or runs in
   `BLOCKED` / `REVISE` / `ESCALATE_TO_FULL`
10. Non-empty `risk_flags` while `council.required` is false
11. Missing freeze core fields (goal, thesis approach, ≥1 step)
12. Missing `study` / empty `surfaces_mapped` or `tools_used` (except SPIKE)
13. Success criteria without matching `acceptance_trace`
14. Heuristic risk flags present in goal/steps but absent from `risk_flags`
15. With `--repo-root`: no FACT locator that resolves under the repo

`PLANNED` proofs are allowed when `reason` states the exact post-implement method.

## Validation

```bash
python3 -B scripts/validate_plan_report.py plan-report.json --repo-root "$PWD"
# optional pack:
python3 -B scripts/render_plan_html.py plan-report.json --out "$PLAN_DIR"
python3 -B scripts/validate_plan_report.py plan-report.json --require-html
```

Re-validate after any report edit. Cite only a validator `VALID` result as
machine proof of the freeze.

## Human response

Return status, depth signal, plan directory path, whether HTML was emitted,
thesis summary, open residuals/blockers, risk flags, study surfaces, and
council skip or result. Do not claim readiness when the freeze validator fails.
