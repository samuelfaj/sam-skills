#!/usr/bin/env python3
"""Validate a demo report, media evidence graph, authorization, and cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PREFIXES = {
    "criteria": "AC-",
    "risks": "R-",
    "scenarios": "S-",
    "checks": "T-",
    "commands": "CMD-",
    "artifacts": "ART-",
    "cleanup": "CL-",
}


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def validate(manifest: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def need(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    need(
        report.get("manifest_fingerprint") == manifest.get("fingerprint"),
        "manifest fingerprint mismatch",
    )
    target = report.get("target", {})
    need(
        target.get("base_sha") == manifest.get("target", {}).get("base_sha"),
        "base SHA mismatch",
    )
    need(
        target.get("head_sha") == manifest.get("target", {}).get("head_sha"),
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

    def refs(value: Any, table: str, owner: str, required: bool = True) -> list[str]:
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

    for risk_id, risk in tables.get("risks", {}).items():
        refs(risk.get("criterion_ids"), "criteria", risk_id)
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
    for scenario_id, scenario in tables.get("scenarios", {}).items():
        refs(scenario.get("criterion_ids"), "criteria", scenario_id)
        refs(scenario.get("risk_ids"), "risks", scenario_id)
        check_ids = refs(scenario.get("check_ids"), "checks", scenario_id)
        artifact_ids = refs(scenario.get("artifact_ids"), "artifacts", scenario_id)
        reciprocal(scenario_id, check_ids, "checks", "scenario_ids")
        reciprocal(scenario_id, artifact_ids, "artifacts", "scenario_ids")
        for field in ("initial_state", "actions", "proof_moment", "final_state"):
            need(bool(scenario.get(field)), f"{scenario_id} missing {field}")
    for check_id, check in tables.get("checks", {}).items():
        scenario_ids = refs(check.get("scenario_ids"), "scenarios", check_id)
        command_ids = refs(check.get("command_ids"), "commands", check_id)
        reciprocal(check_id, scenario_ids, "scenarios", "check_ids")
        reciprocal(check_id, command_ids, "commands", "check_ids")
        need(bool(check.get("assertion")), f"{check_id} missing assertion")

    failed_command = False
    for command_id, command in tables.get("commands", {}).items():
        check_ids = refs(command.get("check_ids"), "checks", command_id)
        reciprocal(command_id, check_ids, "checks", "command_ids")
        status = command.get("status")
        need(status in {"PASS", "FAIL", "NOT_RUN"}, f"{command_id} invalid status")
        need(
            bool(command.get("command")) and bool(command.get("evidence")),
            f"{command_id} missing command or evidence",
        )
        failed_command = failed_command or status != "PASS"

    uploaded = False
    invalid_media = False
    for artifact_id, artifact in tables.get("artifacts", {}).items():
        scenario_ids = refs(artifact.get("scenario_ids"), "scenarios", artifact_id)
        reciprocal(artifact_id, scenario_ids, "scenarios", "artifact_ids")
        status = artifact.get("status")
        need(status in {"LOCAL", "UPLOADED"}, f"{artifact_id} invalid status")
        path = str(artifact.get("path", ""))
        local_file = Path(path)
        media = artifact.get("media", {})
        metadata = media.get("metadata", {})
        valid = True
        valid &= path.lower().endswith(".mp4")
        valid &= local_file.is_file() and local_file.stat().st_size > 0
        if local_file.is_file():
            with local_file.open("rb") as source:
                valid &= b"ftyp" in source.read(64)
            valid &= file_digest(local_file) == media.get("sha256")
        valid &= media.get("mime_type") == "video/mp4"
        valid &= media.get("conversion_status") == "PASS"
        valid &= bool(re.fullmatch(r"[0-9a-f]{64}", str(media.get("sha256", ""))))
        valid &= metadata.get("has_video") is True
        valid &= (
            isinstance(metadata.get("duration_seconds"), (int, float))
            and metadata.get("duration_seconds", 0) > 0
        )
        valid &= isinstance(metadata.get("width"), int) and metadata.get("width", 0) > 0
        valid &= (
            isinstance(metadata.get("height"), int) and metadata.get("height", 0) > 0
        )
        valid &= artifact.get("playback_verified") is True
        privacy = artifact.get("privacy_review", {})
        contact = artifact.get("contact_sheet_review", {})
        valid &= privacy.get("status") == "PASS" and bool(privacy.get("evidence"))
        valid &= contact.get("status") == "PASS" and bool(contact.get("evidence"))
        need(valid, f"{artifact_id} has invalid or unverified MP4 evidence")
        invalid_media = invalid_media or not valid
        if status == "UPLOADED":
            uploaded = True
            need(
                bool(artifact.get("receipt"))
                and artifact.get("readback_verified") is True,
                f"{artifact_id} lacks verified remote receipt",
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
        "real data requires verified local, test, or dev environment",
    )
    command_defs = report.get("command_definitions", {})
    changed = bool(manifest.get("command_definitions"))
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
    audit = report.get("plan_audit", {})
    need(
        audit.get("status") in {"PASS", "FAIL"} and bool(audit.get("evidence")),
        "plan audit required",
    )
    recording = report.get("recording", {})
    need(
        isinstance(recording.get("real_ui"), bool), "recording.real_ui must be boolean"
    )
    need(
        isinstance(recording.get("requires_linked_backend"), bool),
        "requires_linked_backend must be boolean",
    )
    need(
        isinstance(recording.get("linked_backend"), bool),
        "linked_backend must be boolean",
    )
    if recording.get("real_ui") is False:
        need(
            bool(recording.get("fallback_reason")),
            "fallback recording requires exact reason",
        )
    if recording.get("requires_linked_backend") is True:
        need(
            recording.get("linked_backend") is True
            or bool(recording.get("fallback_reason")),
            "missing linked backend proof or fallback reason",
        )
    authorization = report.get("authorization", {})
    need(
        isinstance(authorization.get("publish_requested"), bool),
        "publish_requested must be boolean",
    )
    need(
        not uploaded or authorization.get("publish_requested") is True,
        "artifact uploaded without explicit authorization",
    )
    publication = report.get("publication", {})
    pub_status = publication.get("status")
    need(
        pub_status in {"NOT_REQUESTED", "PUBLISHED", "BLOCKED"},
        "invalid publication status",
    )
    if pub_status == "PUBLISHED":
        need(
            authorization.get("publish_requested") is True,
            "publication lacks authorization",
        )
        need(
            bool(publication.get("receipt"))
            and publication.get("readback_verified") is True,
            "publication lacks verified readback",
        )
    if pub_status == "BLOCKED":
        need(
            bool(publication.get("error") or publication.get("reason")),
            "blocked publication requires a concrete error or reason",
        )
    if authorization.get("publish_requested") is False:
        need(
            pub_status == "NOT_REQUESTED",
            "publication state conflicts with local-only authorization",
        )

    decision = report.get("decision")
    need(decision in {"READY_LOCAL", "PUBLISHED", "BLOCKED"}, "invalid decision")
    if authorization.get("publish_requested") is True:
        need(
            pub_status != "NOT_REQUESTED",
            "requested publication cannot remain NOT_REQUESTED",
        )
        need(
            decision != "READY_LOCAL",
            "requested publication cannot finish READY_LOCAL",
        )
    if decision in {"READY_LOCAL", "PUBLISHED"}:
        need(not failed_command, f"{decision} with failed or unrun proof command")
        need(not invalid_media, f"{decision} with invalid media")
        need(not cleanup_blocked, f"{decision} with blocked cleanup")
        need(not unsafe_real_data, f"{decision} with unsafe real-data environment")
        need(audit.get("status") == "PASS", f"{decision} with failed plan audit")
    if decision == "READY_LOCAL":
        need(
            pub_status == "NOT_REQUESTED" and not uploaded,
            "READY_LOCAL contains published evidence",
        )
    if decision == "PUBLISHED":
        need(
            pub_status == "PUBLISHED" and uploaded,
            "PUBLISHED lacks uploaded artifact and publication receipt",
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("report")
    args = parser.parse_args()
    try:
        errors = validate(load(args.manifest), load(args.report))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: demo report is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
