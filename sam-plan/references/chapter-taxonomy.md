# Chapter Taxonomy

## Contents

1. Core chapters
2. Gated chapters
3. Depth → chapter matrix
4. Naming

## Core chapters

| ID | Slug | Purpose |
| --- | --- | --- |
| 00 | visao-objetivo | Goal, why now, measurable success |
| 01 | escopo | In scope, non-goals, invariants, no-go |
| 02 | evidencia-estado | Facts from repo/domain; assumptions; unknowns |
| 03 | tese | Chosen approach and rejected alternatives |
| 04 | passos | Ordered steps with deps, surfaces, DoD |
| 05 | riscos-decisoes | Risks, decisions, accept/mitigate |
| 06 | verificacao | Proof map for material claims and steps |
| 07 | simplicidade | Cuts, deferred work, retained complexity |
| 08 | council | Council results, objections, dispositions |
| 99 | execution-log | Planning ledger and receipts |

## Gated chapters

Emit only when the case type or evidence makes them decision-changing:

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

## Depth → chapter matrix

| Depth | Required chapters | Optional |
| --- | --- | --- |
| `simple` | `00`, `04`; add `05`/`06` only if material | Single-file merge of 00+04 allowed via `00-plano` |
| `standard` | `00`–`07`, `99`; `08` when council ran | Gated chapters that change decisions |
| `deep` | All core including `08`/`99` | Every applicable gated chapter |

For `simple`, `01`–`03` content may live inside `00` instead of separate files.
Never emit empty ceremonial pages.

## Naming

Files: `NN-slug.html` with zero-padded index and kebab-case slug.
Nav labels match the filename stem. Keep language consistent with the prompt
locale when the user writes in that locale.
