#!/usr/bin/env python3
"""Validate Codex advisor caller-bound model/effort and safety routing."""

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
SAMPLE_MODEL = "gpt-5.6-sol"
# Stands in for the real CLI: streams a noisy transcript and writes the final
# message to the --output-last-message file, echoing how the prompt arrived.
FAKE_CLI = """
import os, sys
prompt = sys.stdin.read()
argv = sys.argv[1:]
leak = any("SECRET-QUESTION" in arg for arg in argv)
print("TRANSCRIPT-NOISE exec rg ...")
print("TRANSCRIPT-NOISE tokens used", file=sys.stderr)
if os.environ.get("FAKE_MODE") == "fail":
    raise SystemExit(1)
target = argv[argv.index("--output-last-message") + 1]
with open(target, "w", encoding="utf-8") as handle:
    handle.write(f"FINAL stdin={len(prompt)} leak={leak} last={argv[-1]}\\n")
"""


def resolve(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(RESOLVER), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def check_last_message_and_run() -> None:
    """The final message goes to a file (flag before the stdin '-'); --run
    must feed the prompt via stdin and surface only that final message."""
    with tempfile.TemporaryDirectory(prefix="sam-advisor-") as temporary:
        root = Path(temporary)
        prompt = root / "prompt.md"
        prompt.write_text("SECRET-QUESTION: is the cache safe?\n", encoding="utf-8")
        base = ("--model", SAMPLE_MODEL, "--effort", "high")

        command = json.loads(resolve(*base, "--prompt-file", str(prompt)).stdout)["command"]
        flag = command.index("--output-last-message")
        if command[-1] != "-" or command[flag + 1] != f"{prompt}.last.md":
            raise RuntimeError("last-message capture must precede the final stdin '-'")

        fake = root / "codex"
        fake.write_text(f"#!{sys.executable}\n{FAKE_CLI}", encoding="utf-8")
        fake.chmod(0o755)
        env = {**os.environ, "PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}"}
        ok = resolve(*base, "--run", "--prompt-file", str(prompt), env=env)
        lines = ok.stdout.splitlines()
        expected = f"FINAL stdin={len(prompt.read_text(encoding='utf-8'))} leak=False last=-"
        if ok.returncode != 0 or not lines or not lines[0].startswith("ADVISOR status=ok"):
            raise RuntimeError(f"--run did not succeed: {ok.stdout}{ok.stderr}")
        if lines[1:] != [expected]:
            raise RuntimeError(f"--run did not print only the final message: {lines}")
        log = Path(f"{prompt}.log").read_text(encoding="utf-8")
        if "TRANSCRIPT-NOISE" in ok.stdout or log.count("TRANSCRIPT-NOISE") != 2:
            raise RuntimeError("--run must keep the transcript in the log, not stdout")

        failed = resolve(*base, "--run", "--prompt-file", str(prompt), env={**env, "FAKE_MODE": "fail"})
        if failed.returncode == 0 or "status=failed" not in failed.stdout:
            raise RuntimeError("--run did not surface a failed invocation as a blocker")
        if resolve(*base, "--run", env=env).returncode == 0:
            raise RuntimeError("--run without --prompt-file did not fail closed")
        if resolve(*base, "--run", "--prompt-file", "prompt.md", env=env).returncode == 0:
            raise RuntimeError("relative --prompt-file did not fail closed")


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
        if command[-1] != "-" or "read-only" not in command or "--ephemeral" not in command:
            raise RuntimeError("stdin, read-only, or ephemeral safety flag missing")
        if SAMPLE_MODEL not in command:
            raise RuntimeError("selected model missing from argv")
        if any("dangerously" in item for item in command):
            raise RuntimeError("unsafe Codex flag present")

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

    check_last_message_and_run()

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

    print("PASS: Codex advisor caller-bound model/effort, stdin, and read-only contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
