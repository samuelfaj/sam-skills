# Conditional Risk Lenses

Load only lenses reached by the target behavior.

## Security and Permissions

- Trace identity, tenant, role, object ownership, and deny paths.
- Prove server-side enforcement; UI hiding is not authorization.
- Check secrets, PII, logs, analytics, and error responses.

## Data and Transactions

- Trace validation, persistence, uniqueness, deletion, rollback, and retries.
- Check partial writes, duplicate delivery, ordering, and recovery.
- Require migration and rollback proof for destructive or incompatible changes.

## Contracts and Integrations

- Inspect producer and consumer together: API/client, event/handler,
  schema/storage, config/reader, type/implementation, migration/model.
- Verify compatibility, timeouts, retries, idempotency, and error translation.
- Use dependency source, types, or primary documentation for external behavior.

## Concurrency and State

- Check races, stale cache, lost updates, cancellation, ordering, and duplicate work.
- Prefer existing atomic boundaries and state models over new flags.

## User Experience

- Verify useful labels rather than opaque identifiers.
- Check loading, empty, error, disabled, permission, focus, keyboard, and recovery.
- Avoid client lookup loops, unbounded option payloads, and hidden failures.

## Browser-to-Service Flows

- Observe the exact method and URL used by the real client.
- Confirm the route exists in the running service and the client points to it.
- Check preflight and failed-response headers when cross-origin behavior applies.
- Do not accept a fix that exposes the error but leaves the user action failing.

## Delivery and Operations

- Check configuration drift, rollout order, backward compatibility, monitoring,
  rollback, packaging, signing, and recovery only when affected.
- Separate local proof from remote deployment or publication proof.

## Maintainability

- Keep logic in the owning layer and reuse established helpers.
- Reject speculative configurability, pass-through wrappers, duplicated rules,
  unchecked casts, and scattered special cases.
- Judge file or module size against repository conventions and reader burden,
  not an arbitrary universal line limit.
