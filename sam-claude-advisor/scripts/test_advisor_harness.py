#!/usr/bin/env python3
"""Validate Claude advisor caller-bound model/effort and safety routing."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RESOLVER = SCRIPT_DIR / "resolve_advisor.py"
SKILL = SCRIPT_DIR.parent / "SKILL.md"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
SAMPLE_MODEL = "opus"


def resolve(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(RESOLVER), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    missing = resolve()
    if missing.returncode == 0:
        raise RuntimeError("resolver accepted missing --model/--effort")

    missing_effort = resolve("--model", SAMPLE_MODEL)
    if missing_effort.returncode == 0:
        raise RuntimeError("resolver accepted missing --effort")

    missing_model = resolve("--effort", "high")
    if missing_model.returncode == 0:
        raise RuntimeError("resolver accepted missing --model")

    for effort in EFFORTS:
        result = resolve("--model", SAMPLE_MODEL, "--effort", effort)
        if result.returncode != 0:
            raise RuntimeError(f"valid effort {effort} rejected: {result.stderr}")
        plan = json.loads(result.stdout)
        command = plan["command"]
        if plan["model"] != SAMPLE_MODEL or plan["effort"] != effort:
            raise RuntimeError(f"model/effort not preserved for {effort}")
        if "plan" not in command or "Read,Glob,Grep" not in command:
            raise RuntimeError("plan permission or read-only tools missing")
        if "--no-session-persistence" not in command:
            raise RuntimeError("session persistence was not disabled")
        if SAMPLE_MODEL not in command:
            raise RuntimeError("selected model missing from argv")
        if any("dangerously" in item for item in command):
            raise RuntimeError("unsafe Claude flag present")

    equals_form = json.loads(
        resolve(f"--model={SAMPLE_MODEL}", "--effort=high").stdout
    )
    if equals_form["model"] != SAMPLE_MODEL or equals_form["effort"] != "high":
        raise RuntimeError("equals-form model/effort override was not preserved")

    invalid = resolve("--model", SAMPLE_MODEL, "--effort", "ultra")
    if invalid.returncode == 0 or invalid.stdout:
        raise RuntimeError("unsupported effort did not fail closed")

    empty_model = resolve("--model", "   ", "--effort", "high")
    if empty_model.returncode == 0:
        raise RuntimeError("empty model was accepted")

    text = SKILL.read_text(encoding="utf-8")
    for fragment in (
        "host-runtime-matrix.md",
        "Bind `model` and `effort`",
        "through stdin",
        "Do not silently fall back",
        "Act only as an advisor",
    ):
        if fragment not in text:
            raise RuntimeError(f"skill contract missing {fragment!r}")

    print("PASS: Claude advisor caller-bound model/effort, stdin, and read-only contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
