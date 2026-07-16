#!/usr/bin/env python3
"""Audit a demo plan for unsafe data, execution, and publication intent."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

SECRET = re.compile(
    r"(?:bearer\s+[a-z0-9._-]{12,}|(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}|eyJ[a-zA-Z0-9_-]{10,}\.)",
    re.I,
)


def strings(value: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f"{path}[{index}]")


def audit(manifest: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def issue(kind: str, location: str, evidence: str) -> None:
        issues.append(
            {
                "id": f"AUD-{len(issues) + 1:03d}",
                "kind": kind,
                "location": location,
                "evidence": evidence[:240],
            }
        )

    environment = report.get("environment", {})
    if environment.get("real_data") is True and environment.get("kind") not in {
        "local",
        "test",
        "dev",
    }:
        issue(
            "UNSAFE_REAL_DATA",
            "$.environment",
            "real data target is not verified local/test/dev",
        )
    publication = report.get("publication", {})
    if (
        publication.get("status") == "PUBLISHED"
        and report.get("authorization", {}).get("publish_requested") is not True
    ):
        issue(
            "UNAUTHORIZED_PUBLICATION",
            "$.publication",
            "publication exists without explicit request",
        )
    if (
        manifest.get("command_definitions")
        and report.get("command_definitions", {}).get("inspected") is not True
    ):
        issue(
            "UNINSPECTED_COMMAND",
            "$.command_definitions",
            "changed command definitions were not inspected",
        )
    for location, text in strings(report):
        match = SECRET.search(text)
        if match:
            issue(
                "SECRET_LIKE_TEXT",
                location,
                "secret-like value redacted; remove it from the report",
            )
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}


def load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("report")
    args = parser.parse_args()
    try:
        result = audit(load(args.manifest), load(args.report))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
