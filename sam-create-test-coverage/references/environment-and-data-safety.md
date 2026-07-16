# Environment and Data Safety

## Identity gate

Record environment kind, identity, UI/API endpoints, database or tenant identity,
and evidence. Treat aliases, tunnels, proxies, and copied snapshots as unknown
until proven.

Real-data E2E is allowed only on verified `local`, `test`, or `dev` targets.
Never automate production credentials, customer tenants, or private customer data.

## Startup

Inspect changed scripts, hooks, package commands, test configs, containers, and
CI definitions before execution. Prefer existing lockfiles and repository commands.
Use temporary overrides outside the repository and unused ports when possible.

Confirm that every client points to the frozen backend before trusting results.

## Cleanup ledger

Register PIDs, containers, ports, records, environment files, logs, screenshots,
traces, and videos at creation time. Stop or delete only resources created by the run.

Use `RETAINED` only for an explicitly requested safe artifact and include its
exact path and reason. Any `BLOCKED` cleanup prevents full completion.
