#!/usr/bin/env python3
"""Validate a sam-task orchestration report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PHASE_IDS = ["plan", "refine", "work", "closure"]
PHASE_SKILLS = {
    "plan": "sam-plan",
    "refine": "sam-refine-task",
    "work": "sam-work",
    "closure": "sam-review+sam-council",
}
PHASE_TERMINALS = {
    "plan": {"READY_TO_EXECUTE"},
    "refine": {"HIGH_CONFIDENCE"},
    "work": {"COMPLETE"},
    "closure": {"CLEAN"},
}
PHASE_ITERATION_STATUSES = {
    "plan": {"READY_TO_EXECUTE", "NOT_CONFIDENT", "BLOCKED"},
    "refine": {"HIGH_CONFIDENCE", "NOT_CONFIDENT", "BLOCKED"},
    "work": {"COMPLETE", "BLOCKED", "IN_PROGRESS"},
    "closure": {"CLEAN", "OPEN", "BLOCKED"},
}
WORKFLOW_STATUSES = {"COMPLETE", "BLOCKED", "IN_PROGRESS"}
CLASSIFICATIONS = {"BUG", "FEATURE"}
DEPTHS = {"simple", "standard", "deep"}
COUNCIL_PASS = {"TRIAGE_PASS", "APPROVED", "APPROVED_WITH_CONDITIONS"}
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
    if status not in PHASE_ITERATION_STATUSES[phase_id]:
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
    if open_items and not corrections and not is_last:
        errors.append(f"{prefix} with open items requires correction receipts")
    if is_last:
        if open_items and status in PHASE_TERMINALS[phase_id]:
            errors.append(f"{prefix} cannot finish terminal with open items")
        if status not in PHASE_TERMINALS[phase_id] and status not in {
            "BLOCKED",
            "IN_PROGRESS",
            "OPEN",
            "NOT_CONFIDENT",
        }:
            errors.append(f"{prefix} has unexpected terminal status")


def validate_phase(
    phase: Any,
    expected_id: str,
    final_head: Any,
    workflow_status: str,
    errors: list[str],
) -> None:
    prefix = f"phase {expected_id}"
    if not isinstance(phase, dict):
        errors.append(f"{prefix} must be an object")
        return
    if phase.get("id") != expected_id:
        errors.append(f"{prefix} is missing or out of order")
    if phase.get("skill") != PHASE_SKILLS[expected_id]:
        errors.append(f"{prefix} must use {PHASE_SKILLS[expected_id]}")

    status = phase.get("status")
    if not nonempty_string(status):
        errors.append(f"{prefix} status is required")

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

    head = phase.get("validated_head_sha")
    if expected_id in {"plan", "refine"}:
        if head is not None and not REVISION.fullmatch(str(head)):
            errors.append(f"{prefix} validated_head_sha must be null or a revision")
    else:
        if workflow_status == "COMPLETE":
            if phase.get("current") is not True:
                errors.append(f"{prefix} proof must be current for COMPLETE")
            if head != final_head:
                errors.append(f"{prefix} proof is stale for the final head")
            if status not in PHASE_TERMINALS[expected_id]:
                errors.append(f"{prefix} lacks accepted terminal for COMPLETE")
        elif head is not None and not REVISION.fullmatch(str(head)):
            errors.append(f"{prefix} validated_head_sha must be a revision")

    if workflow_status == "COMPLETE" and expected_id in {"plan", "refine"}:
        if status not in PHASE_TERMINALS[expected_id]:
            errors.append(f"{prefix} lacks accepted terminal for COMPLETE")
        if phase.get("current") is not True:
            errors.append(f"{prefix} must be marked current for COMPLETE")


def validate_closure(closure: Any, final_head: Any, workflow_status: str, errors: list[str]) -> None:
    if not isinstance(closure, dict):
        errors.append("closure object is required")
        return
    max_iterations = closure.get("max_iterations")
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool) or max_iterations < 1:
        errors.append("closure.max_iterations must be a positive integer")
    used = closure.get("iterations_used")
    if not isinstance(used, int) or isinstance(used, bool) or used < 0:
        errors.append("closure.iterations_used must be a non-negative integer")
    final_status = closure.get("final_status")
    if final_status not in {"CLEAN", "OPEN", "BLOCKED"}:
        errors.append("closure.final_status is invalid")

    iterations = closure.get("iterations")
    if not isinstance(iterations, list):
        errors.append("closure.iterations must be an array")
        return
    if used != len(iterations):
        errors.append("closure.iterations_used must equal iterations length")
    if isinstance(max_iterations, int) and used > max_iterations:
        errors.append("closure exceeded max_iterations")

    for index, item in enumerate(iterations, start=1):
        prefix = f"closure iteration {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if item.get("sequence") != index:
            errors.append(f"{prefix} sequence must be contiguous from one")
        if not REVISION.fullmatch(str(item.get("head_sha", ""))):
            errors.append(f"{prefix} head_sha must be a revision")
        review_status = item.get("review_status")
        if review_status not in {
            "APPROVE",
            "CHANGES_REQUIRED",
            "COMMENT_ONLY",
            "BLOCKED",
        }:
            errors.append(f"{prefix} review_status is invalid")
        council_status = item.get("council_status")
        if not nonempty_string(council_status):
            errors.append(f"{prefix} council_status is required")
        if not nonempty_string(item.get("council_profile")):
            errors.append(f"{prefix} council_profile is required")
        if not string_list(item.get("open_findings")):
            errors.append(f"{prefix} open_findings must be a string array")
        if not string_list(item.get("correction_receipts")):
            errors.append(f"{prefix} correction_receipts must be a string array")
        if not nonempty_string(item.get("review_receipt")):
            errors.append(f"{prefix} review_receipt is required")
        if not nonempty_string(item.get("council_receipt")):
            errors.append(f"{prefix} council_receipt is required")
        if not string_list(item.get("evidence"), nonempty=True):
            errors.append(f"{prefix} requires evidence")

        open_findings = item.get("open_findings") if isinstance(item.get("open_findings"), list) else []
        corrections = (
            item.get("correction_receipts")
            if isinstance(item.get("correction_receipts"), list)
            else []
        )
        is_last = index == len(iterations)
        if open_findings and not corrections and not is_last:
            errors.append(f"{prefix} with open findings requires correction receipts")
        if is_last and workflow_status == "COMPLETE":
            if open_findings:
                errors.append("final closure iteration cannot have open findings for COMPLETE")
            if review_status != "APPROVE":
                errors.append("final closure review_status must be APPROVE for COMPLETE")
            if council_status not in COUNCIL_PASS:
                errors.append(
                    "final closure council_status must be an accepted pass status for COMPLETE"
                )
            if item.get("head_sha") != final_head:
                errors.append("final closure head_sha must match target.final_head_sha")

    if workflow_status == "COMPLETE":
        if final_status != "CLEAN":
            errors.append("COMPLETE requires closure.final_status CLEAN")
        if not iterations:
            errors.append("COMPLETE requires at least one closure iteration")
    if workflow_status == "BLOCKED" and final_status == "CLEAN" and not iterations:
        errors.append("BLOCKED report cannot claim CLEAN closure without iterations")


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if report.get("workflow") != "task":
        errors.append("workflow must be 'task'")
    if not nonempty_string(report.get("workflow_id")):
        errors.append("workflow_id is required")

    status = report.get("status")
    if status not in WORKFLOW_STATUSES:
        errors.append("status must be COMPLETE, BLOCKED, or IN_PROGRESS")

    request = report.get("request")
    if not isinstance(request, dict):
        errors.append("request must be an object")
        request = {}
    if not HEX64.fullmatch(str(request.get("prompt_sha256", ""))):
        errors.append("request.prompt_sha256 must be 64 lowercase hex characters")
    if not nonempty_string(request.get("prompt_summary")):
        errors.append("request.prompt_summary is required")
    classification = request.get("classification")
    if classification not in CLASSIFICATIONS:
        errors.append("request.classification must be BUG or FEATURE")

    target = report.get("target")
    if not isinstance(target, dict):
        errors.append("target must be an object")
        target = {}
    if not nonempty_string(target.get("repo_root")) or not Path(
        str(target.get("repo_root", ""))
    ).is_absolute():
        errors.append("target.repo_root must be an absolute path")
    if not nonempty_string(target.get("base_ref")):
        errors.append("target.base_ref is required")
    for field in ("base_sha", "final_head_sha"):
        if not REVISION.fullmatch(str(target.get(field, ""))):
            errors.append(f"target.{field} must be a revision")
    if not HEX64.fullmatch(str(target.get("final_change_fingerprint", ""))):
        errors.append("target.final_change_fingerprint must be 64 lowercase hex")

    plan = report.get("plan")
    if not isinstance(plan, dict):
        errors.append("plan summary object is required")
        plan = {}
    else:
        if not nonempty_string(plan.get("plan_dir")) or not Path(
            str(plan.get("plan_dir", ""))
        ).is_absolute():
            errors.append("plan.plan_dir must be an absolute path")
        if plan.get("depth") not in DEPTHS:
            errors.append("plan.depth is invalid")
        if plan.get("status") != "READY_TO_EXECUTE" and status == "COMPLETE":
            errors.append("COMPLETE requires plan.status READY_TO_EXECUTE")
        if not nonempty_string(plan.get("validator_receipt")):
            errors.append("plan.validator_receipt is required")

    phases = report.get("phases")
    if not isinstance(phases, list) or len(phases) != len(PHASE_IDS):
        errors.append("phases must contain exactly plan, refine, work, closure")
        phases = []
    final_head = target.get("final_head_sha")
    for expected_id, phase in zip(PHASE_IDS, phases):
        validate_phase(phase, expected_id, final_head, str(status), errors)
    if phases and [p.get("id") for p in phases if isinstance(p, dict)] != PHASE_IDS:
        errors.append("phases must be ordered plan, refine, work, closure")

    validate_closure(report.get("closure"), final_head, str(status), errors)

    work_path = report.get("work_report_path")
    if status == "COMPLETE":
        if not nonempty_string(work_path) or not Path(str(work_path)).is_absolute():
            errors.append("COMPLETE requires absolute work_report_path")
    elif work_path is not None and work_path != "" and (
        not nonempty_string(work_path) or not Path(str(work_path)).is_absolute()
    ):
        errors.append("work_report_path must be absolute when present")

    if not string_list(report.get("residuals")):
        errors.append("residuals must be a string array")
    if not string_list(report.get("blockers")):
        errors.append("blockers must be a string array")

    if status == "COMPLETE":
        if report.get("blockers"):
            errors.append("COMPLETE forbids non-empty blockers")
    elif status == "BLOCKED":
        residuals = report.get("residuals") if isinstance(report.get("residuals"), list) else []
        blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
        if not residuals and not blockers:
            errors.append("BLOCKED requires residuals or blockers")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to task-report.json")
    args = parser.parse_args()
    try:
        report = load_json(args.report)
    except ValueError as error:
        print(f"INVALID\n{error}")
        return 2
    errors = validate(report)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
