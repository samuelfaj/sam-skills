#!/usr/bin/env python3
"""Resolve a safe Claude advisor invocation without executing it.

The calling agent supplies model and effort (from the sam-orchestrate
host-runtime-matrix advisor row, or an explicit user override).
"""

from __future__ import annotations

import argparse
import json
import sys


EFFORTS = ("low", "medium", "high", "xhigh", "max")


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
    return parser.parse_args()


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
