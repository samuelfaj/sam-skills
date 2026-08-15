#!/usr/bin/env python3
"""Validate a sam-gauntlet-loop report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gauntlet_core import load_json_object, validate_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to report JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        text = args.report.read_text(encoding="utf-8")
        report = load_json_object(text, "report")
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    errors = validate_report(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("VALID")
    print(json.dumps({"result": report["decision"]["result"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
