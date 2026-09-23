# Risk Lenses

Headings name the bundle risk tags they serve. Items are investigation prompts, not findings.

## Security (`security`)

Authentication and authorization at every changed entry point; tenant, object, and role boundaries checked separately; token, session, header, cookie, credential, redirect, and sensitive-data handling; denial behavior and tests for changed privileged operations. Reject concerns without a reachable attacker-controlled path.

## Data and Migrations (`data-migration`)

Compatibility with existing and partially migrated data; nullability, defaults, constraints, indexes, ordering, precision, enum changes; transaction boundaries, partial writes, retries, rollback, recovery. Inspect migration/model, serializer/schema, and writer/reader pairs together. Destructive or irreversible changes need a safe rollout or recovery path.

## Concurrency, Jobs, Integrations (`concurrency-jobs`, `integration`)

Idempotency, deduplication, ordering, locking, retries, timeouts, cancellation; partial failures and externally visible side effects; bounded concurrency and backpressure at realistic scale. Provider-specific shapes stay behind existing adapter boundaries. Logs and errors carry useful context without secrets.

## Public Contracts (`public-contract`)

Compare API, event, CLI, library, schema, and configuration producers with consumers: backward compatibility, defaults, versioning, unknown or missing fields; generated clients, manifests, examples, and authoritative documentation.

## Frontend and UX (`user-visible`)

Loading, success, empty, error, retry, disabled, and stale states; focus, keyboard access, labels, semantics, contrast, visible validation; effect cleanup, subscriptions, races, stale closures, state ownership; API error mapping and useful feedback. Changed critical flows need behavior proof when safe infrastructure exists.

## Infrastructure and Delivery (`delivery`)

Secret scope, permissions, branch conditions, cache keys, artifacts, reproducibility; deployment ordering, rollback, environment parity, unsafe defaults. Distinguish local proof from remote deployment or pipeline state.

## Performance and Observability

N+1 access, unbounded queries, I/O in loops, missing pagination, required indexes, avoidable renders, repeated parsing, large client work, cache invalidation. Critical failures need structured diagnostic context; never log credentials, tokens, personal data, or full third-party payloads.

## Architecture and Maintainability

Enforce only boundaries the repository established. Accept a maintainability finding only when the diff introduces concrete coupling, duplicated policy, hidden side effects, untestability, or a materially harder change path; line count, casts, optionality, wrappers, and helper count are signals only. Prefer deleting concepts, collapsing duplicate paths, or moving logic to the canonical owner; reject a broad rewrite when a smaller owner-boundary correction resolves the failure class. `IMPORTANT` only for a proven material regression; `BLOCKER` only when correctness, security, data integrity, compatibility, or testability is concretely compromised.
