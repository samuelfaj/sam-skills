# Evidence Policy

## Contents

1. Classifications
2. What counts as evidence
3. Materiality
4. Study receipts
5. Planning limits

## Classifications

- `FACT`: supported by code, tests, logs, config, authoritative docs, or a
  recorded user decision. Every fact needs a locator.
- `ASSUMPTION`: plausible but unverified. Material assumptions block
  `READY_TO_EXECUTE` unless the owner explicitly accepts them (`ACCEPTED`) or
  they are `VERIFIED`.
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

## Study receipts

Before `READY_TO_EXECUTE`, the freeze must show investigation happened:

- `study.tools_used` and `study.surfaces_mapped` non-empty (except SPIKE)
- At least one `FACT` with a non-empty locator
- With `--repo-root`, path locators must exist on disk (`path` / `path:line`)
- Non-empty `thesis.rejected_alternatives`
- Steps with non-empty `dod` and resolvable `proof_ids` when listed
- `acceptance_trace` covering each success criterion
- Risk flags set when high-risk signals apply (validator heuristics also catch
  under-flagging on goal/steps — see council-integration)

These are machine-checked. They replace chapter ceremony as the honesty floor.

## Planning limits

This skill plans; it does not implement. Planned post-implementation proofs are
`PLANNED` with an exact method. Unresolved required proof stays `NOT_RUN` and
prevents `READY_TO_EXECUTE`.

Redact secrets, credentials, tokens, and private customer data from plans,
HTML, and reports.

## Graph impact (advisory)

When a host code graph is available (`$RC_GRAPHIFY_GRAPH_JSON` or equivalent),
prefer recording optional impact evidence during study:

- Evidence `kind` such as `graph-impact` naming callers/dependents with locators
- Cite `graphify query` / `path` / `explain` in `study.tools_used`

When unavailable, do **not** fail `READY_TO_EXECUTE`. Record a residual or a
non-material UNKNOWN with a probe. Never fabricate graph consultation. Graphify
is not a hard dependency of sam-plan.

