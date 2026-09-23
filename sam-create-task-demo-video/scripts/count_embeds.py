#!/usr/bin/env python3
"""Check that every uploaded media URL is embedded as a player or image.

Reads a PR/MR body saved from the platform API (markup only: no rendered page,
no screenshots). Pass each uploaded URL by kind from the upload receipts.
Fenced code, indented code blocks, inline code, <pre>/<code> blocks, and HTML
comments are removed first: they render as text, never as a player. Inline code
and HTML take whichever starts first, so the body is checked with each removed
first and must pass both ways.

- Video, GitHub (user-attachments URL): every occurrence is the bare URL alone
  on its own line (at most 3 leading spaces).
- Video, GitLab (/uploads/ URL with .mp4 .m4v .mov .webm .ogv): every occurrence
  is inside ![alt](url).
- Image, either host: every occurrence is inside ![alt](url).

Forbidden media links fail the check: a non-image Markdown link, HTML anchor,
or reference-style definition pointing at a media file or a GitHub attachment
asset (user-attachments/assets/ or legacy github.com/<owner>/<repo>/assets/,
which carry no extension), a linked thumbnail, a <video> tag, and any
repository blob/raw/LFS URL of a media file, however it is wrapped. Links to
uploaded non-media files (logs, archives) are allowed.

No scan backtracks across the body, so run time stays linear in its size.
Prints one JSON line and exits 0 only when every URL is embedded
correctly and no media link exists; 1 on FAIL; 2 on unreadable input or no URLs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VIDEO_EXTENSIONS = (".mp4", ".m4v", ".mov", ".webm", ".ogv")
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS + (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
COMMITTED = ("/blob/", "/raw/", "raw.githubusercontent.com/", "media.githubusercontent.com/")
ASSET = re.compile(r"user-attachments/assets/|github\.com/[^/\s]+/[^/\s]+/assets/", re.I)
URL_CHAR = r"[^\s()<>\"'\]]"
TOKEN_BREAK = re.compile(r"[\s()<>\"'\[\]]+")
# Each pattern captures a link destination (link text may nest one bracket
# level; anchor attribute values may hold ">"; a definition's destination may
# sit on the next line). A media capture is a media link.
LINK_DESTINATIONS = (
    re.compile(r"(?<!!)\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*<?([^()\s<>]*)"),
    re.compile(
        r"<a\b(?:[^<>\"']|\"[^\"]{0,1024}\"|'[^']{0,1024}')*?\shref\s*=\s*[\"']?([^\"'\s<>]*)", re.I
    ),
    re.compile(r"(?m)^ {0,3}\[[^\[\]]+\]:[ \t]*\n?[ \t]*<?([^\s<>]*)"),
)
HTML_OPENER = re.compile(r"<!--|<(pre|code)\b[^<>]*>", re.I)
FORBIDDEN_TAGS = (
    re.compile(r"\[\s*!\[[^\[\]]*\]\([^()]*\)\s*\]\("),  # linked thumbnail
    re.compile(r"<video\b", re.I),
)


def media_path(url: str) -> bool:
    path = re.split(r"[?#]", url, maxsplit=1)[0].rstrip(".,;:!*_~").lower()
    return path.endswith(MEDIA_EXTENSIONS)


def media_link(url: str) -> bool:
    return media_path(url) or bool(ASSET.search(url))


def code_spans(text: str) -> str:
    """Replace inline code spans with CODE: a backtick run closes at the next run of
    equal length within its paragraph (linear pairing, never a backtracking scan)."""
    blocks = []
    for block in re.split(r"(\n[ \t]*\n)", text):
        runs = list(re.finditer(r"`+", block))
        later: dict[int, list[int]] = {}
        for index in range(len(runs) - 1, -1, -1):
            later.setdefault(len(runs[index].group()), []).append(index)
        pieces, cursor, index = [], 0, 0
        while index < len(runs):
            stack = later[len(runs[index].group())]
            while stack and stack[-1] <= index:
                stack.pop()
            if not stack:
                index += 1
                continue
            close = stack.pop()
            pieces.append(block[cursor : runs[index].start()] + "CODE")
            cursor, index = runs[close].end(), close + 1
        blocks.append("".join(pieces) + block[cursor:])
    return "".join(blocks)


def rendered_texts(body: str) -> tuple[str, str]:
    """Drop what renders as text: fenced, indented, inline, and HTML code; comments.

    An indented code block (4+ spaces or a tab) starts only after a blank line
    or at the top, and never inside a list item, where indentation continues it.
    """
    lines: list[str] = []
    fence = ""
    previous_blank, in_list, in_code = True, False, False
    for line in body.splitlines():
        if fence:
            if re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*", line):
                fence = ""
            continue
        blank = not line.strip()
        indented = bool(re.match(r"(?: {4}|\t)", line))
        if in_code and (blank or indented):
            continue
        in_code = False
        if indented and previous_blank and not in_list and not blank:
            in_code = True
            continue
        opening = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if opening:
            fence = opening.group(1)
            continue
        if not blank and not indented:
            in_list = bool(re.match(r" {0,3}(?:[-*+]|\d{1,9}[.)])(?:[ \t]|$)", line))
        previous_blank = blank
        lines.append(line)
    # A placeholder keeps a line with code on it from reading as a bare URL line.
    text = "\n".join(lines)
    return strip_html_text(code_spans(text)), code_spans(strip_html_text(text))


def strip_html_text(text: str) -> str:
    """Replace closed HTML comments and <pre>/<code> elements with CODE; an
    unclosed one runs to the end only when it starts a line (an HTML block).
    Each kind searches for its closer at most once past any position."""
    pieces, cursor, exhausted = [], 0, set()
    while match := HTML_OPENER.search(text, cursor):
        name = (match.group(1) or "").lower()
        closer = re.compile(rf"</{name}\s*>", re.I) if name else re.compile("-->")
        found = None if name in exhausted else closer.search(text, match.end())
        if found:
            pieces.append(text[cursor : match.start()] + "CODE")
            cursor = found.end()
            continue
        exhausted.add(name)
        newline = text.rfind("\n", max(0, match.start() - 4), match.start())
        lead = text[newline + 1 : match.start()] if newline >= 0 or match.start() <= 3 else "x"
        if not lead.strip(" "):
            pieces.append(text[cursor : match.start()] + "CODE")
            cursor = len(text)
            break
        pieces.append(text[cursor : match.end()])
        cursor = match.end()
    return "".join(pieces) + text[cursor:]


def media_links(text: str) -> int:
    links = 0
    for pattern in LINK_DESTINATIONS:
        links += sum(media_link(match.group(1)) for match in pattern.finditer(text))
    links += sum(len(pattern.findall(text)) for pattern in FORBIDDEN_TAGS)
    # A committed media file is never an embed, bare, autolinked, or wrapped.
    for token in TOKEN_BREAK.split(text):
        lowered = re.split(r"[?#]", token, maxsplit=1)[0].lower()
        links += media_path(token) and any(marker in lowered for marker in COMMITTED)
    return links


def placement(text: str, url: str, kind: str) -> str | None:
    """Return None when every occurrence of url is the right embed, else why not."""
    escaped = re.escape(url)
    total = len(re.findall(rf"{escaped}(?!{URL_CHAR})", text))
    image = len(re.findall(rf"!\[[^\[\]]*\]\(\s*{escaped}(?:\s+\"[^\"\n]{{0,256}}\")?\s*\)", text))
    bare = len(re.findall(rf"(?m)^ {{0,3}}{escaped}[ \t]*$", text))
    video_file = url.lower().split("?")[0].endswith(VIDEO_EXTENSIONS)
    if "user-attachments/" not in url and "/uploads/" not in url:
        return "not a host upload URL (user-attachments or /uploads/)"
    if total == 0:
        return "missing"
    if kind == "video" and "user-attachments/" in url:
        return None if bare == total else "video must be the bare URL alone on its own line"
    if kind == "video" and not video_file:
        return "GitLab video needs a video extension"
    return None if image == total else f"{kind} must be inside ![alt](url)"


def check(body: str, videos: list[str], images: list[str]) -> dict[str, object]:
    texts = rendered_texts(body)
    problems = []
    embedded = {"video": 0, "image": 0}
    for kind, urls in (("video", videos), ("image", images)):
        for url in urls:
            problem = next(filter(None, (placement(text, url, kind) for text in texts)), None)
            if problem:
                problems.append(f"{url}: {problem}")
            else:
                embedded[kind] += 1
    links = max(media_links(text) for text in texts)
    ok = not problems and links == 0
    return {
        "videos": f"{embedded['video']}/{len(videos)}",
        "images": f"{embedded['image']}/{len(images)}",
        "media_links": links,
        "problems": problems[:10],
        "status": "PASS" if ok else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body", help="body file read back from the API, or - for stdin")
    parser.add_argument("--video-url", action="append", default=[], help="uploaded video URL")
    parser.add_argument("--image-url", action="append", default=[], help="uploaded image URL")
    args = parser.parse_args()
    if not args.video_url and not args.image_url:
        print("ERROR: pass every uploaded URL with --video-url/--image-url", file=sys.stderr)
        return 2
    try:
        body = (
            sys.stdin.read()
            if args.body == "-"
            else Path(args.body).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    result = check(body, args.video_url, args.image_url)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
