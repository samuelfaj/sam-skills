#!/usr/bin/env python3
"""Reject common test-suite weakening patterns in an E2E bundle patch."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ADDED_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("FOCUSED_TEST", re.compile(r"\b(?:test|it|describe)\.only\s*\(")),
    ("SKIPPED_TEST", re.compile(r"\b(?:test|it|describe)\.(?:skip|fixme)\s*\(")),
    ("RETRY_INCREASE", re.compile(r"\b(?:retries|retry)\s*[:=(]\s*[1-9]")),
    (
        "TIMEOUT_INCREASE",
        re.compile(
            r"\b(?:setDefaultTimeout|setTimeout|timeout)\s*\(?\s*[1-9][0-9]{3,}"
        ),
    ),
    (
        "SNAPSHOT_REFRESH",
        re.compile(r"(?:--update-snapshots|updateSnapshot|toMatchSnapshot\s*\(\s*\))"),
    ),
    (
        "WEAK_ASSERTION",
        re.compile(r"\.(?:toBeTruthy|toBeDefined|toBeAnything|not\.toThrow)\s*\("),
    ),
    ("ARBITRARY_SLEEP", re.compile(r"\bwaitForTimeout\s*\(")),
)
ASSERTION = re.compile(r"\bexpect\s*\(|\bassert(?:ion)?[.(]")


def audit(bundle: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    audited_paths: set[str] = set()
    for item in bundle.get("files", []):
        if not (item.get("is_test") or item.get("command_definition")):
            continue
        for field in ("path", "previous_path"):
            value = item.get(field)
            if isinstance(value, str):
                audited_paths.add(value)
        if item.get("is_test") and str(item.get("status", "")).startswith("D"):
            issues.append(
                {
                    "id": f"AUD-{len(issues) + 1:03d}",
                    "kind": "TEST_FILE_DELETED",
                    "path": str(item.get("path", "unknown-test-file")),
                    "evidence": "changed target deletes a test file",
                }
            )

    def header_path(line: str) -> str | None:
        value = line[4:].split("\t", 1)[0]
        if value == "/dev/null":
            return None
        return value[2:] if value.startswith(("a/", "b/")) else value

    current_file = ""
    old_file: str | None = None
    removed_assertions = 0
    for raw_line in str(bundle.get("patch", "")).splitlines():
        if raw_line.startswith("--- a/") or raw_line == "--- /dev/null":
            old_file = header_path(raw_line)
            current_file = old_file or ""
            continue
        if raw_line.startswith("+++ b/") or raw_line == "+++ /dev/null":
            current_file = header_path(raw_line) or old_file or ""
            continue
        if current_file not in audited_paths:
            continue
        if (
            raw_line.startswith("-")
            and not raw_line.startswith("---")
            and ASSERTION.search(raw_line[1:])
        ):
            removed_assertions += 1
        if not raw_line.startswith("+") or raw_line.startswith("+++"):
            continue
        code = raw_line[1:]
        if current_file.endswith("_harness.py") and "audit-fixture: allow" in code:
            continue
        for kind, pattern in ADDED_RULES:
            if pattern.search(code):
                issues.append(
                    {
                        "id": f"AUD-{len(issues) + 1:03d}",
                        "kind": kind,
                        "path": current_file,
                        "evidence": code.strip()[:240],
                    }
                )
    if removed_assertions:
        issues.append(
            {
                "id": f"AUD-{len(issues) + 1:03d}",
                "kind": "ASSERTION_REMOVED",
                "path": "multiple-or-current-test-files",
                "evidence": f"removed assertion-like lines: {removed_assertions}",
            }
        )
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("bundle")
    parsed = args.parse_args()
    try:
        bundle = json.loads(Path(parsed.bundle).read_text(encoding="utf-8"))
        result = audit(bundle)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
