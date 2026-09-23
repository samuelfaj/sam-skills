# Review Output Contract

One schema for every target mode. Keys are exact (missing or extra keys fail); `schema_version` is `1`. Keep *derived* values as the scaffold wrote them.

| Field | Rule |
| --- | --- |
| `target` `{mode, base_sha, head_sha, bundle_fingerprint}` | *derived* from the bundle |
| `intent` | non-empty lists `intended_behavior`, `invariants`; list `must_not_change`; non-empty `owner_boundary`; boolean `user_visible_change` |
| `scope` | *derived* `current_file_count`, `current_non_test_lines` (bundle summary); integers ≥ 0 `baseline_file_count`, `baseline_non_test_lines` (first-cycle counts); `review_cycle` ≥ 1; booleans `scope_expansion_approved` (user approved a change to the agreed goal or contracts) and `remaining_findings_reclassified` (`review_cycle > 2` without it is a convergence block) |
| `file_coverage[]` `{path, classification, reason}` | one row per bundle path; `REVIEWED`, `GENERATED`, `TYPE_ONLY`, `TEST`, `CONFIG`, `EXCLUDED`; reason required |
| `test_coverage[]` `{behavior, level, status, paths, reason, finding_id}` | ≥ 1; level `UNIT`, `INTEGRATION`, `E2E`, `CONTRACT`, `STATIC`, `MANUAL`; status `COVERED` (a meaningful existing or changed test proves it), `MISSING_REQUIRED` (every test-policy.md Required-Test Gate condition holds; links an accepted `BLOCKER` with `test_gap: true`), `MISSING_OPTIONAL` (useful hardening without merge-blocking risk), `UNSUPPORTED` (the repository lacks that level; name the closest safe proof), `NOT_APPLICABLE` (say why); other rows' `finding_id` null or known |
| `validations[]` `{command, status, classification, reason, receipt?}` | ≥ 1; `PASS`, `FAIL`, `NOT_RUN`; class per SKILL §5; reason required. `PASS`/`FAIL` cite the absolute run_checked `receipt` and match it (*derived*: `command` = argv joined by single spaces, status, classification); `PASS` needs all-zero exits, `FAIL` a non-zero one. `NOT_RUN` has no receipt |
| `behavior_proof` `{status, evidence}` | `PROVEN` (evidence required), `NOT_PROVEN`, `NOT_APPLICABLE` |
| `decision` `{result, confidence, non_gating_requested, remaining_corrections}` | see Decision; `LOW`, `MEDIUM`, `HIGH`; boolean; string list |
| `publication` | keep the *derived* `NOT_REQUESTED` block unless a precise action is authorized (publication-policy.md § Report Fields); non-proposal targets allow only it |
| `review_basis` | optional; see Review Basis |

**Findings** `{id, severity, status, scope, path, line, side, failure_mode, impact, evidence, required_change, test_gap, rejection_reason}`: unique `id`; `BLOCKER`, `IMPORTANT`, `SUGGESTION`; `ACCEPTED`, `REJECTED`, `FOLLOW_UP`, `STOP_AND_ESCALATE`; scope `IN_SCOPE`, `FOLLOW_UP`, `STOP_AND_ESCALATE`; boolean `test_gap`. `path` null or a bundle path; `line` null or positive inside that `side`'s changed ranges; `side` `NEW`/`OLD`, required with a line. `ACCEPTED`: non-empty `failure_mode`, `impact`, `evidence`, `required_change`; null `rejection_reason`; `test_gap` only on a `BLOCKER` with a `MISSING_REQUIRED` row. `REJECTED`: `rejection_reason`. `STOP_AND_ESCALATE`: `failure_mode`, `impact`, `evidence`.

## Decision

| Result | Choose when (validator-enforced unless marked) |
| --- | --- |
| `CHANGES_REQUIRED` | an accepted `BLOCKER`/`IMPORTANT` remains (a required test gap or `TARGET`/`INTRODUCED` `FAIL` must be an accepted `BLOCKER`) and nothing escalates (reviewer rule); `remaining_corrections` = exactly those ids |
| `BLOCKED` | an unresolved `STOP_AND_ESCALATE`, scope, or convergence condition (the validator also accepts a remaining correction; never choose `BLOCKED` for that alone) |
| `APPROVE` | no required correction, `STOP_AND_ESCALATE`, convergence block, or target `FAIL`; no flaky and only repeated `STABLE` target receipts; `PROVEN` when `user_visible_change`; empty `remaining_corrections` |
| `COMMENT_ONLY` | `non_gating_requested: true` (explicit non-gating request) |

`SUGGESTION` never blocks.

## Review Basis

R0 (bundle B0, head H0) is the most recent VALID report for this target (the previous cycle), never an older one. Cite it as the base only if it still validates, receipts included, with the same target mode, base SHA, and `--path` filters. Otherwise run FULL without a base: re-adjudicate every open R0 finding by hand (below); set `review_cycle` to R0's + 1 and `baseline_*` to first-cycle counts (the scaffold prefills cycle 1).

Run DELTA only for `branch`/`range`/`proposal`, and only when the delta touches no public contract/API/schema, auth/security/permissions, persistence/migrations, shared module used outside the change, or risk path (a bundle risk tag or a `lock|sign|notar|public|export` substring) and has no more changed lines than the original change; otherwise FULL. DELTA also builds `--mode range --range H0..H1 --out <work>/delta-<c>` with the same `--path` filters, reads only that patch, and reviews its hunks and the callers/callees of touched symbols.

Scaffold with `--base-review <R0> --base-bundle <B0>`, plus `--delta-bundle <work>/delta-<c>/bundle.json` for DELTA. It copies frozen intent and R0's open findings (accepted `BLOCKER`/`IMPORTANT`, `STOP_AND_ESCALATE`). Re-adjudicate each open R0 finding: it stays in `findings` by id or, once fixed, moves to `resolved_findings[]` `{id, evidence}`, never both; with a base, only open base findings resolve. DELTA carries rows whose per-file patch is byte-identical into `carried_forward` (keep them equal to the base's) and base `test_coverage` rows with `reason` cleared: re-affirm or replace each.

`review_basis` `{mode, base_review, base_bundle, delta_bundle, carried_forward, resolved_findings}` is scaffold-written: mode `FULL` or `DELTA`; without `base_review` it is FULL with the rest null or empty, except `resolved_findings`. The validator recomputes the mode, risk-path, and size triggers.
