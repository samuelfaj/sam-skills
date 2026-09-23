#!/usr/bin/env python3
"""Validate Grok worker model, effort, prompt-file, and safety routing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RESOLVER = SCRIPT_DIR / "resolve_worker.py"
SKILL = SCRIPT_DIR.parent / "SKILL.md"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL = "grok-4.6"
# Stands in for the real CLI: reads the task only from --prompt-file and wraps
# the report in metadata the caller must not have to read.
FAKE_CLI = """
import json, os, sys
argv = sys.argv[1:]
task = open(argv[argv.index("--prompt-file") + 1], encoding="utf-8").read()
piped = sys.stdin.read()
if os.environ.get("FAKE_MODE") == "fail":
    print("fatal: sandbox unavailable", file=sys.stderr)
    raise SystemExit(3)
print(json.dumps({"text": f"REPORT task={len(task)} piped={len(piped)}",
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
    """--run must deliver the task only via --prompt-file, surface only the
    `text` report, keep the envelope in the log, and delete the prompt only
    after success and only outside any repository, where it cannot be a
    tracked or wanted file."""
    with tempfile.TemporaryDirectory(prefix="sam-grok-worker-run-") as temporary:
        root = Path(temporary).resolve()
        fake = root / "grok"
        fake.write_text(f"#!{sys.executable}\n{FAKE_CLI}", encoding="utf-8")
        fake.chmod(0o755)
        env = {
            **os.environ,
            "PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}",
            "GIT_CEILING_DIRECTORIES": str(root.parent),
        }
        prompt = root / "task.prompt"
        prompt.write_text("Fix the bounded bug.\n", encoding="utf-8")
        size = len(prompt.read_text(encoding="utf-8"))

        failed = resolve("--prompt-file", str(prompt), "--run", env={**env, "FAKE_MODE": "fail"})
        if failed.returncode == 0 or "status=failed" not in failed.stdout:
            raise RuntimeError("--run did not surface a failed invocation as a blocker")
        if not prompt.exists():
            raise RuntimeError("--run deleted the prompt file after a failure")

        ok = resolve("--prompt-file", str(prompt), "--run", env=env)
        lines = ok.stdout.splitlines()
        if ok.returncode != 0 or not lines or not lines[0].startswith("WORKER status=ok"):
            raise RuntimeError(f"--run did not succeed: {ok.stdout}{ok.stderr}")
        if "defaulted=true" not in lines[0] or lines[1:] != [f"REPORT task={size} piped=0"]:
            raise RuntimeError(f"--run did not print only the prompt-file report: {lines}")
        log = Path(f"{prompt}.log").read_text(encoding="utf-8")
        if "ENVELOPE-NOISE" in ok.stdout or "ENVELOPE-NOISE" not in log:
            raise RuntimeError("--run must keep the raw envelope in the log, not stdout")
        if prompt.exists() or "prompt=deleted" not in lines[0]:
            raise RuntimeError("--run kept a prompt file outside any repository after success")
        if resolve("--prompt-file", str(prompt), "--run", env=env).returncode == 0:
            raise RuntimeError("--run with a missing prompt file did not fail closed")

        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
        in_tree = repo / "docs/task.md"
        in_tree.parent.mkdir()
        in_tree.write_text("Fix the bounded bug.\n", encoding="utf-8")
        kept = resolve("--prompt-file", str(in_tree), "--run", env=env)
        if kept.returncode != 0 or "prompt=kept" not in kept.stdout.splitlines()[0]:
            raise RuntimeError(f"--run in a repository did not report a kept prompt: {kept.stdout}")
        if not in_tree.exists():
            raise RuntimeError("--run deleted a prompt file inside a repository work tree")


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

        check_run_mode()

        text = SKILL.read_text(encoding="utf-8")
        for fragment in (
            "grok-4.6",
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
