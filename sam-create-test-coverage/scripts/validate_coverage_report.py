#!/usr/bin/env python3
"""Validate a multi-layer coverage report and its evidence graph."""

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
    "behaviors": "B-",
    "risks": "R-",
    "scenarios": "S-",
    "tests": "T-",
    "commands": "CMD-",
    "artifacts": "ART-",
    "cleanup": "CL-",
}


def read_object(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(
    baseline: dict[str, Any], bundle: dict[str, Any], report: dict[str, Any]
) -> list[str]:
    errors: list[str] = []

    def need(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    need(
        report.get("baseline_fingerprint") == baseline.get("fingerprint"),
        "baseline fingerprint mismatch",
    )
    need(
        report.get("bundle_fingerprint") == bundle.get("fingerprint"),
        "bundle fingerprint mismatch",
    )
    need(
        baseline.get("target", {}).get("base_sha")
        == bundle.get("target", {}).get("base_sha"),
        "baseline and final base SHA differ",
    )
    need(
        baseline.get("target", {}).get("head_sha")
        == bundle.get("target", {}).get("head_sha"),
        "baseline and final head SHA differ",
    )
    target = report.get("target", {})
    need(
        target.get("base_sha") == bundle.get("target", {}).get("base_sha"),
        "base SHA mismatch",
    )
    need(
        target.get("head_sha") == bundle.get("target", {}).get("head_sha"),
        "head SHA mismatch",
    )
    intent = report.get("intent", {})
    need(bool(intent.get("summary")), "intent.summary is required")
    need(isinstance(intent.get("invariants"), list), "intent.invariants must be a list")
    need(isinstance(intent.get("no_go"), list), "intent.no_go must be a list")

    tables: dict[str, dict[str, dict[str, Any]]] = {}
    seen: set[str] = set()
    for name, prefix in PREFIXES.items():
        values = report.get(name)
        need(
            isinstance(values, list) and bool(values),
            f"{name} must be a non-empty list",
        )
        table: dict[str, dict[str, Any]] = {}
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
                if item_id in seen:
                    errors.append(f"duplicate id: {item_id}")
                seen.add(item_id)
                table[item_id] = item
        tables[name] = table

    def references(
        value: Any, table: str, owner: str, required: bool = True
    ) -> list[str]:
        if not isinstance(value, list) or (required and not value):
            errors.append(f"{owner} must reference {table}")
            return []
        result: list[str] = []
        for item in value:
            if not isinstance(item, str):
                errors.append(f"{owner} {table} references must be strings")
                continue
            result.append(item)
        for item in result:
            if item not in tables.get(table, {}):
                errors.append(f"{owner} references unknown {table} id: {item}")
        return result

    def reciprocal(owner: str, targets: list[str], table: str, backref: str) -> None:
        for target_id in targets:
            target = tables.get(table, {}).get(target_id)
            backlinks = target.get(backref) if target is not None else None
            if target is not None and (
                not isinstance(backlinks, list) or owner not in backlinks
            ):
                errors.append(
                    f"{owner} -> {target_id} missing reciprocal {backref} link"
                )

    for criterion_id, criterion in tables.get("criteria", {}).items():
        need(
            isinstance(criterion.get("text"), str)
            and bool(criterion.get("text", "").strip()),
            f"{criterion_id} missing text",
        )

    for behavior_id, behavior in tables.get("behaviors", {}).items():
        references(behavior.get("criterion_ids"), "criteria", behavior_id)
        need(bool(behavior.get("description")), f"{behavior_id} missing description")
        need(
            isinstance(behavior.get("paths"), list) and bool(behavior.get("paths")),
            f"{behavior_id} missing paths",
        )
    for risk_id, risk in tables.get("risks", {}).items():
        references(risk.get("criterion_ids"), "criteria", risk_id)
        references(risk.get("behavior_ids"), "behaviors", risk_id)
        need(
            risk.get("level") in {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
            f"{risk_id} invalid level",
        )
        need(
            any(
                isinstance(risk.get(field), str) and bool(risk.get(field, "").strip())
                for field in ("evidence", "description")
            ),
            f"{risk_id} missing evidence or description",
        )

    required_gap = False
    e2e_required = False
    for scenario_id, scenario in tables.get("scenarios", {}).items():
        references(scenario.get("criterion_ids"), "criteria", scenario_id)
        references(scenario.get("behavior_ids"), "behaviors", scenario_id)
        references(scenario.get("risk_ids"), "risks", scenario_id)
        status = scenario.get("status")
        layer = scenario.get("layer")
        need(
            status
            in {"PLANNED", "AUTOMATED", "MANUAL_PROOF", "REDUNDANT", "NOT_COVERED"},
            f"{scenario_id} invalid status",
        )
        need(
            layer
            in {"UNIT", "COMPONENT", "INTEGRATION", "API_CONTRACT", "E2E", "MANUAL"},
            f"{scenario_id} invalid layer",
        )
        test_ids = references(
            scenario.get("test_ids", []), "tests", scenario_id, status == "AUTOMATED"
        )
        artifact_ids = references(
            scenario.get("artifact_ids", []), "artifacts", scenario_id, False
        )
        reciprocal(scenario_id, test_ids, "tests", "scenario_ids")
        reciprocal(scenario_id, artifact_ids, "artifacts", "scenario_ids")
        if status == "AUTOMATED":
            need(bool(test_ids), f"{scenario_id} automated without tests")
        if status in {"MANUAL_PROOF", "REDUNDANT", "NOT_COVERED"}:
            need(
                bool(scenario.get("reason") or scenario.get("evidence")),
                f"{scenario_id} requires rationale",
            )
        need(
            bool(scenario.get("sufficiency")),
            f"{scenario_id} missing layer sufficiency",
        )
        required_gap = required_gap or status in {"PLANNED", "NOT_COVERED"}
        e2e_required = e2e_required or (
            layer == "E2E" and status in {"AUTOMATED", "PLANNED"}
        )

    proof_gap = False
    for test_id, test in tables.get("tests", {}).items():
        scenario_ids = references(test.get("scenario_ids"), "scenarios", test_id)
        command_ids = references(test.get("command_ids"), "commands", test_id)
        reciprocal(test_id, scenario_ids, "scenarios", "test_ids")
        reciprocal(test_id, command_ids, "commands", "test_ids")
        need(bool(command_ids), f"{test_id} missing commands")
        need(
            bool(test.get("path")) and bool(test.get("name")),
            f"{test_id} missing path or name",
        )
        proof = test.get("regression_proof", {})
        status = proof.get("status")
        need(
            status in {"RED_GREEN", "MUTATION", "CONTRACT", "NOT_PROVEN"},
            f"{test_id} invalid regression proof",
        )
        need(
            bool(proof.get("evidence")), f"{test_id} regression proof missing evidence"
        )
        # Any unproven test blocks FULL. "required" is self-assigned, so it cannot
        # be the thing that decides whether missing proof matters.
        proof_gap = proof_gap or status == "NOT_PROVEN"

    target_failure = False
    for command_id, command in tables.get("commands", {}).items():
        test_ids = references(command.get("test_ids"), "tests", command_id)
        reciprocal(command_id, test_ids, "tests", "command_ids")
        status = command.get("status")
        classification = command.get("classification")
        need(status in {"PASS", "FAIL", "NOT_RUN"}, f"{command_id} invalid status")
        need(
            classification in {"TARGET", "BASELINE", "ENVIRONMENT", "EXTERNAL"},
            f"{command_id} invalid classification",
        )
        need(
            bool(command.get("command")) and bool(command.get("evidence")),
            f"{command_id} missing command or evidence",
        )
        target_failure = target_failure or (
            classification == "TARGET" and status != "PASS"
        )

    uploaded = False
    for artifact_id, artifact in tables.get("artifacts", {}).items():
        scenario_ids = references(
            artifact.get("scenario_ids"), "scenarios", artifact_id
        )
        reciprocal(artifact_id, scenario_ids, "scenarios", "artifact_ids")
        status = artifact.get("status")
        need(
            status in {"LOCAL", "UPLOADED", "NOT_CREATED"},
            f"{artifact_id} invalid status",
        )
        need(
            artifact.get("safety_review") is True, f"{artifact_id} lacks safety review"
        )
        if status == "UPLOADED":
            uploaded = True
            need(
                bool(artifact.get("receipt"))
                and artifact.get("readback_verified") is True,
                f"{artifact_id} lacks verified receipt",
            )

    cleanup_blocked = False
    for cleanup_id, cleanup in tables.get("cleanup", {}).items():
        status = cleanup.get("status")
        need(
            status in {"CLEANED", "RETAINED", "BLOCKED"}, f"{cleanup_id} invalid status"
        )
        need(bool(cleanup.get("resource")), f"{cleanup_id} missing resource")
        if status != "CLEANED":
            need(bool(cleanup.get("reason")), f"{cleanup_id} requires reason")
        cleanup_blocked = cleanup_blocked or status == "BLOCKED"

    environment = report.get("environment", {})
    need(
        environment.get("kind")
        in {"unknown", "local", "test", "dev", "staging", "production"},
        "invalid environment kind",
    )
    need(
        bool(environment.get("identity")) and bool(environment.get("evidence")),
        "environment identity and evidence required",
    )
    unsafe_real_data = environment.get("real_data") is True and environment.get(
        "kind"
    ) not in {"local", "test", "dev"}
    need(
        not unsafe_real_data,
        "real-data E2E requires verified local, test, or dev environment",
    )

    command_defs = report.get("command_definitions", {})
    changed = bool(bundle.get("command_definitions"))
    need(
        command_defs.get("changed") is changed,
        "command definition changed flag mismatch",
    )
    if changed:
        need(
            command_defs.get("inspected") is True
            and bool(command_defs.get("evidence")),
            "changed command definitions not inspected",
        )
    audit = report.get("test_diff_audit", {})
    need(
        audit.get("status") in {"PASS", "FAIL"} and bool(audit.get("evidence")),
        "test diff audit required",
    )
    authorization = report.get("authorization", {})
    need(
        isinstance(authorization.get("publish_requested"), bool),
        "publish_requested must be boolean",
    )
    need(
        not uploaded or authorization.get("publish_requested") is True,
        "artifact uploaded without authorization",
    )
    real_system = report.get("real_system_proof", {})
    need(
        real_system.get("status")
        in {"PROVEN", "FALLBACK", "NOT_PROVEN", "NOT_APPLICABLE"},
        "invalid real-system proof",
    )
    need(bool(real_system.get("evidence")), "real-system proof needs evidence")
    # Execution receipts: re-verify every reported command against run_checked.py
    # output so a typed "PASS" cannot close a gate.
    receipts = verify_commands(tables.get("commands", {}), errors)
    wiring_status = verify_wiring(report.get("test_wiring"), errors)

    # Machine-derived risk floor: the builder tags the diff, so the report cannot
    # silently call a security/data/contract change low risk to dodge hard proof.
    elevated_tags = {"security", "data", "contract", "concurrency"} & set(
        bundle.get("risk_tags") or []
    )
    declared_levels = {
        str(risk.get("level")) for risk in tables.get("risks", {}).values()
    }
    if elevated_tags:
        need(
            bool(declared_levels & {"HIGH", "CRITICAL"}),
            "changed diff carries elevated risk tags "
            f"({', '.join(sorted(elevated_tags))}) but no HIGH or CRITICAL risk is declared",
        )

    # High risk demands discriminating proof: CONTRACT alone is assertable, so it
    # does not close a HIGH or CRITICAL risk.
    risk_levels = {
        risk_id: str(risk.get("level"))
        for risk_id, risk in tables.get("risks", {}).items()
    }
    scenarios_table = tables.get("scenarios", {})
    weak_high_risk_proof: list[str] = []
    for test_id, test in tables.get("tests", {}).items():
        linked_levels: set[str] = set()
        for scenario_id in test.get("scenario_ids") or []:
            scenario = scenarios_table.get(str(scenario_id), {})
            if not isinstance(scenario, dict):
                continue
            for risk_id in scenario.get("risk_ids") or []:
                linked_levels.add(risk_levels.get(str(risk_id), ""))
        if linked_levels & {"HIGH", "CRITICAL"}:
            proof_status = (test.get("regression_proof") or {}).get("status")
            if proof_status not in {"RED_GREEN", "MUTATION"}:
                weak_high_risk_proof.append(str(test_id))

    decision = report.get("decision")
    need(decision in {"FULL", "PARTIAL", "BLOCKED"}, "invalid decision")

    if decision == "FULL":
        need(not required_gap, "FULL with planned or uncovered scenario")
        need(not proof_gap, "FULL with unproven regression test")
        need(not target_failure, "FULL with target validation failure")
        need(not cleanup_blocked, "FULL with blocked cleanup")
        need(audit.get("status") == "PASS", "FULL with failed test diff audit")
        need(not unsafe_real_data, "FULL with unsafe real-data environment")
        need(
            not receipts["flaky"],
            "FULL with flaky command(s): " + ", ".join(receipts["flaky"]),
        )
        need(
            not receipts["unstable_target"],
            "FULL requires repeated stable TARGET proof; unstable: "
            + ", ".join(receipts["unstable_target"]),
        )
        need(
            wiring_status in {"PROVEN", "NOT_APPLICABLE"},
            "FULL requires proven test wiring (runner must discover each new test)",
        )
        need(
            not weak_high_risk_proof,
            "FULL requires RED_GREEN or MUTATION proof for HIGH/CRITICAL risk: "
            + ", ".join(sorted(weak_high_risk_proof)),
        )
        if e2e_required:
            need(
                real_system.get("status") == "PROVEN",
                "FULL with E2E but no proven real system",
            )
        else:
            need(
                real_system.get("status") in {"PROVEN", "NOT_APPLICABLE"},
                "FULL with unverified real-system claim",
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("report")
    args = parser.parse_args()
    try:
        errors = validate(
            read_object(args.baseline),
            read_object(args.bundle),
            read_object(args.report),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: coverage report is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
