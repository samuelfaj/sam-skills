#!/usr/bin/env python3
"""Parse a DELEGATION.md ledger and report whether every unit is verified."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


HEADER_RE = re.compile(r"^\|\s*#\s*\|")
SEPARATOR_RE = re.compile(r"^:?-+:?$")
COMMAND_RE = re.compile(
    r"\b(?:node|python3?|pytest|git|npx|npm|pnpm|make|tsc|deno|bash|sh|ruby|go|cargo)\b",
    re.I,
)
PATH_RE = re.compile(r"\b[\w./-]+\.[a-z0-9]{1,5}\b", re.I)
MEASURE_RE = re.compile(r"\b\d+\s*(passed|pass|ok|of)\b", re.I)
EXIT_RE = re.compile(r"exit\s+\d+", re.I)


@dataclass(frozen=True)
class Row:
    unit: str
    name: str
    files: str
    worker: str
    acceptance: str
    status: str


def split_cells(line: str) -> list[str]:
    cells = (
        line.replace("\\|", "\x00").split("|")[1:-1]
    )
    return [cell.strip().replace("\x00", "|") for cell in cells]


def parse_rows(lines: list[str]) -> tuple[int, list[Row], list[tuple[int, list[str]]]]:
    header_idx = next((index for index, line in enumerate(lines) if HEADER_RE.match(line)), -1)
    if header_idx == -1:
        raise ValueError("not a DELEGATION.md ledger (no unit table header)")
    rows: list[Row] = []
    malformed: list[tuple[int, list[str]]] = []
    for index in range(header_idx + 1, len(lines)):
        raw = lines[index].strip()
        if not raw:
            continue
        if not raw.startswith("|"):
            break
        cells = split_cells(raw)
        if cells and all(cell == "" or SEPARATOR_RE.match(cell) for cell in cells):
            continue
        if len(cells) < 6:
            malformed.append((index + 1, cells))
            continue
        if cells[0] == "..." or cells[1] == "...":
            continue
        rows.append(
            Row(
                unit=cells[0],
                name=cells[1],
                files=cells[2],
                worker=cells[3],
                acceptance=cells[4],
                status=cells[5].lower(),
            )
        )
    return header_idx, rows, malformed


def is_strong_evidence(line: str) -> bool:
    for span in re.findall(r"`[^`]+`", line):
        inner = span[1:-1].strip()
        if re.search(r"\s", inner) or re.search(r"[/.]", inner):
            return True
    return bool(
        COMMAND_RE.search(line)
        or PATH_RE.search(line)
        or MEASURE_RE.search(line)
        or EXIT_RE.search(line)
    )


def evidence_present(lines: list[str], header_idx: int) -> bool:
    in_rules = False
    strong = 0
    for raw in lines[header_idx + 1 :]:
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^##\s+", line):
            in_rules = bool(re.match(r"^##\s+Rules of this ledger\s*$", line, re.I))
            continue
        if line.startswith("|") or in_rules:
            continue
        if line.lower().startswith("units:"):
            continue
        if re.search(r"<[^>]+>", line):
            continue
        if is_strong_evidence(line):
            strong += 1
    return strong >= 1


def inspect(path: Path) -> tuple[int, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return 2, f"ledger: cannot read {path}: {error}"
    lines = text.splitlines()
    try:
        header_idx, rows, malformed = parse_rows(lines)
    except ValueError as error:
        return 2, f"ledger: {path} is {error}"
    if not rows:
        return 2, f"ledger: {path} has a table header but no unit rows"
    counts = {"pending": 0, "done": 0, "verified": 0, "other": 0}
    unverified: list[Row] = []
    for row in rows:
        if row.status in counts:
            counts[row.status] += 1
        else:
            counts["other"] += 1
        if row.status != "verified":
            unverified.append(row)
    evidence_ok = evidence_present(lines, header_idx)
    report = [
        f"ledger: {path}",
        f"  units:       {len(rows)}",
        f"  verified:    {counts['verified']}",
        f"  done:        {counts['done']}",
        f"  pending:     {counts['pending']}",
    ]
    if counts["other"]:
        report.append(f"  other:       {counts['other']}")
    if malformed:
        report.append(f"  malformed:   {len(malformed)}")
    report.append(f"  evidence:    {'present' if evidence_ok else 'MISSING'}")
    if unverified:
        report.append("  unverified rows:")
        report.extend(f"    - #{row.unit} {row.name} [{row.status}]" for row in unverified)
    if malformed:
        report.append("  malformed rows:")
        report.extend(
            f"    - line {line_no}: {' | '.join(cells)}" for line_no, cells in malformed
        )
    complete = (
        all(row.status == "verified" for row in rows)
        and evidence_ok
        and not malformed
    )
    report.append(
        "  -> ledger complete: every unit verified."
        if complete
        else "  -> ledger INCOMPLETE."
    )
    return (0 if complete else 1), "\n".join(report)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="DELEGATION.md")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    code, report = inspect(Path(args.path))
    stream = sys.stdout if code != 2 else sys.stderr
    print(report, file=stream)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
