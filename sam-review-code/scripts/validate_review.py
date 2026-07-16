#!/usr/bin/env python3
"""Validate a structured sam-review-code report against its review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
FILE_CLASSIFICATIONS = {
    "REVIEWED",
    "GENERATED",
    "TYPE_ONLY",
    "TEST",
    "CONFIG",
    "EXCLUDED",
}
SEVERITIES = {"BLOCKER", "IMPORTANT", "SUGGESTION"}
FINDING_STATUSES = {"ACCEPTED", "REJECTED", "FOLLOW_UP", "STOP_AND_ESCALATE"}
SCOPES = {"IN_SCOPE", "FOLLOW_UP", "STOP_AND_ESCALATE"}
TEST_LEVELS = {"UNIT", "INTEGRATION", "E2E", "CONTRACT", "MANUAL", "STATIC"}
TEST_STATUSES = {
    "COVERED",
    "MISSING_REQUIRED",
    "OPTIONAL",
    "NOT_SUPPORTED",
    "NOT_APPLICABLE",
}
VALIDATION_STATUSES = {"PASS", "FAIL", "NOT_RUN"}
VALIDATION_CLASSIFICATIONS = {
    "TARGET",
    "INTRODUCED",
    "BASELINE",
    "ENVIRONMENT",
    "EXTERNAL",
}
BEHAVIOR_STATUSES = {"PROVEN", "NOT_PROVEN", "NOT_APPLICABLE"}
DECISIONS = {"APPROVE", "CHANGES_REQUIRED", "COMMENT_ONLY", "BLOCKED"}
CONFIDENCE_LEVELS = {"LOW", "MEDIUM", "HIGH"}


class ValidationFailure(RuntimeError):
    """Report malformed input rather than a review-contract error."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a structured review report against a build_review_bundle JSON file."
    )
    parser.add_argument(
        "--bundle", required=True, help="Path to the review bundle JSON."
    )
    parser.add_argument("report", help="Path to the report JSON, or - for stdin.")
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    try:
        if path == "-":
            value = json.load(sys.stdin)
        else:
            with Path(path).open(encoding="utf-8") as handle:
                value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(f"could not read JSON {path!r}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure(f"JSON root must be an object: {path!r}")
    return value


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def text_list(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(text(item) for item in value)
    )


def integer(value: Any, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def exceeds_double(baseline: Any, current: Any) -> bool:
    if not integer(baseline) or not integer(current):
        return False
    if baseline == 0:
        return current > 0
    return current > 2 * baseline


def fingerprint(bundle: dict[str, Any]) -> str:
    payload = dict(bundle)
    payload.pop("fingerprint", None)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def line_is_changed(line: int, ranges: list[Any]) -> bool:
    for item in ranges:
        if (
            isinstance(item, list)
            and len(item) == 2
            and integer(item[0], minimum=1)
            and integer(item[1], minimum=item[0])
            and item[0] <= line <= item[1]
        ):
            return True
    return False


def validate(bundle: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if bundle.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"bundle.schema_version must be {SCHEMA_VERSION}")
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"report.schema_version must be {SCHEMA_VERSION}")

    expected_fingerprint = fingerprint(bundle)
    if bundle.get("fingerprint") != expected_fingerprint:
        errors.append("bundle fingerprint does not match bundle contents")

    bundle_target = bundle.get("target")
    report_target = report.get("target")
    if not isinstance(bundle_target, dict):
        errors.append("bundle.target must be an object")
        bundle_target = {}
    if not isinstance(report_target, dict):
        errors.append("report.target must be an object")
        report_target = {}
    for field in ("mode", "base_sha", "head_sha"):
        if report_target.get(field) != bundle_target.get(field):
            errors.append(f"report.target.{field} must match the bundle")
    if report_target.get("bundle_fingerprint") != bundle.get("fingerprint"):
        errors.append("report.target.bundle_fingerprint must match the bundle")

    intent = report.get("intent")
    if not isinstance(intent, dict):
        errors.append("intent must be an object")
        intent = {}
    for field in ("intended_behavior", "must_not_change", "invariants"):
        if not text_list(intent.get(field), allow_empty=field != "intended_behavior"):
            errors.append(f"intent.{field} must be a list of non-empty strings")
    if not text(intent.get("owner_boundary")):
        errors.append("intent.owner_boundary must be non-empty")
    if not isinstance(intent.get("user_visible_change"), bool):
        errors.append("intent.user_visible_change must be boolean")

    raw_summary = bundle.get("summary")
    summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
    scope = report.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
        scope = {}
    numeric_scope_fields = (
        "baseline_file_count",
        "baseline_non_test_lines",
        "current_file_count",
        "current_non_test_lines",
        "review_cycle",
    )
    for field in numeric_scope_fields:
        minimum = 1 if field == "review_cycle" else 0
        if not integer(scope.get(field), minimum=minimum):
            errors.append(f"scope.{field} must be an integer >= {minimum}")
    for field in ("scope_expansion_approved", "remaining_findings_reclassified"):
        if not isinstance(scope.get(field), bool):
            errors.append(f"scope.{field} must be boolean")

    bundle_file_count = summary.get("file_count")
    bundle_non_test_lines = (summary.get("non_test_added_lines") or 0) + (
        summary.get("non_test_deleted_lines") or 0
    )
    if scope.get("current_file_count") != bundle_file_count:
        errors.append("scope.current_file_count must equal bundle.summary.file_count")
    if scope.get("current_non_test_lines") != bundle_non_test_lines:
        errors.append(
            "scope.current_non_test_lines must equal bundle non-test added plus deleted lines"
        )

    bundle_files = bundle.get("files")
    if not isinstance(bundle_files, list):
        errors.append("bundle.files must be a list")
        bundle_files = []
    files_by_path: dict[str, dict[str, Any]] = {}
    for item in bundle_files:
        if isinstance(item, dict) and text(item.get("path")):
            files_by_path[item["path"]] = item

    file_coverage = report.get("file_coverage")
    if not isinstance(file_coverage, list):
        errors.append("file_coverage must be a list")
        file_coverage = []
    covered_paths: list[str] = []
    for index, item in enumerate(file_coverage):
        prefix = f"file_coverage[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        path = item.get("path")
        classification = item.get("classification")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"{prefix}.path must be non-empty")
            continue
        covered_paths.append(path)
        if classification not in FILE_CLASSIFICATIONS:
            errors.append(f"{prefix}.classification is invalid")
        if not text(item.get("reason")):
            errors.append(f"{prefix}.reason must be non-empty")
    duplicates = sorted(
        {path for path in covered_paths if covered_paths.count(path) > 1}
    )
    if duplicates:
        errors.append("file_coverage contains duplicates: " + ", ".join(duplicates))
    missing_paths = sorted(set(files_by_path) - set(covered_paths))
    extra_paths = sorted(set(covered_paths) - set(files_by_path))
    if missing_paths:
        errors.append(
            "file_coverage is missing bundle paths: " + ", ".join(missing_paths)
        )
    if extra_paths:
        errors.append(
            "file_coverage contains paths outside the bundle: " + ", ".join(extra_paths)
        )

    findings = report.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
        findings = []
    finding_ids: set[str] = set()
    accepted_blocking: set[str] = set()
    accepted_test_gaps: set[str] = set()
    stop_findings: set[str] = set()

    for index, item in enumerate(findings):
        prefix = f"findings[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        finding_id = item.get("id")
        if not isinstance(finding_id, str) or not finding_id.strip():
            errors.append(f"{prefix}.id must be non-empty")
            continue
        if finding_id in finding_ids:
            errors.append(f"duplicate finding id: {finding_id}")
        finding_ids.add(finding_id)

        severity = item.get("severity")
        status = item.get("status")
        finding_scope = item.get("scope")
        if severity not in SEVERITIES:
            errors.append(f"{prefix}.severity is invalid")
        if status not in FINDING_STATUSES:
            errors.append(f"{prefix}.status is invalid")
            continue
        if finding_scope not in SCOPES:
            errors.append(f"{prefix}.scope is invalid")
        if not isinstance(item.get("test_gap"), bool):
            errors.append(f"{prefix}.test_gap must be boolean")

        if status == "ACCEPTED":
            if finding_scope != "IN_SCOPE":
                errors.append(f"{prefix} accepted findings must be IN_SCOPE")
            path_value = item.get("path")
            path = path_value if isinstance(path_value, str) else None
            if path is None or path not in files_by_path:
                errors.append(f"{prefix}.path must identify a bundle file")
            line = item.get("line")
            ranges = (
                files_by_path.get(path, {}).get("changed_lines") or []
                if path is not None
                else []
            )
            if ranges and line is None:
                errors.append(
                    f"{prefix}.line is required when the file has changed lines"
                )
            if line is not None and not integer(line, minimum=1):
                errors.append(f"{prefix}.line must be null or an integer >= 1")
            elif (
                path in files_by_path
                and isinstance(line, int)
                and not isinstance(line, bool)
                and line >= 1
            ):
                if ranges and not line_is_changed(line, ranges):
                    errors.append(f"{prefix}.line must identify a changed line")
            for field in ("failure_mode", "impact", "required_change"):
                if not text(item.get(field)):
                    errors.append(f"{prefix}.{field} must be non-empty")
            if not text_list(item.get("evidence"), allow_empty=False):
                errors.append(f"{prefix}.evidence must contain at least one item")
            if severity in {"BLOCKER", "IMPORTANT"}:
                accepted_blocking.add(finding_id)
            if item.get("test_gap"):
                if severity != "BLOCKER":
                    errors.append(f"{prefix} required test gaps must be BLOCKER")
                accepted_test_gaps.add(finding_id)
        elif status == "REJECTED":
            if not text(item.get("rejection_reason")):
                errors.append(f"{prefix}.rejection_reason is required for REJECTED")
        elif status == "FOLLOW_UP":
            if finding_scope != "FOLLOW_UP":
                errors.append(f"{prefix} FOLLOW_UP status requires FOLLOW_UP scope")
            if not text(item.get("required_change")):
                errors.append(
                    f"{prefix}.required_change must explain the follow-up boundary"
                )
        elif status == "STOP_AND_ESCALATE":
            stop_findings.add(finding_id)
            if finding_scope != "STOP_AND_ESCALATE":
                errors.append(
                    f"{prefix} STOP_AND_ESCALATE status requires STOP_AND_ESCALATE scope"
                )
            if not text(item.get("required_change")):
                errors.append(
                    f"{prefix}.required_change must name the required decision"
                )

    test_coverage = report.get("test_coverage")
    if not isinstance(test_coverage, list):
        errors.append("test_coverage must be a list")
        test_coverage = []
    elif not test_coverage:
        errors.append(
            "test_coverage must contain at least one scenario or NOT_APPLICABLE entry"
        )
    referenced_test_gaps: set[str] = set()
    for index, item in enumerate(test_coverage):
        prefix = f"test_coverage[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not text(item.get("behavior")):
            errors.append(f"{prefix}.behavior must be non-empty")
        if item.get("level") not in TEST_LEVELS:
            errors.append(f"{prefix}.level is invalid")
        status = item.get("status")
        if status not in TEST_STATUSES:
            errors.append(f"{prefix}.status is invalid")
        if not isinstance(item.get("paths"), list) or not all(
            text(path) for path in item.get("paths", [])
        ):
            errors.append(f"{prefix}.paths must be a list of non-empty strings")
        if not text(item.get("reason")):
            errors.append(f"{prefix}.reason must be non-empty")
        if status == "MISSING_REQUIRED":
            finding_id = item.get("finding_id")
            if finding_id not in accepted_test_gaps:
                errors.append(
                    f"{prefix}.finding_id must reference an accepted BLOCKER test gap"
                )
            else:
                referenced_test_gaps.add(finding_id)
    unreferenced_gaps = sorted(accepted_test_gaps - referenced_test_gaps)
    if unreferenced_gaps:
        errors.append(
            "accepted test-gap findings missing from test_coverage: "
            + ", ".join(unreferenced_gaps)
        )

    validations = report.get("validations")
    if not isinstance(validations, list):
        errors.append("validations must be a list")
        validations = []
    elif not validations:
        errors.append(
            "validations must contain at least one PASS, FAIL, or NOT_RUN entry"
        )
    introduced_validation_failure = False
    for index, item in enumerate(validations):
        prefix = f"validations[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not text(item.get("command")):
            errors.append(f"{prefix}.command must be non-empty")
        if item.get("status") not in VALIDATION_STATUSES:
            errors.append(f"{prefix}.status is invalid")
        if item.get("classification") not in VALIDATION_CLASSIFICATIONS:
            errors.append(f"{prefix}.classification is invalid")
        if not text(item.get("reason")):
            errors.append(f"{prefix}.reason must be non-empty")
        if item.get("status") == "FAIL" and item.get("classification") == "INTRODUCED":
            introduced_validation_failure = True

    behavior = report.get("behavior_proof")
    if not isinstance(behavior, dict):
        errors.append("behavior_proof must be an object")
        behavior = {}
    behavior_status = behavior.get("status")
    if behavior_status not in BEHAVIOR_STATUSES:
        errors.append("behavior_proof.status is invalid")
    if not text_list(behavior.get("evidence")):
        errors.append("behavior_proof.evidence must be a list of non-empty strings")
    if behavior_status in {"PROVEN", "NOT_PROVEN"} and not behavior.get("evidence"):
        errors.append(
            "behavior_proof.evidence is required when behavior is PROVEN or NOT_PROVEN"
        )
    if (
        intent.get("user_visible_change") is True
        and behavior_status == "NOT_APPLICABLE"
    ):
        errors.append("user-visible changes cannot use NOT_APPLICABLE behavior proof")

    decision = report.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
        decision = {}
    result = decision.get("result")
    if result not in DECISIONS:
        errors.append("decision.result is invalid")
    if decision.get("confidence") not in CONFIDENCE_LEVELS:
        errors.append("decision.confidence is invalid")
    if not isinstance(decision.get("non_gating_requested"), bool):
        errors.append("decision.non_gating_requested must be boolean")
    raw_remaining = decision.get("remaining_corrections")
    if not text_list(raw_remaining):
        errors.append(
            "decision.remaining_corrections must be a list of non-empty strings"
        )
        remaining: list[str] = []
    else:
        remaining = (
            [item for item in raw_remaining if isinstance(item, str)]
            if isinstance(raw_remaining, list)
            else []
        )

    file_expanded = exceeds_double(
        scope.get("baseline_file_count"), scope.get("current_file_count")
    )
    line_expanded = exceeds_double(
        scope.get("baseline_non_test_lines"), scope.get("current_non_test_lines")
    )
    scope_blocked = bool(
        (file_expanded or line_expanded) and not scope.get("scope_expansion_approved")
    )
    cycle_blocked = bool(
        integer(scope.get("review_cycle"), minimum=1)
        and scope.get("review_cycle", 1) > 2
        and not scope.get("remaining_findings_reclassified")
    )

    required_remaining = accepted_blocking | stop_findings
    if result == "APPROVE":
        if accepted_blocking:
            errors.append(
                "APPROVE is invalid while accepted BLOCKER or IMPORTANT findings remain"
            )
        if stop_findings or scope_blocked or cycle_blocked:
            errors.append(
                "APPROVE is invalid while scope or escalation blockers remain"
            )
        if intent.get("user_visible_change") is True and behavior_status != "PROVEN":
            errors.append("APPROVE requires PROVEN behavior for a user-visible change")
        if introduced_validation_failure:
            errors.append(
                "APPROVE is invalid while an introduced validation failure remains"
            )
        if remaining:
            errors.append("APPROVE requires an empty remaining_corrections list")
    elif result == "CHANGES_REQUIRED":
        if not accepted_blocking:
            errors.append(
                "CHANGES_REQUIRED requires an accepted BLOCKER or IMPORTANT finding"
            )
    elif result == "BLOCKED":
        if not (stop_findings or scope_blocked or cycle_blocked):
            errors.append(
                "BLOCKED requires a scope, convergence, or stop-and-escalate condition"
            )
    elif result == "COMMENT_ONLY" and decision.get("non_gating_requested") is not True:
        errors.append("COMMENT_ONLY requires decision.non_gating_requested=true")

    if introduced_validation_failure and not accepted_blocking:
        errors.append(
            "each introduced validation failure must map to an accepted BLOCKER or IMPORTANT finding"
        )

    missing_remaining = sorted(required_remaining - set(remaining))
    if missing_remaining:
        errors.append(
            "decision.remaining_corrections is missing finding IDs: "
            + ", ".join(missing_remaining)
        )

    return errors


def main() -> int:
    args = parse_args()
    try:
        bundle = load_json(args.bundle)
        report = load_json(args.report)
    except ValidationFailure as failure:
        print(f"validate_review: {failure}", file=sys.stderr)
        return 2

    errors = validate(bundle, report)
    if errors:
        print("INVALID REVIEW REPORT", file=sys.stderr)
        for message in errors:
            print(f"- {message}", file=sys.stderr)
        return 1
    print("VALID REVIEW REPORT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
