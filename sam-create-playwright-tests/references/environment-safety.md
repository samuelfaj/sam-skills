# Environment Safety

## Identity gate

Record environment kind, human-readable identity, UI URL, API URL, database or
tenant identity, and the evidence used to resolve each value.

Allowed real-data targets are verified `local`, `test`, or `dev`. Treat aliases,
proxies, tunnels, copied production snapshots, and unknown targets as unknown
until proven otherwise. Do not infer safety from a hostname alone.

Never run automated browser tests against production services, production
credentials, customer tenants, or private customer data.

## Startup

1. Inspect changed scripts, hooks, package commands, container definitions, and
   Playwright configuration before execution.
2. Prefer commands and lockfiles already supported by the repository.
3. Use temporary environment files outside the repository when possible.
4. Allocate unused ports and confirm the UI calls the intended backend.
5. Record PID, container, port, override, and created data immediately.

## Data

- Prefer isolated factories, seeds, test accounts, and deterministic identifiers.
- Create only the records required by a scenario.
- Never log secrets, cookies, authorization headers, tokens, or private fields.
- Prove read-after-write behavior before cleanup when persistence is in scope.

## Cleanup

Stop only processes and containers started by this run. Remove created data,
temporary environment files, raw recordings, and generated reports unless the
user explicitly asks to retain an artifact. Never use broad cleanup commands.

Use `RETAINED` only with a safe exact path or resource identifier and reason.
Use `BLOCKED` when cleanup could not be completed; never report full completion.
