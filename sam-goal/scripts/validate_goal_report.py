#!/usr/bin/env python3
"""Validate a sam-goal report against the output contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ACTIONS = {"execute", "review", "audit"}
INTENSITIES = {"lite", "full", "ultra"}
MODES = {"solo", "delegated"}
GATES = {"open", "closed"}
RESULTS = {"COMPLETE", "IN_PROGRESS", "BLOCKED"}
EVIDENCE_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "INFO"}
HOST_KEYS = {"claude-code", "codex", "grok"}
HOST_STATUSES = {"DETECTED", "OVERRIDE", "UNKNOWN", "CONFLICT", "INVALID"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read report: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("report root must be an object")
    return value


def mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    return value


def text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be non-empty text")
        return ""
    return value.strip()


def absolute_path(value: Any, label: str, errors: list[str]) -> str:
    raw = text(value, label, errors)
    if raw and not Path(raw).is_absolute():
        errors.append(f"{label} must be an absolute path")
    return raw


def integer(value: Any, label: str, errors: list[str], *, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{label} must be an integer")
        return 0
    if minimum is not None and value < minimum:
        errors.append(f"{label} must be >= {minimum}")
    return value


def string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        errors.append(f"{label} must be an array of non-empty strings")
        return []
    return [item.strip() for item in value]


def choice(value: Any, label: str, allowed: set[str], errors: list[str]) -> str:
    raw = text(value, label, errors)
    if raw and raw not in allowed:
        errors.append(f"{label} must be one of {sorted(allowed)}")
    return raw


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if report.get("workflow") != "goal":
        errors.append("workflow must be 'goal'")
    text(report.get("goal"), "goal", errors)
    action = choice(report.get("action"), "action", ACTIONS, errors)
    choice(report.get("intensity"), "intensity", INTENSITIES, errors)
    mode = choice(report.get("mode"), "mode", MODES, errors)
    integer(report.get("tree_depth"), "tree_depth", errors, minimum=1)
    absolute_path(report.get("goal_dir"), "goal_dir", errors)
    host = mapping(report.get("host"), "host", errors)
    host_status = choice(host.get("status"), "host.status", HOST_STATUSES, errors)
    host_key = host.get("key")
    if host_status in {"DETECTED", "OVERRIDE"}:
        if host_key not in HOST_KEYS:
            errors.append("host.key must be claude-code, codex, or grok")
    elif host and host_key is not None:
        errors.append("host.key must be null unless status is DETECTED or OVERRIDE")
    if host:
        text(host.get("detected_from"), "host.detected_from", errors)

    units = mapping(report.get("units"), "units", errors)
    integer(units.get("counted"), "units.counted", errors, minimum=1)
    gate = choice(units.get("gate"), "units.gate", GATES, errors)
    text(units.get("reason"), "units.reason", errors)
    if mode == "delegated" and gate != "open":
        errors.append("delegated mode requires units.gate open")
    if mode == "solo" and gate != "closed":
        errors.append("solo mode requires units.gate closed")
    ladder = mapping(report.get("ladder"), "ladder", errors)
    integer(ladder.get("rung"), "ladder.rung", errors, minimum=1)
    if ladder and ladder.get("rung", 1) > 7:
        errors.append("ladder.rung must be <= 7")
    text(ladder.get("rationale"), "ladder.rationale", errors)
    string_list(ladder.get("skipped"), "ladder.skipped", errors)
    new_deps = string_list(ladder.get("new_dependencies"), "ladder.new_dependencies", errors)
    authorized = string_list(
        ladder.get("authorized_dependencies"), "ladder.authorized_dependencies", errors
    )
    unauthorized = [item for item in new_deps if item not in authorized]

    gates = mapping(report.get("gates"), "gates", errors)
    absolute_path(gates.get("path"), "gates.path", errors)
    total = integer(gates.get("total"), "gates.total", errors, minimum=0)
    met = integer(gates.get("met"), "gates.met", errors, minimum=0)
    abandoned = integer(gates.get("abandoned"), "gates.abandoned", errors, minimum=0)
    unmet = string_list(gates.get("unmet"), "gates.unmet", errors)
    abandoned_ids = string_list(gates.get("abandoned_ids"), "gates.abandoned_ids", errors)
    if gates and met + abandoned + len(unmet) != total:
        errors.append("gates.met + gates.abandoned + len(unmet) must equal gates.total")
    if abandoned != len(abandoned_ids):
        errors.append("gates.abandoned must equal len(abandoned_ids)")

    delegation = report.get("delegation")
    if mode == "solo":
        if delegation is not None:
            errors.append("solo mode requires delegation null")
    else:
        payload = mapping(delegation, "delegation", errors)
        absolute_path(payload.get("path"), "delegation.path", errors)
        d_units = integer(payload.get("units"), "delegation.units", errors, minimum=1)
        verified = integer(payload.get("verified"), "delegation.verified", errors, minimum=0)
        pending = integer(payload.get("pending"), "delegation.pending", errors, minimum=0)
        if "complete" in payload and not isinstance(payload.get("complete"), bool):
            errors.append("delegation.complete must be a boolean")
        if payload and verified + pending > d_units:
            errors.append("delegation.verified + pending cannot exceed units")

    review = mapping(report.get("overbuild_review"), "overbuild_review", errors)
    if not isinstance(review.get("lean_already"), bool):
        errors.append("overbuild_review.lean_already must be a boolean")
    integer(review.get("net_lines"), "overbuild_review.net_lines", errors)
    findings = review.get("findings")
    if not isinstance(findings, list):
        errors.append("overbuild_review.findings must be an array")
        findings = []
    elif review.get("lean_already") and findings:
        errors.append("lean_already cannot include findings")
    elif review.get("lean_already") is False and not findings:
        errors.append("overbuild_review without lean_already needs findings")

    checks = mapping(report.get("checks"), "checks", errors)
    gates_check = checks.get("gates")
    ledger_check = checks.get("ledger")
    if action == "execute":
        gate_run = mapping(gates_check, "checks.gates", errors)
        integer(gate_run.get("exit_code"), "checks.gates.exit_code", errors, minimum=0)
        text(gate_run.get("summary"), "checks.gates.summary", errors)
        if total < 1:
            errors.append("execute requires at least one gate")
    elif gates_check is not None:
        gate_run = mapping(gates_check, "checks.gates", errors)
        if gate_run:
            integer(gate_run.get("exit_code"), "checks.gates.exit_code", errors, minimum=0)
            text(gate_run.get("summary"), "checks.gates.summary", errors)
    if mode == "delegated":
        ledger_run = mapping(ledger_check, "checks.ledger", errors)
        integer(ledger_run.get("exit_code"), "checks.ledger.exit_code", errors, minimum=0)
        text(ledger_run.get("summary"), "checks.ledger.summary", errors)
    elif ledger_check is not None:
        errors.append("solo mode requires checks.ledger null")

    evidence = report.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty array")
        evidence = []
    ids: set[str] = set()
    pass_count = 0
    for index, raw in enumerate(evidence):
        item = mapping(raw, f"evidence[{index}]", errors)
        evidence_id = text(item.get("id"), f"evidence[{index}].id", errors)
        if evidence_id:
            if evidence_id in ids:
                errors.append(f"evidence repeats id {evidence_id}")
            ids.add(evidence_id)
        status = choice(
            item.get("status"), f"evidence[{index}].status", EVIDENCE_STATUSES, errors
        )
        text(item.get("detail"), f"evidence[{index}].detail", errors)
        if status == "PASS":
            pass_count += 1

    decision = mapping(report.get("decision"), "decision", errors)
    result = choice(decision.get("result"), "decision.result", RESULTS, errors)
    remaining = string_list(decision.get("remaining"), "decision.remaining", errors)
    if result == "COMPLETE":
        if remaining:
            errors.append("COMPLETE requires empty decision.remaining")
        if unmet:
            errors.append("COMPLETE requires empty gates.unmet")
        if unauthorized:
            errors.append("COMPLETE forbids unauthorized new_dependencies")
        if pass_count < 1:
            errors.append("COMPLETE requires at least one PASS evidence item")
        if action == "execute":
            if not isinstance(gates_check, dict) or gates_check.get("exit_code") != 0:
                errors.append("COMPLETE execute requires checks.gates.exit_code 0")
        if mode == "delegated":
            if not isinstance(delegation, dict) or not delegation.get("complete"):
                errors.append("COMPLETE delegated requires delegation.complete true")
            if isinstance(delegation, dict) and delegation.get("verified") != delegation.get(
                "units"
            ):
                errors.append("COMPLETE delegated requires verified == units")
            if not isinstance(ledger_check, dict) or ledger_check.get("exit_code") != 0:
                errors.append("COMPLETE delegated requires checks.ledger.exit_code 0")
    elif result in RESULTS and not remaining:
        errors.append(f"{result} requires non-empty decision.remaining")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    return parser.parse_args()


def main() -> int:
    try:
        report = load_json(Path(parse_args().report))
        errors = validate(report)
    except ValueError as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 1
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        print(f"INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
