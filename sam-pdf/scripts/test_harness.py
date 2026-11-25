#!/usr/bin/env python3
"""Prove the build, preflight and PDF checks on generated fixtures.

Each check states why the rule exists, so a regression names the harm.
Chromium and poppler steps are skipped (and said so) when the tools are missing.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build_doc.py"
PRINT = HERE / "print_pdf.py"
CHECK = HERE / "check_pdf.py"
CHECKS = 0
SKIPPED: list[str] = []


def check(condition: bool, reason: str) -> None:
    global CHECKS
    CHECKS += 1
    assert condition, reason


def run(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True)


def screen(path: Path, size: tuple[int, int], bands: int) -> None:
    """A fake screenshot: white page, gray sidebar, text-like bars with blank gaps."""
    im = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, 200, size[1]), fill=(235, 238, 240))
    step = size[1] // bands
    for k in range(bands):
        top = k * step + 20
        draw.rectangle((260, top, size[0] - 60, top + step * 3 // 5), fill=(40, 60, 90))
    im.save(path)


def spec(tmp: Path, pages: list[dict]) -> Path:
    path = tmp / "spec.json"
    path.write_text(json.dumps({
        "title": "Fixture", "lang": "pt-BR", "page_size": "A4", "orientation": "landscape",
        "roles": {"patient": {"label": "Paciente", "tone": "blue"}},
        "pages": pages,
    }), encoding="utf-8")
    return path


def test_build(tmp: Path) -> Path:
    screen(tmp / "wide.png", (2880, 1800), 6)
    # 28 bands put the naive cut rows (1400 and 2800) inside bars, so only a real gap search passes.
    screen(tmp / "tall.png", (1400, 4200), 28)
    screen(tmp / "phone.png", (780, 1688), 8)
    pages = [
        {"kind": "cover", "title": "Como funciona", "subtitle": "Telas reais", "meta": "Teste"},
        {"kind": "cards", "section": "Visão geral", "title": "Passos", "numbered": True,
         "cards": [{"title": "Um", "text": "Primeiro"}, {"title": "Dois", "text": "Segundo"}]},
        {"kind": "single", "section": "1 · App", "role": "patient", "title": "Início",
         "text": ["Texto curto."], "image": {"src": "wide.png", "crop": {"left": 200}, "trim": True}},
        {"kind": "pair", "section": "1 · App", "role": "patient", "title": "Antes e depois",
         "text": "Duas telas.", "images": [{"src": "wide.png", "label": "Antes"}, {"src": "wide.png", "label": "Depois"}]},
        {"kind": "split", "section": "1 · App", "title": "Página longa", "image": {"src": "tall.png", "parts": 3}},
        {"kind": "phones", "section": "2 · Celular", "title": "Celular",
         "images": [{"src": "phone.png", "label": f"Tela {i}"} for i in range(4)]},
        {"kind": "list", "section": "Próximos passos", "title": "Falta ajustar", "items": ["Um item", "Outro item"]},
    ]
    result = run(BUILD, spec(tmp, pages), "--out", tmp / "out")
    check(result.returncode == 0, f"a valid spec must build: {result.stderr}")
    html = (tmp / "out" / "doc.html").read_text(encoding="utf-8")
    check(html.count('class="page') == len(pages), "one fixed-size page per spec entry, nothing merged or dropped")
    check("@page{size:297mm 210mm" in html, "A4 landscape must reach the printer as the CSS page size")
    check("role-patient{background" in html and 'class="role role-patient"' in html, "role badges carry their tone")
    parts = sorted((tmp / "out" / "img").glob("p005-1-*.jpg"))
    check(len(parts) == 3, "a tall screen split into 3 parts so it stays readable")
    tall = Image.open(tmp / "tall.png").convert("L")
    # Cuts must land in blank gaps; a cut through a bar would slice a line of text in half.
    offset = 0
    for part in parts[:-1]:
        height = round(Image.open(part).height * 1400 / Image.open(part).width)
        offset += height
        # The next part starts at the cut row; that row must be a blank gap.
        low, high = tall.crop((0, offset, tall.width, offset + 1)).getextrema()
        check(high - low < 60, f"split cut at row {offset} crosses content")
    single = Image.open(tmp / "out" / "img" / "p003-1.jpg").convert("RGB")
    check(min(single.getpixel((6, single.height // 2))) >= 248, "the app sidebar is cropped away, leaving only the screen content")
    check(single.width == 2000, "wide screens are downscaled to keep the PDF small")

    bad = run(BUILD, spec(tmp, [{"kind": "single", "title": "x", "image": {"src": "missing.png"}}]), "--out", tmp / "bad")
    check(bad.returncode == 1 and "image not found" in bad.stderr, "a missing screenshot fails the build loudly")
    role = run(BUILD, spec(tmp, [{"kind": "list", "role": "nobody", "title": "x", "items": ["a"]}]), "--out", tmp / "bad")
    check(role.returncode == 1 and "unknown role" in role.stderr, "an undeclared role must not render an unstyled badge")
    kind = run(BUILD, spec(tmp, [{"kind": "poster", "title": "x"}]), "--out", tmp / "bad")
    check(kind.returncode == 1 and "unknown kind" in kind.stderr, "an unknown layout must not be skipped silently")
    return tmp / "out" / "doc.html"


def chromium_ready() -> bool:
    if importlib.util.find_spec("playwright") is None:
        return False
    probe = "from playwright.sync_api import sync_playwright\nwith sync_playwright() as p: p.chromium.launch().close()"
    return subprocess.run([sys.executable, "-c", probe], capture_output=True).returncode == 0


def test_print(tmp: Path, html: Path) -> Path | None:
    if not chromium_ready():
        SKIPPED.append("print_pdf.py (Playwright Chromium not installed)")
        return None
    pdf = tmp / "doc.pdf"
    good = run(PRINT, html, "--out", pdf)
    check(good.returncode == 0 and pdf.is_file(), f"a fitting document must print: {good.stdout}{good.stderr}")

    overflow = html.read_text(encoding="utf-8").replace(
        "<li>Outro item</li>", "".join(f"<li>Item longo número {i} que não cabe na página.</li>" for i in range(60)), 1
    )
    broken = html.parent / "broken.html"
    broken.write_text(overflow, encoding="utf-8")
    stale = tmp / "broken.pdf"
    stale.write_bytes(b"%PDF-old")
    blocked = run(PRINT, broken, "--out", stale)
    check(blocked.returncode == 1, "text that runs off the page must block the PDF")
    check("past bottom margin" in blocked.stdout or "overflows" in blocked.stdout, "the report names the page problem")
    check(not stale.exists(), "a blocked run removes the old PDF so it is not mistaken for the new one")

    wide = html.read_text(encoding="utf-8").replace(
        "<h3>Um</h3>", '<h3 style="width:30mm">beatriz.souza.oliveira@exemplo-longo.com.br</h3>', 1
    )
    word = html.parent / "word.html"
    word.write_text(wide, encoding="utf-8")
    clipped = run(PRINT, word, "--out", tmp / "word.pdf")
    check(clipped.returncode == 1 and "wider than its box" in clipped.stdout, "an unbreakable word spilling out of its card blocks the PDF")

    tiny = html.read_text(encoding="utf-8").replace("<img ", '<img style="max-height:15mm" ', 1)
    small = html.parent / "small.html"
    small.write_text(tiny, encoding="utf-8")
    shrunk = run(PRINT, small, "--out", tmp / "small.pdf")
    check(shrunk.returncode == 1 and "short side" in shrunk.stdout, "an unreadably small screenshot blocks the PDF")
    return pdf


def test_check(tmp: Path, pdf: Path | None) -> None:
    if pdf is None:
        SKIPPED.append("check_pdf.py (no PDF without Chromium)")
        return
    if not all(shutil.which(tool) for tool in ("pdfinfo", "pdffonts", "pdftoppm")):
        SKIPPED.append("check_pdf.py (poppler not installed)")
        return
    ok = run(CHECK, pdf, "--sheets", tmp / "sheets", "--pages", 7, "--size", "A4", "--zoom", "3")
    report = json.loads(ok.stdout)
    check(ok.returncode == 0 and not report["problems"], f"the fixture PDF passes: {ok.stdout}")
    check(len(report["sheets"]) == 1 and Path(report["zoomed"][0]).is_file(), "contact sheets and zoom renders exist for review")
    wrong = run(CHECK, pdf, "--sheets", tmp / "sheets2", "--pages", 8, "--size", "Letter")
    problems = json.loads(wrong.stdout)["problems"]
    check(wrong.returncode == 1 and any("expected 8 pages" in p for p in problems), "a missing page is caught")
    check(any("page size" in p for p in problems), "the wrong paper size is caught")

    blank_html = tmp / "blank.html"
    blank_html.write_text(
        "<!doctype html><style>@page{size:297mm 210mm;margin:0}.page{width:297mm;height:210mm;break-after:page}</style>"
        '<section class="page"><h1>Texto</h1></section><section class="page"></section>',
        encoding="utf-8",
    )
    blank_pdf = tmp / "blank.pdf"
    subprocess.run(
        [sys.executable, "-c",
         "import sys\nfrom playwright.sync_api import sync_playwright\n"
         "with sync_playwright() as p:\n b=p.chromium.launch();pg=b.new_page();pg.goto(sys.argv[1])\n"
         " pg.pdf(path=sys.argv[2],prefer_css_page_size=True);b.close()",
         blank_html.as_uri(), str(blank_pdf)],
        check=True, capture_output=True,
    )
    blank = run(CHECK, blank_pdf, "--sheets", tmp / "sheets3")
    check(blank.returncode == 1 and "page 2 renders blank" in blank.stdout, "an empty page is caught before delivery")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        html = test_build(tmp)
        pdf = test_print(tmp, html)
        test_check(tmp, pdf)
    note = f"; skipped: {', '.join(SKIPPED)}" if SKIPPED else ""
    print(f"sam-pdf harness: {CHECKS} checks passed{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
