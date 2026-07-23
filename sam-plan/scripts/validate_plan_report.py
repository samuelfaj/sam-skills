#!/usr/bin/env python3
"""Validate sam-plan plan-report.json against the output contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]
STATUSES = {"READY_TO_EXECUTE", "NOT_CONFIDENT", "BLOCKED"}
DEPTHS = {"simple", "standard", "deep"}
CASE_TYPES = {"BUG", "FEATURE", "PRODUCT", "MIGRATION", "OPS", "SPIKE"}
CLASSIFICATIONS = {"FACT", "ASSUMPTION", "UNKNOWN"}
PROOF_STATUSES = {"PASS", "PLANNED", "NOT_RUN", "BLOCKED", "NOT_APPLICABLE"}
ID_PATTERNS = {
    "evidence": re.compile(r"^E-\d{3,}$"),
    "assumptions": re.compile(r"^A-\d{3,}$"),
    "unknowns": re.compile(r"^U-\d{3,}$"),
    "steps": re.compile(r"^S-\d{3,}$"),
    "risks": re.compile(r"^R-\d{3,}$"),
    "verifications": re.compile(r"^V-\d{3,}$"),
    "thesis": re.compile(r"^T-\d{3,}$"),
}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHAPTER_ID_RE = re.compile(r"^\d{2}$")


def load_json(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def mapping(value: Any, label: str, errors: list[str]) -> JsonObject:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    return value


def sequence(value: Any, label: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    return value


def nonempty_text(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be non-empty text")
        return ""
    return value.strip()


def string_list(
    value: Any, label: str, errors: list[str], *, allow_empty: bool = True
) -> list[str]:
    items = sequence(value, label, errors)
    if not all(isinstance(item, str) and item.strip() for item in items):
        errors.append(f"{label} must contain only non-empty strings")
        return []
    result = [item.strip() for item in items]
    if not allow_empty and not result:
        errors.append(f"{label} must not be empty")
    if len(result) != len(set(result)):
        errors.append(f"{label} must not contain duplicates")
    return result


def unique_ids(
    items: list[JsonObject], key: str, pattern: re.Pattern[str], label: str, errors: list[str]
) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_id = nonempty_text(item.get("id"), f"{label}[{index}].id", errors)
        if not item_id:
            continue
        if not pattern.fullmatch(item_id):
            errors.append(f"{label}[{index}].id must match {pattern.pattern}")
        if item_id in seen:
            errors.append(f"{label} repeats id {item_id}")
        seen.add(item_id)
    return seen


def validate_blocks(blocks: list[Any], label: str, errors: list[str]) -> None:
    for index, raw in enumerate(blocks):
        block = mapping(raw, f"{label}[{index}]", errors)
        if not block:
            continue
        block_type = nonempty_text(block.get("type"), f"{label}[{index}].type", errors)
        if block_type in {"paragraph", "callout", "code", "list"}:
            if block_type == "list":
                items = sequence(block.get("items"), f"{label}[{index}].items", errors)
                if not items:
                    errors.append(f"{label}[{index}].items must not be empty")
                else:
                    for item_index, item in enumerate(items):
                        nonempty_text(
                            item, f"{label}[{index}].items[{item_index}]", errors
                        )
            else:
                nonempty_text(block.get("text"), f"{label}[{index}].text", errors)
            if block_type == "callout":
                tone = block.get("tone", "info")
                if tone not in {"info", "ok", "warn", "danger", "decision"}:
                    errors.append(f"{label}[{index}].tone is invalid")
        elif block_type == "table":
            headers = string_list(
                block.get("headers"), f"{label}[{index}].headers", errors, allow_empty=False
            )
            rows = sequence(block.get("rows"), f"{label}[{index}].rows", errors)
            for row_index, row in enumerate(rows):
                if not isinstance(row, list) or not all(
                    isinstance(cell, str) for cell in row
                ):
                    errors.append(
                        f"{label}[{index}].rows[{row_index}] must be a string array"
                    )
                    continue
                if headers and len(row) != len(headers):
                    errors.append(
                        f"{label}[{index}].rows[{row_index}] length must match headers"
                    )
        else:
            if block_type:
                errors.append(f"{label}[{index}].type is unsupported: {block_type}")


def validate_report(report: JsonObject, *, require_html: bool, report_path: Path) -> list[str]:
    errors: list[str] = []

    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if report.get("workflow") != "plan":
        errors.append("workflow must be 'plan'")

    status = nonempty_text(report.get("status"), "status", errors)
    if status and status not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")

    depth = nonempty_text(report.get("depth"), "depth", errors)
    if depth and depth not in DEPTHS:
        errors.append(f"depth must be one of {sorted(DEPTHS)}")

    case_type = nonempty_text(report.get("case_type"), "case_type", errors)
    if case_type and case_type not in CASE_TYPES:
        errors.append(f"case_type must be one of {sorted(CASE_TYPES)}")

    nonempty_text(report.get("complexity_rationale"), "complexity_rationale", errors)

    frozen = mapping(report.get("frozen"), "frozen", errors)
    for key in (
        "prompt_hash",
        "prompt_summary",
        "goal",
    ):
        nonempty_text(frozen.get(key), f"frozen.{key}", errors)
    for key in (
        "non_goals",
        "success_criteria",
        "invariants",
        "constraints",
        "no_go",
    ):
        string_list(frozen.get(key), f"frozen.{key}", errors, allow_empty=True)

    output = mapping(report.get("output"), "output", errors)
    plan_dir = nonempty_text(output.get("plan_dir"), "output.plan_dir", errors)
    html_files = string_list(
        output.get("html_files"), "output.html_files", errors, allow_empty=False
    )
    for name in html_files:
        if not name.endswith(".html") or "/" in name or "\\" in name:
            errors.append(f"output.html_files entry must be an html basename: {name}")

    evidence_items = [
        mapping(item, f"evidence[{index}]", errors)
        for index, item in enumerate(sequence(report.get("evidence"), "evidence", errors))
    ]
    evidence_ids = unique_ids(
        evidence_items, "id", ID_PATTERNS["evidence"], "evidence", errors
    )
    for index, item in enumerate(evidence_items):
        classification = nonempty_text(
            item.get("classification"), f"evidence[{index}].classification", errors
        )
        if classification and classification not in CLASSIFICATIONS:
            errors.append(f"evidence[{index}].classification is invalid")
        nonempty_text(item.get("kind"), f"evidence[{index}].kind", errors)
        nonempty_text(item.get("claim"), f"evidence[{index}].claim", errors)
        locator = item.get("locator", "")
        if classification == "FACT":
            nonempty_text(locator, f"evidence[{index}].locator", errors)
        elif locator is not None and not isinstance(locator, str):
            errors.append(f"evidence[{index}].locator must be text")

    assumption_items = [
        mapping(item, f"assumptions[{index}]", errors)
        for index, item in enumerate(
            sequence(report.get("assumptions"), "assumptions", errors)
        )
    ]
    assumption_ids = unique_ids(
        assumption_items, "id", ID_PATTERNS["assumptions"], "assumptions", errors
    )
    for index, item in enumerate(assumption_items):
        nonempty_text(item.get("claim"), f"assumptions[{index}].claim", errors)
        state = nonempty_text(item.get("state"), f"assumptions[{index}].state", errors)
        if state and state not in {
            "UNVERIFIED",
            "ACCEPTED",
            "VERIFIED",
            "REJECTED",
        }:
            errors.append(f"assumptions[{index}].state is invalid")
        for evidence_id in string_list(
            item.get("evidence_ids", []),
            f"assumptions[{index}].evidence_ids",
            errors,
        ):
            if evidence_id not in evidence_ids:
                errors.append(
                    f"assumptions[{index}].evidence_ids unknown id {evidence_id}"
                )

    unknown_items = [
        mapping(item, f"unknowns[{index}]", errors)
        for index, item in enumerate(sequence(report.get("unknowns"), "unknowns", errors))
    ]
    unique_ids(unknown_items, "id", ID_PATTERNS["unknowns"], "unknowns", errors)
    for index, item in enumerate(unknown_items):
        nonempty_text(item.get("claim"), f"unknowns[{index}].claim", errors)
        if "material" not in item or not isinstance(item.get("material"), bool):
            errors.append(f"unknowns[{index}].material must be a boolean")

    thesis = mapping(report.get("thesis"), "thesis", errors)
    thesis_id = nonempty_text(thesis.get("id"), "thesis.id", errors)
    if thesis_id and not ID_PATTERNS["thesis"].fullmatch(thesis_id):
        errors.append("thesis.id must match T-###")
    nonempty_text(thesis.get("summary"), "thesis.summary", errors)
    nonempty_text(thesis.get("approach"), "thesis.approach", errors)
    string_list(
        thesis.get("rejected_alternatives"),
        "thesis.rejected_alternatives",
        errors,
        allow_empty=True,
    )

    step_items = [
        mapping(item, f"steps[{index}]", errors)
        for index, item in enumerate(sequence(report.get("steps"), "steps", errors))
    ]
    if not step_items:
        errors.append("steps must not be empty")
    step_ids = unique_ids(step_items, "id", ID_PATTERNS["steps"], "steps", errors)
    for index, item in enumerate(step_items):
        nonempty_text(item.get("title"), f"steps[{index}].title", errors)
        nonempty_text(item.get("why"), f"steps[{index}].why", errors)
        depends = string_list(
            item.get("depends_on", []), f"steps[{index}].depends_on", errors
        )
        for dep in depends:
            if dep not in step_ids:
                errors.append(f"steps[{index}].depends_on unknown id {dep}")
        string_list(item.get("surfaces", []), f"steps[{index}].surfaces", errors)
        string_list(item.get("dod", []), f"steps[{index}].dod", errors, allow_empty=False)
        string_list(item.get("proof_ids", []), f"steps[{index}].proof_ids", errors)
        if "simpler_rejected" in item and item["simpler_rejected"] is not None:
            if not isinstance(item["simpler_rejected"], str):
                errors.append(f"steps[{index}].simpler_rejected must be text or null")

    risk_items = [
        mapping(item, f"risks[{index}]", errors)
        for index, item in enumerate(sequence(report.get("risks"), "risks", errors))
    ]
    unique_ids(risk_items, "id", ID_PATTERNS["risks"], "risks", errors)
    for index, item in enumerate(risk_items):
        nonempty_text(item.get("claim"), f"risks[{index}].claim", errors)
        severity = nonempty_text(item.get("severity"), f"risks[{index}].severity", errors)
        if severity and severity not in {"low", "medium", "high", "blocker"}:
            errors.append(f"risks[{index}].severity is invalid")
        nonempty_text(item.get("mitigation"), f"risks[{index}].mitigation", errors)
        risk_status = nonempty_text(item.get("status"), f"risks[{index}].status", errors)
        if risk_status and risk_status not in {
            "OPEN",
            "MITIGATED",
            "ACCEPTED",
            "CLOSED",
        }:
            errors.append(f"risks[{index}].status is invalid")

    verification_items = [
        mapping(item, f"verifications[{index}]", errors)
        for index, item in enumerate(
            sequence(report.get("verifications"), "verifications", errors)
        )
    ]
    verification_ids = unique_ids(
        verification_items, "id", ID_PATTERNS["verifications"], "verifications", errors
    )
    for index, item in enumerate(verification_items):
        nonempty_text(item.get("proof"), f"verifications[{index}].proof", errors)
        proof_status = nonempty_text(
            item.get("status"), f"verifications[{index}].status", errors
        )
        if proof_status and proof_status not in PROOF_STATUSES:
            errors.append(f"verifications[{index}].status is invalid")
        if proof_status == "PLANNED":
            nonempty_text(item.get("reason"), f"verifications[{index}].reason", errors)
        string_list(
            item.get("claim_ids", []), f"verifications[{index}].claim_ids", errors
        )

    for index, item in enumerate(step_items):
        for proof_id in string_list(
            item.get("proof_ids", []), f"steps[{index}].proof_ids", errors
        ):
            if proof_id not in verification_ids:
                errors.append(f"steps[{index}].proof_ids unknown id {proof_id}")

    chapter_items = [
        mapping(item, f"chapters[{index}]", errors)
        for index, item in enumerate(sequence(report.get("chapters"), "chapters", errors))
    ]
    if not chapter_items:
        errors.append("chapters must not be empty")
    chapter_slugs: set[str] = set()
    for index, item in enumerate(chapter_items):
        chapter_id = nonempty_text(item.get("id"), f"chapters[{index}].id", errors)
        if chapter_id and not CHAPTER_ID_RE.fullmatch(chapter_id):
            errors.append(f"chapters[{index}].id must be two digits")
        slug = nonempty_text(item.get("slug"), f"chapters[{index}].slug", errors)
        if slug and not SLUG_RE.fullmatch(slug):
            errors.append(f"chapters[{index}].slug must be kebab-case")
        if slug:
            if slug in chapter_slugs:
                errors.append(f"chapters repeats slug {slug}")
            chapter_slugs.add(slug)
        nonempty_text(item.get("title"), f"chapters[{index}].title", errors)
        nonempty_text(item.get("summary"), f"chapters[{index}].summary", errors)
        sections = sequence(item.get("sections"), f"chapters[{index}].sections", errors)
        if not sections:
            errors.append(f"chapters[{index}].sections must not be empty")
        for section_index, raw_section in enumerate(sections):
            section = mapping(
                raw_section, f"chapters[{index}].sections[{section_index}]", errors
            )
            nonempty_text(
                section.get("heading"),
                f"chapters[{index}].sections[{section_index}].heading",
                errors,
            )
            blocks = sequence(
                section.get("blocks"),
                f"chapters[{index}].sections[{section_index}].blocks",
                errors,
            )
            if not blocks:
                errors.append(
                    f"chapters[{index}].sections[{section_index}].blocks must not be empty"
                )
            validate_blocks(
                blocks,
                f"chapters[{index}].sections[{section_index}].blocks",
                errors,
            )

    expected_html = [f"{item.get('id')}-{item.get('slug')}.html" for item in chapter_items]
    if html_files and expected_html and set(html_files) != set(expected_html):
        # allow exact order match preference but require same set
        missing = sorted(set(expected_html) - set(html_files))
        extra = sorted(set(html_files) - set(expected_html))
        if missing:
            errors.append(f"output.html_files missing chapter files: {missing}")
        if extra:
            errors.append(f"output.html_files has unknown files: {extra}")

    if depth == "simple" and len(chapter_items) > 3:
        errors.append("simple depth allows at most 3 chapters")

    council = mapping(report.get("council"), "council", errors)
    if "required" not in council or not isinstance(council.get("required"), bool):
        errors.append("council.required must be a boolean")
    required = bool(council.get("required"))
    skip_reason = council.get("skip_reason")
    runs = sequence(council.get("runs"), "council.runs", errors)
    if required:
        if skip_reason not in (None, ""):
            errors.append("council.skip_reason must be empty when required")
        if not runs:
            errors.append("council.runs must not be empty when required")
        for index, raw_run in enumerate(runs):
            run = mapping(raw_run, f"council.runs[{index}]", errors)
            nonempty_text(run.get("profile"), f"council.runs[{index}].profile", errors)
            nonempty_text(run.get("status"), f"council.runs[{index}].status", errors)
            nonempty_text(
                run.get("thesis_id"), f"council.runs[{index}].thesis_id", errors
            )
    else:
        if depth in {"standard", "deep"}:
            # standard/deep may still skip only with explicit reason when blocked
            nonempty_text(skip_reason, "council.skip_reason", errors)
        elif depth == "simple":
            nonempty_text(skip_reason, "council.skip_reason", errors)

    simplicity = mapping(report.get("simplicity"), "simplicity", errors)
    string_list(simplicity.get("cuts"), "simplicity.cuts", errors, allow_empty=True)
    string_list(
        simplicity.get("retained_complexity_justifications"),
        "simplicity.retained_complexity_justifications",
        errors,
        allow_empty=True,
    )

    residuals = string_list(report.get("residuals"), "residuals", errors)
    blockers = string_list(report.get("blockers"), "blockers", errors)

    material_unknowns = [
        item
        for item in unknown_items
        if isinstance(item.get("material"), bool) and item.get("material")
    ]
    open_high_risks = [
        item
        for item in risk_items
        if item.get("severity") in {"high", "blocker"}
        and item.get("status") == "OPEN"
    ]
    bad_proofs = [
        item
        for item in verification_items
        if item.get("status") in {"NOT_RUN", "BLOCKED"}
    ]
    unaccepted_assumptions = [
        item
        for item in assumption_items
        if item.get("state") == "UNVERIFIED"
    ]

    if status == "READY_TO_EXECUTE":
        if blockers:
            errors.append("READY_TO_EXECUTE forbids non-empty blockers")
        if material_unknowns:
            errors.append("READY_TO_EXECUTE forbids material unknowns")
        if open_high_risks:
            errors.append("READY_TO_EXECUTE forbids open high/blocker risks")
        if bad_proofs:
            errors.append(
                "READY_TO_EXECUTE forbids verification status NOT_RUN or BLOCKED"
            )
        if unaccepted_assumptions:
            errors.append(
                "READY_TO_EXECUTE forbids UNVERIFIED assumptions; accept or verify them"
            )
        if required and runs:
            terminal = {run.get("status") for run in runs if isinstance(run, dict)}
            blockedish = terminal & {"BLOCKED", "REVISE", "ESCALATE_TO_FULL"}
            if blockedish:
                errors.append(
                    "READY_TO_EXECUTE forbids unresolved council statuses "
                    f"{sorted(blockedish)}"
                )
    elif status in {"NOT_CONFIDENT", "BLOCKED"}:
        if not residuals and not blockers and not material_unknowns and not bad_proofs:
            errors.append(
                f"{status} requires residuals, blockers, material unknowns, or bad proofs"
            )

    if require_html:
        if not plan_dir:
            errors.append("--require-html needs output.plan_dir")
        else:
            root = Path(plan_dir)
            if not root.is_dir():
                errors.append(f"plan_dir does not exist: {root}")
            else:
                report_on_disk = root / "plan-report.json"
                if not report_on_disk.is_file():
                    errors.append("plan_dir must contain plan-report.json")
                for name in html_files:
                    path = root / name
                    if not path.is_file():
                        errors.append(f"missing rendered html: {name}")
                    else:
                        text = path.read_text(encoding="utf-8")
                        if "<html" not in text.lower():
                            errors.append(f"{name} is not HTML")
                        if "<nav" not in text.lower():
                            errors.append(f"{name} missing nav")

    # silence unused for linters / future checks
    _ = (assumption_ids, residuals, report_path)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to plan-report.json")
    parser.add_argument(
        "--require-html",
        action="store_true",
        help="Also require rendered HTML files on disk under output.plan_dir",
    )
    args = parser.parse_args()

    try:
        report = load_json(args.report)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"INVALID\nfailed to load report: {error}")
        return 2

    errors = validate_report(
        report, require_html=args.require_html, report_path=args.report
    )
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
