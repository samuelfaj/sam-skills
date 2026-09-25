# Plan Output Contract

`plan-report.json` is one UTF-8 JSON object. The scaffold prefills mechanical
fields and the renderer writes `output`; fill the rest in place.

```jsonc
{
  "schema_version": 1, "workflow": "plan", "status": "READY_TO_EXECUTE|NOT_CONFIDENT|BLOCKED",
  "depth": "simple|standard|deep", "case_type": "BUG|FEATURE|PRODUCT|MIGRATION|OPS|SPIKE",
  "complexity_rationale": "", "risk_flags": [],
  "risk_flag_dismissals": [{"flag": "", "reason": "", "evidence_ids": ["E-001"]}],  // optional
  "study": {"tools_used": [], "surfaces_mapped": [], "prompt_ambiguities": [], "repo_root": "/abs"},
  "frozen": {"prompt_hash": "", "prompt_summary": "", "goal": "", "non_goals": [],
             "success_criteria": [], "invariants": [], "constraints": [], "no_go": []},
  "output": {"plan_dir": "/abs", "html_files": ["00-plano.html"], "agent_file": "agent-plan.md",
              "artifact_sha256": {}, "rendered_report_sha256": ""},
  "evidence": [{"id": "E-001", "kind": "CODE", "classification": "FACT|ASSUMPTION|UNKNOWN",
                "claim": "", "locator": "required for FACT"}],
  "assumptions": [{"id": "A-001", "claim": "", "state": "UNVERIFIED|ACCEPTED|VERIFIED|REJECTED",
                   "evidence_ids": [], "decision_reason": ""}],
  "unknowns": [{"id": "U-001", "claim": "", "material": true, "probe": "", "why_immaterial": ""}],
  "thesis": {"id": "T-001", "summary": "", "approach": "", "rejected_alternatives": []},
  "steps": [{"id": "S-001", "title": "", "why": "", "how": [], "depends_on": [], "surfaces": [],
             "dod": [], "proof_ids": ["V-001"], "preconditions": [], "simpler_rejected": null,
             "out_of_acceptance": ""}],
  "risks": [{"id": "R-001", "claim": "", "severity": "low|medium|high|blocker", "mitigation": "",
             "status": "OPEN|MITIGATED|ACCEPTED|CLOSED"}],
  "verifications": [{"id": "V-001", "proof": "", "reason": "", "claim_ids": [],
                     "status": "PASS|PLANNED|NOT_RUN|BLOCKED|NOT_APPLICABLE"}],
  "acceptance_trace": [{"criterion": "exact success_criteria text", "step_ids": [], "proof_ids": []}],
  "council": {"required": false, "skip_reason": "",
              "runs": [{"profile": "fast|full", "status": "", "thesis_id": "T-001", "report_path": "/abs"}]},
  "simplicity": {"cuts": [], "retained_complexity_justifications": []},
  "chapters": [], "residuals": [], "blockers": []
}
```

`frozen.prompt_hash` is the sha256 hex of the exact prompt bytes (scaffold
`--prompt-file`); under a parent it is the parent's frozen prompt sha256, which
`sam-task` requires to equal `request.prompt_sha256`. Optional unless a rule
requires them: `chapters` (schema in chapter-taxonomy.md), `preconditions`
(evidence/assumption IDs), `simpler_rejected`, `out_of_acceptance`, `probe`,
`why_immaterial`, `decision_reason`.

## Risk Flags

`risk_flags` holds every flag that applies:

| Flag | Fire when |
| --- | --- |
| `security_privacy` | Secrets, PII, tenancy, authz, abuse surface |
| `auth_boundary` | Login, roles, permissions, session, identity change |
| `data_migration` | Schema, backfill, dual-write, data rewrite |
| `irreversible` | Hard-to-reverse state, destructive ops, one-way rollout |
| `public_contract` | Public API/SDK/event compatibility |
| `multi_service` | Cross-service orchestration or multi-system cutover |
| `payments` | Charges, payouts, invoices, money movement |
| `compliance` | Regulated process, audit, retention, jurisdiction |
| `user_requested_council` | User explicitly asked for council/adversarial review |
| `material_uncertainty` | Load-bearing unknown or assumption the planner cannot close |

