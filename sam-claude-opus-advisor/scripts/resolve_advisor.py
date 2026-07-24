#!/usr/bin/env python3
"""Resolve a safe, fixed Claude Opus advisor invocation without executing it."""

from __future__ import annotations

import argparse
import json
import sys


EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL = "opus"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--effort", choices=EFFORTS, default="high")
    return parser.parse_args()


def main() -> int:
    effort = parse_args().effort
    effort_supplied = any(
        argument == "--effort" or argument.startswith("--effort=")
        for argument in sys.argv[1:]
    )
    command = [
        "claude",
        "--print",
        "--model",
        MODEL,
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
    print(
        json.dumps(
            {
                "advisor": "claude",
                "model": MODEL,
                "effort": effort,
                "defaulted": not effort_supplied,
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
