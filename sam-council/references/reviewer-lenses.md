# Reviewer Lenses

## Required seats

### Logic

Test whether conclusions follow from evidence. Find contradictions, circular
arguments, undefined terms, false dichotomies, hidden scope changes, and success
criteria that do not test the stated objective.

### Assumptions

Identify load-bearing premises. Ask which single false premise invalidates the
plan, what range was assumed, how it was measured, what disconfirms it, and
whether a planned experiment gates execution early enough.

### Execution

Attack sequencing, ownership, dependencies, delivery estimates, environment
parity, migrations, release mechanics, maintenance, incident response, and
decommissioning. Find steps that cannot be verified or reversed.

### Adversarial

Try to break the system through malformed input, abuse, privilege boundaries,
partial failure, concurrency, duplication, reordering, retry storms, timeout,
resource exhaustion, dependency failure, compromised credentials, and
second-order effects.

### Alternatives

Find the smallest solution that meets the objective. Compare no change, manual
operation, feature flags, existing platform capability, buy versus build,
synchronous versus asynchronous flow, phased delivery, and reversible
experiments. Include switching and long-term ownership cost.

### Problem frame

Challenge the requested solution and the definition of success. Test whether
the root problem, affected users, current-state evidence, causal mechanism, and
decision timing are correct. Detect proxy metrics and solution-first framing.

## Conditional seats

Add every seat whose trigger applies.

- **`security-privacy`:** identity, authorization, tenancy, secrets, data
  minimization, retention, audit, supply chain, abuse, and threat model.
- **`data-migration`:** source of truth, schema, integrity, backfill,
  dual-write, reconciliation, ordering, retention, deletion, and rollback.
- **`reliability-performance`:** SLOs, capacity, hot paths, latency budgets,
  queues, caches, backpressure, overload, region failure, and recovery.
- **`api-compatibility`:** contracts, versioning, clients, rollout order,
  idempotency, error semantics, and backward/forward compatibility.
- **`testability-release`:** risk-to-test mapping, deterministic fixtures,
  environment truth, staged rollout, feature flags, canaries, and proof.
- **`operations-observability`:** logs, metrics, traces, alerts, runbooks,
  ownership, support burden, manual repair, and decommissioning.
- **`cost-dependency`:** unit economics, spend ceilings, vendor lock-in,
  quotas, licensing, support, procurement, and exit strategy.
- **`product-ux`:** user value, discoverability, error
  recovery, permissions, accessibility, localization, and behavior change.
- **`compliance-governance`:** applicable policy, audit evidence, retention,
  segregation of duties, approval authority, and jurisdiction.

## Seat selection record

For every conditional seat, record `SELECTED` or `NOT_APPLICABLE` plus a
system-specific reason. “Not relevant” alone is not evidence.

## Reviewer discipline

- Search the assigned lens deeply; do not broaden into a generic review.
- Return no material objection when that is the honest result.
- Prefer one causal failure mechanism over many stylistic observations.
- Separate observed fact, inference, assumption, and missing evidence.
- State what would change the verdict.
- Offer the smallest sufficient correction after proving the failure.
- Never approve by deference to another seat or by expected consensus.
