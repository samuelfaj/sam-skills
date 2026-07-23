# Council Integration

## Contents

1. When to invoke
2. What to send
3. How to fold results
4. Depth policy

## When to invoke

Load and follow `../sam-council/SKILL.md` and its references. Do not emulate
council from memory.

| Depth | Minimum council |
| --- | --- |
| `simple` | None if no high-risk trigger; record skip reason |
| `standard` | One `fast` pass on the executable thesis `T-*` |
| `deep` | Skeleton pass + closing pass; use `full` when triggers fire |

Always escalate off pure skip when security, migration, irreversibility, or
other council full-triggers apply—even if the prose looks short.

## What to send

Build a relevant-only packet:

- Frozen goal, non-goals, constraints, no-go
- Thesis approach, steps, risks, and success criteria
- Evidence and assumption ledgers with locators
- Only the chapter text under review

Cap reviewers per council contract. Prefer fewer load-bearing objections.

## How to fold results

For each material objection:

1. Disposition: `ACCEPT`, `PARTIAL`, `REJECT`, `INVESTIGATE`, or `ACCEPT_RISK`.
2. Apply the smallest plan correction when accepted or partial.
3. Map to step, risk, verification, or residual IDs.
4. Store the validated council report path under `council.runs`.

Never report `READY_TO_EXECUTE` while a supported blocker remains, a high risk
is unmitigated without explicit owner acceptance, or the council result is
`BLOCKED` / `REVISE` without a completed correction pass.

`TRIAGE_PASS` is not implementation approval; it only means the bounded triage
found no reason to escalate. Still require a coherent plan and verification map.

## Depth policy

On `simple`, a self-critical pass by the planner is enough when risk is low.
If that pass surfaces a material failure mode, escalate depth and run council.
