#!/usr/bin/env python3
"""Compile a host-safe gauntlet prompt and self-validate its report. Does not run the loop."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gauntlet_core import FETCH_METHODS, HOSTS, KINDS, build_report, validate_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=HOSTS)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--bar-name", required=True)
    parser.add_argument("--bar-locator", required=True)
    parser.add_argument("--fetch-method", required=True, choices=FETCH_METHODS)
    parser.add_argument("--kind", required=True, choices=KINDS)
    parser.add_argument("--budget", default="")
    parser.add_argument(
        "--user-host",
        action="store_true",
        help="The user named --host after detection returned UNKNOWN or CONFLICT",
    )
    parser.add_argument("--report", type=Path, help="Also save the validated report here")
    return parser.parse_args()


def repo_root(where: Path) -> Path | None:
    """The git top level of `where`, or None outside a repository, for a missing dir, or without git."""
    try:
        found = subprocess.run(
            ["git", "-C", str(where), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    top = found.stdout.strip()
    return Path(top).resolve() if found.returncode == 0 and top else None


def main() -> int:
    args = parse_args()
    if args.report:
        args.report = args.report.expanduser().resolve()
        # Both the cwd's repository and the one holding the report path count.
        for top in (repo_root(Path.cwd()), repo_root(args.report.parent)):
            if top and args.report.is_relative_to(top):
                print(f"ERROR: --report must be outside the repository {top}", file=sys.stderr)
                return 2
    try:
        report = build_report(
            host=args.host,
            goal=args.goal,
            bar_name=args.bar_name,
            bar_locator=args.bar_locator,
            fetch_method=args.fetch_method,
            kind=args.kind,
            budget=args.budget,
            user_host=args.user_host,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    errors = validate_report(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 1
    if args.report:
        try:
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        except OSError as error:
            print(f"ERROR: cannot write --report {args.report}: {error.strerror or error}", file=sys.stderr)
            return 2
    host = report["host"]
    remaining = report["decision"]["remaining"]
    if remaining:
        for gap in remaining:
            print(f"ERROR: {gap}", file=sys.stderr)
        codes = ",".join(dict.fromkeys(gap.split(":", 1)[0] for gap in remaining))
        print(f"VALID BLOCKED {codes}")
        return 2
    print(report["prompt"])
    print(f"VALID PROMPT_READY host={host['key']} ({host['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
