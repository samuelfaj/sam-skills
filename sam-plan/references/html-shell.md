# HTML Shell

## Contents

1. When to render
2. Visual contract (light theme)
3. Page structure
4. Components
5. Generation rule

## When to render

HTML pack is **required** on every terminal plan. It is the human-readable plan
artifact: openable in a browser so people understand goal, thesis, steps,
evidence, and status without reading JSON.

The freeze (`plan-report.json`) remains the machine source of truth for parents
and validators. Chat/Markdown may summarize; they do not replace the pack.

If `chapters` is empty, still render: the renderer synthesizes a single compact
page from the freeze.

## Visual contract (light theme)

Self-contained HTML (CSS in `<style>`, no external build). **Light theme only**
(soft page background, white cards, dark ink). Do not ship dark-only packs.

Match the readability of a Lacco-style plan pack without hardcoding a product brand:

- Soft page background (`#f5f7f6` or equivalent), white cards, sticky horizontal nav
- Clear H1/H2 hierarchy, dense tables, monospace for paths
- Callouts: neutral, ok, warn, danger, decision
- `color-scheme: light` so OS/browser UI stays light around the pack

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

After render, re-validate with `--require-html` so files exist on disk under
`output.plan_dir`.
