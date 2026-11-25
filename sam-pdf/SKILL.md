---
name: sam-pdf
description: "Produce a polished, verified PDF (product walkthroughs, flow explainers with many screenshots, reports, proposals) from a JSON page spec through print-ready HTML, a layout preflight that blocks any overflowing page, and a page-by-page visual check. Use when the user asks for a PDF, a presentation document, a walkthrough of a system with screenshots, or runs /sam-pdf."
---

# Sam PDF

Build PDFs that read well and render without errors. Content lives in a JSON spec, `scripts/build_doc.py` turns it into fixed-size HTML pages, `scripts/print_pdf.py` refuses to print while any page has a layout problem, and `scripts/check_pdf.py` proves the file and renders every page for review.

## Non-Negotiable Contract

- **No PDF with a known layout problem.** Ship only a file produced by `print_pdf.py` with zero problems. Fix the spec, copy or images; never loosen a check or hide overflow to get a pass.
- **Every page gets looked at.** Review all contact sheets from `check_pdf.py`, plus zoomed renders of dense pages. A passing script is necessary, not sufficient.
- **Facts come from the source.** Each claim is backed by code, configuration, a captured screen or the user. Unverifiable claims are cut. See [references/writing.md](references/writing.md).
- **Honest setup.** Disclose test environments, fictional data and placeholder images inside the document, and list known defects and unverified items on a closing page.
- **Privacy.** No real personal or health data in screenshots, file names or copy. Captures run against disposable data.
- **Leave no residue.** Remove temporary capture tests, stop containers and servers you started, and keep scratch work out of the product repository unless the user asks to commit it.

## Workflow

1. **Brief.** Settle audience, purpose, language, paper (`A4`/`Letter`, landscape for screenshots) and the journey or argument the document follows. Decide what the reader must understand by the last page.
2. **Outline.** Chapters in the order the reader lives the flow. Cover, overview page naming every actor, one page per step, closing open-items page. Choose page kinds from [references/spec.md](references/spec.md).
3. **Material.** For a running product, capture screens with a scripted, rerunnable journey per [references/screenshots.md](references/screenshots.md), then review every shot on contact sheets and recapture bad ones. Collect facts from the code while writing.
4. **Direction.** Reuse the product's colors and self-hosted fonts in `theme`. When `sam-design` is installed, run it for the visual direction and report its ledger; otherwise follow the sizing rules in [references/spec.md](references/spec.md).
5. **Copy.** Write the spec text per [references/writing.md](references/writing.md); run it through a humanizer skill in the target language when one is installed.
6. **Build, preflight, print.**
   ```bash
   python3 scripts/build_doc.py spec.json --out build
   python3 scripts/print_pdf.py build/doc.html --out build/document.pdf
   ```
   `print_pdf.py` checks every page for overflow, text past the margins, words wider than their box, images that failed to load or render under 25 mm, and fonts that failed. On problems it writes no PDF and deletes any older one at that path. Fix and rerun; for a too-small image, split it, crop it or give it its own page.
7. **Check and review.**
   ```bash
   python3 scripts/check_pdf.py build/document.pdf --sheets build/review --pages N --size A4 --zoom 2,7
   ```
   It verifies page count, paper size, embedded fonts and blank pages, and writes contact sheets plus zoomed pages. Open every sheet. Look for cut-off content, unreadable screens, repeated or empty-looking pages, wrong order, inconsistent terms and test artifacts (spinners, ids, `localhost`). Fix, rebuild and recheck until clean.
8. **Deliver.** Copy the PDF where the user asked (default: their Desktop), show a few rendered pages in chat when the host can display images, then clean up.

Requirements: Python 3.9+, Pillow, Playwright for Python with Chromium (`python3 -m pip install pillow playwright && python3 -m playwright install chromium`), and poppler (`pdfinfo`, `pdffonts`, `pdftoppm`). If one is missing, say which and how to install it before going on.

## Return

Report in the user's language:

- PDF path, page count, paper size and file size.
- What the document covers, as the chapter list.
- Verification: preflight result, `check_pdf.py` result, which pages were reviewed and at what zoom, and anything not verified (for example, not opened in a specific viewer).
- What the document discloses (test data, placeholders) and the open items it lists.
- Cleanup done, and where the spec and capture script live if the user wants to regenerate.
