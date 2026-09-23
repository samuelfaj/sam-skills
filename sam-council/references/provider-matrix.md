# Multi-Provider Matrix

## Providers

A provider is any independent agent runtime that can receive the frozen
packet, stay read-only, and return the response contract (for example
`codex`, `claude-code`, `grok`, `local-agent`). Pass one `--provider` per
provider to `init`, the controller's first.

## Panels

Every provider runs the full required panel plus every selected specialist
against the same packet. Seat IDs are `{provider}/{seat}` from listed
providers; each result's `provider` equals its ID prefix. Blindness holds
across seats and providers. Verifiers: fresh `closure-verifier`,
`system-verifier`, and `meta-arbiter` (replacing `arbiter`).

## Confrontation

After blind synthesis:

1. Build one evidence-backed position per provider.
2. Send each provider its own prior material claims plus peers' material
   claims, never a vote tally or desired result.
3. Require `ACCEPT`, `REBUT`, or `CONCEDE` with evidence IDs; a rebuttal
   without stronger evidence leaves the claim open.
4. Preserve supported minority blockers.
5. The meta-arbiter weighs evidence quality, severity, reversibility, and proof
   of closure; provider count has no decision weight.

Record `confrontation` (required unless `BLOCKED`): `provider_positions` (one
per provider: `provider`, `stance` `APPROVE|APPROVE_WITH_CONDITIONS|REVISE|BLOCK`,
`material_objection_ids`, `preferred_correction`), `disagreements` (`topic`,
`provider_ids`, `summary`), `resolution: "EVIDENCE_WEIGHTED"`,
`surviving_claim_ids`, `rejected_claim_summaries`, `rationale`.

## Fallbacks

- A named provider is unavailable: report the exact failure; continue only
  while the user's requested minimum provider count remains available.
- Fewer than two remain: downgrade to `single-host` if multi-provider was
  optional; return `BLOCKED` if it was mandatory.
