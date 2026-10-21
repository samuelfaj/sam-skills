#!/usr/bin/env python3
"""Lint a Trello board export against the sam-trello card contract.

Input is JSON: {"cards": [{"id", "name", "desc", "shortUrl", "idLabels", "idMembers"}]}
(open cards only). Prints one ERROR line per problem and a final summary.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEADINGS = ["Context", "Goal", "Scope", "Definition of done", "Exclusions"]
LINK_RE = re.compile(r"\[[^\]]*\]\((https://trello\.com/c/[A-Za-z0-9]+)[^)]*\)")
DASHES = "\u2014\u2013"


def sentence_lengths(desc: str) -> list[int]:
    lengths: list[int] = []
    for line in desc.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"`[^`]*`", "X", line)
        line = re.sub(r"\]\([^)]*\)", "]", line)
        line = re.sub(r"https?://\S+", "X", line)
        line = re.sub(r"^(?:[-*] |\d+\. )", "", line)
        for sentence in re.split(r"(?<=[.!?:])\s+", line):
            words = [word for word in sentence.split() if re.search(r"\w", word)]
            if words:
                lengths.append(len(words))
    return lengths


def section(desc: str, heading: str, headings: list[str]) -> str | None:
    marker = f"## {heading}"
    start = desc.find(marker)
    if start < 0:
        return None
    body_start = start + len(marker)
    ends = [
        desc.find(f"## {other}", body_start) for other in headings if other != heading
    ]
    ends = [end for end in ends if end >= 0]
    return desc[body_start : min(ends) if ends else len(desc)]


def links_after(text: str, label: str, stop_label: str) -> list[str] | None:
    start = text.find(label)
    if start < 0:
        return None
    start += len(label)
    end = text.find(stop_label, start) if stop_label else -1
    chunk = text[start : end if end >= 0 else len(text)]
    return LINK_RE.findall(chunk)


def lint(cards: list[dict], args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    title_re = re.compile(
        rf"^{re.escape(args.prefix)} - {re.escape(args.task_word)} (\d+): \S"
    )
    headings = [h.strip() for h in args.headings.split(",")]
    all_headings = headings + [args.dependencies_heading]
    by_url = {card["shortUrl"]: card for card in cards}
    number: dict[str, int] = {}
    seen: dict[int, str] = {}
    for card in cards:
        match = title_re.match(card["name"])
        if not match:
            errors.append(
                f"title must be '{args.prefix} - {args.task_word} N: ...': {card['name']}"
            )
            continue
        n = int(match.group(1))
        if n in seen:
            errors.append(f"duplicate number {n}: {card['name']} and {seen[n]}")
        seen[n] = card["name"]
        number[card["id"]] = n
    if seen and sorted(seen) != list(range(1, len(seen) + 1)):
        errors.append(f"numbers must run 1..{len(seen)} without gaps: {sorted(seen)}")

    declared: dict[str, tuple[set[str], set[str]]] = {}
    for card in cards:
        name, desc = card["name"], card["desc"]
        order = [headings[0], args.dependencies_heading, *headings[1:]]
        positions = [desc.find(f"## {heading}") for heading in order]
        if -1 in positions or positions != sorted(positions):
            errors.append(f"sections must be {order} in order: {name}")
            continue
        for heading in order:
            body = section(desc, heading, all_headings) or ""
            if len(body.strip()) < 4:
                errors.append(f"empty section '{heading}': {name}")
        if any(ch in desc or ch in name for ch in DASHES):
            errors.append(f"em or en dash found: {name}")
        lengths = sentence_lengths(desc)
        if lengths and max(lengths) > args.max_sentence:
            errors.append(f"sentence of {max(lengths)} words (max {args.max_sentence}): {name}")
        if lengths and sum(lengths) / len(lengths) > args.max_average:
            errors.append(f"average sentence over {args.max_average} words: {name}")
        if args.label and args.label not in card.get("idLabels", []):
            errors.append(f"missing client label: {name}")
        if args.member and args.member not in card.get("idMembers", []):
            errors.append(f"missing assignee: {name}")

        deps = section(desc, args.dependencies_heading, all_headings) or ""
        before = links_after(deps, args.before_label, args.after_label)
        after = links_after(deps, args.after_label, "")
        if before is None or after is None:
            errors.append(
                f"dependencies need '{args.before_label}' and '{args.after_label}': {name}"
            )
            continue
        for url in before + after:
            if url not in by_url:
                errors.append(f"dead dependency link {url}: {name}")
        declared[card["id"]] = (
            {by_url[u]["id"] for u in before if u in by_url},
            {by_url[u]["id"] for u in after if u in by_url},
        )

    for card_id, (before, after) in declared.items():
        me = number.get(card_id)
        name = next(c["name"] for c in cards if c["id"] == card_id)
        for other in before:
            if me and number.get(other, 0) >= me:
                errors.append(f"dependency must have a lower number: {name}")
            if card_id not in declared.get(other, (set(), set()))[1]:
                errors.append(f"'{name}' needs a task that does not list it as unlocked")
        for other in after:
            if me and number.get(other, 10**9) <= me:
                errors.append(f"unlocked task must have a higher number: {name}")
            if card_id not in declared.get(other, (set(), set()))[0]:
                errors.append(f"'{name}' unlocks a task that does not list it as a dependency")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--prefix", required=True, help="client name, e.g. Berwanger")
    parser.add_argument("--task-word", default="Task")
    parser.add_argument("--headings", default=",".join(HEADINGS), help="template headings in order, comma separated")
    parser.add_argument("--dependencies-heading", default="Dependencies")
    parser.add_argument("--before-label", default="Finish these first:")
    parser.add_argument("--after-label", default="Unlocks:")
    parser.add_argument("--label", help="label id every card must have")
    parser.add_argument("--member", help="member id every card must have")
    parser.add_argument("--max-sentence", type=int, default=30)
    parser.add_argument("--max-average", type=float, default=15)
    args = parser.parse_args()
    data = json.loads(args.export.read_text(encoding="utf-8"))
    errors = lint(data["cards"], args)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(f"INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"VALID: {len(data['cards'])} card(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
