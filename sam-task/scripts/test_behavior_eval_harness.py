#!/usr/bin/env python3
"""Adversarial checks for the behavioral evaluation scorer."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_behavior_eval.py"
CATALOG = ROOT / "assets/behavior-eval-scenarios.json"
REVISION = "a" * 40
REPORT_HASH = "b" * 64


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def clean_run() -> dict[str, Any]:
    catalog = load_catalog()
    results = []
    for index, scenario in enumerate(catalog["scenarios"], start=1):
        results.append(
            {
                "scenario_id": scenario["id"],
                "terminal": scenario["expected_terminals"][0],
                "validator_receipt": "VALID",
                "report_sha256": REPORT_HASH,
                "acceptance_checks": [
                    {
                        "id": check["id"],
                        "passed": True,
                        "evidence": f"receipt for {check['id']}",
                    }
                    for check in scenario["acceptance_checks"]
                ],
                "human_corrections": index % 2,
                "iterations": 1,
                "wall_time_seconds": 10 + index,
                "input_tokens": None if index == 1 else 1000 + index,
                "output_tokens": None if index == 1 else 200 + index,
                "cost_usd": None,
            }
        )
    return {
        "schema_version": 1,
        "suite_id": catalog["suite_id"],
        "skill_revision": REVISION,
        "results": results,
    }


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run_validate(path: Path, *, complete: bool = True) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-B", str(VALIDATOR), str(path)]
    if complete:
        command.append("--require-complete-suite")
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def assert_valid(path: Path, snippet: str = '"false_completions": 0') -> None:
    result = run_validate(path)
    if result.returncode != 0 or "VALID" not in result.stdout:
        raise AssertionError(f"expected VALID:\n{result.stdout}{result.stderr}")
    if snippet not in result.stdout:
        raise AssertionError(f"missing metric {snippet!r}:\n{result.stdout}")


def assert_invalid(path: Path, snippet: str, *, complete: bool = True) -> None:
    result = run_validate(path, complete=complete)
    if result.returncode == 0:
        raise AssertionError(f"expected INVALID containing {snippet!r}")
    if snippet not in result.stdout:
        raise AssertionError(f"missing {snippet!r}:\n{result.stdout}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sam-behavior-eval-") as raw:
        root = Path(raw)

        good = root / "good.json"
        write(good, clean_run())
        assert_valid(good)

        false_complete = clean_run()
        false_complete["results"][1]["acceptance_checks"][0]["passed"] = False
        false_path = root / "false-complete.json"
        write(false_path, false_complete)
        assert_invalid(false_path, "false completion")

        wrong_terminal = clean_run()
        wrong_terminal["results"][0]["terminal"] = "BLOCKED"
        wrong_path = root / "wrong-terminal.json"
        write(wrong_path, wrong_terminal)
        assert_invalid(wrong_path, "is not accepted")

        missing = clean_run()
        missing["results"] = missing["results"][:-1]
        missing_path = root / "missing.json"
        write(missing_path, missing)
        assert_invalid(missing_path, "complete suite is missing scenarios")

        duplicate = clean_run()
        duplicate["results"].append(deepcopy(duplicate["results"][0]))
        duplicate_path = root / "duplicate.json"
        write(duplicate_path, duplicate)
        assert_invalid(duplicate_path, "duplicates scenario")

        weak_evidence = clean_run()
        weak_evidence["results"][0]["acceptance_checks"][0]["evidence"] = ""
        weak_path = root / "weak-evidence.json"
        write(weak_path, weak_evidence)
        assert_invalid(weak_path, "evidence is required")

        bad_metric = clean_run()
        bad_metric["results"][0]["wall_time_seconds"] = -1
        bad_metric_path = root / "bad-metric.json"
        write(bad_metric_path, bad_metric)
        assert_invalid(bad_metric_path, "wall_time_seconds must be a non-negative number")

        partial = clean_run()
        partial["results"] = partial["results"][:1]
        partial_path = root / "partial.json"
        write(partial_path, partial)
        result = run_validate(partial_path, complete=False)
        if result.returncode != 0 or '"scenarios_tested": 1' not in result.stdout:
            raise AssertionError(f"expected valid partial run:\n{result.stdout}")

        print("PASS: 8 behavioral-eval harness scenarios")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
