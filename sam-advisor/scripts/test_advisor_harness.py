#!/usr/bin/env python3
"""Validate advisor caller-bound advisor/model/effort and safety routing."""

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
SAMPLE_MODELS = {"codex": "gpt-5.6-sol", "claude": "opus"}
# Stand in for the real CLIs: echo how the prompt arrived and surround the
# answer with noise the caller must not have to read.
FAKE_CODEX = """
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
FAKE_CLAUDE = """
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


def install_fake(root: Path, name: str, body: str) -> dict[str, str]:
    fake = root / name
    fake.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    fake.chmod(0o755)
    return {**os.environ, "PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}"}


def check_codex_run() -> None:
    """The final message goes to a file (flag before the stdin '-'); --run
    must feed the prompt via stdin and surface only that final message."""
    with tempfile.TemporaryDirectory(prefix="sam-advisor-") as temporary:
        root = Path(temporary)
        prompt = root / "prompt.md"
        prompt.write_text("SECRET-QUESTION: is the cache safe?\n", encoding="utf-8")
        base = ("--advisor", "codex", "--model", SAMPLE_MODELS["codex"], "--effort", "high")

        command = json.loads(resolve(*base, "--prompt-file", str(prompt)).stdout)["command"]
        flag = command.index("--output-last-message")
        if command[-1] != "-" or command[flag + 1] != f"{prompt}.last.md":
            raise RuntimeError("last-message capture must precede the final stdin '-'")

        env = install_fake(root, "codex", FAKE_CODEX)
        ok = resolve(*base, "--run", "--prompt-file", str(prompt), env=env)
        lines = ok.stdout.splitlines()
        expected = f"FINAL stdin={len(prompt.read_text(encoding='utf-8'))} leak=False last=-"
        if ok.returncode != 0 or not lines or not lines[0].startswith("ADVISOR status=ok"):
            raise RuntimeError(f"codex --run did not succeed: {ok.stdout}{ok.stderr}")
        if lines[1:] != [expected]:
            raise RuntimeError(f"codex --run did not print only the final message: {lines}")
        log = Path(f"{prompt}.log").read_text(encoding="utf-8")
        if "TRANSCRIPT-NOISE" in ok.stdout or log.count("TRANSCRIPT-NOISE") != 2:
            raise RuntimeError("codex --run must keep the transcript in the log, not stdout")

        failed = resolve(*base, "--run", "--prompt-file", str(prompt), env={**env, "FAKE_MODE": "fail"})
        if failed.returncode == 0 or "status=failed" not in failed.stdout:
            raise RuntimeError("codex --run did not surface a failed invocation as a blocker")
        if resolve(*base, "--run", env=env).returncode == 0:
            raise RuntimeError("codex --run without --prompt-file did not fail closed")
        if resolve(*base, "--run", "--prompt-file", "prompt.md", env=env).returncode == 0:
            raise RuntimeError("codex relative --prompt-file did not fail closed")


def check_claude_run() -> None:
    """--run must send the prompt only via stdin and surface only the answer."""
    with tempfile.TemporaryDirectory(prefix="sam-advisor-") as temporary:
        root = Path(temporary)
        env = install_fake(root, "claude", FAKE_CLAUDE)
        prompt = root / "prompt.md"
        prompt.write_text("SECRET-QUESTION: is the cache safe?\n", encoding="utf-8")
        base = ("--advisor", "claude", "--model", SAMPLE_MODELS["claude"], "--effort", "high", "--run")

        ok = resolve(*base, "--prompt-file", str(prompt), env=env)
        lines = ok.stdout.splitlines()
        expected = f"ANSWER stdin={len(prompt.read_text(encoding='utf-8'))} leak=False"
        if ok.returncode != 0 or not lines or not lines[0].startswith("ADVISOR status=ok"):
            raise RuntimeError(f"claude --run did not succeed: {ok.stdout}{ok.stderr}")
        if lines[1:] != [expected]:
            raise RuntimeError(f"claude --run did not print only the stdin-fed answer: {lines}")
        log = Path(f"{prompt}.log").read_text(encoding="utf-8")
        if "ENVELOPE-NOISE" in ok.stdout or "ENVELOPE-NOISE" not in log:
            raise RuntimeError("claude --run must keep the raw envelope in the log, not stdout")

        failed = resolve(*base, "--prompt-file", str(prompt), env={**env, "FAKE_MODE": "fail"})
        if failed.returncode == 0 or "status=failed" not in failed.stdout:
            raise RuntimeError("claude --run did not surface a failed invocation as a blocker")
        if resolve(*base, env=env).returncode == 0:
            raise RuntimeError("claude --run without --prompt-file did not fail closed")
        if resolve(*base, "--prompt-file", "prompt.md", env=env).returncode == 0:
            raise RuntimeError("claude --run with a relative --prompt-file did not fail closed")


