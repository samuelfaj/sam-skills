#!/usr/bin/env python3
"""Validate a sam-work completion report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PHASE_IDS = [
    "implementation",
    "refine",
    "review",
    "simplify",
    "coverage",
    "proposal",
    "playwright",
    "demo",
]

FIXED_SKILLS = {
    "refine": "sam-refine-task",
    "review": "sam-review",
    "simplify": "sam-simplify-task",
    "coverage": "sam-create-test-coverage",
    "proposal": "sam-pr-description",
    "playwright": "sam-create-playwright-tests",
    "demo": "sam-create-task-demo-video",
}

FINAL_STATUSES = {
    "implementation": {"COMPLETE"},
    "refine": {"HIGH_CONFIDENCE"},
    "review": {"APPROVE"},
    "simplify": {"SIMPLEST_DEFENSIBLE", "NO_CHANGE"},
    "coverage": {"FULL"},
    "proposal": {"READY"},
    "playwright": {"COMPLETE", "NOT_APPLICABLE"},
    "demo": {"PUBLISHED"},
}

ITERATION_STATUSES = {
    "implementation": {"COMPLETE", "BLOCKED"},
    "refine": {"HIGH_CONFIDENCE", "NOT_CONFIDENT", "BLOCKED"},
    "review": {"APPROVE", "CHANGES_REQUIRED", "COMMENT_ONLY", "BLOCKED"},
    "simplify": {
        "SIMPLEST_DEFENSIBLE",
        "NO_CHANGE",
        "CHANGES_APPLIED",
        "BLOCKED",
    },
    "coverage": {"FULL", "PARTIAL", "BLOCKED"},
    "proposal": {"READY", "BLOCKED"},
    "playwright": {"COMPLETE", "PARTIAL", "NOT_APPLICABLE", "BLOCKED"},
    "demo": {"PUBLISHED", "BLOCKED"},
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load report: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("report root must be an object")
    return value


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(nonempty_string(item) for item in value)
    )


def is_https_url(value: Any) -> bool:
    if not nonempty_string(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_iteration(
    phase_id: str,
    iteration: Any,
    expected_sequence: int,
    is_last: bool,
    errors: list[str],
) -> None:
    prefix = f"phase {phase_id} iteration {expected_sequence}"
    if not isinstance(iteration, dict):
        errors.append(f"{prefix} must be an object")
        return
    if iteration.get("sequence") != expected_sequence:
        errors.append(f"{prefix} sequence must be contiguous from one")
    for field in ("input_fingerprint", "output_fingerprint"):
        if not HEX64.fullmatch(str(iteration.get(field, ""))):
            errors.append(f"{prefix} {field} must be 64 lowercase hex characters")
    status = iteration.get("status")
    if status not in ITERATION_STATUSES[phase_id]:
        errors.append(f"{prefix} has unsupported status {status!r}")
    open_items = iteration.get("open_required_items")
    corrections = iteration.get("correction_receipts")
    if not string_list(open_items):
        errors.append(f"{prefix} open_required_items must be a string array")
        open_items = []
    if not string_list(corrections):
        errors.append(f"{prefix} correction_receipts must be a string array")
        corrections = []
    if not string_list(iteration.get("evidence"), nonempty=True):
        errors.append(f"{prefix} requires evidence")
    if open_items and not corrections:
        errors.append(f"{prefix} with open items requires correction receipts")
    if is_last:
        if open_items:
            errors.append(f"{prefix} cannot finish with open required items")
        if status not in FINAL_STATUSES[phase_id]:
            errors.append(f"{prefix} is not an accepted terminal status")
    elif not open_items and not corrections:
        errors.append(
            f"{prefix} must record either corrected findings or a later invalidation"
        )


def validate_phase(
    phase: Any,
    expected_id: str,
    classification: Any,
    web_system: Any,
    final_head: Any,
    errors: list[str],
) -> None:
    prefix = f"phase {expected_id}"
    if not isinstance(phase, dict):
        errors.append(f"{prefix} must be an object")
        return
    if phase.get("id") != expected_id:
        errors.append(f"{prefix} is missing or out of order")

    expected_skill = FIXED_SKILLS.get(expected_id)
    if expected_id == "implementation":
        expected_skill = "sam-fix-bug" if classification == "BUG" else "sam-create-feature"
    if phase.get("skill") != expected_skill:
        errors.append(f"{prefix} must use {expected_skill}")

    applicability = phase.get("applicability")
    status = phase.get("status")
    if expected_id == "playwright" and web_system is False:
        if applicability != "NOT_APPLICABLE" or status != "NOT_APPLICABLE":
            errors.append("non-web Playwright phase must be explicitly NOT_APPLICABLE")
        if not nonempty_string(phase.get("not_applicable_reason")):
            errors.append("non-web Playwright phase requires a concrete reason")
    else:
        if applicability != "REQUIRED":
            errors.append(f"{prefix} must be REQUIRED")
        if phase.get("not_applicable_reason") is not None:
            errors.append(f"{prefix} cannot have a not-applicable reason")
        if status not in FINAL_STATUSES[expected_id] or status == "NOT_APPLICABLE":
            errors.append(f"{prefix} does not have an accepted final status")

    if phase.get("current") is not True:
        errors.append(f"{prefix} proof must be current")
    if phase.get("validated_head_sha") != final_head:
        errors.append(f"{prefix} proof is stale for the final head")
    if not string_list(phase.get("evidence"), nonempty=True):
        errors.append(f"{prefix} requires evidence")
    if not string_list(phase.get("validator_receipts"), nonempty=True):
        errors.append(f"{prefix} requires validator receipts")

    iterations = phase.get("iterations")
    if not isinstance(iterations, list) or not iterations:
        errors.append(f"{prefix} requires at least one iteration")
        return
    for index, iteration in enumerate(iterations, start=1):
        validate_iteration(
            expected_id,
            iteration,
            index,
            index == len(iterations),
            errors,
        )
    if isinstance(iterations[-1], dict) and status != iterations[-1].get("status"):
        errors.append(f"{prefix} status must match its final iteration")


def validate_environment(name: str, value: Any, errors: list[str]) -> None:
    prefix = f"environment {name}"
    if not isinstance(value, dict):
        errors.append(f"{prefix} is required")
        return
    if value.get("kind") != "DEVELOPMENT":
        errors.append(f"{prefix} must be verified DEVELOPMENT")
    if value.get("identity_verified") is not True:
        errors.append(f"{prefix} identity must be verified")
    if not string_list(value.get("identity_evidence"), nonempty=True):
        errors.append(f"{prefix} requires identity evidence")
    if value.get("real_data") is not True:
        errors.append(f"{prefix} must use real development data")
    if value.get("dedicated_data") is not True:
        errors.append(f"{prefix} must use dedicated data")
    if value.get("cleanup_status") != "COMPLETE":
        errors.append(f"{prefix} cleanup must be COMPLETE")
    if value.get("privacy_review") != "PASS":
        errors.append(f"{prefix} privacy review must PASS")


def validate_proposal(value: Any, final_head: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("proposal receipt is required")
        return
    if not nonempty_string(value.get("platform")):
        errors.append("proposal platform is required")
    if not is_https_url(value.get("url")):
        errors.append("proposal URL must be HTTPS")
    if not nonempty_string(value.get("proposal_id")):
        errors.append("proposal ID is required")
    if not isinstance(value.get("created_by_workflow"), bool):
        errors.append("proposal created_by_workflow must be boolean")
    if value.get("description_validated") is not True:
        errors.append("proposal description must be validated")
    if not nonempty_string(value.get("description_receipt")):
        errors.append("proposal description receipt is required")
    if value.get("remote_head_sha") != final_head:
        errors.append("proposal remote head does not match final head")
    if not string_list(value.get("rendered_readback_evidence"), nonempty=True):
        errors.append("proposal rendered readback evidence is required")
    if value.get("required_ci_status") not in {"PASS", "NOT_CONFIGURED"}:
        errors.append("proposal required CI must PASS or be NOT_CONFIGURED")


def validate_videos(report: dict[str, Any], web_system: Any, errors: list[str]) -> None:
    inventory = report.get("video_inventory")
    if not isinstance(inventory, dict):
        errors.append("video_inventory is required")
        return
    keys = (
        "playwright_discovered",
        "playwright_uploaded",
        "demo_discovered",
        "demo_uploaded",
    )
    for key in keys:
        value = inventory.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"video_inventory {key} must be a non-negative integer")

    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be an array")
        return
    counts = {"playwright": 0, "demo": 0}
    identities: set[tuple[Any, Any, Any]] = set()
    for index, artifact in enumerate(artifacts, start=1):
        prefix = f"artifact {index}"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be an object")
            continue
        phase = artifact.get("phase")
        if phase not in counts:
            errors.append(f"{prefix} phase must be playwright or demo")
            continue
        counts[phase] += 1
        local_path = artifact.get("local_path")
        if not nonempty_string(local_path) or not Path(local_path).is_absolute():
            errors.append(f"{prefix} local_path must be absolute")
        elif phase == "demo" and Path(local_path).suffix.lower() != ".mp4":
            errors.append(f"{prefix} demo video must be an MP4")
        if not HEX64.fullmatch(str(artifact.get("sha256", ""))):
            errors.append(f"{prefix} sha256 must be 64 lowercase hex characters")
        if not is_https_url(artifact.get("uploaded_url")):
            errors.append(f"{prefix} uploaded_url must be HTTPS")
        if not nonempty_string(artifact.get("upload_receipt")):
            errors.append(f"{prefix} upload receipt is required")
        if artifact.get("player_verified") is not True:
            errors.append(f"{prefix} must have a verified rendered video player")
        if not string_list(artifact.get("readback_evidence"), nonempty=True):
            errors.append(f"{prefix} requires player readback evidence")
        identity = (local_path, artifact.get("sha256"), artifact.get("uploaded_url"))
        if identity in identities:
            errors.append(f"{prefix} duplicates another video artifact")
        identities.add(identity)

    playwright_discovered = inventory.get("playwright_discovered")
    playwright_uploaded = inventory.get("playwright_uploaded")
    demo_discovered = inventory.get("demo_discovered")
    demo_uploaded = inventory.get("demo_uploaded")
    if web_system is True:
        if not isinstance(playwright_discovered, int) or playwright_discovered < 1:
            errors.append("web workflow requires at least one Playwright video")
        if playwright_uploaded != playwright_discovered:
            errors.append("every discovered Playwright video must be uploaded")
    elif playwright_discovered != 0 or playwright_uploaded != 0:
        errors.append("non-web workflow cannot claim Playwright videos")
    if demo_discovered is None or not isinstance(demo_discovered, int) or demo_discovered < 1:
        errors.append("workflow requires at least one demo video")
    if demo_uploaded != demo_discovered:
        errors.append("every discovered demo video must be uploaded")
    if counts["playwright"] != playwright_uploaded:
        errors.append("Playwright artifact count must equal uploaded inventory")
    if counts["demo"] != demo_uploaded:
        errors.append("demo artifact count must equal uploaded inventory")


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not nonempty_string(report.get("workflow_id")):
        errors.append("workflow_id is required")

    request = report.get("request")
    if not isinstance(request, dict):
        errors.append("request object is required")
        request = {}
    classification = request.get("classification")
    web_system = request.get("web_system")
    if classification not in {"BUG", "FEATURE"}:
        errors.append("request classification must be BUG or FEATURE")
    if not isinstance(web_system, bool):
        errors.append("request web_system must be boolean")
    if not HEX64.fullmatch(str(request.get("prompt_sha256", ""))):
        errors.append("request prompt_sha256 must be 64 lowercase hex characters")
    if not string_list(request.get("classification_evidence"), nonempty=True):
        errors.append("request classification evidence is required")

    authorization = report.get("authorization")
    expected_authorization = {
        "create_or_update_proposal": True,
        "publish_playwright_videos": True,
        "publish_demo_video": True,
        "merge": False,
        "deploy": False,
    }
    if authorization != expected_authorization:
        errors.append("authorization must exactly match the sam-work write boundary")

    target = report.get("target")
    if not isinstance(target, dict):
        errors.append("target object is required")
        target = {}
    repo_root = target.get("repo_root")
    if not nonempty_string(repo_root) or not Path(repo_root).is_absolute():
        errors.append("target repo_root must be absolute")
    if not nonempty_string(target.get("base_ref")):
        errors.append("target base_ref is required")
    for field in ("base_sha", "final_head_sha"):
        if not REVISION.fullmatch(str(target.get(field, ""))):
            errors.append(f"target {field} must be a 40- or 64-character revision")
    if not HEX64.fullmatch(str(target.get("final_change_fingerprint", ""))):
        errors.append("target final_change_fingerprint must be 64 lowercase hex characters")
    final_head = target.get("final_head_sha")

    phases = report.get("phases")
    if not isinstance(phases, list) or len(phases) != len(PHASE_IDS):
        errors.append("phases must contain exactly all eight canonical phases")
    else:
        for phase, phase_id in zip(phases, PHASE_IDS):
            validate_phase(
                phase,
                phase_id,
                classification,
                web_system,
                final_head,
                errors,
            )

    validate_proposal(report.get("proposal"), final_head, errors)

    environments = report.get("environments")
    if not isinstance(environments, dict):
        errors.append("environments object is required")
        environments = {}
    validate_environment("demo", environments.get("demo"), errors)
    if web_system is True:
        validate_environment("playwright", environments.get("playwright"), errors)
    elif environments.get("playwright") not in (None, {}):
        errors.append("non-web workflow must not claim a Playwright environment")

    validate_videos(report, web_system, errors)

    final = report.get("final")
    if not isinstance(final, dict):
        errors.append("final object is required")
    else:
        if final.get("result") != "COMPLETE":
            errors.append("final result must be COMPLETE")
        if final.get("completed_phase_ids") != PHASE_IDS:
            errors.append("final completed_phase_ids must list every phase in order")
        if final.get("blockers") != []:
            errors.append("complete workflow cannot have blockers")
        if final.get("final_head_sha") != final_head:
            errors.append("final head must match target final head")
        if final.get("final_change_fingerprint") != target.get(
            "final_change_fingerprint"
        ):
            errors.append("final change fingerprint must match target")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = load_json(Path(args.report))
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    errors = validate(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAIL: {len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("PASS: sam-work report proves every required phase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
