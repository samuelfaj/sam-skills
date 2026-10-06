#!/usr/bin/env python3
"""Resolve a safe, fixed Grok worker invocation; with --run, execute it.

--run runs the argv without a shell, keeps the raw JSON and stderr in
<prompt-file>.log, prints one status line plus only the `text` report, and
deletes the prompt file after a successful run only when git reports no
repository around it (a file inside a repository may be tracked or wanted).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL = "grok-4.6"
SANDBOX = "workspace"
TAIL_LINES = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--effort", choices=EFFORTS, default="high")
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="Absolute path to the worker prompt file (required by headless Grok)",
    )
    parser.add_argument("--run", action="store_true", help="execute and print only the report")
    return parser.parse_args()


def outside_repository(path: Path) -> bool:
    """True only when git positively reports no repository around the path."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except OSError:
        return False
    return result.returncode != 0 and "not a git repository" in result.stderr


def run(command: list[str], prompt_file: Path, effort: str, defaulted: bool) -> int:
    log = Path(f"{prompt_file}.log")
    try:
        proc = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True, check=False
        )
    except OSError as error:
        print(f"WORKER status=failed error={error}")
        return 127
    log.write_bytes(b"== stdout ==\n" + proc.stdout + b"\n== stderr ==\n" + proc.stderr)
    report, is_error = None, False
    try:
        envelope = json.loads(proc.stdout)
        report = envelope.get("text")
        is_error = bool(envelope.get("is_error"))
    except (ValueError, AttributeError):
        pass
    ok = proc.returncode == 0 and not is_error and isinstance(report, str) and report.strip()
    deleted = bool(ok) and outside_repository(prompt_file)
    if deleted:
        prompt_file.unlink(missing_ok=True)
    print(
        f"WORKER status={'ok' if ok else 'failed'} exit={proc.returncode} "
        f"model={MODEL} effort={effort} defaulted={str(defaulted).lower()} "
        f"prompt={'deleted' if deleted else 'kept'} log={log}"
    )
    if ok:
        print(report.strip())
        return 0
    tail = proc.stderr.decode("utf-8", "replace").splitlines()[-TAIL_LINES:]
    if tail:
        print("\n".join(tail))
    return proc.returncode or 1


def main() -> int:
    args = parse_args()
    effort = args.effort
    effort_supplied = any(
        argument == "--effort" or argument.startswith("--effort=")
        for argument in sys.argv[1:]
    )
    prompt_file = str(Path(args.prompt_file).expanduser())
    if not Path(prompt_file).is_absolute():
        print(
            "ERROR: --prompt-file must be an absolute path",
            file=sys.stderr,
        )
        return 2
    command = [
        "grok",
        "--prompt-file",
        prompt_file,
        "--model",
        MODEL,
        "--effort",
        effort,
        "--output-format",
        "json",
        "--sandbox",
        SANDBOX,
        "--always-approve",
        "--no-memory",
        "--no-subagents",
        "--disallowed-tools",
        "Agent",
        "--no-auto-update",
    ]
    if args.run:
        if not Path(prompt_file).is_file():
            print("ERROR: --prompt-file does not exist", file=sys.stderr)
            return 2
        return run(command, Path(prompt_file), effort, not effort_supplied)
    print(
        json.dumps(
            {
                "worker": "grok",
                "model": MODEL,
                "effort": effort,
                "defaulted": not effort_supplied,
                "sandbox": SANDBOX,
                "writable": True,
                "ephemeral": True,
                "prompt_transport": "prompt-file",
                "prompt_file": prompt_file,
                "command": command,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
