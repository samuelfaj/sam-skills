# Conditional Risk Lenses

## Security and Permissions

Trace identity, tenant, role, object ownership, and deny paths; prove
server-side enforcement (UI hiding is not authorization). Check secrets, PII,
logs, analytics, and error responses.

## Data and Transactions

Trace validation, persistence, uniqueness, deletion, rollback, retries, partial
writes, duplicate delivery, ordering, and recovery. Destructive or incompatible
changes need migration and rollback proof.

## Contracts and Integrations

Inspect producer and consumer together (API/client, event/handler,
schema/storage, config/reader, type/implementation, migration/model). Verify
compatibility, timeouts, retries, idempotency, and error translation. Take
external behavior from dependency source, types, or primary documentation.

## Concurrency and State

Check races, stale cache, lost updates, cancellation, ordering, and duplicate
work; prefer existing atomic boundaries and state models over new flags.

## User Experience

Show useful labels, not opaque identifiers. Check loading, empty, error,
disabled, permission, focus, keyboard and other accessibility, and recovery
states. Avoid client lookup loops, unbounded option payloads, and hidden
failures.

## Browser-to-Service Flows

Observe the real client's exact method and URL; confirm the route exists in the
running service and the client points to it. Check preflight and
failed-response headers when cross-origin behavior applies. Exposing the error
while the user action still fails is not a fix.

## Delivery and Operations

Only when affected: configuration drift, rollout order, backward compatibility,
monitoring, rollback, packaging, signing, and recovery. Separate local proof
from remote deployment or publication proof.

## Maintainability

Keep logic in the owning layer; reuse established helpers. Reject speculative
configurability, pass-through wrappers, duplicated rules, unchecked casts, and
scattered special cases. Judge file or module size by repository conventions
and reader burden, not a universal line limit.
