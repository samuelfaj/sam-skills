# Bar Policy

A gauntlet loop only produces quality if the comparison target is real. A
rubric lets the agent grade itself against words it wrote. A bar forces a
side-by-side pick against something that already exists.

## Three tests

Every bar must pass all three before compile:

- **Named.** A specific artifact, not a category. "Stripe pricing page" works.
  "Award-winning SaaS sites" does not.
- **Fetchable.** The critic can screenshot it, read it, run it, or open it. If
  the agent cannot obtain the reference, it will hallucinate the comparison.
- **Comparable.** Both artifacts can sit side by side and a judge can pick one.
  If you cannot imagine the A/B, it is not a bar. One bar is one artifact of
  one kind. Two products, a live app plus a repo, or a brochure URL plus a
  desktop window are two bars. Offer them separately. Do not compile a union.

Reject a bar that fails any test. Offer two or three replacements instead of
compiling.

The locator must be the surface the later critic will open. A marketing page,
launch post, or README is not the live app, checkout, or running product. If
the user has that window or path open, name it (bundle, title, file). Do not
swap in a brochure URL. A benchmark or test suite named beside a repo is the
measurable half of that same artifact, not a second product.

## Bars by goal type

| Goal | Bar that works |
| --- | --- |
| Website, app, UI | A named live page, screenshotted at the same viewport |
| Game, 3D, visual | Real footage or screenshots from a named shipped title |
| Writing | A specific published piece, same length and format |
| Code, tooling | A named repo's implementation plus its benchmark or tests |
| Research, analysis | A named report or paper methods section |
| Deck, doc, deliverable | A real artifact from a firm known for it, same page count |

Prefer the hardest bar the critic can genuinely reach. An easy bar exits on
round one. When the goal has a measurable half, name the number beside the
reference: taste plus a number beats taste alone.

## Fetch methods

| Method | Use when |
| --- | --- |
| `screenshot` | Visual A/B; same viewport as the work |
| `read` | Prose, docs, papers, source |
| `run` | CLI, benchmark, test suite, binary |
| `open` | Repo, artifact, or file the critic can inspect |

If fetch fails, the critic must return `unfetched`. That is `BLOCKED`, not a
win.
