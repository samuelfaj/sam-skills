# Complexity Routing

## Contents

1. Depth levels
2. Classification signals
3. Required effort by depth
4. Escalation rules

## Depth levels

| Depth | Use when | Chapters | Council |
| --- | --- | --- | --- |
| `simple` | One clear change, low risk, reversible, few files | 1–3 core only | Optional; skip when no high-risk trigger |
| `standard` | Multi-step feature/bug with real seams | Core pack | At least one `fast` pass on the executable thesis |
| `deep` | Product-shaped, migration, security, multi-system | Core + every gated chapter that changes decisions | Skeleton `fast` + close pass; `full` when council triggers fire |

Default when uncertain: `standard`. Prefer `simple` over ceremony.

## Classification signals for `simple`

All of the following should hold, or the missing ones must be non-material:

- Goal fits in one sentence with unambiguous success.
- Touch surface is small (about one module, endpoint, screen, or script).
- No migration, auth/privacy boundary change, public contract break, or irreversible rollout.
- No multi-team coordination or multi-service orchestration.
- Existing patterns in the repo already cover the approach.
- User prompt does not request architecture, roadmap, or product design depth.

If any high-risk signal appears, do not stay on `simple`.

## High-risk signals (block `simple`)

Security/privacy, payments, data migration, destructive ops, production-only paths,
public API compatibility, compliance, multi-provider infrastructure, or hard-to-reverse
schema/state changes.

## Required effort by depth

### `simple`

1. Freeze goal, non-goals, success, and no-go in one short block.
2. Minimal evidence: enough facts to justify the chosen steps.
3. One thesis, ordered steps with DoD, and a tiny verification list.
4. Skip council when no high-risk trigger; record `council.skip_reason`.
5. Render a compact HTML pack (overview + steps; risks only if any).

### `standard`

Full core chapter set, evidence ledger, simplicity cuts, verification map, and at
least one validated `sam-council` `fast` run on the executable thesis. Escalate to
`full` when the council contract requires it.

### `deep`

Everything in `standard`, plus every gated chapter that changes an implementation
decision, residual decision log, and a closing council pass on the final thesis.

## Escalation rules

- Explicit user request for `deep` / full product plan → honor it.
- Council `ESCALATE_TO_FULL` or open blocker/high → deepen the plan; do not report
  `READY_TO_EXECUTE` while those remain open.
- Do not invent chapters to look thorough. Prefer fewer pages that change decisions.
