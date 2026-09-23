#!/usr/bin/env python3
"""Validate Claude advisor caller-bound model/effort and safety routing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RESOLVER = SCRIPT_DIR / "resolve_advisor.py"
SKILL = SCRIPT_DIR.parent / "SKILL.md"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
SAMPLE_MODEL = "opus"
# Stands in for the real CLI: echoes how the prompt arrived and wraps the
# answer in metadata the caller must not have to read.
FAKE_CLI = """
import json, os, sys
prompt = sys.stdin.read()
leak = any("SECRET-QUESTION" in arg for arg in sys.argv[1:])
if os.environ.get("FAKE_MODE") == "fail":
    print(json.dumps({"is_error": True, "result": "auth failed"}))
    print("fatal: not logged in", file=sys.stderr)
    raise SystemExit(1)
print(json.dumps({"is_error": False, "result": f"ANSWER stdin={len(prompt)} leak={leak}",
                  "usage": {"ENVELOPE-NOISE": 1}}))
"""


def resolve(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(RESOLVER), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def check_run_mode() -> None:
    """--run must send the prompt only via stdin and surface only the answer."""
    with tempfile.TemporaryDirectory(prefix="sam-advisor-") as temporary:
        root = Path(temporary)
        fake = root / "claude"
        fake.write_text(f"#!{sys.executable}\n{FAKE_CLI}", encoding="utf-8")
        fake.chmod(0o755)
        prompt = root / "prompt.md"
        prompt.write_text("SECRET-QUESTION: is the cache safe?\n", encoding="utf-8")
        env = {**os.environ, "PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}"}
        base = ("--model", SAMPLE_MODEL, "--effort", "high", "--run")

        ok = resolve(*base, "--prompt-file", str(prompt), env=env)
        lines = ok.stdout.splitlines()
        expected = f"ANSWER stdin={len(prompt.read_text(encoding='utf-8'))} leak=False"
        if ok.returncode != 0 or not lines or not lines[0].startswith("ADVISOR status=ok"):
            raise RuntimeError(f"--run did not succeed: {ok.stdout}{ok.stderr}")
        if lines[1:] != [expected]:
            raise RuntimeError(f"--run did not print only the stdin-fed answer: {lines}")
        log = Path(f"{prompt}.log").read_text(encoding="utf-8")
        if "ENVELOPE-NOISE" in ok.stdout or "ENVELOPE-NOISE" not in log:
            raise RuntimeError("--run must keep the raw envelope in the log, not stdout")

        failed = resolve(*base, "--prompt-file", str(prompt), env={**env, "FAKE_MODE": "fail"})
        if failed.returncode == 0 or "status=failed" not in failed.stdout:
            raise RuntimeError("--run did not surface a failed invocation as a blocker")
        if resolve(*base, env=env).returncode == 0:
            raise RuntimeError("--run without --prompt-file did not fail closed")
        if resolve(*base, "--prompt-file", "prompt.md", env=env).returncode == 0:
            raise RuntimeError("--run with a relative --prompt-file did not fail closed")


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

    check_run_mode()

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
