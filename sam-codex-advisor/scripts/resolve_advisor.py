#!/usr/bin/env python3
"""Resolve a safe Codex advisor invocation; with --run, execute it.

The calling agent supplies model and effort (from the sam-orchestrate
host-runtime-matrix advisor row, or an explicit user override). With
--prompt-file, the argv writes the final message to <prompt-file>.last.md.
--run pipes the prompt file through stdin (never argv), runs the argv without
a shell, keeps the transcript in <prompt-file>.log, and prints one status line
plus only the final message.
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
        help="Caller-selected Codex model (matrix advisor row or user override)",
    )
    parser.add_argument(
        "--effort",
        required=True,
        choices=EFFORTS,
        help="Caller-selected reasoning effort (matrix advisor row or user override)",
    )
    parser.add_argument("--run", action="store_true", help="execute and print only the answer")
    parser.add_argument("--prompt-file", help="absolute prompt file (required with --run)")
    return parser.parse_args()


def run(command: list[str], prompt_file: str, last_message: Path) -> int:
    try:
        prompt = Path(prompt_file).read_bytes()
    except OSError as error:
        print(f"ERROR: cannot read --prompt-file: {error}", file=sys.stderr)
        return 2
    log = Path(f"{prompt_file}.log")
    last_message.unlink(missing_ok=True)
    try:
        proc = subprocess.run(command, input=prompt, capture_output=True, check=False)
    except OSError as error:
        print(f"ADVISOR status=failed error={error}")
        return 127
    log.write_bytes(b"== stdout ==\n" + proc.stdout + b"\n== stderr ==\n" + proc.stderr)
    try:
        answer = last_message.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        answer = ""
    ok = proc.returncode == 0 and bool(answer)
    print(
        f"ADVISOR status={'ok' if ok else 'failed'} exit={proc.returncode} "
        f"last_message={last_message} log={log}"
    )
    if ok:
        print(answer)
        return 0
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
    if args.prompt_file is not None and not Path(args.prompt_file).is_absolute():
        print("ERROR: --prompt-file must be an absolute path", file=sys.stderr)
        return 2
    if args.run and args.prompt_file is None:
        print("ERROR: --run requires --prompt-file", file=sys.stderr)
        return 2
    effort = args.effort
    command = [
        "codex",
        "exec",
        "--strict-config",
        "--ephemeral",
        "--ignore-user-config",
        "--sandbox",
        "read-only",
        "--model",
        model,
        "--config",
        f'model_reasoning_effort="{effort}"',
    ]
    last_message = Path(f"{args.prompt_file}.last.md") if args.prompt_file else None
    if last_message is not None:
        command += ["--output-last-message", str(last_message)]
    command.append("-")
    if args.run and last_message is not None:
        return run(command, args.prompt_file, last_message)
    print(
        json.dumps(
            {
                "advisor": "codex",
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
