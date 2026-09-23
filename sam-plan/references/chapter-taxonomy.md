# Chapter Taxonomy (optional lenses)

Add a chapter only when it changes an implementation decision or the user asks
for a multi-page pack; never emit empty ceremonial pages. For a multi-page
handoff emit the minimal set that carries decisions; for a dense product or
migration plan, only focused lenses.

## Schema

`chapters[]`: `{id, slug, title, summary, sections}` with a two-digit `id`, a
unique kebab-case `slug`, and non-empty `sections: [{heading, blocks}]` and
`blocks`. Each chapter renders to `<id>-<slug>.html`; nav labels match the
stem. All text renders escaped. Show non-empty
`simplicity.retained_complexity_justifications` as a `warn` callout (the
compact page adds it automatically).

| Block `type` | Fields |
| --- | --- |
| `paragraph`, `code` | `text` |
| `list` | `items` (non-empty strings), optional `ordered` |
| `callout` | `text`, `tone` `info|ok|warn|danger|decision` (default `info`) |
| `table` | `headers` (non-empty unique strings), `rows` (string arrays of header length) |

## Lens Catalog

Use any subset:

| ID | Slug | Purpose |
| --- | --- | --- |
| 00 | visao-objetivo | Goal, why now, measurable success |
| 01 | escopo | In scope, non-goals, invariants, no-go |
| 02 | evidencia-estado | Facts, assumptions, unknowns |
| 03 | tese | Approach and rejected alternatives |
| 04 | passos | Ordered steps with deps, surfaces, DoD |
| 05 | riscos-decisoes | Risks, decisions, accept/mitigate |
| 06 | verificacao | Proof map |
| 07 | simplicidade | Cuts and retained complexity |
| 08 | council | Council results when a run happened |
| 99 | execution-log | Planning ledger and receipts |

Situational lenses, only when decision-changing:

| Trigger | Slug examples |
| --- | --- |
| User-facing flows | personas-jornadas, telas-wireframes, copy |
| Data shape changes | modelagem-dados, migracao |
| Multi-component design | arquitetura, integracoes |
| Auth/privacy/compliance | seguranca-privacidade |
| Ship process | rollout-rollback, qa-testes, backlog |
| AI agents/prompts | prompts-agentes |
| Monetization | monetizacao |
| Ops/observability | analytics-observabilidade |
