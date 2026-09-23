# Complexity Routing

Depth sets plan density only.

| Depth | Use when | Plan shape |
| --- | --- | --- |
| `simple` | One clear change, low risk, reversible, few files | Short freeze; just enough FACT locators to justify the steps; one thesis; tiny verification list |
| `standard` | Multi-step feature or bug with real seams | Same shape, denser evidence and risks; optional lenses |
| `deep` | Product-shaped, migration, multi-system | Dense freeze; only lenses that change decisions |

## `simple` Requires

All hold, or the missing ones are non-material:

- The goal fits one sentence with unambiguous success.
- Small touch surface (about one module, endpoint, screen, or script).
- No migration, auth/privacy boundary change, public contract break, or
  irreversible rollout.
- No multi-team coordination or multi-service orchestration.
- Existing repository patterns already cover the approach.
- The prompt does not request architecture, roadmap, or product-design depth.

High-risk signals block `simple` and map to `risk_flags`: security/privacy,
payments, data migration, destructive ops, production-only paths, public API
compatibility, compliance, multi-provider infrastructure, and hard-to-reverse
schema or state changes.

## Escalation

- Explicit user request for a deep or full product plan: denser freeze and
  richer lenses.
- Council `ESCALATE_TO_FULL` or an open blocker/high risk: deepen the plan
  (READY stays blocked per output-contract READY 1, 3, 15).
