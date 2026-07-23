#!/usr/bin/env python3
"""Create a plan output directory with a safe, empty layout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        help="Absolute or relative path for the plan directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable result on stdout",
    )
    args = parser.parse_args()

    plan_dir = Path(args.out).expanduser()
    if not plan_dir.is_absolute():
        plan_dir = (Path.cwd() / plan_dir).resolve()
    else:
        plan_dir = plan_dir.resolve()

    if plan_dir.exists() and not plan_dir.is_dir():
        print(f"error: path exists and is not a directory: {plan_dir}", file=sys.stderr)
        return 2

    plan_dir.mkdir(parents=True, exist_ok=True)
    assets = plan_dir / "assets"
    assets.mkdir(exist_ok=True)
    gitkeep = assets / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    result = {
        "plan_dir": str(plan_dir),
        "assets_dir": str(assets),
        "created": True,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(str(plan_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
