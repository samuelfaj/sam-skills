# Complexity Routing

## Contents

1. Depth signals
2. Classification signals
3. Effort guidance
4. Escalation rules

## Depth signals

Depth is a **routing signal**, not a chapter or council lock.

| Depth | Use when | Plan shape | Council |
| --- | --- | --- | --- |
| `simple` | One clear change, low risk, reversible, few files | Compact freeze + light HTML pack | Skip unless a risk trigger fires |
| `standard` | Multi-step feature/bug with real seams | Denser freeze + light HTML; optional lenses | Only on risk triggers or user request |
| `deep` | Product-shaped, migration, multi-system | Dense freeze + light HTML; lenses that change decisions | Risk triggers likely; escalate per council |

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
schema/state changes. Map these into `risk_flags` (see council-integration).

## Effort guidance

### `simple`

1. Short freeze of goal, non-goals, success, no-go.
2. Minimal evidence: enough FACT locators to justify the steps.
3. One thesis, ordered steps with DoD, tiny verification list.
4. Skip council when no risk trigger; record `council.skip_reason`.

### `standard` / `deep`

Same freeze shape, denser evidence and risks. Always render the light-theme HTML
pack. Add optional chapter lenses only when they change an implementation
decision. Run council when risk triggers fire or the user requests it—not
because the depth label is `standard`.

## Escalation rules

- Explicit user request for deep / full product plan → denser freeze and richer HTML lenses.
- Council `ESCALATE_TO_FULL` or open blocker/high → deepen the plan; do not report
  `READY_TO_EXECUTE` while those remain open.
- Do not invent chapters to look thorough. Prefer fewer pages that change decisions.
