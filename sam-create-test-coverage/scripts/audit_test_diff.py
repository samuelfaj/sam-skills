#!/usr/bin/env python3
"""Audit a test patch for focus, suppression, configuration, and assertion weakening."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
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
    ("WEAK_ASSERTION", re.compile(r"\.(?:toBeTruthy|toBeDefined|not\.toThrow)\s*\(")),
    ("ARBITRARY_SLEEP", re.compile(r"\b(?:sleep|waitForTimeout)\s*\(")),
    (
        "COVERAGE_BYPASS",
        re.compile(r"(?:istanbul ignore|c8 ignore|coverage: ignore|nocover)"),
    ),
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

    current = ""
    old_file: str | None = None
    removed = 0
    for line in str(bundle.get("patch", "")).splitlines():
        if line.startswith("--- a/") or line == "--- /dev/null":
            old_file = header_path(line)
            current = old_file or ""
            continue
        if line.startswith("+++ b/") or line == "+++ /dev/null":
            current = header_path(line) or old_file or ""
            continue
        if current not in audited_paths:
            continue
        if (
            line.startswith("-")
            and not line.startswith("---")
            and ASSERTION.search(line[1:])
        ):
            removed += 1
        if not line.startswith("+") or line.startswith("+++"):
            continue
        code = line[1:]
        if current.endswith("_harness.py") and "audit-fixture: allow" in code:
            continue
        for kind, pattern in RULES:
            if pattern.search(code):
                issues.append(
                    {
                        "id": f"AUD-{len(issues) + 1:03d}",
                        "kind": kind,
                        "path": current,
                        "evidence": code.strip()[:240],
                    }
                )
    if removed:
        issues.append(
            {
                "id": f"AUD-{len(issues) + 1:03d}",
                "kind": "ASSERTION_REMOVED",
                "path": "changed-test-files",
                "evidence": f"removed assertion-like lines: {removed}",
            }
        )
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle")
    args = parser.parse_args()
    try:
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        result = audit(bundle)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
