# Evidence Policy

## Contents

1. Classifications
2. What counts as evidence
3. Materiality
4. Planning limits

## Classifications

- `FACT`: supported by code, tests, logs, config, authoritative docs, or a
  recorded user decision. Every fact needs a locator.
- `ASSUMPTION`: plausible but unverified. Material assumptions block
  `READY_TO_EXECUTE` unless the owner explicitly accepts them in the report.
- `UNKNOWN`: missing or contradictory evidence. Material unknowns block
  `READY_TO_EXECUTE`.

Never upgrade confidence by repetition. Prefer `UNKNOWN` over invention.

## What counts as evidence

Inspect only what is needed to plan: repository files, tests, schemas, issue
text, safe local runtime observations, and explicit user constraints. Record
stable locators (path, symbol, command, or decision quote).

Do not treat absent external systems, guessed production state, or imagined
APIs as facts.

## Materiality

A claim is material when a wrong answer would change steps, risk, scope, or
verification. Non-material color may stay narrative without IDs.

Link steps and risks to evidence or assumption IDs when they depend on them.

## Planning limits

This skill plans; it does not implement. Planned post-implementation proofs are
`PLANNED` with an exact method. Unresolved required proof stays `NOT_RUN` and
prevents `READY_TO_EXECUTE`.

Redact secrets, credentials, tokens, and private customer data from plans,
HTML, and reports.
