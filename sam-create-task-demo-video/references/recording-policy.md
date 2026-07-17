# Recording Policy

## Environment gate

Record environment kind, identity, UI/API endpoints, database or tenant, and
evidence. Real data is allowed only on verified `local`, `test`, or `dev` targets.
Never record production credentials, customer tenants, or private customer data.

## Real-UI fidelity (default)

The demo must look like a real person using the real product.

**Prefer, in order:**

1. Repository-supported app boot (direct, container, or compose).
2. Real product URL/route that owns the changed behavior.
3. Normal auth or an existing demo/test account on that app.
4. Deterministic seed data on the linked backend—not a fake in-browser-only state
   when the backend is available.
5. Human-paced actions on the same controls users use.

**Do not create for the demo alone (unless real UI is blocked):**

- New pages, routes, or components whose only purpose is the walkthrough.
- Storybook/story mounts, component shells, or mock screens that bypass router,
  layout, providers, auth, or API clients.
- Parallel “demo UI” copies of product screens.

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
- Keep captions short and inject them only in the browser session; do not modify
  product files for captions.
- Avoid browser surfaces that expose tokens, internal URLs, emails, or identifiers.
- Keep the demo scoped to linked acceptance criteria.
- Prefer the real navigation path over deep-linking past auth/layout only when
  that path is part of the proof story.

## Fallback

Use a mocked or isolated surface only after recording each real-system attempt and
blocker (boot, auth, seed, ports, backend link). Label the artifact and proof
status `FALLBACK`; set `recording.real_ui` to `false` with an exact
`fallback_reason`. Never describe fallback as a real linked UI demonstration.
Create the thinnest temporary surface only when those attempts fail; prefer
unlocking the real product page when possible.