def check_advisor(advisor: str) -> None:
    model = SAMPLE_MODELS[advisor]
    missing_effort = resolve("--advisor", advisor, "--model", model)
    if missing_effort.returncode == 0:
        raise RuntimeError(f"{advisor}: resolver accepted missing --effort")

    missing_model = resolve("--advisor", advisor, "--effort", "high")
    if missing_model.returncode == 0:
        raise RuntimeError(f"{advisor}: resolver accepted missing --model")

    for effort in EFFORTS:
        result = resolve("--advisor", advisor, "--model", model, "--effort", effort)
        if result.returncode != 0:
            raise RuntimeError(f"{advisor}: valid effort {effort} rejected: {result.stderr}")
        plan = json.loads(result.stdout)
        command = plan["command"]
        if plan["advisor"] != advisor or plan["model"] != model or plan["effort"] != effort:
            raise RuntimeError(f"{advisor}: advisor/model/effort not preserved for {effort}")
        if command[0] != advisor or model not in command:
            raise RuntimeError(f"{advisor}: binary or selected model missing from argv")
        if any("dangerously" in item for item in command):
            raise RuntimeError(f"{advisor}: unsafe flag present")
        if advisor == "codex":
            if command[-1] != "-" or "read-only" not in command or "--ephemeral" not in command:
                raise RuntimeError("stdin, read-only, or ephemeral safety flag missing")
        elif "plan" not in command or "Read,Glob,Grep" not in command:
            raise RuntimeError("plan permission or read-only tools missing")
        elif "--no-session-persistence" not in command:
            raise RuntimeError("session persistence was not disabled")

    equals_form = json.loads(
        resolve(f"--advisor={advisor}", f"--model={model}", "--effort=high").stdout
    )
    if equals_form["model"] != model or equals_form["effort"] != "high":
        raise RuntimeError(f"{advisor}: equals-form model/effort override was not preserved")

    invalid = resolve("--advisor", advisor, "--model", model, "--effort", "ultra")
    if invalid.returncode == 0 or invalid.stdout:
        raise RuntimeError(f"{advisor}: unsupported effort did not fail closed")

    empty_model = resolve("--advisor", advisor, "--model", "   ", "--effort", "high")
    if empty_model.returncode == 0:
        raise RuntimeError(f"{advisor}: empty model was accepted")


def main() -> int:
    if resolve().returncode == 0:
        raise RuntimeError("resolver accepted missing --advisor/--model/--effort")

    no_advisor = resolve("--model", "opus", "--effort", "high")
    if no_advisor.returncode == 0 or no_advisor.stdout:
        raise RuntimeError("resolver accepted a missing --advisor")

    unknown = resolve("--advisor", "unknown-runtime", "--model", "m", "--effort", "high")
    if unknown.returncode == 0 or unknown.stdout or "unknown-runtime" not in unknown.stderr:
        raise RuntimeError("unknown advisor did not fail loud")

    for advisor in SAMPLE_MODELS:
        check_advisor(advisor)
    check_codex_run()
    check_claude_run()

    text = SKILL.read_text(encoding="utf-8")
    for fragment in (
        "host-runtime-matrix.md",
        "Bind `advisor`, `model`, and `effort`",
        "through stdin",
        "Do not silently fall back",
        "Act only as an advisor",
        "never guess it",
    ):
        if fragment not in text:
            raise RuntimeError(f"skill contract missing {fragment!r}")

    print("PASS: advisor caller-bound advisor/model/effort, stdin, and read-only contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
