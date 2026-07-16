# Risk Lenses

Read only the lenses relevant to the changed files and bundle risk tags.
Treat each item as an investigation prompt, not an automatic finding.

## Security and Authorization

- Trace authentication and authorization at every changed entry point.
- Verify tenant, object, and role boundaries separately.
- Check token, session, header, cookie, credential, redirect, and sensitive-data handling.
- Confirm denial behavior and tests for changed privileged operations.
- Reject security concerns that lack a reachable attacker-controlled path.

## Data and Migrations

- Verify compatibility with existing and partially migrated data.
- Check nullability, defaults, constraints, indexes, ordering, precision, and enum changes.
- Trace transaction boundaries, partial writes, retries, rollback, and recovery.
- Inspect migration/model, serializer/schema, and writer/reader pairs together.
- Require a safe rollout or recovery path for destructive or irreversible changes.

## Concurrency, Jobs, and Integrations

- Check idempotency, deduplication, ordering, locking, retries, timeouts, and cancellation.
- Trace partial failures and externally visible side effects.
- Verify bounded concurrency and backpressure at realistic scale.
- Confirm provider-specific shapes remain behind existing adapter boundaries.
- Check logs and errors for useful context without secret leakage.

## Public Contracts and Compatibility

- Compare API, event, CLI, library, schema, and configuration producers with consumers.
- Check backward compatibility, defaults, versioning, and unknown or missing fields.
- Verify generated clients, manifests, examples, and documentation when authoritative.
- Consult dependency source, types, or primary documentation before accepting a contract claim.

## Frontend and User Experience

- Trace loading, success, empty, error, retry, disabled, and stale states.
- Check focus, keyboard access, labels, semantics, contrast, and visible validation.
- Verify effect cleanup, subscriptions, races, stale closures, and state ownership.
- Check API error mapping and useful user-facing feedback.
- Require behavior proof for changed critical flows when safe infrastructure exists.

## Infrastructure and Delivery

- Inspect secret scope, permissions, branch conditions, cache keys, artifacts, and reproducibility.
- Check deployment ordering, rollback, environment parity, and unsafe defaults.
- Treat changed scripts and hooks as untrusted until their diff is inspected.
- Distinguish local proof from remote deployment or pipeline state.

## Performance and Observability

- Check N+1 access, unbounded queries, I/O in loops, missing pagination, and required indexes.
- Check avoidable renders, repeated parsing, large client work, and cache invalidation.
- Require enough structured context to diagnose critical failures.
- Avoid logging credentials, tokens, personal data, or full third-party payloads.

## Architecture and Maintainability

- Enforce only boundaries already established by the repository.
- Accept a maintainability finding only when the diff introduces concrete coupling,
  duplicated policy, hidden side effects, untestability, or a materially harder change path.
- Treat line count, casts, optionality, wrappers, and helper count as investigation signals only.
- Prefer deleting concepts, collapsing duplicate paths, or moving logic to the canonical owner.
- Reject broad rewrites when a smaller owner-boundary correction resolves the failure class.
- Use `IMPORTANT` only for a proven material regression. Use `BLOCKER` only when
  correctness, security, data integrity, compatibility, or testability is concretely compromised.
