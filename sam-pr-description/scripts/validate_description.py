#!/usr/bin/env python3
"""Validate a proposal description and its evidence against immutable context."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

CHANGE_TYPES = {"BUG_FIX", "NEW_FEATURE", "REFACTOR", "DOCUMENTATION", "OTHER"}
CHANGE_LABELS = {
    "BUG_FIX": "Bug fix",
    "NEW_FEATURE": "New feature",
    "REFACTOR": "Refactor",
    "DOCUMENTATION": "Documentation",
    "OTHER": "Other",
}
EVIDENCE_TYPES = {"DIFF", "FILE", "COMMIT", "VALIDATION", "USER", "REMOTE"}
EVIDENCE_STATUSES = {"PASS", "FAIL", "NOT_RUN", "INFO"}
CLAIM_CATEGORIES = {
    "SCOPE",
    "IMPLEMENTATION",
    "TEST",
    "SAFETY",
    "ARCHITECTURE",
    "BUSINESS_RULE",
    "REFERENCE",
}
REMOTE_STATUSES = {"NOT_REQUESTED", "PLANNED", "UPDATED", "PARTIAL", "BLOCKED"}
REQUIRED_HEADINGS = [
    "Description",
    "Type of Change",
    "Scope",
    "Behavior and Business Rules",
    "What Was Done",
    "Architecture and Trade-offs",
    "Safety and Risks",
    "Validation",
    "Tests",
    "Author Checklist",
    "Notes for Reviewer",
]
PLACEHOLDER_RE = re.compile(
    r"<!--|-->|\b(?:TODO|TBD)\b|_{4,}|<specific type>|<module or path>|<command>",
    re.IGNORECASE,
)
SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def fingerprint(value: dict[str, Any]) -> str:
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


def validate_context(
    context: dict[str, Any], errors: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    require_keys(
        context,
        {
            "schema_version",
            "target",
            "commits",
            "reference_candidates",
            "files",
            "patch",
            "patch_sha256",
            "context_fingerprint",
        },
        {
            "schema_version",
            "target",
            "commits",
            "reference_candidates",
            "files",
            "patch",
            "patch_sha256",
            "context_fingerprint",
        },
        "context",
        errors,
    )
    if context.get("schema_version") != 1:
        errors.append("context.schema_version must be 1")
    value = copy.deepcopy(context)
    recorded = value.pop("context_fingerprint", None)
    if recorded != fingerprint(value):
        errors.append("context fingerprint does not match context content")
    patch = context.get("patch")
    if not isinstance(patch, str):
        errors.append("context.patch must be a string")
    elif (
        context.get("patch_sha256") != hashlib.sha256(patch.encode("utf-8")).hexdigest()
    ):
        errors.append("context patch_sha256 does not match patch content")
    target = context.get("target")
    if not isinstance(target, dict):
        errors.append("context.target must be an object")
        target = {}
    require_keys(
        target,
        {
            "base_ref",
            "head_ref",
            "requested_base_sha",
            "base_sha",
            "head_sha",
            "comparison",
        },
        {
            "base_ref",
            "head_ref",
            "requested_base_sha",
            "base_sha",
            "head_sha",
            "comparison",
        },
        "context.target",
        errors,
    )
    for key in ("base_ref", "head_ref"):
        nonempty_string(target.get(key), f"context.target.{key}", errors)
    for key in ("requested_base_sha", "base_sha", "head_sha"):
        sha_value = nonempty_string(target.get(key), f"context.target.{key}", errors)
        if sha_value and not SHA_RE.fullmatch(sha_value):
            errors.append(f"context.target.{key} must be a full Git object ID")
    if target.get("comparison") not in {"direct", "merge-base"}:
        errors.append("context.target.comparison must be direct or merge-base")
    files = object_list(context.get("files"), "context.files", errors)
    commits = object_list(context.get("commits"), "context.commits", errors)
    if not files:
        errors.append("context.files must not be empty")
    if not commits:
        errors.append("context.commits must not be empty")
    for index, commit in enumerate(commits):
        require_keys(
            commit,
            {"sha", "subject"},
            {"sha", "subject"},
            f"context.commits[{index}]",
            errors,
        )
        sha = nonempty_string(
            commit.get("sha"), f"context.commits[{index}].sha", errors
        )
        if sha and not SHA_RE.fullmatch(sha):
            errors.append(f"context.commits[{index}].sha must be a full Git object ID")
        nonempty_string(
            commit.get("subject"), f"context.commits[{index}].subject", errors
        )
    return target, files, commits


def validate(context: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    context_target, context_files, context_commits = validate_context(context, errors)
    require_keys(
        report,
        {
            "schema_version",
            "target",
            "language",
            "change_types",
            "file_coverage",
            "evidence",
            "claims",
            "body",
            "remote_update",
        },
        {
            "schema_version",
            "target",
            "language",
            "change_types",
            "file_coverage",
            "evidence",
            "claims",
            "body",
            "remote_update",
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
        {"base_sha", "head_sha", "context_fingerprint"},
        {"base_sha", "head_sha", "context_fingerprint"},
        "report.target",
        errors,
    )
    for key in ("base_sha", "head_sha"):
        if target.get(key) != context_target.get(key):
            errors.append(f"report.target.{key} does not match context")
    if target.get("context_fingerprint") != context.get("context_fingerprint"):
        errors.append("report.target.context_fingerprint does not match context")
    nonempty_string(report.get("language"), "language", errors)

    change_types = string_list(
        report.get("change_types"), "change_types", errors, nonempty=True
    )
    invalid_types = sorted(set(change_types) - CHANGE_TYPES)
    if invalid_types:
        errors.append(f"change_types has invalid values: {', '.join(invalid_types)}")
    if len(set(change_types)) != len(change_types):
        errors.append("change_types must not contain duplicates")

    context_paths: list[str] = []
    for index, item in enumerate(context_files):
        path = item.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"context.files[{index}].path must be a non-empty string")
        else:
            context_paths.append(path)
    context_path_set = set(context_paths)
    coverage = object_list(report.get("file_coverage"), "file_coverage", errors)
    covered_paths: list[str] = []
    for index, item in enumerate(coverage):
        label = f"file_coverage[{index}]"
        require_keys(
            item,
            {"path", "section", "summary"},
            {"path", "section", "summary"},
            label,
            errors,
        )
        path = nonempty_string(item.get("path"), f"{label}.path", errors)
        section = nonempty_string(item.get("section"), f"{label}.section", errors)
        summary = nonempty_string(item.get("summary"), f"{label}.summary", errors)
        if path:
            covered_paths.append(path)
        if section and section not in REQUIRED_HEADINGS:
            errors.append(f"{label}.section must name a required body heading")
        if path and path not in context_path_set:
            errors.append(f"{label}.path is not in context")
        body_value = report.get("body")
        if isinstance(body_value, str):
            if path and path not in body_value:
                errors.append(f"{label}.path is not represented in body")
            if summary and summary not in body_value:
                errors.append(f"{label}.summary is not represented in body")
    duplicates = sorted(
        {path for path in covered_paths if covered_paths.count(path) > 1}
    )
    if duplicates:
        errors.append(f"file_coverage contains duplicates: {', '.join(duplicates)}")
    if set(covered_paths) != context_path_set:
        missing = sorted(context_path_set - set(covered_paths))
        extra = sorted(set(covered_paths) - context_path_set)
        if missing:
            errors.append(f"file_coverage missing paths: {', '.join(missing)}")
        if extra:
            errors.append(f"file_coverage has unknown paths: {', '.join(extra)}")

    commit_shas = {
        item.get("sha") for item in context_commits if isinstance(item.get("sha"), str)
    }
    evidence = object_list(report.get("evidence"), "evidence", errors)
    evidence_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(evidence):
        label = f"evidence[{index}]"
        require_keys(
            item,
            {"id", "type", "reference", "status", "detail"},
            {"id", "type", "reference", "status", "detail"},
            label,
            errors,
        )
        evidence_id = nonempty_string(item.get("id"), f"{label}.id", errors)
        if evidence_id in evidence_by_id:
            errors.append(f"duplicate evidence id: {evidence_id}")
        elif evidence_id:
            evidence_by_id[evidence_id] = item
        evidence_type = item.get("type")
        if evidence_type not in EVIDENCE_TYPES:
            errors.append(f"{label}.type is invalid")
        reference = nonempty_string(item.get("reference"), f"{label}.reference", errors)
        if item.get("status") not in EVIDENCE_STATUSES:
            errors.append(f"{label}.status is invalid")
        if evidence_type == "VALIDATION" and item.get("status") == "INFO":
            errors.append(f"{label} VALIDATION must be PASS, FAIL, or NOT_RUN")
        if evidence_type != "VALIDATION" and item.get("status") != "INFO":
            errors.append(f"{label} non-validation evidence must use INFO status")
        if evidence_type in {"DIFF", "FILE"} and reference not in context_path_set:
            errors.append(f"{label}.reference must be a changed path")
        if evidence_type == "COMMIT" and reference not in commit_shas:
            errors.append(f"{label}.reference must be a context commit SHA")
        nonempty_string(item.get("detail"), f"{label}.detail", errors)

    body = nonempty_string(report.get("body"), "body", errors)
    if body.startswith("```") or body.rstrip().endswith("```"):
        errors.append("body must be raw Markdown without an outer code fence")
    placeholder = PLACEHOLDER_RE.search(body)
    if placeholder:
        errors.append(
            f"body contains placeholder or template marker: {placeholder.group(0)}"
        )
    headings = re.findall(r"^## ([^\n]+)$", body, flags=re.MULTILINE)
    if headings != REQUIRED_HEADINGS:
        errors.append("body headings must appear exactly once in the required order")

    marked_labels = {
        match.group(1).strip()
        for match in re.finditer(
            r"^- \[[xX]\] ([^\n:]+)(?::[^\n]*)?$", body, flags=re.MULTILINE
        )
        if match.group(1).strip() in set(CHANGE_LABELS.values())
    }
    expected_labels = {
        CHANGE_LABELS[item] for item in change_types if item in CHANGE_LABELS
    }
    if marked_labels != expected_labels:
        errors.append("checked Type of Change boxes must match change_types")
    if "OTHER" in change_types and re.search(
        r"^- \[[xX]\] Other:\s*(?:$|Not applicable$)", body, re.MULTILINE
    ):
        errors.append("checked Other type requires a specific value")

    claims = object_list(report.get("claims"), "claims", errors)
    if not claims:
        errors.append("claims must contain at least one evidence-backed statement")
    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        label = f"claims[{index}]"
        require_keys(
            claim,
            {"id", "category", "text", "evidence_ids"},
            {"id", "category", "text", "evidence_ids"},
            label,
            errors,
        )
        claim_id = nonempty_string(claim.get("id"), f"{label}.id", errors)
        if claim_id in claim_ids:
            errors.append(f"duplicate claim id: {claim_id}")
        claim_ids.add(claim_id)
        if claim.get("category") not in CLAIM_CATEGORIES:
            errors.append(f"{label}.category is invalid")
        text = nonempty_string(claim.get("text"), f"{label}.text", errors)
        if text and text not in body:
            errors.append(f"{label}.text is not present verbatim in body")
        evidence_ids = string_list(
            claim.get("evidence_ids"), f"{label}.evidence_ids", errors, nonempty=True
        )
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_by_id:
                errors.append(f"{label} references unknown evidence {evidence_id}")

    remote = report.get("remote_update")
    if not isinstance(remote, dict):
        errors.append("remote_update must be an object")
        remote = {}
    require_keys(
        remote,
        {
            "requested",
            "expected_head_sha",
            "observed_head_sha",
            "status",
            "receipts",
            "error",
        },
        {
            "requested",
            "expected_head_sha",
            "observed_head_sha",
            "status",
            "receipts",
            "error",
        },
        "remote_update",
        errors,
    )
    requested = remote.get("requested")
    if not isinstance(requested, bool):
        errors.append("remote_update.requested must be boolean")
    if remote.get("expected_head_sha") != context_target.get("head_sha"):
        errors.append("remote_update.expected_head_sha must match context head")
    observed = nonempty_string(
        remote.get("observed_head_sha"), "remote_update.observed_head_sha", errors
    )
    status = remote.get("status")
    if status not in REMOTE_STATUSES:
        errors.append("remote_update.status is invalid")
    receipts = object_list(remote.get("receipts"), "remote_update.receipts", errors)
    for index, receipt in enumerate(receipts):
        label = f"remote_update.receipts[{index}]"
        require_keys(
            receipt,
            {"kind", "id", "url", "status"},
            {"kind", "id", "url", "status"},
            label,
            errors,
        )
        for key in ("kind", "id", "url", "status"):
            nonempty_string(receipt.get(key), f"{label}.{key}", errors)
    error = remote.get("error")
    if error is not None and (not isinstance(error, str) or not error):
        errors.append("remote_update.error must be null or a non-empty string")
    drifted = bool(observed and observed != context_target.get("head_sha"))
    if requested is False:
        if status != "NOT_REQUESTED" or receipts or error is not None:
            errors.append(
                "local draft must use NOT_REQUESTED with no receipts or error"
            )
    elif requested is True:
        if drifted:
            if status != "BLOCKED" or receipts or not error:
                errors.append(
                    "head drift must block the update with no receipts and an error"
                )
        else:
            if status == "NOT_REQUESTED":
                errors.append("requested update cannot be NOT_REQUESTED")
            if status == "PLANNED" and (receipts or error is not None):
                errors.append("planned update must have no receipts or error")
            if status == "UPDATED" and (not receipts or error is not None):
                errors.append("updated description requires receipts and no error")
            if status == "PARTIAL" and (not receipts or not error):
                errors.append("partial update requires receipts and an error")
            if status == "BLOCKED" and (receipts or not error):
                errors.append("blocked update requires no receipts and an error")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        context = load_json(Path(args.context), "context")
        report = load_json(Path(args.report), "report")
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    errors = validate(context, report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAIL: {len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("PASS: proposal description and evidence are internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
