#!/usr/bin/env python3
"""Resolve a safe, fixed Grok worker invocation without executing it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL = "grok-4.6"
SANDBOX = "workspace"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--effort", choices=EFFORTS, default="high")
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="Absolute path to the worker prompt file (required by headless Grok)",
    )
    return parser.parse_args()


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
