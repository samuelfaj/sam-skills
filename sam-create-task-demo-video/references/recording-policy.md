# Recording Policy

## Environment gate

Record environment kind, identity, UI/API endpoints, database or tenant, and
evidence. Real data is allowed only on verified `local`, `test`, or `dev` targets.
Never record production credentials, customer tenants, or private customer data.

## Startup

Inspect changed scripts, hooks, package commands, containers, browser config, and
CI definitions before execution. Prefer supported lockfiles and commands. Use
temporary environment overrides and unused ports when possible.

Confirm the browser reaches the intended backend. Register PIDs, containers,
ports, records, overrides, raw media, and temporary files at creation time.

## Recording

- Use a stable viewport and deterministic account or seed.
- Wait for visible readiness or network completion, not arbitrary timing.
- Pause on initial state, key action, proof moment, and final state.
- Keep captions short and inject them only in the browser session.
- Avoid browser surfaces that expose tokens, internal URLs, emails, or identifiers.
- Keep the demo scoped to linked acceptance criteria.

## Fallback

Use a mocked or isolated surface only after recording each real-system attempt and
blocker. Label the artifact and proof status `FALLBACK`; never describe it as a
real linked UI demonstration.
