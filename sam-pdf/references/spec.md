# Page spec for build_doc.py

## Contents

- Top level
- Page kinds and when to use them
- Image options
- Sizing rules that keep screens readable

## Top level

```json
{
  "title": "Product · How it works",
  "lang": "pt-BR",
  "page_size": "A4",
  "orientation": "landscape",
  "theme": {
    "primary": "#1f5f9c", "ink": "#242c29", "muted": "#5e6b65", "line": "#d7e4f0", "bg": "#f2f7fc",
    "font_body": {"file": "fonts/body-400.woff2", "weight": "400 700"},
    "font_heading": {"file": "fonts/display-600.woff2", "weight": "600 700"}
  },
  "roles": {"patient": {"label": "Paciente", "tone": "blue"}, "staff": {"label": "Equipe", "tone": "amber"}},
  "pages": []
}
```

- Paths are relative to the spec file. `page_size` is `A4` or `Letter`; `orientation` is `landscape` (default, best for screenshots) or `portrait` (text-heavy reports).
- Take theme colors and font files from the product's own design tokens and self-hosted fonts. Fonts must be local files; a web font URL fails in an offline print.
- `roles` label who sees or does each screen. Tones: `blue`, `green`, `amber`, `gray`, `red`. A page may name only declared roles.

Common page fields: `section` (chapter label shown in the header, e.g. `"3 · Questionário"`), `role`, `title`, `text` (one string or a list of short paragraphs). Page numbers are automatic.

## Page kinds and when to use them

| Kind | Use for | Fields |
| --- | --- | --- |
| `cover` | First page | `brand`, `title`, `subtitle`, `meta` (audience and date) |
| `cards` | Journey overview, principles, safety net | `cards: [{title, text}]`, `columns` (default 3), `numbered`, `intro`, `note: {title, items}` |
| `list` | Open items, next steps | `items`, `intro`, `numbered` (default true) |
| `single` | One important screen; copy column on the left | `image` |
| `pair` | Before/after, two steps, or two roles side by side | `images` (2, each with `label`) |
| `stack` | Two wide, short panels | `images` (2); heights follow each image's shape |
| `split` | One tall page (long form, chart, record) cut into readable columns | `image` with `parts` 2-3 |
| `phones` | 3-5 mobile screens | `images` with `label` |
| `grid` | 4 small items in 2x2 (e-mails, cards) | `images` with `label` |

Order chapters the way the reader lives the flow, not by system module. Open with a cover and an overview page that names every actor, and close with an honest open-items page.

## Image options

Applied in this order: `crop` -> `trim` -> `keep_width` -> `height_ratio` -> split -> downscale.

- `crop: {"left": 488, "top": 0, "right": 0, "bottom": 0}` removes pixels from each edge. Use it to drop an app sidebar that repeats on every screen; keep the sidebar on the first screen of each area so the reader learns where they are.
- `trim: true` removes empty borders that match the bottom-right corner color.
- `keep_width: 0.5` keeps the left fraction of the width (a narrow column of content in a wide screen).
- `height_ratio: 0.65` keeps the top part, as height = width x ratio. Use when only the top of a long page matters.
- `parts: 3` (split pages) cuts at the quietest rows near each third so no line of text is sliced.
- `max_width` overrides the downscale width (default 2000 px; 1400 split, 1000 grid, 700 phones).

## Sizing rules that keep screens readable

- One screen per page when the text on it matters; two side by side only when the comparison is the point.
- Never more than 2 desktop screens, 4 grid items or 5 phones on a landscape page.
- A desktop screenshot narrower than about 130 mm is hard to read; split or crop instead of shrinking. `print_pdf.py` blocks any image under 25 mm on its short side.
- Body text 10.5 pt, titles 19 pt, captions above the image. Keep each page's copy to 1-3 short paragraphs.
