#!/usr/bin/env python3
"""Turn a JSON page spec into print-ready HTML (doc.html plus prepared images).

Every page is a fixed-size box. Images are cropped, trimmed, split and
downscaled here so the printer only lays out what already fits.
Usage: build_doc.py spec.json --out DIR
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:  # pragma: no cover - reported to the caller
    sys.exit("build_doc.py needs Pillow: python3 -m pip install pillow")

HERE = Path(__file__).resolve().parent
CSS = HERE.parent / "assets" / "doc.css"
PAGE_SIZES = {"A4": (297, 210), "Letter": (279.4, 215.9)}
TONES = {
    "blue": ("#e6f0fa", "#1a5288"),
    "green": ("#e3f2ea", "#1d6346"),
    "amber": ("#f6eddc", "#74500f"),
    "gray": ("#eceff1", "#3d4a52"),
    "red": ("#fbe7e6", "#8a2a22"),
}
THEME_DEFAULTS = {
    "primary": "#1f5f9c",
    "ink": "#242c29",
    "muted": "#5e6b65",
    "line": "#d7e4f0",
    "bg": "#f2f7fc",
}
SHOT_KINDS = {"single", "pair", "stack", "split", "phones", "grid"}
MAX_WIDTH = {"phones": 700, "grid": 1000, "split": 1400}
esc = html.escape


class SpecError(ValueError):
    pass


def trim(im: Image.Image, pad: int = 36, tolerance: int = 10) -> Image.Image:
    """Remove borders that match the bottom-right corner color, keeping `pad` px."""
    rgb = im.convert("RGB")
    corner = rgb.getpixel((rgb.width - 2, rgb.height - 2))
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, corner))
    box = diff.convert("L").point(lambda v: 255 if v > tolerance else 0).getbbox()
    if not box:
        return im
    left, top, right, bottom = box
    return im.crop((
        max(0, left - pad), max(0, top - pad),
        min(rgb.width, right + pad), min(rgb.height, bottom + pad),
    ))


def quiet_row(im: Image.Image, target: int, window: int) -> int:
    """Row near `target` with the least contrast, so a split never cuts through text."""
    gray = im.convert("L")
    best, best_score = target, None
    for y in range(max(1, target - window), min(im.height - 1, target + window)):
        low, high = gray.crop((0, y, gray.width, y + 1)).getextrema()
        score = high - low
        closer = best_score is not None and score == best_score and abs(y - target) < abs(best - target)
        if best_score is None or score < best_score or closer:
            best, best_score = y, score
    return best


def split_rows(im: Image.Image, parts: int) -> list[tuple[int, int]]:
    window = max(20, im.height // (parts * 6))
    cuts = [0] + [quiet_row(im, round(im.height * k / parts), window) for k in range(1, parts)] + [im.height]
    return list(zip(cuts, cuts[1:]))


def prepare(spec_dir: Path, out: Path, image: dict, kind: str, stem: str) -> list[dict]:
    """Apply crop -> trim -> height limit -> split -> downscale; return saved files."""
    src = (spec_dir / image["src"]).resolve()
    if not src.is_file():
        raise SpecError(f"image not found: {image['src']}")
    im = Image.open(src)
    im.load()
    crop = image.get("crop")
    if crop:
        left, top, right, bottom = (int(crop.get(k, 0)) for k in ("left", "top", "right", "bottom"))
        if left + right >= im.width or top + bottom >= im.height:
            raise SpecError(f"crop removes the whole image: {image['src']}")
        im = im.crop((left, top, im.width - right, im.height - bottom))
    if image.get("trim"):
        im = trim(im)
    if image.get("keep_width"):
        im = im.crop((0, 0, max(1, round(im.width * float(image["keep_width"]))), im.height))
    if image.get("height_ratio"):
        im = im.crop((0, 0, im.width, min(im.height, round(im.width * float(image["height_ratio"])))))
    pieces = [im]
    if kind == "split":
        pieces = [im.crop((0, a, im.width, b)) for a, b in split_rows(im, int(image.get("parts", 2)))]
    limit = int(image.get("max_width", MAX_WIDTH.get(kind, 2000)))
    saved = []
    for index, piece in enumerate(pieces):
        piece = piece.convert("RGB")
        if piece.width > limit:
            piece = piece.resize((limit, round(piece.height * limit / piece.width)), Image.LANCZOS)
        name = f"{stem}-{index + 1}.jpg" if len(pieces) > 1 else f"{stem}.jpg"
        piece.save(out / "img" / name, "JPEG", quality=84, optimize=True, progressive=True)
        saved.append({"file": name, "w": piece.width, "h": piece.height})
    return saved


def paras(lines) -> str:
    if isinstance(lines, str):
        lines = [lines]
    return "".join(f"<p>{esc(line)}</p>" for line in lines or [])


def img(item: dict, alt: str) -> str:
    return f'<img src="img/{item["file"]}" width="{item["w"]}" height="{item["h"]}" alt="{esc(alt)}">'


def bar(spec: dict, page: dict, number: int) -> str:
    role = page.get("role")
    badge = ""
    if role:
        roles = spec.get("roles", {})
        if role not in roles:
            raise SpecError(f"page {number}: unknown role {role!r}")
        badge = f'<span class="role role-{esc(role)}">{esc(roles[role]["label"])}</span>'
    return (
        f'<header class="bar"><span class="sec">{esc(page.get("section", ""))}</span>{badge}'
        f'<span class="num">{number}</span></header>'
    )


def figure(item: dict, label: str | None, grow: float | None = None) -> str:
    """`grow` sizes stacked screenshots by their shape so a short panel is not inflated."""
    caption = f"<figcaption>{esc(label)}</figcaption>" if label else ""
    style = f' style="flex:{grow:.3f} 1 0"' if grow else ""
    return f'<figure class="shot labeled"{style}>{caption}<div class="frame fit">{img(item, label or "")}</div></figure>'


def shot_page(spec: dict, page: dict, number: int, files: list[list[dict]]) -> str:
    kind = page["kind"]
    title = esc(page["title"])
    images = page.get("images") or [page["image"]]
    if kind == "single":
        body = (
            f'<div class="single"><div class="copy"><h2>{title}</h2>{paras(page.get("text"))}</div>'
            f'<figure class="shot fit">{img(files[0][0], page["title"])}</figure></div>'
        )
    else:
        if kind == "split":
            figs = "".join(f'<figure class="shot fit">{img(item, page["title"])}</figure>' for item in files[0])
            layout = f"row split split-{len(files[0])}"
        else:
            figs = "".join(
                figure(f[0], image.get("label"), f[0]["h"] / f[0]["w"] if kind == "stack" else None)
                for f, image in zip(files, images)
            )
            layout = {"pair": "row", "stack": "col", "phones": "row phones", "grid": "grid"}[kind]
        body = (
            f'<div class="top"><h2>{title}</h2><div class="lead">{paras(page.get("text"))}</div></div>'
            f'<div class="{layout}">{figs}</div>'
        )
    return f'<section class="page" data-kind="{kind}">{bar(spec, page, number)}<div class="body">{body}</div></section>'


def cover_page(spec: dict, page: dict) -> str:
    brand = f'<div class="brand">{esc(page["brand"])}</div>' if page.get("brand") else ""
    return (
        f'<section class="page cover"><div class="cover-in">{brand}<h1>{esc(page["title"])}</h1>'
        f'<p class="sub">{esc(page.get("subtitle", ""))}</p><p class="meta">{esc(page.get("meta", ""))}</p>'
        f"</div></section>"
    )


def number_tag(index: int, numbered: bool) -> str:
    return f'<span class="n">{index + 1}</span>' if numbered else ""


def intro(page: dict) -> str:
    return f'<p class="lead-big">{esc(page["intro"])}</p>' if page.get("intro") else ""


def cards_page(spec: dict, page: dict, number: int) -> str:
    numbered = page.get("numbered", False)
    columns = int(page.get("columns", 3))
    cards = "".join(
        f'<li>{number_tag(i, numbered)}<h3>{esc(card["title"])}</h3>{paras(card.get("text"))}</li>'
        for i, card in enumerate(page["cards"])
    )
    note = ""
    if page.get("note"):
        items = "".join(f"<li>{esc(x)}</li>" for x in page["note"].get("items", []))
        note = f'<aside class="note"><h3>{esc(page["note"].get("title", ""))}</h3><ul>{items}</ul></aside>'
    return (
        f'<section class="page text" data-kind="cards">{bar(spec, page, number)}<div class="body">'
        f'<h2>{esc(page["title"])}</h2>{intro(page)}'
        f'<ul class="cards{" dense" if columns >= 5 else ""}" style="--cols:{columns}">{cards}</ul>{note}</div></section>'
    )


def list_page(spec: dict, page: dict, number: int) -> str:
    items = "".join(f"<li>{esc(x)}</li>" for x in page["items"])
    tag = "ol" if page.get("numbered", True) else "ul"
    return (
        f'<section class="page text" data-kind="list">{bar(spec, page, number)}<div class="body">'
        f'<h2>{esc(page["title"])}</h2>{intro(page)}'
        f'<{tag} class="items">{items}</{tag}></div></section>'
    )


def font_face(family: str, font: dict, spec_dir: Path) -> str:
    path = (spec_dir / font["file"]).resolve()
    if not path.is_file():
        raise SpecError(f"font file not found: {font['file']}")
    fmt = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}.get(path.suffix)
    if not fmt:
        raise SpecError(f"unsupported font format: {path.name}")
    weight = esc(str(font.get("weight", "400 700")))
    return f"@font-face{{font-family:'{family}';font-weight:{weight};src:url('{path.as_uri()}') format('{fmt}');}}"


def theme_css(spec: dict, spec_dir: Path) -> str:
    theme = {**THEME_DEFAULTS, **spec.get("theme", {})}
    size = spec.get("page_size", "A4")
    if size not in PAGE_SIZES:
        raise SpecError(f"page_size must be one of {sorted(PAGE_SIZES)}")
    w, h = PAGE_SIZES[size]
    if spec.get("orientation", "landscape") == "portrait":
        w, h = h, w
    faces, stacks = [], {}
    for key, fallback in (("font_body", "system-ui, sans-serif"), ("font_heading", "system-ui, sans-serif")):
        font = theme.get(key)
        if font:
            family = f"Doc {key.split('_')[1].title()}"
            faces.append(font_face(family, font, spec_dir))
            stacks[key] = f"'{family}', {fallback}"
        else:
            stacks[key] = fallback
    variables = [f"--{k}:{v};" for k, v in theme.items() if k in THEME_DEFAULTS]
    variables += [f"--font-body:{stacks['font_body']};", f"--font-heading:{stacks['font_heading']};"]
    variables += [f"--page-w:{w}mm;", f"--page-h:{h}mm;"]
    roles = ""
    for key, role in spec.get("roles", {}).items():
        tone = role.get("tone", "gray")
        if tone not in TONES:
            raise SpecError(f"role {key}: tone must be one of {sorted(TONES)}")
        background, color = TONES[tone]
        roles += f".role-{key}{{background:{background};color:{color};}}"
    return "".join(faces) + f"@page{{size:{w}mm {h}mm;margin:0;}}:root{{{''.join(variables)}}}" + roles


def build(spec_path: Path, out: Path) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_dir = spec_path.parent
    pages = spec.get("pages")
    if not pages:
        raise SpecError("spec.pages is empty")
    (out / "img").mkdir(parents=True, exist_ok=True)
    rendered = []
    for number, page in enumerate(pages, start=1):
        kind = page.get("kind")
        if kind == "cover":
            rendered.append(cover_page(spec, page))
        elif kind == "cards":
            rendered.append(cards_page(spec, page, number))
        elif kind == "list":
            rendered.append(list_page(spec, page, number))
        elif kind in SHOT_KINDS:
            images = page.get("images") or ([page["image"]] if page.get("image") else [])
            if not images:
                raise SpecError(f"page {number}: {kind} needs image or images")
            files = [prepare(spec_dir, out, image, kind, f"p{number:03d}-{i + 1}") for i, image in enumerate(images)]
            rendered.append(shot_page(spec, page, number, files))
        else:
            raise SpecError(f"page {number}: unknown kind {kind!r}")
    css = theme_css(spec, spec_dir) + CSS.read_text(encoding="utf-8")
    doc = (
        f'<!doctype html><html lang="{esc(spec.get("lang", "en"))}"><head><meta charset="utf-8">'
        f'<title>{esc(spec.get("title", "Document"))}</title><style>{css}</style></head>'
        f'<body>{"".join(rendered)}</body></html>'
    )
    (out / "doc.html").write_text(doc, encoding="utf-8")
    return {"html": str(out / "doc.html"), "pages": len(rendered)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.spec, args.out)
    except (SpecError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
