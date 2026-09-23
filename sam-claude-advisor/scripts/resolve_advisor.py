#!/usr/bin/env python3
"""Resolve a safe Claude advisor invocation; with --run, execute it.

The calling agent supplies model and effort (from the sam-orchestrate
host-runtime-matrix advisor row, or an explicit user override). --run pipes
the prompt file through stdin (never argv), runs the argv without a shell,
writes the raw output to <prompt-file>.log, and prints one status line plus
only the answer text.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


EFFORTS = ("low", "medium", "high", "xhigh", "max")
TAIL_LINES = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        required=True,
        help="Caller-selected Claude model alias/id (matrix advisor row or user override)",
    )
    parser.add_argument(
        "--effort",
        required=True,
        choices=EFFORTS,
        help="Caller-selected effort (matrix advisor row or user override)",
    )
    parser.add_argument("--run", action="store_true", help="execute and print only the answer")
    parser.add_argument("--prompt-file", help="absolute prompt file (required with --run)")
    return parser.parse_args()


def run(command: list[str], prompt_file: str | None) -> int:
    if not prompt_file or not Path(prompt_file).is_absolute():
        print("ERROR: --run requires an absolute --prompt-file", file=sys.stderr)
        return 2
    try:
        prompt = Path(prompt_file).read_bytes()
    except OSError as error:
        print(f"ERROR: cannot read --prompt-file: {error}", file=sys.stderr)
        return 2
    log = Path(f"{prompt_file}.log")
    try:
        proc = subprocess.run(command, input=prompt, capture_output=True, check=False)
    except OSError as error:
        print(f"ADVISOR status=failed error={error}")
        return 127
    log.write_bytes(b"== stdout ==\n" + proc.stdout + b"\n== stderr ==\n" + proc.stderr)
    answer, is_error = None, True
    try:
        envelope = json.loads(proc.stdout)
        answer = envelope.get("result")
        is_error = bool(envelope.get("is_error"))
    except (ValueError, AttributeError):
        pass
    ok = proc.returncode == 0 and not is_error and isinstance(answer, str) and answer.strip()
    print(
        f"ADVISOR status={'ok' if ok else 'failed'} exit={proc.returncode} "
        f"is_error={str(is_error).lower()} log={log}"
    )
    if ok:
        print(answer.strip())
        return 0
    if isinstance(answer, str) and answer.strip():
        print(answer.strip()[:2000])
    tail = proc.stderr.decode("utf-8", "replace").splitlines()[-TAIL_LINES:]
    if tail:
        print("\n".join(tail))
    return proc.returncode or 1


def main() -> int:
    args = parse_args()
    model = args.model.strip()
    if not model:
        print("error: --model must be non-empty", file=sys.stderr)
        return 2
    effort = args.effort
    command = [
        "claude",
        "--print",
        "--model",
        model,
        "--effort",
        effort,
        "--permission-mode",
        "plan",
        "--tools",
        "Read,Glob,Grep",
        "--no-session-persistence",
        "--output-format",
        "json",
    ]
    if args.run:
        return run(command, args.prompt_file)
    print(
        json.dumps(
            {
                "advisor": "claude",
                "model": model,
                "effort": effort,
                "read_only": True,
                "ephemeral": True,
                "prompt_transport": "stdin",
                "command": command,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
