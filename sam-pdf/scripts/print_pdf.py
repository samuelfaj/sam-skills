#!/usr/bin/env python3
"""Preflight doc.html in headless Chromium, then print it to PDF only if every page fits.

Checks each `.page` for overflow, content past the margins, images that did not
load or render too small, and fonts that failed to load. Any problem blocks the
PDF so a broken page can never ship.
Usage: print_pdf.py DIR/doc.html --out FILE.pdf [--min-image-mm 25]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PREFLIGHT = """
({ minImageMm, marginMm }) => {
  const mm = 96 / 25.4
  const problems = []
  const pages = [...document.querySelectorAll('.page')]
  for (const face of document.fonts) {
    if (face.status === 'error') problems.push(`font failed to load: ${face.family}`)
  }
  pages.forEach((page, index) => {
    const n = index + 1
    if (page.scrollHeight > page.clientHeight + 1 || page.scrollWidth > page.clientWidth + 1)
      problems.push(`page ${n}: content overflows the page`)
    const box = page.getBoundingClientRect()
    const limit = {
      right: box.right - marginMm.right * mm + 1,
      bottom: box.bottom - marginMm.bottom * mm + 1,
    }
    page.querySelectorAll('h1, h2, h3, p, li, figcaption, img, span').forEach((el) => {
      if (el.tagName !== 'IMG' && el.tagName !== 'SPAN' && el.scrollWidth > el.clientWidth + 1)
        problems.push(`page ${n}: ${el.tagName} text is wider than its box "${(el.textContent || '').trim().slice(0, 40)}"`)
      const r = el.getBoundingClientRect()
      if (r.width === 0 && r.height === 0) return
      const label = (el.getAttribute('src') || el.textContent || '').trim().slice(0, 40)
      if (r.bottom > limit.bottom) problems.push(`page ${n}: ${el.tagName} past bottom margin "${label}"`)
      if (r.right > limit.right) problems.push(`page ${n}: ${el.tagName} past right margin "${label}"`)
    })
    page.querySelectorAll('img').forEach((img) => {
      const src = img.getAttribute('src')
      if (!img.complete || img.naturalWidth === 0) problems.push(`page ${n}: image did not load ${src}`)
      const r = img.getBoundingClientRect()
      const small = Math.min(r.width, r.height) / mm
      if (small < minImageMm) problems.push(`page ${n}: image renders ${small.toFixed(0)}mm on its short side ${src}`)
    })
  })
  const images = pages.map((page) =>
    [...page.querySelectorAll('img')].map((img) => {
      const r = img.getBoundingClientRect()
      return `${Math.round(r.width / mm)}x${Math.round(r.height / mm)}mm`
    })
  )
  return { pages: pages.length, problems, images }
}
"""


def preflight_and_print(html: Path, out: Path, min_image_mm: float) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "print_pdf.py needs Playwright for Python: python3 -m pip install playwright "
            "&& python3 -m playwright install chromium"
        )
    # A blocked run must not leave an older PDF that looks current.
    out.unlink(missing_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.goto(html.resolve().as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            # The bottom margin is the page padding; checked elements must end inside it.
            report = page.evaluate(PREFLIGHT, {"minImageMm": min_image_mm, "marginMm": {"right": 12, "bottom": 10}})
            if report["pages"] == 0:
                report["problems"].append("no .page elements found")
            if not report["problems"]:
                out.parent.mkdir(parents=True, exist_ok=True)
                page.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
                report["pdf"] = str(out)
            return report
        finally:
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("html", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-image-mm", type=float, default=25.0)
    args = parser.parse_args()
    if not args.html.is_file():
        print(f"ERROR: {args.html} not found", file=sys.stderr)
        return 1
    report = preflight_and_print(args.html, args.out, args.min_image_mm)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    if report["problems"]:
        print(f"BLOCKED: {len(report['problems'])} layout problem(s); no PDF written", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
