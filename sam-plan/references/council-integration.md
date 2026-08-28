# Council Integration

## Contents

1. Risk triggers
2. When to invoke
3. What to send
4. How to fold results
5. Policy

## Risk triggers

Set one or more `risk_flags` when the case matches. Non-empty `risk_flags`
**requires** `council.required=true` and at least one recorded run before
`READY_TO_EXECUTE`.

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

If none apply, set `council.required=false` and a concrete `skip_reason`.

The freeze validator also **suggests** flags from `case_type=MIGRATION` and from
goal/step/surface text (migration, authz, privacy, public API, payments, etc.).
`READY_TO_EXECUTE` fails if those suggestions are missing from `risk_flags`.
Do not under-flag to skip council.

## When to invoke

Load and follow `../sam-council/SKILL.md`. Do not emulate council from memory.

| Situation | Council |
| --- | --- |
| No risk flags | Skip; record reason |
| Any risk flag | At least one `fast` pass on the executable thesis (escalate per council) |
| User requests deep adversarial review | Honor; use `full` when council triggers demand it |

Depth labels (`simple` / `standard` / `deep`) never alone force council.

## What to send

Build a relevant-only packet:

- Frozen goal, non-goals, constraints, no-go
- Thesis approach, steps, risks, success criteria
- Evidence and assumption ledgers with locators
- Risk flags and only the chapter text under review (if any)

Cap reviewers per council contract. Prefer fewer load-bearing objections.

## How to fold results

For each material objection:

1. Disposition: `ACCEPT`, `PARTIAL`, `REJECT`, `INVESTIGATE`, or `ACCEPT_RISK`.
2. Apply the smallest plan correction when accepted or partial.
3. Map to step, risk, verification, or residual IDs.
4. Store the validated council report path under `council.runs`.

One council run per plan freeze. After that run, apply the smallest accepted
corrections in the freeze. Do not mint a new thesis id and re-dispatch council
unless the user asked in this turn. `REVISE` after the authorized round becomes
plan `NOT_CONFIDENT` (residuals listed) or `BLOCKED` — not a self-authorized
T-00N loop.

Never report `READY_TO_EXECUTE` while a supported blocker remains, a high risk
is unmitigated without explicit owner acceptance, or the council result is
`BLOCKED` / `REVISE` / `ESCALATE_TO_FULL` without a completed correction pass
**inside the same authorized round**.

`TRIAGE_PASS` is not implementation approval; it only means the bounded triage
found no reason to escalate. Still require a coherent freeze and verification map.

## Policy

A self-critical planner pass is enough when risk flags are empty. If that pass
surfaces a material failure mode, add the matching risk flag and run council.
