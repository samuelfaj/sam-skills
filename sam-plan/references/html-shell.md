# HTML Shell

## Contents

1. When to render
2. Visual contract
3. Page structure
4. Components
5. Generation rule

## When to render

HTML pack is **optional**. Emit only when the user asks for HTML/pack or handoff
risk warrants a human-readable multi-page view. The freeze (`plan-report.json`)
remains the machine source of truth.

## Visual contract

Self-contained HTML (CSS in `<style>`, no external build). Match the readability
of a Lacco-style plan pack without hardcoding a product brand:

- Soft page background, white cards, sticky horizontal nav
- Clear H1/H2 hierarchy, dense tables, monospace for paths
- Callouts: neutral, ok, warn, danger, decision

Use system UI fonts. Keep contrast readable on mobile.

## Page structure

```html
<header><h1>…</h1><p>subtitle</p></header>
<nav aria-label="Plan files">…links…</nav>
<main>
  <section><h2>…</h2>…</section>
</main>
```

Every plan file in the pack links every other file in nav order.

## Components

- Tables for steps, risks, evidence, verification
- Tags for IDs (`T-001`, `S-001`, `E-001`)
- Callout boxes for blockers, cuts, and accepted risks
- Optional grid for summary KPI-style facts

Wireframes stay textual unless the user provides or requests images.

## Generation rule

Never hand-author divergent CSS per chapter. Use
`scripts/render_plan_html.py` from the structured `plan-report.json` so nav,
IDs, and shell stay consistent. If `chapters` is empty, the renderer synthesizes
a single compact page from the freeze. Body content may include safe HTML
fragments already sanitized by the planner (no scripts, no inline event handlers).