The validator suggests flags from `case_type=MIGRATION` and from goal, summary, step, and surface keywords (READY 14).

## Structural Rules (every status)

- Non-empty text: `complexity_rationale`, `frozen.prompt_hash`, `prompt_summary`, `goal`, `output.plan_dir`, thesis `id`/`summary`/`approach`, every item's `claim`, `kind`, `state`, `title`, `why`, `severity`, `mitigation`, `proof`, `status`, and `criterion`, and a FACT's `locator`.
- String lists hold non-empty, unique strings. IDs are unique per series; an id shaped like a series must match `E-###`, `A-###`, `U-###`, `T-###`, `S-###`, `R-###`, or `V-###` (3+ digits); other short ids are accepted.
- References resolve: assumption `evidence_ids` to evidence; `depends_on` and trace `step_ids` to steps; step and trace `proof_ids` to verifications.
- `steps` is non-empty; every step has non-empty `dod`. `unknowns[].material` is boolean. `PLANNED` needs a `reason` with the exact post-implementation method.
- `council.required=true`: empty `skip_reason` and at least one run, each with `profile` `fast|full`, a council terminal `status` (`TRIAGE_PASS|ESCALATE_TO_FULL|APPROVED|APPROVED_WITH_CONDITIONS|REVISE|BLOCKED`), `thesis_id`, and an absolute `report_path` to a council report whose `status` equals the run's. `required=false`: non-empty `skip_reason`. Non-empty `risk_flags` needs `required=true`.
- `risk_flag_dismissals[]` (only for a keyword false positive, e.g. a UI-only folder named `session`): unique keyword flags (never `user_requested_council` or `material_uncertainty`), none in `risk_flags`, none matched by `frozen.goal`/`prompt_summary`, and never `data_migration`/`irreversible` under `case_type=MIGRATION`; non-empty `reason`; at least one `evidence_ids`, each a FACT whose locator shows the risk is absent (with a known repo, a file path under it).
- `output.html_files`: `.html` basenames; with chapters, one `<id>-<slug>.html` each.
- `NOT_CONFIDENT` and `BLOCKED` need residuals, blockers, material unknowns, or `NOT_RUN`/`BLOCKED` proofs.
- With `--repo-root` (or a resolvable `study.repo_root`), FACT path locators must exist under the repo with line numbers in range.
- `--require-html`: `plan_dir` exists and holds `plan-report.json` and every listed HTML file, each containing `<html` and `<nav`.

## READY Invariants

`READY_TO_EXECUTE` fails when any holds (`case_type=SPIKE` exempt where marked):

1. Non-empty `blockers`.
2. A material unknown (material unknowns also need `probe`).
3. A `high` or `blocker` risk with status `OPEN`.
4. A verification `NOT_RUN` or `BLOCKED`.
5. An `UNVERIFIED` assumption, or an `ACCEPTED` one without `decision_reason` or `evidence_ids`.
6. Empty `thesis.rejected_alternatives`.
7. No FACT with a locator; with `--repo-root`, none that resolves (a `user decision:` locator counts).
8. A FACT claim with hedge language (appears, seems, maybe, likely, probably, roughly, approximately, might, could be).
9. Missing `study`, or empty `surfaces_mapped` or `tools_used` (SPIKE exempt).
10. Empty `frozen.success_criteria` (SPIKE exempt), a criterion absent from `acceptance_trace`, or a trace entry without a `step_ids` and a `proof_ids`.
11. Depth other than `simple`: a step in no trace `step_ids` and without an `out_of_acceptance` reason, or an immaterial unknown without `why_immaterial`.
12. A step with `dod` but no `proof_ids`; with empty `how[]` or only bullets that restate the title or are under 8 characters; or with empty `surfaces` (SPIKE exempt).
13. A `depends_on` cycle.
14. A heuristic flag suggestion neither in `risk_flags` nor validly dismissed.
15. A council run with status `BLOCKED`, `REVISE`, or `ESCALATE_TO_FULL`.
