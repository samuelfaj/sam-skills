#!/usr/bin/env python3
"""Audit a test patch for focus, suppression, weakening, and coverage bypass.

Canonical shared implementation. Every skill that ships this file must ship a
byte-identical copy; the repository suite validator enforces that.

Silence is never success: a changed test file in a language with no rule pack
raises AUDIT_LANGUAGE_UNSUPPORTED instead of passing quietly.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2

LANGUAGE_BY_SUFFIX: dict[str, str] = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".mts": "javascript",
    ".cts": "javascript",
    ".vue": "javascript",
    ".svelte": "javascript",
    ".py": "python",
    ".go": "go",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "java",
    ".kts": "java",
    ".groovy": "java",
    ".scala": "java",
    ".php": "php",
    ".cs": "csharp",
    ".fs": "csharp",
    ".rs": "rust",
    ".swift": "swift",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
}

RULE_PACKS: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "javascript": (
        ("FOCUSED_TEST", re.compile(r"\b(?:test|it|describe|context|suite)\.only\s*\(")),
        ("FOCUSED_TEST", re.compile(r"\b(?:fdescribe|fit)\s*\(")),
        (
            "SKIPPED_TEST",
            re.compile(r"\b(?:test|it|describe|context)\.(?:skip|fixme|todo)\s*\("),
        ),
        ("SKIPPED_TEST", re.compile(r"\b(?:xdescribe|xit)\s*\(")),
        ("RETRY_INCREASE", re.compile(r"\b(?:retries|retry)\s*[:=(]\s*[1-9]")),
        (
            "TIMEOUT_INCREASE",
            re.compile(r"\b(?:setDefaultTimeout|setTimeout|timeout)\s*\(?\s*[1-9][0-9]{3,}"),
        ),
        (
            "SNAPSHOT_REFRESH",
            re.compile(r"(?:--update-snapshots|updateSnapshot|toMatchSnapshot\s*\(\s*\))"),
        ),
        (
            "WEAK_ASSERTION",
            re.compile(r"\.(?:toBeTruthy|toBeDefined|toBeAnything|not\.toThrow)\s*\("),
        ),
        ("WEAK_ASSERTION", re.compile(r"expect\s*\(\s*true\s*\)\s*\.\s*toBe\s*\(\s*true")),
        ("ARBITRARY_SLEEP", re.compile(r"\b(?:sleep|waitForTimeout)\s*\(")),
        ("COVERAGE_BYPASS", re.compile(r"(?:istanbul ignore|c8 ignore|v8 ignore)")),
    ),
    "python": (
        ("SKIPPED_TEST", re.compile(r"@(?:pytest\.mark\.)?skip(?:if)?\b")),
        ("SKIPPED_TEST", re.compile(r"@unittest\.skip(?:If|Unless)?\b")),
        ("SKIPPED_TEST", re.compile(r"\b(?:pytest\.skip|self\.skipTest)\s*\(")),
        ("EXPECTED_FAILURE", re.compile(r"@pytest\.mark\.xfail\b")),
        ("EXPECTED_FAILURE", re.compile(r"@unittest\.expectedFailure\b")),
        ("FOCUSED_TEST", re.compile(r"@pytest\.mark\.(?:only|focus)\b")),
        ("RETRY_INCREASE", re.compile(r"@(?:pytest\.mark\.)?flaky\b")),
        ("RETRY_INCREASE", re.compile(r"\breruns\s*=\s*[1-9]")),
        ("TIMEOUT_INCREASE", re.compile(r"\btimeout\s*=\s*[1-9][0-9]{3,}")),
        ("WEAK_ASSERTION", re.compile(r"^\s*assert\s+True\s*(?:#.*)?$")),
        ("WEAK_ASSERTION", re.compile(r"\bassertTrue\s*\(\s*True\s*\)")),
        ("WEAK_ASSERTION", re.compile(r"^\s*assert\s+(\S+)\s*==\s*\1\s*$")),
        ("ARBITRARY_SLEEP", re.compile(r"\b(?:time|asyncio)\.sleep\s*\(")),
        (
            "COVERAGE_BYPASS",
            re.compile(r"#\s*(?:pragma:\s*no cover|nocover|coverage:\s*ignore)"),
        ),
    ),
    "go": (
        ("SKIPPED_TEST", re.compile(r"\bt\.Skip(?:Now|f)?\s*\(")),
        ("SKIPPED_TEST", re.compile(r"\btesting\.Short\s*\(\s*\)")),
        ("WEAK_ASSERTION", re.compile(r"\b(?:assert|require)\.True\s*\([^,]+,\s*true\s*\)")),
        ("ARBITRARY_SLEEP", re.compile(r"\btime\.Sleep\s*\(")),
        ("COVERAGE_BYPASS", re.compile(r"//\s*coverage:\s*ignore")),
    ),
    "ruby": (
        ("FOCUSED_TEST", re.compile(r"\b(?:fit|fdescribe|fcontext)\s")),
        ("FOCUSED_TEST", re.compile(r"focus:\s*true|:focus\s*=>\s*true")),
        ("SKIPPED_TEST", re.compile(r"^\s*(?:skip|pending)\b")),
        ("SKIPPED_TEST", re.compile(r"\b(?:xit|xdescribe|xcontext)\s")),
        ("WEAK_ASSERTION", re.compile(r"\.to\s+be_truthy\b")),
        ("WEAK_ASSERTION", re.compile(r"\bassert\s+true\b")),
        ("ARBITRARY_SLEEP", re.compile(r"^\s*sleep[\s(]")),
        ("COVERAGE_BYPASS", re.compile(r"#\s*:nocov:")),
    ),
    "java": (
        ("SKIPPED_TEST", re.compile(r"@(?:Disabled|Ignore)\b")),
        ("SKIPPED_TEST", re.compile(r"\bassumeTrue\s*\(\s*false\s*\)")),
        ("WEAK_ASSERTION", re.compile(r"\bassertTrue\s*\(\s*true\s*\)")),
        ("WEAK_ASSERTION", re.compile(r"\bassertDoesNotThrow\s*\(")),
        ("TIMEOUT_INCREASE", re.compile(r"\btimeout\s*=\s*[1-9][0-9]{3,}")),
        ("ARBITRARY_SLEEP", re.compile(r"\bThread\.sleep\s*\(")),
    ),
    "php": (
        ("SKIPPED_TEST", re.compile(r"\bmarkTest(?:Skipped|Incomplete)\s*\(")),
        ("SKIPPED_TEST", re.compile(r"@group\s+skip\b")),
        ("WEAK_ASSERTION", re.compile(r"\bassertTrue\s*\(\s*true\s*\)")),
        ("WEAK_ASSERTION", re.compile(r"\bexpectNotToPerformAssertions\s*\(")),
        ("ARBITRARY_SLEEP", re.compile(r"\bu?sleep\s*\(")),
        ("COVERAGE_BYPASS", re.compile(r"@codeCoverageIgnore")),
    ),
    "csharp": (
        ("SKIPPED_TEST", re.compile(r"\[(?:Ignore|Explicit)\b")),
        ("SKIPPED_TEST", re.compile(r"\bSkip\s*=\s*\"")),
        ("WEAK_ASSERTION", re.compile(r"\bAssert\.(?:True|IsTrue)\s*\(\s*true\s*\)")),
        ("WEAK_ASSERTION", re.compile(r"\bAssert\.Pass\s*\(")),
        ("ARBITRARY_SLEEP", re.compile(r"\b(?:Thread\.Sleep|Task\.Delay)\s*\(")),
        ("COVERAGE_BYPASS", re.compile(r"\[ExcludeFromCodeCoverage\b")),
    ),
    "rust": (
        ("SKIPPED_TEST", re.compile(r"#\[ignore\b")),
        ("WEAK_ASSERTION", re.compile(r"\bassert!\s*\(\s*true\s*\)")),
        ("ARBITRARY_SLEEP", re.compile(r"\b(?:thread::)?sleep\s*\(")),
    ),
    "swift": (
        ("SKIPPED_TEST", re.compile(r"\bXCTSkip(?:If|Unless)?\b")),
        ("WEAK_ASSERTION", re.compile(r"\bXCTAssertTrue\s*\(\s*true\s*\)")),
        ("ARBITRARY_SLEEP", re.compile(r"\b(?:Thread\.sleep|usleep)\s*\(")),
    ),
    "dart": (
        ("SKIPPED_TEST", re.compile(r"\bskip:\s*(?:true|['\"])")),
        ("WEAK_ASSERTION", re.compile(r"\bexpect\s*\(\s*true\s*,\s*isTrue\s*\)")),
        ("ARBITRARY_SLEEP", re.compile(r"\bsleep\s*\(")),
    ),
    "elixir": (
        ("SKIPPED_TEST", re.compile(r"@tag\s+:skip\b")),
        ("SKIPPED_TEST", re.compile(r"@moduletag\s+:skip\b")),
        ("ARBITRARY_SLEEP", re.compile(r"\b:timer\.sleep\s*\(")),
    ),
}

# Applied to every audited path regardless of language: a green suite produced by
# suppressing the runner's exit code is not proof.
NEUTRALIZATION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CI_FAILURE_SUPPRESSED", re.compile(r"\|\|\s*(?:true\b|:\s*$)")),
    ("CI_FAILURE_SUPPRESSED", re.compile(r"continue-on-error:\s*true")),
    ("CI_FAILURE_SUPPRESSED", re.compile(r"\bset\s+\+e\b")),
    ("CI_FAILURE_SUPPRESSED", re.compile(r"--exit-zero\b")),
    ("CI_FAILURE_SUPPRESSED", re.compile(r"\bignore-errors\b")),
    ("EMPTY_SUITE_TOLERATED", re.compile(r"--passWithNoTests\b")),
    ("EMPTY_SUITE_TOLERATED", re.compile(r"--allow-empty(?:-suite)?\b")),
    (
        "COVERAGE_THRESHOLD_DISABLED",
        re.compile(r"--(?:cov-)?fail-under[= ]\s*0\b"),
    ),
    ("COVERAGE_THRESHOLD_DISABLED", re.compile(r"minimum_coverage:\s*0\b")),
    ("TEST_FILTER_NARROWED", re.compile(r"--(?:testNamePattern|grep)[= ]")),
)

ASSERTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "javascript": re.compile(r"\bexpect\s*\(|\bassert(?:ion)?[.(]|\.should\b"),
    "python": re.compile(r"^\s*assert\s|\bself\.assert\w+\s*\(|\bpytest\.raises\b"),
    "go": re.compile(r"\b(?:assert|require)\.\w+\s*\(|\bt\.(?:Error|Fatal)\w*\s*\("),
    "ruby": re.compile(r"\bexpect\s*\(|\bassert\w*[\s(]|\.should\b"),
    "java": re.compile(r"\bassert\w*\s*\(|\bassertThat\s*\("),
    "php": re.compile(r"\$this->assert\w+\s*\(|\bassert\w+\s*\("),
    "csharp": re.compile(r"\bAssert\.\w+\s*\("),
    "rust": re.compile(r"\bassert(?:_eq|_ne)?!\s*\("),
    "swift": re.compile(r"\bXCTAssert\w*\s*\("),
    "dart": re.compile(r"\bexpect\s*\("),
    "elixir": re.compile(r"\bassert\w*\s|\brefute\w*\s"),
}
GENERIC_ASSERTION = re.compile(r"\bexpect\s*\(|\bassert\w*[\s.(]")


def language_of(path: str) -> str | None:
    return LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower())


def header_path(line: str) -> str | None:
    value = line[4:].split("\t", 1)[0]
    if value == "/dev/null":
        return None
    return value[2:] if value.startswith(("a/", "b/")) else value


def audit(bundle: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    audited_paths: set[str] = set()
    test_paths: set[str] = set()

    def add(kind: str, path: str, evidence: str) -> None:
        issues.append(
            {
                "id": f"AUD-{len(issues) + 1:03d}",
                "kind": kind,
                "path": path,
                "evidence": evidence[:240],
            }
        )

    for item in bundle.get("files", []):
        if not (item.get("is_test") or item.get("command_definition")):
            continue
        for field in ("path", "previous_path"):
            value = item.get(field)
            if isinstance(value, str):
                audited_paths.add(value)
                if item.get("is_test"):
                    test_paths.add(value)
        if item.get("is_test") and str(item.get("status", "")).startswith("D"):
            add(
                "TEST_FILE_DELETED",
                str(item.get("path", "unknown-test-file")),
                "changed target deletes a test file",
            )

    # A test file this auditor cannot analyze must be reported, never assumed clean.
    unsupported = sorted(
        {path for path in test_paths if language_of(path) not in RULE_PACKS}
    )
    for path in unsupported:
        add(
            "AUDIT_LANGUAGE_UNSUPPORTED",
            path,
            "no language rule pack covers this changed test file; audit cannot "
            "prove the suite was not weakened",
        )

    languages_seen: set[str] = set()
    removed_assertions = 0
    current = ""
    old_file: str | None = None
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
        language = language_of(current)
        if language is not None:
            languages_seen.add(language)
        if (
            line.startswith("-")
            and not line.startswith("---")
            and (ASSERTION_PATTERNS.get(language or "", GENERIC_ASSERTION)).search(
                line[1:]
            )
        ):
            removed_assertions += 1
        if not line.startswith("+") or line.startswith("+++"):
            continue
        code = line[1:]
        if (
            current.endswith("_harness.py") or Path(current).name.startswith("test_")
        ) and "audit-fixture: allow" in code:
            continue
        rules = RULE_PACKS.get(language or "", ())
        for kind, pattern in (*rules, *NEUTRALIZATION_RULES):
            if pattern.search(code):
                add(kind, current, code.strip())

    if removed_assertions:
        add(
            "ASSERTION_REMOVED",
            "changed-test-files",
            f"removed assertion-like lines: {removed_assertions}",
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "languages_audited": sorted(languages_seen),
        "unsupported_test_files": unsupported,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle")
    args = parser.parse_args()
    try:
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"audit_test_diff: cannot read bundle: {error}", file=sys.stderr)
        return 2
    if not isinstance(bundle, dict):
        print("audit_test_diff: bundle root must be an object", file=sys.stderr)
        return 2
    result = audit(bundle)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
