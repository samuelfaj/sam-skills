#!/usr/bin/env python3
"""Create or refresh a demo report.json from the manifest and media inspection.

Create (report absent): write a skeleton with manifest-derived fields,
pre-linked AC/R/S/T/CMD/ART/CL ids, and the --publish-requested decision.
Refresh (report present): re-derive manifest_fingerprint, target, and
command_definitions.changed from the manifest and, with --media, the artifact's
path and media block from `media_tools.py inspect` output. Nothing else changes.

Placeholders ("", null, "TODO:<enum>", empty actions/metadata) never validate,
so an unfilled field fails closed. The prefilled intent lists ([]) and the
manifest's environment kind/identity do validate: replace them deliberately.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MEDIA_KEYS = ("path", "mime_type", "sha256")


def load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def skeleton(manifest: dict[str, Any], publish_requested: bool) -> dict[str, Any]:
    environment = manifest.get("environment") or {}
    changed = bool(manifest.get("command_definitions"))
    return {
        "manifest_fingerprint": None,
        "target": {},
        "intent": {"summary": "", "invariants": [], "no_go": []},
        "environment": {
            "kind": environment.get("kind", "unknown"),
            "identity": environment.get("identity", ""),
            "real_data": None,
            "evidence": "",
        },
        "authorization": {"publish_requested": publish_requested},
        "command_definitions": {
            "changed": changed,
            "inspected": None if changed else False,
            "evidence": "" if changed else "manifest lists no changed command definitions",
        },
        "criteria": [{"id": "AC-001", "text": ""}],
        "risks": [
            {
                "id": "R-001",
                "criterion_ids": ["AC-001"],
                "level": "TODO:LOW|MEDIUM|HIGH|CRITICAL",
                "evidence": "",
            }
        ],
        "scenarios": [
            {
                "id": "S-001",
                "criterion_ids": ["AC-001"],
                "risk_ids": ["R-001"],
                "check_ids": ["T-001"],
                "artifact_ids": ["ART-001"],
                "initial_state": "",
                "actions": [],
                "proof_moment": "",
                "final_state": "",
            }
        ],
        "checks": [
            {
                "id": "T-001",
                "scenario_ids": ["S-001"],
                "command_ids": ["CMD-001"],
                "assertion": "",
            }
        ],
        "commands": [
            {
                "id": "CMD-001",
                "check_ids": ["T-001"],
                "command": "",
                "status": "TODO:PASS|FAIL|NOT_RUN",
                "evidence": "",
            }
        ],
        "artifacts": [
            {
                "id": "ART-001",
                "scenario_ids": ["S-001"],
                "status": "TODO:LOCAL|UPLOADED",
                "path": "",
                "media": {
                    "mime_type": "",
                    "conversion_status": "TODO:PASS|FAIL",
                    "sha256": "",
                    "metadata": {},
                },
                "playback_verified": None,
                "privacy_review": {"status": "TODO:PASS|FAIL", "evidence": ""},
                "contact_sheet_review": {"status": "TODO:PASS|FAIL", "evidence": ""},
            }
        ],
        "cleanup": [
            {"id": "CL-001", "resource": "", "status": "TODO:CLEANED|RETAINED|BLOCKED"}
        ],
        "plan_audit": {"status": "TODO:PASS|FAIL", "evidence": ""},
        "recording": {
            "real_ui": None,
            "requires_linked_backend": None,
            "linked_backend": None,
            "fallback_reason": "",
        },
        "publication": {
            "status": "TODO:PUBLISHED|BLOCKED" if publish_requested else "NOT_REQUESTED"
        },
        "decision": "TODO:READY_LOCAL|PUBLISHED|BLOCKED",
    }


def derive(report: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Copy exactly the values the validator compares against the manifest."""
    target = manifest.get("target") or {}
    report["manifest_fingerprint"] = manifest.get("fingerprint")
    if not isinstance(report.get("target"), dict):
        report["target"] = {}
    report["target"].update(
        {"base_sha": target.get("base_sha"), "head_sha": target.get("head_sha")}
    )
    if not isinstance(report.get("command_definitions"), dict):
        report["command_definitions"] = {}
    report["command_definitions"]["changed"] = bool(manifest.get("command_definitions"))


def apply_media(report: dict[str, Any], media: dict[str, Any], artifact_id: str) -> None:
    missing = [key for key in MEDIA_KEYS if not media.get(key)]
    if missing:
        raise ValueError(f"media inspection lacks {', '.join(missing)}")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("report.artifacts must be a list")
    artifact = next(
        (item for item in artifacts if isinstance(item, dict) and item.get("id") == artifact_id),
        None,
    )
    if artifact is None:
        raise ValueError(f"report has no artifact {artifact_id}")
    artifact["path"] = media["path"]
    block = artifact.get("media")
    if not isinstance(block, dict):
        block = artifact["media"] = {}
    block["mime_type"] = media["mime_type"]
    block["sha256"] = media["sha256"]
    block["metadata"] = {
        key: value for key, value in media.items() if key not in MEDIA_KEYS
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument(
        "--publish-requested",
        choices=("true", "false"),
        help="required on create; fixed afterwards",
    )
    parser.add_argument("--media", help="JSON from media_tools.py inspect")
    parser.add_argument("--artifact-id", default="ART-001")
    args = parser.parse_args()
    report_path = Path(args.report)
    try:
        manifest = load(args.manifest)
        if report_path.exists():
            if args.publish_requested is not None:
                raise ValueError(
                    "authorization is fixed at create time; edit "
                    "authorization.publish_requested in the report instead"
                )
            report = load(args.report)
            mode = "refreshed"
        else:
            if args.publish_requested is None:
                raise ValueError("--publish-requested true|false is required to create a report")
            report = skeleton(manifest, args.publish_requested == "true")
            mode = "created"
        derive(report, manifest)
        if args.media:
            apply_media(report, load(args.media), args.artifact_id)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"scaffold: {mode} {report_path} fingerprint={report['manifest_fingerprint']} "
        f"head={report['target'].get('head_sha')} media={'applied' if args.media else 'unchanged'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
