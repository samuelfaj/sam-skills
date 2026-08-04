#!/usr/bin/env python3
"""Validate sam-plan plan-report.json: hard freeze core, required light HTML pack (--require-html)."""

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
FACT_HEDGE_RE = re.compile(
    r"\b(?:appears|seems|maybe|likely|probably|roughly|approximately|might|could be)\b",
    re.IGNORECASE,
)

RISK_FLAGS = {
    "security_privacy",
    "auth_boundary",
    "data_migration",
    "irreversible",
    "public_contract",
    "multi_service",
    "payments",
    "compliance",
    "user_requested_council",
    "material_uncertainty",
}
ID_PATTERNS = {
    "evidence": re.compile(r"^E-\d{3,}$"),
    "assumptions": re.compile(r"^A-\d{3,}$"),
    "unknowns": re.compile(r"^U-\d{3,}$"),
    "steps": re.compile(r"^S-\d{3,}$"),
    "risks": re.compile(r"^R-\d{3,}$"),
    "verifications": re.compile(r"^V-\d{3,}$"),
    "thesis": re.compile(r"^T-\d{3,}$"),
}
# Soft: allow free-form IDs if unique; hard patterns preferred but not required
# when they already match uniqueness. Keep patterns as soft warnings? No —
# harness and docs use E-###. Keep pattern enforcement for known series when
# id looks like series prefix, else require non-empty unique ids.
LOOSE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,63}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHAPTER_ID_RE = re.compile(r"^\d{2}$")
# path, path:line, path:line:col — optional trailing symbol notes
PATH_LOCATOR_RE = re.compile(
    r"^(?P<path>(?:[A-Za-z]:)?[^:\n]+?)(?::(?P<line>\d+))?(?::(?P<col>\d+))?$"
)
DECISION_LOCATOR_RE = re.compile(
    r"^(?:user\s+decision|decision|owner\s+decision)\s*:\s*.+",
    re.IGNORECASE,
)
COMMAND_LOCATOR_RE = re.compile(r"^(?:command|cmd|shell)\s*:\s*.+", re.IGNORECASE)

# Heuristic keyword → risk_flag (strong signals for READY under-flagging)
RISK_HEURISTICS: list[tuple[str, re.Pattern[str]]] = [
    (
        "auth_boundary",
        re.compile(
            r"\b(authz|authorization|login|oauth|rbac|session|permission|role-based|"
            r"identity\s+provider|sso)\b",
            re.I,
        ),
    ),
    (
        "security_privacy",
        re.compile(
            r"\b(secret|pii|privacy|gdpr|tenanc|encryption|credential|password|"
            r"security\s+boundary)\b",
            re.I,
        ),
    ),
    (
        "data_migration",
        re.compile(
            r"\b(migration|migrate|schema\s+change|backfill|dual-?write|"
            r"data\s+rewrite)\b",
            re.I,
        ),
    ),
    (
        "irreversible",
        re.compile(
            r"\b(irreversible|destructive|drop\s+table|one-?way|hard\s+delete|"
            r"no\s+rollback)\b",
            re.I,
        ),
    ),
    (
        "public_contract",
        re.compile(
            r"\b(public\s+api|breaking\s+change|sdk\s+compat|semver|"
            r"api\s+compatibility|open\s+api)\b",
            re.I,
        ),
    ),
    (
        "multi_service",
        re.compile(
            r"\b(multi-?service|cross-?service|microservice|multi-?system|"
            r"service\s+mesh)\b",
            re.I,
        ),
    ),
    (
        "payments",
        re.compile(
            r"\b(payment|stripe|payout|charge\s+card|billing\s+capture|"
            r"money\s+movement|pci)\b",
            re.I,
        ),
    ),
    (
        "compliance",
        re.compile(r"\b(compliance|hipaa|sox|audit\s+log|regulated)\b", re.I),
    ),
]


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
    items: list[JsonObject],
    pattern: re.Pattern[str] | None,
    label: str,
    errors: list[str],
) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_id = nonempty_text(item.get("id"), f"{label}[{index}].id", errors)
        if not item_id:
            continue
        if pattern is not None and not pattern.fullmatch(item_id):
            if not LOOSE_ID.fullmatch(item_id):
                errors.append(
                    f"{label}[{index}].id must match {pattern.pattern} or a short id"
                )
            # Prefer series patterns; accept loose unique ids for flexibility
            elif not pattern.fullmatch(item_id) and item_id[0] in "EAUSRTV":
                # Looks like series but wrong shape
                if not re.match(r"^[EAUSRTV]-", item_id):
                    pass
                elif not pattern.fullmatch(item_id):
                    errors.append(
                        f"{label}[{index}].id must match {pattern.pattern}"
                    )
        if item_id in seen:
            errors.append(f"{label} repeats id {item_id}")
        seen.add(item_id)
    return seen


