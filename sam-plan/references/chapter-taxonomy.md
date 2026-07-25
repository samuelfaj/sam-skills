# Chapter Taxonomy (optional lenses)

## Contents

1. Role
2. Lens catalog
3. Naming
4. When to emit

## Role

Chapters are **optional presentation lenses** on top of the required light-theme
HTML pack. They are not a required matrix. Plans may omit `chapters`; the
renderer then emits a single compact page from the freeze.

Never emit empty ceremonial pages. Only add a lens when it changes an
implementation decision or the user asks for a multi-page pack.

## Lens catalog

Use any subset (or none). IDs/slugs are suggestions for pack mode:

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

### Situational lenses

Emit only when decision-changing:

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

For a compact pack, a single merged `00-plano` page synthesized from the freeze
is enough.

## Naming

Files: `NN-slug.html` with zero-padded index and kebab-case slug when rendering
a pack. Nav labels match the filename stem. Keep language consistent with the
prompt locale.

## When to emit

HTML pack is always required. Chapters control pack shape only:

| Situation | Chapters |
| --- | --- |
| Default plan | None → renderer synthesizes compact `00-plano` light HTML |
| Multi-page / Lacco-style handoff | Minimal set that carries decisions |
| Dense product / migration plan | Focused lenses that change decisions |
