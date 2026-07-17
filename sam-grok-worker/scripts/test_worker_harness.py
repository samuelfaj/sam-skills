#!/usr/bin/env python3
"""Validate Grok worker model, effort, prompt-file, and safety routing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RESOLVER = SCRIPT_DIR / "resolve_worker.py"
SKILL = SCRIPT_DIR.parent / "SKILL.md"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL = "grok-4.5"


def resolve(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(RESOLVER), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    with tempfile.NamedTemporaryFile(
        prefix="sam-grok-worker-",
        suffix=".prompt",
        delete=False,
    ) as handle:
        prompt_path = Path(handle.name).resolve()
        handle.write(b"test prompt\n")

    try:
        missing = resolve()
        if missing.returncode == 0:
            raise RuntimeError("missing --prompt-file did not fail closed")

        relative = resolve("--prompt-file", "relative.prompt")
        if relative.returncode == 0:
            raise RuntimeError("relative --prompt-file did not fail closed")

        default = resolve("--prompt-file", str(prompt_path))
        if default.returncode != 0:
            raise RuntimeError(default.stderr)
        default_plan = json.loads(default.stdout)
        if default_plan["model"] != MODEL or default_plan["effort"] != "high":
            raise RuntimeError("default model or effort drifted")
        if default_plan["defaulted"] is not True:
            raise RuntimeError("default effort was not identified")
        if default_plan["sandbox"] != "workspace" or default_plan["writable"] is not True:
            raise RuntimeError("workspace sandbox or writable flag drifted")
        if default_plan["prompt_transport"] != "prompt-file":
            raise RuntimeError("prompt transport drifted")

        for effort in EFFORTS:
            result = resolve("--prompt-file", str(prompt_path), "--effort", effort)
            if result.returncode != 0:
                raise RuntimeError(f"valid effort {effort} rejected: {result.stderr}")
            plan = json.loads(result.stdout)
            command = plan["command"]
            if plan["effort"] != effort or plan["defaulted"] is not False:
                raise RuntimeError(f"explicit effort {effort} was not preserved")
            if "--prompt-file" not in command or str(prompt_path) not in command:
                raise RuntimeError("prompt-file routing missing")
            if "--always-approve" not in command:
                raise RuntimeError("always-approve missing for unattended worker")
            if "--sandbox" not in command or "workspace" not in command:
                raise RuntimeError("workspace sandbox missing")
            if "--no-memory" not in command or "--no-subagents" not in command:
                raise RuntimeError("ephemeral or no-subagents safety flag missing")
            if "Agent" not in command:
                raise RuntimeError("Agent disallowed-tools entry missing")
            if any("yolo" in item for item in command):
                raise RuntimeError("opaque yolo alias used instead of always-approve")
            if any("dangerously" in item for item in command):
                raise RuntimeError("unsafe worker flag present")

        equals_form = json.loads(
            resolve("--prompt-file", str(prompt_path), "--effort=high").stdout
        )
        if equals_form["effort"] != "high" or equals_form["defaulted"] is not False:
            raise RuntimeError("equals-form effort override was not preserved")

        invalid = resolve("--prompt-file", str(prompt_path), "--effort", "ultra")
        if invalid.returncode == 0 or invalid.stdout:
            raise RuntimeError("unsupported effort did not fail closed")

        text = SKILL.read_text(encoding="utf-8")
        for fragment in (
            "grok-4.5",
            "unless the user explicitly supplies",
            "--prompt-file",
            "Do not silently fall back",
            "Act only as a worker",
            "workspace",
        ):
            if fragment not in text:
                raise RuntimeError(f"skill contract missing {fragment!r}")
    finally:
        prompt_path.unlink(missing_ok=True)

    print(
        "PASS: Grok worker model, effort override, prompt-file, and workspace contract"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
