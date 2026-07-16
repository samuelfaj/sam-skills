# Risk Lenses

Apply only the lenses activated by the actual diff.

- Security and authorization: trust boundaries, identity, permissions,
  validation, secret handling, injection, and sensitive-data exposure.
- Data and migrations: compatibility, existing rows, constraints, indexes,
  transactions, rollback or recovery, and partial failure.
- Concurrency and state: ordering, idempotency, retries, duplicate work, atomic
  updates, stale reads, cache invalidation, and cleanup.
- Public contracts: API, event, schema, type, CLI, file format, configuration,
  generated client, and backward compatibility.
- Integrations: timeouts, retries, provider normalization, rate limits,
  observability, and failure mapping.
- Delivery: CI permissions, environment assumptions, packaging, signing,
  deployment ordering, rollback, and reproducibility.
- User experience: loading, error, empty and partial states, accessibility,
  focus, keyboard behavior, useful feedback, and destructive-action safety.
- Performance: query count, I/O in loops, bounded parallelism, pagination,
  allocation, rendering, and realistic scale.
- Maintainability: ownership, hidden coupling, duplicate policy, unnecessary
  branches, leaky abstractions, and testability.

Maintainability is actionable only when the diff creates a concrete change or
test risk. Do not use arbitrary file-length thresholds. Recommend extraction or
abstraction only when it removes a proven responsibility or duplication.

For every candidate, search for a guard or invariant that disproves it. Record
rejected candidates briefly so the final decision is auditable without
publishing speculative concerns.
