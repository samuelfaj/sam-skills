#!/usr/bin/env python3
"""Compile a host-safe gauntlet prompt. Does not run the loop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gauntlet_core import FETCH_METHODS, HOSTS, KINDS, compile_prompt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=HOSTS)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--bar-name", required=True)
    parser.add_argument("--bar-locator", required=True)
    parser.add_argument("--fetch-method", required=True, choices=FETCH_METHODS)
    parser.add_argument("--kind", required=True, choices=KINDS)
    parser.add_argument("--budget", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        compiled = compile_prompt(
            host=args.host,
            goal=args.goal,
            bar_name=args.bar_name,
            bar_locator=args.bar_locator,
            fetch_method=args.fetch_method,
            kind=args.kind,
            budget=args.budget,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(compiled, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
