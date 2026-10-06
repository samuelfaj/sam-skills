#!/usr/bin/env python3
"""Resolve a safe advisor invocation (codex or claude); with --run, execute it.

The calling agent supplies advisor, model and effort (from the sam-orchestrate
host-runtime-matrix advisor row, or an explicit user override). --run pipes the
prompt file through stdin (never argv), runs the argv without a shell, keeps
the raw output in <prompt-file>.log, and prints one status line plus only the
answer text. The codex argv writes its final message to <prompt-file>.last.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ADVISORS = ("codex", "claude")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
TAIL_LINES = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--advisor",
        required=True,
        choices=ADVISORS,
        help="Advisor runtime to invoke",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Caller-selected model alias/id (matrix advisor row or user override)",
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


def read_prompt(prompt_file: str) -> bytes | None:
    try:
        return Path(prompt_file).read_bytes()
    except OSError as error:
        print(f"ERROR: cannot read --prompt-file: {error}", file=sys.stderr)
        return None


def execute(command: list[str], prompt: bytes, log: Path) -> subprocess.CompletedProcess[bytes] | None:
    try:
        proc = subprocess.run(command, input=prompt, capture_output=True, check=False)
    except OSError as error:
        print(f"ADVISOR status=failed error={error}")
        return None
    log.write_bytes(b"== stdout ==\n" + proc.stdout + b"\n== stderr ==\n" + proc.stderr)
    return proc


def stderr_tail(proc: subprocess.CompletedProcess[bytes]) -> None:
    tail = proc.stderr.decode("utf-8", "replace").splitlines()[-TAIL_LINES:]
    if tail:
        print("\n".join(tail))


def run_codex(command: list[str], prompt_file: str, last_message: Path) -> int:
    prompt = read_prompt(prompt_file)
    if prompt is None:
        return 2
    log = Path(f"{prompt_file}.log")
    last_message.unlink(missing_ok=True)
    proc = execute(command, prompt, log)
    if proc is None:
        return 127
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
    stderr_tail(proc)
    return proc.returncode or 1


def run_claude(command: list[str], prompt_file: str | None) -> int:
    if not prompt_file or not Path(prompt_file).is_absolute():
        print("ERROR: --run requires an absolute --prompt-file", file=sys.stderr)
        return 2
    prompt = read_prompt(prompt_file)
    if prompt is None:
        return 2
    log = Path(f"{prompt_file}.log")
    proc = execute(command, prompt, log)
    if proc is None:
        return 127
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
    stderr_tail(proc)
    return proc.returncode or 1


def codex_command(model: str, effort: str, last_message: Path | None) -> list[str]:
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
    if last_message is not None:
        command += ["--output-last-message", str(last_message)]
    command.append("-")
    return command


def claude_command(model: str, effort: str) -> list[str]:
    return [
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


def main() -> int:
    args = parse_args()
    model = args.model.strip()
    if not model:
        print("error: --model must be non-empty", file=sys.stderr)
        return 2
    last_message = None
    if args.advisor == "codex":
        if args.prompt_file is not None and not Path(args.prompt_file).is_absolute():
            print("ERROR: --prompt-file must be an absolute path", file=sys.stderr)
            return 2
        if args.run and args.prompt_file is None:
            print("ERROR: --run requires --prompt-file", file=sys.stderr)
            return 2
        last_message = Path(f"{args.prompt_file}.last.md") if args.prompt_file else None
        command = codex_command(model, args.effort, last_message)
    else:
        command = claude_command(model, args.effort)
    if args.run:
        if args.advisor == "codex":
            return run_codex(command, args.prompt_file, last_message)
        return run_claude(command, args.prompt_file)
    print(
        json.dumps(
            {
                "advisor": args.advisor,
                "model": model,
                "effort": args.effort,
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
