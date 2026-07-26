#!/usr/bin/env python3
"""Validate and score a recorded sam-skills behavioral evaluation run."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "assets/behavior-eval-scenarios.json"
SCENARIO_ID = re.compile(r"^B-\d{3}$")
REVISION = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(nonempty_string(item) for item in value)
    )


def number(value: Any, *, integer: bool = False, positive: bool = False) -> bool:
    if isinstance(value, bool):
        return False
    if integer:
        if not isinstance(value, int):
            return False
    elif not isinstance(value, (int, float)):
        return False
    return value > 0 if positive else value >= 0


def optional_number(value: Any) -> bool:
    return value is None or number(value)


def validate_catalog(catalog: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    if catalog.get("schema_version") != 1:
        errors.append("catalog.schema_version must be 1")
    if not nonempty_string(catalog.get("suite_id")):
        errors.append("catalog.suite_id is required")
    scenarios = catalog.get("scenarios")
    if not isinstance(scenarios, list) or not 6 <= len(scenarios) <= 10:
        errors.append("catalog.scenarios must contain 6 to 10 scenarios")
        return errors, {}

    by_id: dict[str, dict[str, Any]] = {}
    for index, scenario in enumerate(scenarios, start=1):
        prefix = f"catalog scenario {index}"
        if not isinstance(scenario, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scenario_id = scenario.get("id")
        if not SCENARIO_ID.fullmatch(str(scenario_id or "")):
            errors.append(f"{prefix} id must match B-###")
            continue
        if scenario_id in by_id:
            errors.append(f"{prefix} id must be unique")
            continue
        by_id[str(scenario_id)] = scenario
        for field in ("skill", "category", "prompt"):
            if not nonempty_string(scenario.get(field)):
                errors.append(f"{prefix} {field} is required")
        for field in ("expected_terminals", "completion_terminals"):
            if not string_list(scenario.get(field), nonempty=True):
                errors.append(f"{prefix} {field} requires at least one value")
        checks = scenario.get("acceptance_checks")
        if not isinstance(checks, list) or not checks:
            errors.append(f"{prefix} acceptance_checks requires entries")
            continue
        check_ids: set[str] = set()
        for check in checks:
            if not isinstance(check, dict):
                errors.append(f"{prefix} acceptance check must be an object")
                continue
            check_id = check.get("id")
            if not nonempty_string(check_id) or check_id in check_ids:
                errors.append(f"{prefix} acceptance check IDs must be unique strings")
            else:
                check_ids.add(str(check_id))
            if not nonempty_string(check.get("description")):
                errors.append(f"{prefix} acceptance check description is required")
    return errors, by_id


def validate_run(
    run: dict[str, Any],
    catalog: dict[str, Any],
    scenarios: dict[str, dict[str, Any]],
    *,
    require_complete_suite: bool,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if run.get("schema_version") != 1:
        errors.append("run.schema_version must be 1")
    if run.get("suite_id") != catalog.get("suite_id"):
        errors.append("run.suite_id must match the catalog")
    if not REVISION.fullmatch(str(run.get("skill_revision", ""))):
        errors.append("run.skill_revision must be a 40- or 64-character revision")

    results = run.get("results")
    if not isinstance(results, list) or not results:
        errors.append("run.results requires at least one scenario result")
        return errors, {}

    seen: set[str] = set()
    passes = 0
    false_completions = 0
    corrections: list[float] = []
    iterations: list[float] = []
    wall_times: list[float] = []
    input_tokens: list[float] = []
    output_tokens: list[float] = []
    costs: list[float] = []

    for index, result in enumerate(results, start=1):
        prefix = f"result {index}"
        if not isinstance(result, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scenario_id = result.get("scenario_id")
        if scenario_id not in scenarios:
            errors.append(f"{prefix} references unknown scenario {scenario_id!r}")
            continue
        if scenario_id in seen:
            errors.append(f"{prefix} duplicates scenario {scenario_id}")
            continue
        seen.add(str(scenario_id))
        scenario = scenarios[str(scenario_id)]

        terminal = result.get("terminal")
        if not nonempty_string(terminal):
            errors.append(f"{prefix} terminal is required")
            terminal = ""
        receipt = result.get("validator_receipt")
        validator_valid = nonempty_string(receipt) and str(receipt).startswith("VALID")
        if not validator_valid:
            errors.append(f"{prefix} validator_receipt must start with VALID")
        if not HEX64.fullmatch(str(result.get("report_sha256", ""))):
            errors.append(f"{prefix} report_sha256 must be 64 lowercase hex")

        expected_checks = {
            str(check["id"]) for check in scenario.get("acceptance_checks", [])
            if isinstance(check, dict) and nonempty_string(check.get("id"))
        }
        observed_checks = result.get("acceptance_checks")
        observed_ids: set[str] = set()
        all_checks_pass = True
        if not isinstance(observed_checks, list):
            errors.append(f"{prefix} acceptance_checks must be an array")
            observed_checks = []
            all_checks_pass = False
        for check_index, check in enumerate(observed_checks, start=1):
            check_prefix = f"{prefix} acceptance check {check_index}"
            if not isinstance(check, dict):
                errors.append(f"{check_prefix} must be an object")
                all_checks_pass = False
                continue
            check_id = check.get("id")
            if not nonempty_string(check_id) or check_id in observed_ids:
                errors.append(f"{check_prefix} id must be a unique string")
                all_checks_pass = False
            else:
                observed_ids.add(str(check_id))
            if not isinstance(check.get("passed"), bool):
                errors.append(f"{check_prefix} passed must be boolean")
                all_checks_pass = False
            elif check.get("passed") is not True:
                all_checks_pass = False
            if not nonempty_string(check.get("evidence")):
                errors.append(f"{check_prefix} evidence is required")
                all_checks_pass = False
        if observed_ids != expected_checks:
            errors.append(f"{prefix} acceptance check IDs must match the catalog exactly")
            all_checks_pass = False

        metric_fields = {
            "human_corrections": (True, False),
            "iterations": (True, True),
            "wall_time_seconds": (False, False),
        }
        for field, (integer, positive) in metric_fields.items():
            value = result.get(field)
            if not number(value, integer=integer, positive=positive):
                qualifier = "positive" if positive else "non-negative"
                errors.append(f"{prefix} {field} must be a {qualifier} number")
        for field in ("input_tokens", "output_tokens", "cost_usd"):
            if not optional_number(result.get(field)):
                errors.append(f"{prefix} {field} must be non-negative or null")

        accepted_terminal = terminal in scenario.get("expected_terminals", [])
        scenario_pass = accepted_terminal and validator_valid and all_checks_pass
        if not accepted_terminal:
            errors.append(
                f"{prefix} terminal {terminal!r} is not accepted for scenario {scenario_id}"
            )
        if scenario_pass:
            passes += 1
        if terminal in scenario.get("completion_terminals", []) and (
            not validator_valid or not all_checks_pass
        ):
            false_completions += 1
            errors.append(f"{prefix} is a false completion")

        if number(result.get("human_corrections"), integer=True):
            corrections.append(float(result["human_corrections"]))
        if number(result.get("iterations"), integer=True, positive=True):
            iterations.append(float(result["iterations"]))
        if number(result.get("wall_time_seconds")):
            wall_times.append(float(result["wall_time_seconds"]))
        for field, bucket in (
            ("input_tokens", input_tokens),
            ("output_tokens", output_tokens),
            ("cost_usd", costs),
        ):
            value = result.get(field)
            if value is not None and number(value):
                bucket.append(float(value))

    if require_complete_suite and seen != set(scenarios):
        missing = sorted(set(scenarios) - seen)
        errors.append(f"complete suite is missing scenarios: {', '.join(missing)}")

    def average(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 4) if values else None

    tested = len(seen)
    metrics = {
        "suite_id": catalog.get("suite_id"),
        "skill_revision": run.get("skill_revision"),
        "scenarios_cataloged": len(scenarios),
        "scenarios_tested": tested,
        "scenarios_passed": passes,
        "pass_rate": round(passes / tested, 4) if tested else 0,
        "false_completions": false_completions,
        "false_completion_rate": (
            round(false_completions / tested, 4) if tested else 0
        ),
        "average_human_corrections": average(corrections),
        "average_iterations": average(iterations),
        "average_wall_time_seconds": average(wall_times),
        "average_input_tokens": average(input_tokens),
        "average_output_tokens": average(output_tokens),
        "average_cost_usd": average(costs),
    }
    return errors, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Recorded behavior-eval run JSON")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Scenario catalog JSON",
    )
    parser.add_argument(
        "--require-complete-suite",
        action="store_true",
        help="Reject a run that omits a catalog scenario",
    )
    args = parser.parse_args()

    try:
        catalog = load_object(args.catalog, "catalog")
        run = load_object(args.run, "run")
    except ValueError as error:
        print(f"INVALID\n- {error}")
        return 2

    catalog_errors, scenarios = validate_catalog(catalog)
    if catalog_errors:
        print("INVALID")
        for error in catalog_errors:
            print(f"- {error}")
        return 1

    errors, metrics = validate_run(
        run,
        catalog,
        scenarios,
        require_complete_suite=args.require_complete_suite,
    )
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        print(json.dumps(metrics, sort_keys=True))
        return 1
    print("VALID")
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
