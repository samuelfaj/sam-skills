#!/usr/bin/env python3
"""Validate traceability, safety, proof, publication, and cleanup in an E2E report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Import the shared verifier without leaving bytecode in the skill package.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_receipts import verify_commands, verify_wiring  # noqa: E402

PREFIXES = {
    "criteria": "AC-",
    "risks": "R-",
    "scenarios": "S-",
    "tests": "T-",
    "commands": "CMD-",
    "artifacts": "ART-",
    "cleanup": "CL-",
}


def load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def validate(
    baseline: dict[str, Any], bundle: dict[str, Any], report: dict[str, Any]
) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(
        report.get("baseline_fingerprint") == baseline.get("fingerprint"),
        "baseline fingerprint mismatch",
    )
    require(
        report.get("bundle_fingerprint") == bundle.get("fingerprint"),
        "bundle fingerprint mismatch",
    )
    require(
        baseline.get("target", {}).get("base_sha")
        == bundle.get("target", {}).get("base_sha"),
        "baseline and final base SHA differ",
    )
    require(
        baseline.get("target", {}).get("head_sha")
        == bundle.get("target", {}).get("head_sha"),
        "baseline and final head SHA differ",
    )
    target = report.get("target", {})
    require(
        target.get("base_sha") == bundle.get("target", {}).get("base_sha"),
        "base SHA mismatch",
    )
    require(
        target.get("head_sha") == bundle.get("target", {}).get("head_sha"),
        "head SHA mismatch",
    )
    intent = report.get("intent", {})
    require(bool(intent.get("summary")), "intent.summary is required")
    require(
        isinstance(intent.get("invariants"), list), "intent.invariants must be a list"
    )
    require(isinstance(intent.get("no_go"), list), "intent.no_go must be a list")

    ledgers: dict[str, dict[str, dict[str, Any]]] = {}
    all_ids: set[str] = set()
    for name, prefix in PREFIXES.items():
        values = report.get(name)
        require(
            isinstance(values, list) and bool(values),
            f"{name} must be a non-empty list",
        )
        mapped: dict[str, dict[str, Any]] = {}
        if isinstance(values, list):
            for item in values:
                if not isinstance(item, dict):
                    errors.append(f"{name} entries must be objects")
                    continue
                item_id = item.get("id")
                if not isinstance(item_id, str) or not re.fullmatch(
                    rf"{re.escape(prefix)}\d{{3,}}", item_id
                ):
                    errors.append(f"invalid {name} id: {item_id}")
                    continue
                if item_id in all_ids:
                    errors.append(f"duplicate id: {item_id}")
                all_ids.add(item_id)
                mapped[item_id] = item
        ledgers[name] = mapped

    def refs(items: Any, ledger: str, owner: str, required: bool = True) -> list[str]:
        if not isinstance(items, list) or (required and not items):
            errors.append(f"{owner} must reference {ledger}")
            return []
        result: list[str] = []
        for item in items:
            if not isinstance(item, str):
                errors.append(f"{owner} {ledger} references must be strings")
                continue
            result.append(item)
        for item in result:
            if item not in ledgers.get(ledger, {}):
                errors.append(f"{owner} references unknown {ledger} id: {item}")
        return result

    def reciprocal(owner: str, targets: list[str], ledger: str, backref: str) -> None:
        for target_id in targets:
            target = ledgers.get(ledger, {}).get(target_id)
            backlinks = target.get(backref) if target is not None else None
            if target is not None and (
                not isinstance(backlinks, list) or owner not in backlinks
            ):
                errors.append(
                    f"{owner} -> {target_id} missing reciprocal {backref} link"
                )

    for criterion_id, criterion in ledgers.get("criteria", {}).items():
        require(
            isinstance(criterion.get("text"), str)
            and bool(criterion.get("text", "").strip()),
            f"{criterion_id} missing text",
        )

    for risk_id, risk in ledgers.get("risks", {}).items():
        refs(risk.get("criterion_ids"), "criteria", risk_id)
        require(
            risk.get("level") in {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
            f"{risk_id} has invalid level",
        )
        require(
            any(
                isinstance(risk.get(field), str) and bool(risk.get(field, "").strip())
                for field in ("evidence", "description")
            ),
            f"{risk_id} missing evidence or description",
        )
    for scenario_id, scenario in ledgers.get("scenarios", {}).items():
        refs(scenario.get("criterion_ids"), "criteria", scenario_id)
        refs(scenario.get("risk_ids"), "risks", scenario_id)
        status = scenario.get("status")
        require(
            status in {"AUTOMATED", "MANUAL_PROOF", "REDUNDANT", "NOT_COVERED"},
            f"{scenario_id} invalid status",
        )
        test_ids = refs(
            scenario.get("test_ids", []),
            "tests",
            scenario_id,
            required=status == "AUTOMATED",
        )
        artifact_ids = refs(
            scenario.get("artifact_ids", []),
            "artifacts",
            scenario_id,
            required=False,
        )
        reciprocal(scenario_id, test_ids, "tests", "scenario_ids")
        reciprocal(scenario_id, artifact_ids, "artifacts", "scenario_ids")
        if status == "AUTOMATED":
            require(bool(test_ids), f"{scenario_id} automated without tests")
        if status in {"REDUNDANT", "NOT_COVERED", "MANUAL_PROOF"}:
            require(
                bool(scenario.get("reason") or scenario.get("evidence")),
                f"{scenario_id} requires rationale",
            )
    not_proven = False
    for test_id, test in ledgers.get("tests", {}).items():
        scenario_ids = refs(test.get("scenario_ids"), "scenarios", test_id)
        command_ids = refs(test.get("command_ids"), "commands", test_id)
        reciprocal(test_id, scenario_ids, "scenarios", "test_ids")
        reciprocal(test_id, command_ids, "commands", "test_ids")
        require(bool(command_ids), f"{test_id} has no validation command")
        require(
            bool(test.get("path")) and bool(test.get("name")),
            f"{test_id} missing path or name",
        )
        proof = test.get("regression_proof", {})
        status = proof.get("status")
        require(
            status in {"RED_GREEN", "MUTATION", "CONTRACT", "NOT_PROVEN"},
            f"{test_id} invalid regression proof",
        )
        require(
            bool(proof.get("evidence")), f"{test_id} regression proof needs evidence"
        )
        not_proven = not_proven or status == "NOT_PROVEN"
    target_failure = False
    for command_id, command in ledgers.get("commands", {}).items():
        test_ids = refs(command.get("test_ids"), "tests", command_id)
        reciprocal(command_id, test_ids, "tests", "command_ids")
        status = command.get("status")
        classification = command.get("classification")
        require(status in {"PASS", "FAIL", "NOT_RUN"}, f"{command_id} invalid status")
        require(
            classification in {"TARGET", "BASELINE", "ENVIRONMENT", "EXTERNAL"},
            f"{command_id} invalid classification",
        )
        require(
            bool(command.get("command")) and bool(command.get("evidence")),
            f"{command_id} missing command or evidence",
        )
        target_failure = target_failure or (
            classification == "TARGET" and status != "PASS"
        )
    uploaded = False
    for artifact_id, artifact in ledgers.get("artifacts", {}).items():
        scenario_ids = refs(artifact.get("scenario_ids"), "scenarios", artifact_id)
        reciprocal(artifact_id, scenario_ids, "scenarios", "artifact_ids")
        status = artifact.get("status")
        require(
            status in {"LOCAL", "UPLOADED", "NOT_CREATED"},
            f"{artifact_id} invalid status",
        )
        require(
            artifact.get("safety_review") is True, f"{artifact_id} lacks safety review"
        )
        if status == "UPLOADED":
            uploaded = True
            require(
                bool(artifact.get("receipt"))
                and artifact.get("readback_verified") is True,
                f"{artifact_id} lacks verified receipt",
            )
    cleanup_blocked = False
    for cleanup_id, cleanup in ledgers.get("cleanup", {}).items():
        status = cleanup.get("status")
        require(
            status in {"CLEANED", "RETAINED", "BLOCKED"}, f"{cleanup_id} invalid status"
        )
        require(bool(cleanup.get("resource")), f"{cleanup_id} missing resource")
        if status != "CLEANED":
            require(bool(cleanup.get("reason")), f"{cleanup_id} requires reason")
        cleanup_blocked = cleanup_blocked or status == "BLOCKED"

    environment = report.get("environment", {})
    require(
        environment.get("kind")
        in {"unknown", "local", "test", "dev", "staging", "production"},
        "invalid environment kind",
    )
    require(
        bool(environment.get("identity")) and bool(environment.get("evidence")),
        "environment identity and evidence required",
    )
    unsafe_real_data = environment.get("real_data") is True and environment.get(
        "kind"
    ) not in {"local", "test", "dev"}
    require(
        not unsafe_real_data,
        "real data requires verified local, test, or dev environment",
    )
    command_defs = report.get("command_definitions", {})
    changed_defs = bool(bundle.get("command_definitions"))
    require(
        command_defs.get("changed") is changed_defs,
        "command definition changed flag mismatch",
    )
    if changed_defs:
        require(
            command_defs.get("inspected") is True
            and bool(command_defs.get("evidence")),
            "changed command definitions were not inspected",
        )
    audit = report.get("test_diff_audit", {})
    require(
        audit.get("status") in {"PASS", "FAIL"} and bool(audit.get("evidence")),
        "test diff audit result required",
    )
    authorization = report.get("authorization", {})
    require(
        isinstance(authorization.get("publish_requested"), bool),
        "publish_requested must be boolean",
    )
    require(
        not uploaded or authorization.get("publish_requested") is True,
        "artifact uploaded without authorization",
    )
    behavior = report.get("behavior_proof", {})
    require(
        behavior.get("status") in {"PROVEN", "NOT_PROVEN", "FALLBACK"}
        and bool(behavior.get("evidence")),
        "behavior proof required",
    )
    # Execution receipts: re-verify every reported command against run_checked.py
    # output so a typed "PASS" cannot close a gate.
    receipts = verify_commands(ledgers.get("commands", {}), errors)
    wiring_status = verify_wiring(report.get("test_wiring"), errors)

    decision = report.get("decision")
    require(decision in {"COMPLETE", "PARTIAL", "BLOCKED"}, "invalid decision")
    if decision == "COMPLETE":
        require(
            not any(
                item.get("status") == "NOT_COVERED"
                for item in ledgers.get("scenarios", {}).values()
            ),
            "COMPLETE with uncovered scenario",
        )
        require(not not_proven, "COMPLETE with unproven regression test")
        require(not target_failure, "COMPLETE with target validation failure")
        require(not cleanup_blocked, "COMPLETE with blocked cleanup")
        require(audit.get("status") == "PASS", "COMPLETE with failed test diff audit")
        require(behavior.get("status") == "PROVEN", "COMPLETE without proven behavior")
        require(not unsafe_real_data, "COMPLETE with unsafe real-data environment")
        require(
            not receipts["flaky"],
            "COMPLETE with flaky command(s): " + ", ".join(receipts["flaky"]),
        )
        require(
            not receipts["unstable_target"],
            "COMPLETE requires repeated stable TARGET proof; unstable: "
            + ", ".join(receipts["unstable_target"]),
        )
        require(
            wiring_status in {"PROVEN", "NOT_APPLICABLE"},
            "COMPLETE requires proven test wiring (runner must discover each new test)",
        )
    return errors


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--baseline", required=True)
    args.add_argument("--bundle", required=True)
    args.add_argument("report")
    parsed = args.parse_args()
    try:
        errors = validate(
            load(parsed.baseline), load(parsed.bundle), load(parsed.report)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: E2E report is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
