# Reviewer Lenses

## Fast seats

### Frame and evidence

Test the problem definition, causal logic, conclusions, load-bearing premises,
evidence quality, success criteria, and what would disconfirm the thesis.

### Delivery and failure

Attack sequencing, ownership, dependencies, migrations, operations, abuse,
privilege boundaries, concurrency, retries, partial failure, resource
exhaustion, recovery, and second-order effects.

### Simplification

Find the smallest solution that meets the objective. Compare no change, manual
operation, existing capability, feature flags, phased delivery, buy versus
build, and reversible experiments.

Fast seats only triage. Any applicable conditional domain, critical unknown,
supported blocker/high, or material displaced risk requires
`ESCALATE_TO_FULL`.

## Full required seats

- **`logic`:** contradictions, invalid inference, undefined terms, scope drift,
  false choices, and success criteria that miss the objective.
- **`assumptions`:** load-bearing premises, expected ranges, measurement,
  disconfirming evidence, and experiments that gate execution.
- **`execution`:** delivery, ownership, dependencies, estimates, environment
  parity, migration, release, maintenance, incident response, and retirement.
- **`adversarial`:** malformed input, abuse, authorization, concurrency,
  duplication, reordering, retry storms, timeout, exhaustion, dependency
  failure, compromised credentials, and second-order effects.
- **`alternatives`:** smaller, cheaper, reversible, manual, existing, buy/build,
  synchronous/asynchronous, and phased alternatives with ownership cost.
- **`problem-frame`:** root problem, affected users, current evidence, causal
  mechanism, timing, proxy metrics, and solution-first framing.

## Conditional specialists

Select every applicable domain in `full`. In `fast`, record `ESCALATE:` for an
applicable domain and stop after triage.

- `security-privacy`: identity, authorization, tenancy, secrets, privacy,
  retention, audit, supply chain, and abuse.
- `data-migration`: source of truth, schema, integrity, backfill, dual-write,
  reconciliation, ordering, deletion, and recovery.
- `reliability-performance`: SLOs, capacity, latency, queues, caches,
  backpressure, overload, region failure, and recovery.
- `api-compatibility`: contracts, versions, clients, rollout order,
  idempotency, errors, and compatibility.
- `testability-release`: risk-to-test mapping, fixtures, environment truth,
  staged rollout, flags, canaries, and proof.
- `operations-observability`: logs, metrics, traces, alerts, runbooks,
  ownership, repair, and retirement.
- `cost-dependency`: unit economics, ceilings, lock-in, quotas, licensing,
  procurement, support, and exit.
- `product-ux`: user value, discoverability, recovery, permissions,
  accessibility, localization, and behavior change.
- `compliance-governance`: policy, audit evidence, retention, segregation of
  duties, authority, and jurisdiction.

Record every specialist as `SELECTED:`, `ESCALATE:`, or `NOT_APPLICABLE:` with
a system-specific reason. `SELECTED:` is valid only in `full`; `ESCALATE:` is
valid only in `fast`.

## Reviewer discipline

- Stay inside the assigned lens.
- Return at most 3 material objections and at most 1,000 words.
- Prefer one causal mechanism over multiple stylistic observations.
- Separate fact, inference, assumption, and missing evidence.
- State what would change the verdict and the smallest sufficient correction.
- Return `NO_MATERIAL_OBJECTION` when honest.
- Never approve by deference or vote count.
