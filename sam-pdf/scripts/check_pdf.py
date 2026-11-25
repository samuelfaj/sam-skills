#!/usr/bin/env python3
"""Check a finished PDF and render contact sheets so every page gets looked at.

Verifies page count and size, that every font is embedded, and that no page
renders blank. Writes numbered contact sheets (9 pages each) and optional
zoomed renders of chosen pages. Needs poppler (pdfinfo, pdffonts, pdftoppm).
Usage: check_pdf.py FILE.pdf --sheets DIR [--pages N] [--size A4|Letter]
       [--orientation landscape|portrait] [--zoom 2,19]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - reported to the caller
    sys.exit("check_pdf.py needs Pillow: python3 -m pip install pillow")

SIZES_PT = {"A4": (841.89, 595.28), "Letter": (792.0, 612.0)}
TOLERANCE_PT = 2.0


def run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def page_info(pdf: Path) -> tuple[int, float, float]:
    info = run("pdfinfo", str(pdf))
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE).group(1))
    size = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+) pts", info, re.MULTILINE)
    return pages, float(size.group(1)), float(size.group(2))


def font_problems(pdf: Path) -> list[str]:
    lines = run("pdffonts", str(pdf)).splitlines()[2:]
    problems = []
    for line in lines:
        columns = line.split()
        # name type... encoding emb sub uni object generation
        if len(columns) >= 7 and columns[-5] != "yes":
            problems.append(f"font not embedded: {columns[0]}")
    return problems


def blank_pages(renders: list[Path]) -> list[int]:
    blank = []
    for index, path in enumerate(renders, start=1):
        gray = Image.open(path).convert("L")
        low, high = gray.getextrema()
        if high - low < 12:
            blank.append(index)
    return blank


def contact_sheets(renders: list[Path], out: Path, per_sheet: int = 9, cols: int = 3) -> list[Path]:
    sheets = []
    for start in range(0, len(renders), per_sheet):
        chunk = [Image.open(p).convert("RGB") for p in renders[start:start + per_sheet]]
        w, h = chunk[0].size
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (w + 10) + 10, rows * (h + 24) + 10), (110, 110, 110))
        draw = ImageDraw.Draw(sheet)
        for i, im in enumerate(chunk):
            x, y = 10 + (i % cols) * (w + 10), 10 + (i // cols) * (h + 24)
            draw.text((x, y), f"page {start + i + 1}", fill="white")
            sheet.paste(im, (x, y + 14))
        path = out / f"sheet-{start // per_sheet + 1:02d}.png"
        sheet.save(path)
        sheets.append(path)
    return sheets


def check(pdf: Path, sheets_dir: Path, pages: int | None, size: str | None,
          orientation: str, zoom: list[int]) -> dict:
    problems: list[str] = []
    count, width, height = page_info(pdf)
    if pages is not None and count != pages:
        problems.append(f"expected {pages} pages, found {count}")
    if size:
        w, h = SIZES_PT[size]
        if orientation == "portrait":
            w, h = h, w
        if abs(width - w) > TOLERANCE_PT or abs(height - h) > TOLERANCE_PT:
            problems.append(f"page size {width:.0f}x{height:.0f}pt, expected {size} {orientation}")
    problems += font_problems(pdf)
    sheets_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        run("pdftoppm", "-r", "50", "-png", str(pdf), f"{tmp}/p")
        renders = sorted(Path(tmp).glob("p-*.png"))
        if len(renders) != count:
            problems.append(f"rendered {len(renders)} of {count} pages")
        for number in blank_pages(renders):
            problems.append(f"page {number} renders blank")
        sheets = contact_sheets(renders, sheets_dir) if renders else []
    zoomed = []
    for number in zoom:
        if not 1 <= number <= count:
            problems.append(f"zoom page {number} does not exist")
            continue
        prefix = sheets_dir / f"page-{number:03d}"
        run("pdftoppm", "-r", "110", "-png", "-singlefile", "-f", str(number), "-l", str(number), str(pdf), str(prefix))
        zoomed.append(f"{prefix}.png")
    return {
        "pdf": str(pdf),
        "pages": count,
        "page_size_pt": [round(width, 1), round(height, 1)],
        "bytes": pdf.stat().st_size,
        "problems": problems,
        "sheets": [str(s) for s in sheets],
        "zoomed": zoomed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--sheets", type=Path, required=True)
    parser.add_argument("--pages", type=int)
    parser.add_argument("--size", choices=sorted(SIZES_PT))
    parser.add_argument("--orientation", choices=["landscape", "portrait"], default="landscape")
    parser.add_argument("--zoom", default="", help="comma-separated page numbers to render larger")
    args = parser.parse_args()
    missing = [tool for tool in ("pdfinfo", "pdffonts", "pdftoppm") if not shutil.which(tool)]
    if missing:
        print(f"ERROR: install poppler for {', '.join(missing)}", file=sys.stderr)
        return 2
    if not args.pdf.is_file():
        print(f"ERROR: {args.pdf} not found", file=sys.stderr)
        return 1
    zoom = [int(x) for x in args.zoom.split(",") if x.strip()]
    try:
        report = check(args.pdf, args.sheets, args.pages, args.size, args.orientation, zoom)
    except (subprocess.CalledProcessError, AttributeError) as error:
        print(f"ERROR: could not read {args.pdf}: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=1))
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
