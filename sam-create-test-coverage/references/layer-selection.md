# Layer Selection

Select the lowest layer that proves the real contract without replacing its owner.

## Unit

Use for pure rules, parsing, formatting, serializers, validators, reducers, and
deterministic state transitions. Do not mock the function under test.

## Component

Use for isolated rendering, form state, user interaction, accessibility semantics,
and client-side serialization. Keep network and persistence outside this layer.

## Integration

Use when value comes from coordination: service/repository, cache invalidation,
transaction boundaries, queue consumers, storage, or multiple modules.

## API contract

Use for exact method, path, query, headers, auth, role, payload, validation,
status, response body, and compatibility. Exercise the same route the client uses.

## E2E

Use for critical journeys, navigation/auth wiring, browser-only behavior, and
frontend/backend integration. Drive the real linked UI when safe.

Multiple layers are justified only when they prove different failure boundaries.
Do not add E2E solely to repeat a lower-level branch already proven reliably.
