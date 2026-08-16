#!/usr/bin/env python3
"""Run CHECK commands in gate files, flip boxes, and record evidence."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


GATE_RE = re.compile(r"^- \[( |x|X)\] (.*)$")
ATTR_RE = re.compile(r"^\s+(CHECK|EXPECT|EVIDENCE):\s?(.*)$")
ABANDON_RE = re.compile(r"^ABANDON:\s*(\S+)\s*(.*)$")
EXPECT_RE = re.compile(r"^/(.+)/([a-z]*)$")
FLAG_MAP = {"i": re.I, "m": re.M, "s": re.S, "x": re.X}


@dataclass
class Gate:
    line: int
    checked: bool
    title: str
    id: str
    check: str | None = None
    expect: str | None = None
    evidence: str | None = None
    evidence_line: int = -1


@dataclass
class ParsedGates:
    gates: list[Gate] = field(default_factory=list)
    abandoned: dict[str, str] = field(default_factory=dict)


def default_files(root: Path) -> list[Path]:
    found: list[Path] = []
    top = root / "GATES.md"
    if top.is_file():
        found.append(top)
    gates_dir = root / "gates"
    if gates_dir.is_dir():
        found.extend(sorted(path for path in gates_dir.glob("*.md") if path.is_file()))
    return found


def expand_inputs(values: list[str]) -> list[Path]:
    if not values:
        return default_files(Path.cwd())
    found: list[Path] = []
    for raw in values:
        path = Path(raw)
        if path.is_dir():
            if (path / "GATES.md").is_file() or (path / "gates").is_dir():
                found.extend(default_files(path))
            else:
                found.extend(
                    sorted(item for item in path.glob("*.md") if item.is_file())
                )
            continue
        found.append(path)
    return found


def parse_gates(lines: list[str]) -> ParsedGates:
    parsed = ParsedGates()
    current: Gate | None = None
    for index, line in enumerate(lines):
        match = GATE_RE.match(line)
        if match:
            title = match.group(2).strip()
            identity_match = re.match(r"^(\S+?):", title)
            identity = identity_match.group(1) if identity_match else f"line{index + 1}"
            current = Gate(
                line=index,
                checked=match.group(1).lower() == "x",
                title=re.sub(r"^\S+?:\s*", "", title),
                id=identity,
            )
            parsed.gates.append(current)
            continue
        attr = current and ATTR_RE.match(line)
        if attr and current is not None:
            key = attr.group(1).lower()
            value = attr.group(2).strip()
            setattr(current, key, value)
            if key == "evidence":
                current.evidence_line = index
            continue
        abandoned = ABANDON_RE.match(line)
        if abandoned:
            parsed.abandoned[abandoned.group(1).rstrip(":")] = (
                abandoned.group(2).strip() or "(no reason)"
            )
        if re.match(r"^#|^- ", line) and not match:
            current = None
    return parsed


def expect_matches(expect: str, output: str) -> bool:
    wrapped = EXPECT_RE.fullmatch(expect)
    if wrapped:
        flags = 0
        for char in wrapped.group(2):
            if char not in FLAG_MAP:
                return False
            flags |= FLAG_MAP[char]
        try:
            return re.search(wrapped.group(1), output, flags) is not None
        except re.error:
            return False
    return expect in output


def tail(output: str, limit: int = 200) -> str:
    lines = [item.strip() for item in output.splitlines() if item.strip()]
    last = " | ".join(lines[-2:])
    return (last or "(no output)")[:limit]


def evidence_ready(evidence: str | None) -> bool:
    return bool(evidence) and not re.fullmatch(r"pending", evidence, re.I)


def run_check(command: str, timeout: int) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        return 124, f"{stdout}\n{stderr}\ntimeout after {timeout}s"
    return result.returncode, f"{result.stdout}\n{result.stderr}"


def process_file(path: Path, *, status_only: bool, timeout: int) -> tuple[int, int, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"gate-check: cannot read {path}: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    lines = text.splitlines()
    parsed = parse_gates(lines)
    if not parsed.gates:
        print(f"{path}: no gates found")
        return 0, 0, 0
    changed = False
    met = 0
    unmet = 0
    abandoned = 0
    for gate in parsed.gates:
        if gate.id in parsed.abandoned:
            abandoned += 1
            continue
        pending = not evidence_ready(gate.evidence)
        needs_run = not status_only and bool(gate.check) and (not gate.checked or pending)
        if needs_run and gate.check is not None:
            code, output = run_check(gate.check, timeout)
            ok = expect_matches(gate.expect, output) if gate.expect else code == 0
            if ok:
                lines[gate.line] = re.sub(r"^- \[ \]", "- [x]", lines[gate.line], count=1)
                if gate.evidence_line != -1:
                    indent = re.match(r"^\s*", lines[gate.evidence_line])
                    prefix = indent.group(0) if indent else ""
                    lines[gate.evidence_line] = f"{prefix}EVIDENCE: {tail(output)}"
                gate.checked = True
                gate.evidence = tail(output)
                changed = True
                print(f"  PASS {gate.id}: {gate.title}")
            else:
                print(f"  FAIL {gate.id}: {gate.title}\n       {tail(output)}")
        if gate.checked and evidence_ready(gate.evidence):
            met += 1
            continue
        unmet += 1
        if status_only:
            why = "unchecked" if not gate.checked else "checked but EVIDENCE pending"
            print(f"  UNMET {gate.id} ({why}): {gate.title}")
    if changed:
        path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    print(f"{path}: {len(parsed.gates)} gates")
    return met, unmet, abandoned


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="Gate files or directories")
    parser.add_argument("--status", action="store_true", help="Report only")
    parser.add_argument("--timeout", type=int, default=120, help="Per-check seconds")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    files = expand_inputs(args.files)
    if not files:
        print("gate-check: no gate files found (GATES.md or gates/*.md)", file=sys.stderr)
        return 2
    total_met = 0
    total_unmet = 0
    total_abandoned = 0
    for path in files:
        if not path.is_file():
            print(f"gate-check: cannot read {path}: not a file", file=sys.stderr)
            return 2
        met, unmet, abandoned = process_file(
            path, status_only=args.status, timeout=max(1, args.timeout)
        )
        total_met += met
        total_unmet += unmet
        total_abandoned += abandoned
    extra = f", {total_abandoned} abandoned" if total_abandoned else ""
    if total_unmet == 0:
        print(f"ALL MET ({total_met} met{extra})")
        return 0
    print(f"UNMET: {total_unmet} (met: {total_met}{extra})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