def parse_path_locator(locator: str) -> tuple[str | None, int | None]:
    """Return (relative_path, line) for filesystem locators; None path if exempt."""
    text = locator.strip()
    if not text:
        return None, None
    if DECISION_LOCATOR_RE.fullmatch(text) or COMMAND_LOCATOR_RE.fullmatch(text):
        return None, None
    # Allow "symbol @ path:line"
    if " @" in text:
        text = text.split(" @", 1)[1].strip()
    # Strip trailing parenthetical notes: path:12 (function)
    if " (" in text and text.endswith(")"):
        text = text[: text.rfind(" (")].strip()
    match = PATH_LOCATOR_RE.fullmatch(text)
    if not match:
        return None, None
    path = match.group("path").strip().strip("\"'")
    line_raw = match.group("line")
    line = int(line_raw) if line_raw else None
    # Reject bare words without path separators as non-path (still count as locator text)
    if "/" not in path and "\\" not in path and not path.endswith(
        (".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".kt", ".md", ".json", ".yml", ".yaml", ".toml", ".sql")
    ):
        return None, None
    return path, line


def resolve_locator_path(repo_root: Path, rel: str) -> Path | None:
    candidate = Path(rel)
    if candidate.is_absolute():
        path = candidate
    else:
        path = (repo_root / rel).resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError:
            return None
    return path


def check_locator_against_repo(
    locator: str, repo_root: Path, label: str, errors: list[str]
) -> bool:
    """Return True if locator is path-like and valid, or exempt (decision/command)."""
    rel, line = parse_path_locator(locator)
    if rel is None:
        # decision/command or non-path prose locator — structural only
        return DECISION_LOCATOR_RE.fullmatch(locator.strip()) is not None or (
            COMMAND_LOCATOR_RE.fullmatch(locator.strip()) is not None
        )
    path = resolve_locator_path(repo_root, rel)
    if path is None or not path.is_file():
        errors.append(f"{label}: locator path does not exist under repo: {rel}")
        return False
    if line is not None:
        try:
            line_count = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
        except OSError as error:
            errors.append(f"{label}: cannot read locator path {rel}: {error}")
            return False
        if line < 1 or line > line_count:
            errors.append(
                f"{label}: locator line {line} out of range for {rel} ({line_count} lines)"
            )
            return False
    return True


def collect_heuristic_risk_flags(report: JsonObject) -> set[str]:
    """Suggest risk_flags from case_type + goal/steps/surfaces (not negating rationales)."""
    frozen = report.get("frozen") if isinstance(report.get("frozen"), dict) else {}
    # Intentionally exclude complexity_rationale / non_goals — they often say "no migration".
    blobs: list[str] = [
        str(frozen.get("goal") or ""),
        str(frozen.get("prompt_summary") or ""),
    ]
    case_type = str(report.get("case_type") or "")
    suggested: set[str] = set()
    if case_type == "MIGRATION":
        suggested.update({"data_migration", "irreversible"})
    study = report.get("study") if isinstance(report.get("study"), dict) else {}
    surfaces = (
        study.get("surfaces_mapped")
        if isinstance(study.get("surfaces_mapped"), list)
        else []
    )
    blobs.append(" ".join(str(s) for s in surfaces))
    for step in report.get("steps") or []:
        if isinstance(step, dict):
            blobs.append(str(step.get("title") or ""))
            blobs.append(str(step.get("why") or ""))
            sur = step.get("surfaces") if isinstance(step.get("surfaces"), list) else []
            blobs.append(" ".join(str(s) for s in sur))
    text = "\n".join(blobs)
    for flag, pattern in RISK_HEURISTICS:
        if pattern.search(text):
            suggested.add(flag)
    return suggested


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


def validate_report(
    report: JsonObject,
    *,
    require_html: bool,
    report_path: Path,
    repo_root: Path | None = None,
    check_locators: bool = False,
) -> list[str]:
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

    risk_flags = string_list(
        report.get("risk_flags", []), "risk_flags", errors, allow_empty=True
    )
    for flag in risk_flags:
        if flag not in RISK_FLAGS:
            errors.append(f"risk_flags contains unknown flag: {flag}")

    frozen = mapping(report.get("frozen"), "frozen", errors)
    for key in (
        "prompt_hash",
        "prompt_summary",
        "goal",
    ):
        nonempty_text(frozen.get(key), f"frozen.{key}", errors)
    success_criteria = string_list(
        frozen.get("success_criteria"), "frozen.success_criteria", errors, allow_empty=True
    )
    for key in (
        "non_goals",
        "invariants",
        "constraints",
        "no_go",
    ):
        string_list(frozen.get(key), f"frozen.{key}", errors, allow_empty=True)

    # Study receipts
    study = mapping(report.get("study"), "study", errors) if "study" in report else {}
    if status == "READY_TO_EXECUTE" and "study" not in report:
        errors.append("READY_TO_EXECUTE requires study object")
    surfaces_mapped: list[str] = []
    tools_used: list[str] = []
    if study or "study" in report:
        study = mapping(report.get("study"), "study", errors)
        surfaces_mapped = string_list(
            study.get("surfaces_mapped", []),
            "study.surfaces_mapped",
            errors,
            allow_empty=True,
        )
        tools_used = string_list(
            study.get("tools_used", []),
            "study.tools_used",
            errors,
            allow_empty=True,
        )
        string_list(
            study.get("prompt_ambiguities", []),
            "study.prompt_ambiguities",
            errors,
            allow_empty=True,
        )
        if study.get("repo_root") is not None:
            rr = nonempty_text(study.get("repo_root"), "study.repo_root", errors)
            if rr and repo_root is None:
                candidate = Path(rr).expanduser()
                if candidate.is_dir():
                    repo_root = candidate.resolve()

    output = mapping(report.get("output"), "output", errors)
    plan_dir = nonempty_text(output.get("plan_dir"), "output.plan_dir", errors)
    html_files_raw = output.get("html_files", [])
    if html_files_raw is None:
        html_files_raw = []
    html_files = string_list(
        html_files_raw, "output.html_files", errors, allow_empty=True
    )
    for name in html_files:
        if not name.endswith(".html") or "/" in name or "\\" in name:
            errors.append(f"output.html_files entry must be an html basename: {name}")

    evidence_items = [
        mapping(item, f"evidence[{index}]", errors)
        for index, item in enumerate(sequence(report.get("evidence"), "evidence", errors))
    ]
    evidence_ids = unique_ids(
        evidence_items, ID_PATTERNS["evidence"], "evidence", errors
    )
    fact_with_locator = 0
    resolved_fact_locators = 0
    do_check_locators = check_locators or repo_root is not None
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
            loc = nonempty_text(locator, f"evidence[{index}].locator", errors)
            if loc:
                fact_with_locator += 1
                if do_check_locators and repo_root is not None:
                    if check_locator_against_repo(
                        loc, repo_root, f"evidence[{index}].locator", errors
                    ):
                        # Count path-like or exempt decision locators as resolved
                        rel, _ = parse_path_locator(loc)
                        if rel is not None or DECISION_LOCATOR_RE.fullmatch(loc.strip()):
                            resolved_fact_locators += 1
                elif not do_check_locators:
                    resolved_fact_locators += 1
        elif locator is not None and not isinstance(locator, str):
            errors.append(f"evidence[{index}].locator must be text")

    assumption_items = [
        mapping(item, f"assumptions[{index}]", errors)
        for index, item in enumerate(
            sequence(report.get("assumptions"), "assumptions", errors)
        )
    ]
    assumption_ids = unique_ids(
        assumption_items, ID_PATTERNS["assumptions"], "assumptions", errors
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
        if state == "ACCEPTED":
            evid = item.get("evidence_ids") if isinstance(item.get("evidence_ids"), list) else []
            reason = item.get("decision_reason")
            if not evid and not (isinstance(reason, str) and reason.strip()):
                errors.append(
                    f"assumptions[{index}] ACCEPTED requires decision_reason or evidence_ids"
                )

    unknown_items = [
        mapping(item, f"unknowns[{index}]", errors)
        for index, item in enumerate(sequence(report.get("unknowns"), "unknowns", errors))
    ]
    unique_ids(unknown_items, ID_PATTERNS["unknowns"], "unknowns", errors)
    for index, item in enumerate(unknown_items):
        nonempty_text(item.get("claim"), f"unknowns[{index}].claim", errors)
        if "material" not in item or not isinstance(item.get("material"), bool):
            errors.append(f"unknowns[{index}].material must be a boolean")
        # structural optional fields validated when present
        if "probe" in item and item["probe"] is not None and not isinstance(item["probe"], str):
            errors.append(f"unknowns[{index}].probe must be text when present")
        if (
            "why_immaterial" in item
            and item["why_immaterial"] is not None
            and not isinstance(item["why_immaterial"], str)
        ):
            errors.append(f"unknowns[{index}].why_immaterial must be text when present")

    thesis = mapping(report.get("thesis"), "thesis", errors)
    thesis_id = nonempty_text(thesis.get("id"), "thesis.id", errors)
    if thesis_id and not (
        ID_PATTERNS["thesis"].fullmatch(thesis_id) or LOOSE_ID.fullmatch(thesis_id)
    ):
        errors.append("thesis.id must be a stable id (prefer T-###)")
    nonempty_text(thesis.get("summary"), "thesis.summary", errors)
    nonempty_text(thesis.get("approach"), "thesis.approach", errors)
    rejected = string_list(
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
    step_ids = unique_ids(step_items, ID_PATTERNS["steps"], "steps", errors)
    for index, item in enumerate(step_items):
        nonempty_text(item.get("title"), f"steps[{index}].title", errors)
        nonempty_text(item.get("why"), f"steps[{index}].why", errors)
        depends = string_list(
            item.get("depends_on", []), f"steps[{index}].depends_on", errors
        )
        for dep in depends:
            if dep not in step_ids:
                errors.append(f"steps[{index}].depends_on unknown id {dep}")
        surfaces_list = string_list(
            item.get("surfaces", []), f"steps[{index}].surfaces", errors
        )
        # how[] is optional structurally; READY requires non-empty executable how
        if "how" in item and item["how"] is not None and not isinstance(item["how"], list):
            errors.append(f"steps[{index}].how must be a list of strings when present")
            how_list: list[str] = []
        else:
            how_list = string_list(
                item.get("how", []),
                f"steps[{index}].how",
                errors,
                allow_empty=True,
            )
        if "preconditions" in item and item["preconditions"] is not None:
            if not isinstance(item["preconditions"], list):
                errors.append(
                    f"steps[{index}].preconditions must be a list of strings when present"
                )
            else:
                string_list(
                    item.get("preconditions", []),
                    f"steps[{index}].preconditions",
                    errors,
                    allow_empty=True,
                )
        dod_list = string_list(
            item.get("dod", []), f"steps[{index}].dod", errors, allow_empty=False
        )
        proof_list = string_list(
            item.get("proof_ids", []), f"steps[{index}].proof_ids", errors
        )
        item["_dod"] = dod_list
        item["_proof_ids"] = proof_list
        item["_depends_on"] = depends
        item["_surfaces"] = surfaces_list
        item["_how"] = how_list
        item["_title"] = str(item.get("title") or "").strip()
        if "simpler_rejected" in item and item["simpler_rejected"] is not None:
            if not isinstance(item["simpler_rejected"], str):
                errors.append(f"steps[{index}].simpler_rejected must be text or null")

    # depends_on acyclicity
    if step_ids:
        graph = {
            sid: list(item.get("_depends_on") or [])
            for sid, item in zip(step_ids, step_items)
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for nxt in graph.get(node, []):
                if nxt in graph and dfs(nxt):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        if any(dfs(node) for node in graph):
            errors.append("steps.depends_on must be acyclic")

    risk_items = [
        mapping(item, f"risks[{index}]", errors)
        for index, item in enumerate(sequence(report.get("risks"), "risks", errors))
    ]
    unique_ids(risk_items, ID_PATTERNS["risks"], "risks", errors)
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
        verification_items, ID_PATTERNS["verifications"], "verifications", errors
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

    # Optional acceptance_trace: map success criteria → steps/proofs
    acceptance_raw = report.get("acceptance_trace", [])
    if acceptance_raw is None:
        acceptance_raw = []
    acceptance_items = [
        mapping(item, f"acceptance_trace[{index}]", errors)
        for index, item in enumerate(
            sequence(acceptance_raw, "acceptance_trace", errors)
        )
    ]
    traced_criteria: set[str] = set()
    for index, item in enumerate(acceptance_items):
        criterion = nonempty_text(
            item.get("criterion"), f"acceptance_trace[{index}].criterion", errors
        )
        if criterion:
            traced_criteria.add(criterion)
        for sid in string_list(
            item.get("step_ids", []), f"acceptance_trace[{index}].step_ids", errors
        ):
            if sid not in step_ids:
                errors.append(
                    f"acceptance_trace[{index}].step_ids unknown id {sid}"
                )
        for pid in string_list(
            item.get("proof_ids", []), f"acceptance_trace[{index}].proof_ids", errors
        ):
            if pid not in verification_ids:
                errors.append(
                    f"acceptance_trace[{index}].proof_ids unknown id {pid}"
                )

    # Optional chapters (pack presentation)
    chapters_value = report.get("chapters", [])
    if chapters_value is None:
        chapters_value = []
    chapter_items = [
        mapping(item, f"chapters[{index}]", errors)
        for index, item in enumerate(sequence(chapters_value, "chapters", errors))
    ]
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

    if chapter_items and html_files:
        expected_html = [
            f"{item.get('id')}-{item.get('slug')}.html" for item in chapter_items
        ]
        missing = sorted(set(expected_html) - set(html_files))
        extra = sorted(set(html_files) - set(expected_html))
        if missing:
            errors.append(f"output.html_files missing chapter files: {missing}")
        if extra:
            errors.append(f"output.html_files has unknown files: {extra}")

    council = mapping(report.get("council"), "council", errors)
    if "required" not in council or not isinstance(council.get("required"), bool):
        errors.append("council.required must be a boolean")
    required = bool(council.get("required"))
    skip_reason = council.get("skip_reason")
    runs = sequence(council.get("runs"), "council.runs", errors)
    if risk_flags and not required:
        errors.append("non-empty risk_flags require council.required=true")
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
        if not rejected:
            errors.append(
                "READY_TO_EXECUTE requires non-empty thesis.rejected_alternatives"
            )
        if fact_with_locator < 1:
            errors.append(
                "READY_TO_EXECUTE requires at least one FACT evidence with locator"
            )
        if case_type != "SPIKE" and not surfaces_mapped:
            errors.append(
                "READY_TO_EXECUTE requires non-empty study.surfaces_mapped "
                "(except case_type=SPIKE)"
            )
        if case_type != "SPIKE" and not tools_used:
            errors.append(
                "READY_TO_EXECUTE requires non-empty study.tools_used "
                "(except case_type=SPIKE)"
            )
        if do_check_locators and repo_root is not None and resolved_fact_locators < 1:
            errors.append(
                "READY_TO_EXECUTE with --repo-root requires at least one FACT "
                "locator that resolves under the repo (or user decision: …)"
            )
        # Gap engine: non-empty success criteria (except SPIKE)
        if case_type != "SPIKE" and not success_criteria:
            errors.append(
                "READY_TO_EXECUTE requires non-empty frozen.success_criteria "
                "(except case_type=SPIKE)"
            )
        if success_criteria:
            missing_criteria = [
                c for c in success_criteria if c not in traced_criteria
            ]
            if missing_criteria:
                errors.append(
                    "READY_TO_EXECUTE requires acceptance_trace covering each "
                    f"success criterion; missing: {missing_criteria}"
                )
        # Each acceptance_trace entry needs ≥1 step and ≥1 proof
        for index, raw in enumerate(sequence(report.get("acceptance_trace", []), "acceptance_trace", errors) if isinstance(report.get("acceptance_trace", []), list) else []):
            if not isinstance(raw, dict):
                continue
            sids = raw.get("step_ids") if isinstance(raw.get("step_ids"), list) else []
            pids = raw.get("proof_ids") if isinstance(raw.get("proof_ids"), list) else []
            if not sids:
                errors.append(
                    f"READY_TO_EXECUTE acceptance_trace[{index}] requires ≥1 step_ids"
                )
            if not pids:
                errors.append(
                    f"READY_TO_EXECUTE acceptance_trace[{index}] requires ≥1 proof_ids"
                )
        # Step reachability from criteria (skip for depth simple)
        if depth != "simple" and step_ids:
            referenced_steps: set[str] = set()
            for raw in report.get("acceptance_trace", []) if isinstance(report.get("acceptance_trace"), list) else []:
                if isinstance(raw, dict):
                    for sid in raw.get("step_ids") or []:
                        if isinstance(sid, str):
                            referenced_steps.add(sid)
            for index, item in enumerate(step_items):
                sid = item.get("id")
                if not isinstance(sid, str):
                    continue
                if sid in referenced_steps:
                    continue
                if isinstance(item.get("out_of_acceptance"), str) and item["out_of_acceptance"].strip():
                    continue
                errors.append(
                    f"READY_TO_EXECUTE step {sid} must be reachable from acceptance_trace "
                    "or set out_of_acceptance reason"
                )
        # Steps with DoD need proof_ids; READY needs how + surfaces (except SPIKE)
        for index, item in enumerate(step_items):
            dod = item.get("_dod") or item.get("dod") or []
            proofs = item.get("_proof_ids") if "_proof_ids" in item else item.get("proof_ids") or []
            if dod and not proofs:
                errors.append(
                    f"READY_TO_EXECUTE steps[{index}] with dod requires ≥1 proof_ids"
                )
            how = item.get("_how") if "_how" in item else item.get("how") or []
            how_clean = [
                str(h).strip()
                for h in how
                if isinstance(h, str) and str(h).strip()
            ]
            title = item.get("_title") or str(item.get("title") or "").strip()
            if not how_clean:
                errors.append(
                    f"READY_TO_EXECUTE steps[{index}] requires non-empty how[] "
                    "(imperative procedure bullets for implementers)"
                )
            else:
                # Reject how that only restates the title
                nontrivial = [
                    h
                    for h in how_clean
                    if h.casefold() != title.casefold() and len(h) >= 8
                ]
                if not nontrivial:
                    errors.append(
                        f"READY_TO_EXECUTE steps[{index}].how must be executable "
                        "(not empty, not only restating the title)"
                    )
            if case_type != "SPIKE":
                surfaces = (
                    item.get("_surfaces")
                    if "_surfaces" in item
                    else item.get("surfaces") or []
                )
                if not surfaces:
                    errors.append(
                        f"READY_TO_EXECUTE steps[{index}] requires non-empty surfaces "
                        "(except case_type=SPIKE)"
                    )
        # UNKNOWN probes (depth simple skips non-material probe/why rules)
        for index, item in enumerate(unknown_items):
            material = item.get("material") is True
            probe = item.get("probe")
            why = item.get("why_immaterial")
            if material:
                if not (isinstance(probe, str) and probe.strip()):
                    errors.append(
                        f"READY_TO_EXECUTE unknowns[{index}] material requires probe"
                    )
            elif depth != "simple":
                if not (isinstance(why, str) and why.strip()):
                    errors.append(
                        f"READY_TO_EXECUTE unknowns[{index}] immaterial requires why_immaterial"
                    )
        # Hedge-vs-FACT
        for index, raw in enumerate(report.get("evidence", []) if isinstance(report.get("evidence"), list) else []):
            if not isinstance(raw, dict):
                continue
            if raw.get("classification") != "FACT":
                continue
            claim = raw.get("claim")
            if isinstance(claim, str) and FACT_HEDGE_RE.search(claim):
                errors.append(
                    f"READY_TO_EXECUTE evidence[{index}] FACT claim uses hedge language"
                )
        suggested = collect_heuristic_risk_flags(report)
        missing_flags = sorted(suggested - set(risk_flags))
        if missing_flags:
            errors.append(
                "READY_TO_EXECUTE missing risk_flags suggested by heuristics: "
                f"{missing_flags}"
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
                if not html_files:
                    errors.append("--require-html needs non-empty output.html_files")
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

    _ = (assumption_ids, residuals, report_path, depth)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to plan-report.json")
    parser.add_argument(
        "--require-html",
        action="store_true",
        help="Also require rendered HTML files on disk under output.plan_dir",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Target repository root for locator path resolution",
    )
    parser.add_argument(
        "--check-locators",
        action="store_true",
        help="Require FACT path locators to exist under --repo-root (or study.repo_root)",
    )
    args = parser.parse_args()

    try:
        report = load_json(args.report)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"INVALID\nfailed to load report: {error}")
        return 2

    repo_root = args.repo_root.expanduser().resolve() if args.repo_root else None
    if repo_root is not None and not repo_root.is_dir():
        print(f"INVALID\n--repo-root is not a directory: {repo_root}")
        return 2
    if args.check_locators and repo_root is None:
        # Allow study.repo_root inside validate_report
        pass

    errors = validate_report(
        report,
        require_html=args.require_html,
        report_path=args.report,
        repo_root=repo_root,
        check_locators=args.check_locators or repo_root is not None,
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
