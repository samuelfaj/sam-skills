#!/usr/bin/env python3
"""Validate a remote review report against its immutable Git bundle."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

COVERAGE_CLASSES = {"REVIEWED", "GENERATED", "TYPE_ONLY", "TEST", "CONFIG", "EXCLUDED"}
SEVERITIES = {"BLOCKER", "IMPORTANT", "SUGGESTION"}
FINDING_STATUSES = {"ACCEPTED", "REJECTED", "FOLLOW_UP", "STOP_AND_ESCALATE"}
SCOPES = {"IN_SCOPE", "FOLLOW_UP", "STOP_AND_ESCALATE"}
SIDES = {"NEW", "OLD"}
TEST_LEVELS = {"UNIT", "INTEGRATION", "E2E", "CONTRACT", "STATIC", "MANUAL"}
TEST_STATUSES = {
    "COVERED",
    "MISSING_REQUIRED",
    "MISSING_OPTIONAL",
    "UNSUPPORTED",
    "NOT_APPLICABLE",
}
VALIDATION_STATUSES = {"PASS", "FAIL", "NOT_RUN"}
VALIDATION_CLASSES = {"TARGET", "BASELINE", "ENVIRONMENT", "EXTERNAL"}
BEHAVIOR_STATUSES = {"PROVEN", "NOT_PROVEN", "NOT_APPLICABLE"}
DECISIONS = {"APPROVE", "CHANGES_REQUIRED", "BLOCKED", "COMMENT_ONLY"}
CONFIDENCE = {"LOW", "MEDIUM", "HIGH"}
PUBLICATION_ACTIONS = {"NONE", "COMMENT", "REQUEST_CHANGES", "APPROVE"}
PUBLICATION_STATUSES = {"NOT_REQUESTED", "PLANNED", "PUBLISHED", "PARTIAL", "BLOCKED"}
SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def canonical_fingerprint(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require_keys(
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
    label: str,
    errors: list[str],
) -> None:
    missing = sorted(required - value.keys())
    extra = sorted(value.keys() - allowed)
    if missing:
        errors.append(f"{label} missing keys: {', '.join(missing)}")
    if extra:
        errors.append(f"{label} has unsupported keys: {', '.join(extra)}")


def object_list(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        errors.append(f"{label} must be a list of objects")
        return []
    return value


def string_list(
    value: Any, label: str, errors: list[str], *, nonempty: bool = False
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        errors.append(f"{label} must be a list of non-empty strings")
        return []
    if nonempty and not value:
        errors.append(f"{label} must not be empty")
    return value


def nonempty_string(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty string")
        return ""
    return value


def line_in_ranges(line: int, ranges: Any) -> bool:
    if not isinstance(ranges, list):
        return False
    return any(
        isinstance(item, list)
        and len(item) == 2
        and all(isinstance(part, int) for part in item)
        and item[0] <= line <= item[1]
        for item in ranges
    )


def validate_bundle(
    bundle: dict[str, Any], errors: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    require_keys(
        bundle,
        {
            "schema_version",
            "target",
            "files",
            "patch",
            "patch_sha256",
            "bundle_fingerprint",
        },
        {
            "schema_version",
            "target",
            "files",
            "patch",
            "patch_sha256",
            "bundle_fingerprint",
        },
        "bundle",
        errors,
    )
    if bundle.get("schema_version") != 1:
        errors.append("bundle.schema_version must be 1")
    copy_value = copy.deepcopy(bundle)
    recorded = copy_value.pop("bundle_fingerprint", None)
    if recorded != canonical_fingerprint(copy_value):
        errors.append("bundle fingerprint does not match bundle content")
    patch = bundle.get("patch")
    if not isinstance(patch, str):
        errors.append("bundle.patch must be a string")
    elif (
        bundle.get("patch_sha256") != hashlib.sha256(patch.encode("utf-8")).hexdigest()
    ):
        errors.append("bundle patch_sha256 does not match patch content")
    target = bundle.get("target")
    if not isinstance(target, dict):
        errors.append("bundle.target must be an object")
        target = {}
    require_keys(
        target,
        {
            "platform",
            "repository",
            "change_id",
            "base_ref",
            "head_ref",
            "requested_base_sha",
            "base_sha",
            "head_sha",
            "comparison",
        },
        {
            "platform",
            "repository",
            "change_id",
            "base_ref",
            "head_ref",
            "requested_base_sha",
            "base_sha",
            "head_sha",
            "comparison",
        },
        "bundle.target",
        errors,
    )
    for key in ("platform", "repository", "change_id", "base_ref", "head_ref"):
        nonempty_string(target.get(key), f"bundle.target.{key}", errors)
    for key in ("requested_base_sha", "base_sha", "head_sha"):
        value = nonempty_string(target.get(key), f"bundle.target.{key}", errors)
        if value and not SHA_RE.fullmatch(value):
            errors.append(f"bundle.target.{key} must be a full Git object ID")
    if target.get("comparison") not in {"direct", "merge-base"}:
        errors.append("bundle.target.comparison must be direct or merge-base")
    files = object_list(bundle.get("files"), "bundle.files", errors)
    if not files:
        errors.append("bundle.files must not be empty")
    return target, files


def validate(bundle: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    bundle_target, bundle_files = validate_bundle(bundle, errors)
    require_keys(
        report,
        {
            "schema_version",
            "target",
            "intent",
            "file_coverage",
            "findings",
            "test_coverage",
            "validations",
            "behavior_proof",
            "decision",
            "publication",
        },
        {
            "schema_version",
            "target",
            "intent",
            "file_coverage",
            "findings",
            "test_coverage",
            "validations",
            "behavior_proof",
            "decision",
            "publication",
        },
        "report",
        errors,
    )
    if report.get("schema_version") != 1:
        errors.append("report.schema_version must be 1")

    target = report.get("target")
    if not isinstance(target, dict):
        errors.append("report.target must be an object")
        target = {}
    require_keys(
        target,
        {"base_sha", "head_sha", "bundle_fingerprint"},
        {"base_sha", "head_sha", "bundle_fingerprint"},
        "report.target",
        errors,
    )
    for key in ("base_sha", "head_sha"):
        if target.get(key) != bundle_target.get(key):
            errors.append(f"report.target.{key} does not match bundle")
    if target.get("bundle_fingerprint") != bundle.get("bundle_fingerprint"):
        errors.append("report.target.bundle_fingerprint does not match bundle")

    intent = report.get("intent")
    if not isinstance(intent, dict):
        errors.append("intent must be an object")
        intent = {}
    require_keys(
        intent,
        {
            "intended_behavior",
            "must_not_change",
            "invariants",
            "owner_boundary",
            "user_visible_change",
        },
        {
            "intended_behavior",
            "must_not_change",
            "invariants",
            "owner_boundary",
            "user_visible_change",
        },
        "intent",
        errors,
    )
    string_list(
        intent.get("intended_behavior"),
        "intent.intended_behavior",
        errors,
        nonempty=True,
    )
    string_list(intent.get("must_not_change"), "intent.must_not_change", errors)
    string_list(intent.get("invariants"), "intent.invariants", errors, nonempty=True)
    nonempty_string(intent.get("owner_boundary"), "intent.owner_boundary", errors)
    if not isinstance(intent.get("user_visible_change"), bool):
        errors.append("intent.user_visible_change must be boolean")

    file_by_path: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(bundle_files):
        path = item.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"bundle.files[{index}].path must be a non-empty string")
            continue
        if path in file_by_path:
            errors.append(f"bundle contains duplicate path: {path}")
        file_by_path[path] = item

    coverage = object_list(report.get("file_coverage"), "file_coverage", errors)
    covered_paths: list[str] = []
    for index, item in enumerate(coverage):
        label = f"file_coverage[{index}]"
        require_keys(
            item,
            {"path", "classification", "reason"},
            {"path", "classification", "reason"},
            label,
            errors,
        )
        path = nonempty_string(item.get("path"), f"{label}.path", errors)
        if path:
            covered_paths.append(path)
        if item.get("classification") not in COVERAGE_CLASSES:
            errors.append(f"{label}.classification is invalid")
        nonempty_string(item.get("reason"), f"{label}.reason", errors)
    duplicates = sorted(
        {path for path in covered_paths if covered_paths.count(path) > 1}
    )
    if duplicates:
        errors.append(f"file_coverage contains duplicates: {', '.join(duplicates)}")
    expected_paths = set(file_by_path)
    actual_paths = set(covered_paths)
    if expected_paths != actual_paths:
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        if missing:
            errors.append(f"file_coverage missing paths: {', '.join(missing)}")
        if extra:
            errors.append(f"file_coverage has unknown paths: {', '.join(extra)}")

    findings = object_list(report.get("findings"), "findings", errors)
    findings_by_id: dict[str, dict[str, Any]] = {}
    accepted_required: list[str] = []
    stop_findings: list[str] = []
    for index, finding in enumerate(findings):
        label = f"findings[{index}]"
        require_keys(
            finding,
            {
                "id",
                "severity",
                "status",
                "scope",
                "path",
                "line",
                "side",
                "failure_mode",
                "impact",
                "evidence",
                "required_change",
                "test_gap",
                "rejection_reason",
            },
            {
                "id",
                "severity",
                "status",
                "scope",
                "path",
                "line",
                "side",
                "failure_mode",
                "impact",
                "evidence",
                "required_change",
                "test_gap",
                "rejection_reason",
            },
            label,
            errors,
        )
        finding_id = nonempty_string(finding.get("id"), f"{label}.id", errors)
        if finding_id in findings_by_id:
            errors.append(f"duplicate finding id: {finding_id}")
        elif finding_id:
            findings_by_id[finding_id] = finding
        if finding.get("severity") not in SEVERITIES:
            errors.append(f"{label}.severity is invalid")
        if finding.get("status") not in FINDING_STATUSES:
            errors.append(f"{label}.status is invalid")
        if finding.get("scope") not in SCOPES:
            errors.append(f"{label}.scope is invalid")
        path = finding.get("path")
        if path is not None and (not isinstance(path, str) or path not in file_by_path):
            errors.append(f"{label}.path must be null or a bundle path")
        line = finding.get("line")
        if line is not None and (not isinstance(line, int) or line < 1):
            errors.append(f"{label}.line must be null or a positive integer")
        side = finding.get("side")
        if side is not None and side not in SIDES:
            errors.append(f"{label}.side must be null, NEW, or OLD")
        if line is not None and side is None:
            errors.append(f"{label}.side is required when line is present")
        if line is not None and isinstance(path, str) and side in SIDES:
            ranges_key = "new_changed_ranges" if side == "NEW" else "old_changed_ranges"
            if not line_in_ranges(line, file_by_path[path].get(ranges_key)):
                errors.append(f"{label}.line is not a changed {side.lower()} line")
        if finding.get("status") == "ACCEPTED":
            nonempty_string(
                finding.get("failure_mode"), f"{label}.failure_mode", errors
            )
            nonempty_string(finding.get("impact"), f"{label}.impact", errors)
            string_list(
                finding.get("evidence"), f"{label}.evidence", errors, nonempty=True
            )
            nonempty_string(
                finding.get("required_change"), f"{label}.required_change", errors
            )
            if finding.get("rejection_reason") is not None:
                errors.append(
                    f"{label}.rejection_reason must be null for accepted findings"
                )
            if finding.get("severity") in {"BLOCKER", "IMPORTANT"} and finding_id:
                accepted_required.append(finding_id)
        elif finding.get("status") == "REJECTED":
            nonempty_string(
                finding.get("rejection_reason"), f"{label}.rejection_reason", errors
            )
        if finding.get("status") == "STOP_AND_ESCALATE":
            nonempty_string(
                finding.get("failure_mode"), f"{label}.failure_mode", errors
            )
            nonempty_string(finding.get("impact"), f"{label}.impact", errors)
            string_list(
                finding.get("evidence"), f"{label}.evidence", errors, nonempty=True
            )
            if finding_id:
                stop_findings.append(finding_id)
        if not isinstance(finding.get("test_gap"), bool):
            errors.append(f"{label}.test_gap must be boolean")

    tests = object_list(report.get("test_coverage"), "test_coverage", errors)
    if not tests:
        errors.append("test_coverage must contain at least one scenario")
    for index, item in enumerate(tests):
        label = f"test_coverage[{index}]"
        require_keys(
            item,
            {"behavior", "level", "status", "paths", "reason", "finding_id"},
            {"behavior", "level", "status", "paths", "reason", "finding_id"},
            label,
            errors,
        )
        nonempty_string(item.get("behavior"), f"{label}.behavior", errors)
        if item.get("level") not in TEST_LEVELS:
            errors.append(f"{label}.level is invalid")
        if item.get("status") not in TEST_STATUSES:
            errors.append(f"{label}.status is invalid")
        string_list(item.get("paths"), f"{label}.paths", errors)
        nonempty_string(item.get("reason"), f"{label}.reason", errors)
        test_finding_id = item.get("finding_id")
        if item.get("status") == "MISSING_REQUIRED":
            linked_finding = (
                findings_by_id.get(test_finding_id)
                if isinstance(test_finding_id, str)
                else None
            )
            if (
                not linked_finding
                or linked_finding.get("status") != "ACCEPTED"
                or linked_finding.get("severity") != "BLOCKER"
            ):
                errors.append(
                    f"{label} MISSING_REQUIRED must link to an accepted BLOCKER"
                )
            elif not linked_finding.get("test_gap"):
                errors.append(f"{label} linked blocker must set test_gap true")
        elif test_finding_id is not None and test_finding_id not in findings_by_id:
            errors.append(f"{label}.finding_id references an unknown finding")

    validations = object_list(report.get("validations"), "validations", errors)
    if not validations:
        errors.append("validations must contain at least one entry")
    target_failures = 0
    for index, item in enumerate(validations):
        label = f"validations[{index}]"
        require_keys(
            item,
            {"command", "status", "classification", "reason"},
            {"command", "status", "classification", "reason"},
            label,
            errors,
        )
        nonempty_string(item.get("command"), f"{label}.command", errors)
        if item.get("status") not in VALIDATION_STATUSES:
            errors.append(f"{label}.status is invalid")
        if item.get("classification") not in VALIDATION_CLASSES:
            errors.append(f"{label}.classification is invalid")
        nonempty_string(item.get("reason"), f"{label}.reason", errors)
        if item.get("status") == "FAIL" and item.get("classification") == "TARGET":
            target_failures += 1

    behavior = report.get("behavior_proof")
    if not isinstance(behavior, dict):
        errors.append("behavior_proof must be an object")
        behavior = {}
    require_keys(
        behavior,
        {"status", "evidence"},
        {"status", "evidence"},
        "behavior_proof",
        errors,
    )
    if behavior.get("status") not in BEHAVIOR_STATUSES:
        errors.append("behavior_proof.status is invalid")
    behavior_evidence = string_list(
        behavior.get("evidence"), "behavior_proof.evidence", errors
    )
    if behavior.get("status") == "PROVEN" and not behavior_evidence:
        errors.append("PROVEN behavior requires evidence")

    decision = report.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
        decision = {}
    require_keys(
        decision,
        {"result", "confidence", "non_gating_requested", "remaining_corrections"},
        {"result", "confidence", "non_gating_requested", "remaining_corrections"},
        "decision",
        errors,
    )
    result = decision.get("result")
    if result not in DECISIONS:
        errors.append("decision.result is invalid")
    if decision.get("confidence") not in CONFIDENCE:
        errors.append("decision.confidence is invalid")
    if not isinstance(decision.get("non_gating_requested"), bool):
        errors.append("decision.non_gating_requested must be boolean")
    remaining = string_list(
        decision.get("remaining_corrections"), "decision.remaining_corrections", errors
    )
    expected_remaining = sorted(set(accepted_required))
    if result == "APPROVE":
        if expected_remaining or stop_findings:
            errors.append(
                "APPROVE cannot retain required or stop-and-escalate findings"
            )
        if target_failures:
            errors.append("APPROVE cannot retain a target validation failure")
        if (
            intent.get("user_visible_change") is True
            and behavior.get("status") != "PROVEN"
        ):
            errors.append("APPROVE requires proof for a user-visible change")
        if remaining:
            errors.append("APPROVE must have no remaining corrections")
    elif result == "CHANGES_REQUIRED":
        if not expected_remaining:
            errors.append("CHANGES_REQUIRED requires an accepted BLOCKER or IMPORTANT")
        if sorted(set(remaining)) != expected_remaining:
            errors.append("remaining_corrections must match accepted required findings")
    elif result == "BLOCKED":
        if not stop_findings and not remaining:
            errors.append("BLOCKED requires a recorded blocker or remaining correction")
    elif result == "COMMENT_ONLY":
        if decision.get("non_gating_requested") is not True:
            errors.append("COMMENT_ONLY requires explicit non-gating request")
    if target_failures and not any(
        finding.get("status") == "ACCEPTED" and finding.get("severity") == "BLOCKER"
        for finding in findings
    ):
        errors.append("target validation failure must map to an accepted BLOCKER")

    publication = report.get("publication")
    if not isinstance(publication, dict):
        errors.append("publication must be an object")
        publication = {}
    require_keys(
        publication,
        {
            "requested",
            "expected_head_sha",
            "observed_head_sha",
            "review_id",
            "action",
            "status",
            "inline_comments",
            "receipts",
            "error",
        },
        {
            "requested",
            "expected_head_sha",
            "observed_head_sha",
            "review_id",
            "action",
            "status",
            "inline_comments",
            "receipts",
            "error",
        },
        "publication",
        errors,
    )
    requested = publication.get("requested")
    if not isinstance(requested, bool):
        errors.append("publication.requested must be boolean")
    if publication.get("expected_head_sha") != bundle_target.get("head_sha"):
        errors.append("publication.expected_head_sha must match bundle head")
    observed_head = nonempty_string(
        publication.get("observed_head_sha"), "publication.observed_head_sha", errors
    )
    review_id = nonempty_string(
        publication.get("review_id"), "publication.review_id", errors
    )
    if review_id and not re.fullmatch(r"[A-Za-z0-9._:-]{12,128}", review_id):
        errors.append("publication.review_id has invalid format")
    action = publication.get("action")
    status = publication.get("status")
    if action not in PUBLICATION_ACTIONS:
        errors.append("publication.action is invalid")
    if status not in PUBLICATION_STATUSES:
        errors.append("publication.status is invalid")
    inline_comments = object_list(
        publication.get("inline_comments"), "publication.inline_comments", errors
    )
    receipts = object_list(publication.get("receipts"), "publication.receipts", errors)
    for index, comment in enumerate(inline_comments):
        label = f"publication.inline_comments[{index}]"
        require_keys(
            comment,
            {"finding_id", "path", "line", "side"},
            {"finding_id", "path", "line", "side"},
            label,
            errors,
        )
        comment_finding_id = comment.get("finding_id")
        comment_finding = (
            findings_by_id.get(comment_finding_id)
            if isinstance(comment_finding_id, str)
            else None
        )
        if (
            not comment_finding
            or comment_finding.get("status") != "ACCEPTED"
            or comment_finding.get("severity")
            not in {
                "BLOCKER",
                "IMPORTANT",
            }
        ):
            errors.append(f"{label} must reference an accepted required finding")
        elif (
            comment.get("path") != comment_finding.get("path")
            or comment.get("line") != comment_finding.get("line")
            or comment.get("side") != comment_finding.get("side")
        ):
            errors.append(f"{label} position must match its finding")
    for index, receipt in enumerate(receipts):
        label = f"publication.receipts[{index}]"
        require_keys(
            receipt,
            {"kind", "id", "url", "status"},
            {"kind", "id", "url", "status"},
            label,
            errors,
        )
        for key in ("kind", "id", "url", "status"):
            nonempty_string(receipt.get(key), f"{label}.{key}", errors)

    error = publication.get("error")
    if error is not None and (not isinstance(error, str) or not error):
        errors.append("publication.error must be null or a non-empty string")
    expected_head = bundle_target.get("head_sha")
    drifted = bool(observed_head and observed_head != expected_head)
    if requested is False:
        if (
            action != "NONE"
            or status != "NOT_REQUESTED"
            or inline_comments
            or receipts
            or error is not None
        ):
            errors.append(
                "non-requested publication must be a clean NOT_REQUESTED local draft"
            )
    elif requested is True:
        if drifted:
            if action != "NONE" or status != "BLOCKED" or receipts or not error:
                errors.append(
                    "head drift must abort publication with BLOCKED, NONE, no receipts, and an error"
                )
        else:
            if status == "NOT_REQUESTED":
                errors.append("requested publication cannot be NOT_REQUESTED")
            if status == "BLOCKED" and (action != "NONE" or receipts or not error):
                errors.append(
                    "blocked publication requires NONE, no receipts, and an error"
                )
            if status == "PLANNED" and (
                action == "NONE" or receipts or error is not None
            ):
                errors.append(
                    "planned publication requires an action, no receipts, and no error"
                )
            if status == "PUBLISHED" and (
                action == "NONE" or not receipts or error is not None
            ):
                errors.append(
                    "published review requires an action, receipts, and no error"
                )
            if status == "PARTIAL" and (action == "NONE" or not receipts or not error):
                errors.append(
                    "partial publication requires an action, receipts, and an error"
                )
        if action == "APPROVE" and result != "APPROVE":
            errors.append("publication APPROVE action requires APPROVE decision")
        if action == "REQUEST_CHANGES" and result != "CHANGES_REQUIRED":
            errors.append("REQUEST_CHANGES action requires CHANGES_REQUIRED decision")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle = load_json(Path(args.bundle), "bundle")
        report = load_json(Path(args.report), "report")
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    errors = validate(bundle, report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAIL: {len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("PASS: remote review report is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
