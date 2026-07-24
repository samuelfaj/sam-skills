#!/usr/bin/env python3
"""Validate Claude Opus advisor model, effort, and safety routing."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RESOLVER = SCRIPT_DIR / "resolve_advisor.py"
SKILL = SCRIPT_DIR.parent / "SKILL.md"
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def resolve(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(RESOLVER), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    default = resolve()
    if default.returncode != 0:
        raise RuntimeError(default.stderr)
    default_plan = json.loads(default.stdout)
    if default_plan["model"] != "opus" or default_plan["effort"] != "high":
        raise RuntimeError("default model or effort drifted")
    if default_plan["defaulted"] is not True:
        raise RuntimeError("default effort was not identified")

    for effort in EFFORTS:
        result = resolve("--effort", effort)
        if result.returncode != 0:
            raise RuntimeError(f"valid effort {effort} rejected: {result.stderr}")
        plan = json.loads(result.stdout)
        command = plan["command"]
        if plan["effort"] != effort or plan["defaulted"] is not False:
            raise RuntimeError(f"explicit effort {effort} was not preserved")
        if "plan" not in command or "Read,Glob,Grep" not in command:
            raise RuntimeError("plan permission or read-only tools missing")
        if "--no-session-persistence" not in command:
            raise RuntimeError("session persistence was not disabled")
        if any("dangerously" in item for item in command):
            raise RuntimeError("unsafe Claude flag present")

    equals_form = json.loads(resolve("--effort=high").stdout)
    if equals_form["effort"] != "high" or equals_form["defaulted"] is not False:
        raise RuntimeError("equals-form effort override was not preserved")

    invalid = resolve("--effort", "ultra")
    if invalid.returncode == 0 or invalid.stdout:
        raise RuntimeError("unsupported effort did not fail closed")

    text = SKILL.read_text(encoding="utf-8")
    for fragment in (
        "model alias `opus` exactly",
        "unless the user explicitly supplies",
        "through stdin",
        "Do not silently fall back",
        "Act only as an advisor",
    ):
        if fragment not in text:
            raise RuntimeError(f"skill contract missing {fragment!r}")

    print("PASS: Claude Opus advisor model, effort override, stdin, and read-only contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
