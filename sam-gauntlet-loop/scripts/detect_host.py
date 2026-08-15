#!/usr/bin/env python3
"""Detect the active gauntlet host from process environment only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gauntlet_core import DETECT_STATUSES, HOSTS, detect_host


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=HOSTS, help="Explicit host override")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = detect_host(override=args.host)
    print(json.dumps(result, indent=2))
    if result["status"] not in DETECT_STATUSES:
        print("ERROR: unknown detector status", file=sys.stderr)
        return 2
    if result["status"] in {"DETECTED", "OVERRIDE"}:
        return 0
    print(f"ERROR: host {result['status']}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
