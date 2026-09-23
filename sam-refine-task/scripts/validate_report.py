#!/usr/bin/env python3
"""Validate a workflow report against immutable baseline/current scope bundles.

With --scaffold, write or refresh the report instead: bundle-derived fields are
recomputed, authored fields are kept, and missing fields get fail-closed
placeholders that never validate until replaced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


JsonObject = dict[str, Any]
WORKFLOWS = {
    "sam-create-feature": "feature",
    "sam-fix-bug": "bugfix",
    "sam-refine-task": "refinement",
    "sam-simplify-task": "simplification",
}
DECISIONS = {
    "feature": {"COMPLETE", "CHANGES_REQUIRED", "BLOCKED"},
    "bugfix": {"COMPLETE", "CHANGES_REQUIRED", "BLOCKED"},
    "refinement": {"HIGH_CONFIDENCE", "NOT_CONFIDENT", "BLOCKED"},
    "simplification": {"SIMPLEST_DEFENSIBLE", "NO_CHANGE", "BLOCKED"},
}
COMPLETION = {
    "feature": {"COMPLETE"},
    "bugfix": {"COMPLETE"},
    "refinement": {"HIGH_CONFIDENCE"},
    "simplification": {"SIMPLEST_DEFENSIBLE", "NO_CHANGE"},
}
EXEMPT_LOCATOR_RE = re.compile(
    r"^(?:user\s+decision|owner\s+decision|decision|command|cmd|shell)\s*:", re.I
)
PATH_LOCATOR_RE = re.compile(r"^(?P<path>[^:\n]+?)(?::(?P<line>\d+))?(?::\d+)?$")


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


def file_map(
    bundle: JsonObject, label: str, errors: list[str]
) -> dict[str, JsonObject]:
    result: dict[str, JsonObject] = {}
    for index, raw in enumerate(
        sequence(bundle.get("files"), f"{label}.files", errors)
    ):
        item = mapping(raw, f"{label}.files[{index}]", errors)
        path = nonempty_text(item.get("path"), f"{label}.files[{index}].path", errors)
        if path in result:
            errors.append(f"{label}.files repeats path {path}")
        elif path:
            result[path] = item
    return result


def changed_paths(
    before: dict[str, JsonObject], after: dict[str, JsonObject]
) -> set[str]:
    return {
        path
        for path in before.keys() | after.keys()
        if before.get(path) != after.get(path)
    }


def evidence_ids(
    value: Any,
    label: str,
    known: dict[str, JsonObject],
    errors: list[str],
    *,
    require_pass: bool = False,
    require_failure: bool = False,
    allow_empty: bool = True,
) -> list[str]:
    ids = string_list(value, label, errors, allow_empty=allow_empty)
    for evidence_id in ids:
        if evidence_id not in known:
            errors.append(f"{label} references unknown evidence {evidence_id}")
        elif require_pass and known[evidence_id].get("status") != "PASS":
            errors.append(f"{label} requires passing evidence {evidence_id}")
    if require_failure:
        statuses = [
            known[evidence_id].get("status")
            for evidence_id in ids
            if evidence_id in known
        ]
        if "FAIL" not in statuses:
            errors.append(f"{label} requires at least one failing evidence entry")
        if "NOT_RUN" in statuses:
            errors.append(f"{label} cannot use NOT_RUN as failing proof")
    return ids


def load_plan_evidence(value: Any, errors: list[str]) -> dict[str, JsonObject] | None:
    if not isinstance(value, str) or not Path(value).is_absolute():
        errors.append("plan_report must be an absolute path when evidence cites plan_ref")
        return None
    try:
        plan = load_json(Path(value))
    except (OSError, ValueError) as exception:
        errors.append(f"plan_report is unreadable: {exception}")
        return None
    if plan.get("workflow") != "plan":
        errors.append("plan_report must be a plan freeze (workflow plan)")
        return None
    items = plan.get("evidence") if isinstance(plan.get("evidence"), list) else []
    return {
        item["id"]: item
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def pinned_text(root: Path, relative: str, current: JsonObject) -> str | None:
    """Content of a repo path as the current bundle captured it, or None.

    A path the bundle lists as changed is read from the working tree only while
    its bytes still match the captured hash; any other path is read from the
    pinned head commit, so later commits never change the answer.
    """
    entries = {
        item.get("path"): item
        for item in current.get("files") or []
        if isinstance(item, dict)
    }
    entry = entries.get(relative)
    if entry is not None:
        try:
            data = (root / relative).read_bytes()
        except OSError:
            return None
        if entry.get("state") != "file" or (
            hashlib.sha256(data).hexdigest() != entry.get("worktree_sha256")
        ):
            return None
        return data.decode("utf-8", "replace")
    head = current.get("head_sha")
    executable = shutil.which("git")
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40,64}", head):
        return None
    if executable is None or root in Path(executable).resolve().parents:
        return None
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")
    }
    environment.update(
        {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull}
    )
    result = subprocess.run(
        [executable, "-C", str(root), "-c", "core.fsmonitor=false", "--no-pager",
         "cat-file", "blob", f"{head}:{relative}"],
        env=environment, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    return result.stdout.decode("utf-8", "replace") if result.returncode == 0 else None


def check_plan_ref(
    item: JsonObject,
    label: str,
    plan_evidence: dict[str, JsonObject] | None,
    current: JsonObject,
    errors: list[str],
) -> None:
    """Reused plan FACTs must be re-checked: same locator, resolving in the captured tree."""
    ref = nonempty_text(item.get("plan_ref"), f"{label}.plan_ref", errors)
    locator = nonempty_text(item.get("locator"), f"{label}.locator", errors)
    if item.get("status") != "PASS":
        errors.append(f"{label} plan_ref evidence must be PASS after re-checking its locator")
    if plan_evidence is None or not ref or not locator:
        return
    source = plan_evidence.get(ref)
    if source is None or source.get("classification") != "FACT":
        errors.append(f"{label}.plan_ref {ref} is not a FACT in plan_report")
        return
    if locator != str(source.get("locator") or "").strip():
        errors.append(f"{label}.locator must equal the locator of plan {ref}")
        return
    if EXEMPT_LOCATOR_RE.match(locator):
        return
    text = locator.split(" @", 1)[1].strip() if " @" in locator else locator
    if " (" in text and text.endswith(")"):
        text = text[: text.rfind(" (")].strip()
    match = PATH_LOCATOR_RE.fullmatch(text)
    content: str | None = None
    repo_root = current.get("repo_root")
    if match and isinstance(repo_root, str) and repo_root:
        root = Path(repo_root).resolve()
        candidate = Path(match.group("path").strip())
        path = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if root in path.parents:
            content = pinned_text(root, path.relative_to(root).as_posix(), current)
    if content is None:
        errors.append(f"{label}.locator does not resolve in the captured tree: {locator}")
        return
    line = match.group("line") if match else None
    if line:
        count = len(content.splitlines())
        if not 1 <= int(line) <= count:
            errors.append(f"{label}.locator line {line} is out of range ({count} lines)")


def validate_domain(
    workflow: str,
    report: JsonObject,
    evidence: dict[str, JsonObject],
    delta: set[str],
    blockers: list[str],
    errors: list[str],
) -> None:
    if workflow == "feature":
        requirements = sequence(report.get("requirements"), "requirements", errors)
        if not requirements:
            errors.append("requirements must not be empty")
        requirement_ids: list[str] = []
        for index, raw in enumerate(requirements):
            item = mapping(raw, f"requirements[{index}]", errors)
            requirement_id = nonempty_text(
                item.get("id"), f"requirements[{index}].id", errors
            )
            if requirement_id:
                requirement_ids.append(requirement_id)
            nonempty_text(item.get("text"), f"requirements[{index}].text", errors)
            status = item.get("status")
            if status not in {"CONFIRMED", "ASSUMED", "BLOCKED"}:
                errors.append(f"requirements[{index}].status is invalid")
            ids = evidence_ids(
                item.get("evidence_ids"),
                f"requirements[{index}].evidence_ids",
                evidence,
                errors,
            )
            if status == "CONFIRMED" and not ids:
                errors.append(f"requirements[{index}] needs evidence")
            if status == "BLOCKED" or (
                status == "ASSUMED" and item.get("material") is True
            ):
                blockers.append(f"unresolved requirement {item.get('id', index)}")
        if len(requirement_ids) != len(set(requirement_ids)):
            errors.append("requirements must use unique ids")
        tdd = mapping(report.get("tdd"), "tdd", errors)
        status = tdd.get("status")
        if status not in {
            "RED_GREEN",
            "ALTERNATIVE_PROOF",
            "NOT_APPLICABLE",
            "BLOCKED",
        }:
            errors.append("tdd.status is invalid")
        if status == "RED_GREEN":
            evidence_ids(
                tdd.get("red_evidence_ids"),
                "tdd.red_evidence_ids",
                evidence,
                errors,
                require_failure=True,
                allow_empty=False,
            )
            evidence_ids(
                tdd.get("green_evidence_ids"),
                "tdd.green_evidence_ids",
                evidence,
                errors,
                require_pass=True,
                allow_empty=False,
            )
        elif status in {"ALTERNATIVE_PROOF", "NOT_APPLICABLE"}:
            nonempty_text(tdd.get("reason"), "tdd.reason", errors)
            if status == "ALTERNATIVE_PROOF":
                evidence_ids(
                    tdd.get("proof_evidence_ids"),
                    "tdd.proof_evidence_ids",
                    evidence,
                    errors,
                    require_pass=True,
                    allow_empty=False,
                )
        elif status == "BLOCKED":
            blockers.append("TDD or alternative proof is blocked")

    elif workflow == "bugfix":
        bug = mapping(report.get("bug"), "bug", errors)
        for field in ("observed", "expected", "root_cause", "fix_boundary"):
            nonempty_text(bug.get(field), f"bug.{field}", errors)
        evidence_ids(
            bug.get("root_cause_evidence_ids"),
            "bug.root_cause_evidence_ids",
            evidence,
            errors,
            allow_empty=False,
        )
        reproduction = mapping(report.get("reproduction"), "reproduction", errors)
        status = reproduction.get("status")
        if status not in {"REPRODUCED", "PROVEN_BY_CONTRACT", "BLOCKED"}:
            errors.append("reproduction.status is invalid")
        if status in {"REPRODUCED", "PROVEN_BY_CONTRACT"}:
            evidence_ids(
                reproduction.get("evidence_ids"),
                "reproduction.evidence_ids",
                evidence,
                errors,
                allow_empty=False,
            )
        else:
            blockers.append("bug reproduction is blocked")
        regression = mapping(report.get("regression_proof"), "regression_proof", errors)
        status = regression.get("status")
        if status not in {"DIFFERENTIAL", "ALTERNATIVE_PROOF", "NOT_PROVEN"}:
            errors.append("regression_proof.status is invalid")
        if status == "DIFFERENTIAL":
            evidence_ids(
                regression.get("failing_evidence_ids"),
                "regression_proof.failing_evidence_ids",
                evidence,
                errors,
                require_failure=True,
                allow_empty=False,
            )
            evidence_ids(
                regression.get("passing_evidence_ids"),
                "regression_proof.passing_evidence_ids",
                evidence,
                errors,
                require_pass=True,
                allow_empty=False,
            )
        elif status == "ALTERNATIVE_PROOF":
            nonempty_text(regression.get("reason"), "regression_proof.reason", errors)
            evidence_ids(
                regression.get("evidence_ids"),
                "regression_proof.evidence_ids",
                evidence,
                errors,
                require_pass=True,
                allow_empty=False,
            )
        else:
            blockers.append("regression proof is missing")

    elif workflow == "refinement":
        claims = sequence(report.get("claims"), "claims", errors)
        if not claims:
            errors.append("claims must not be empty")
        for index, raw in enumerate(claims):
            item = mapping(raw, f"claims[{index}]", errors)
            nonempty_text(item.get("claim"), f"claims[{index}].claim", errors)
            status = item.get("status")
            if status not in {"FACT", "ASSUMPTION", "UNKNOWN"}:
                errors.append(f"claims[{index}].status is invalid")
            if not isinstance(item.get("material"), bool):
                errors.append(f"claims[{index}].material must be boolean")
            ids = evidence_ids(
                item.get("evidence_ids"),
                f"claims[{index}].evidence_ids",
                evidence,
                errors,
            )
            if status == "FACT" and not ids:
                errors.append(f"claims[{index}] fact needs evidence")
            if status == "UNKNOWN":
                probe = item.get("probe")
                if not (isinstance(probe, str) and probe.strip()):
                    errors.append(f"claims[{index}] UNKNOWN requires probe")
            if item.get("material") is True and status != "FACT":
                blockers.append(f"material claim {index} is not proven")
        loopholes = sequence(report.get("loopholes"), "loopholes", errors)
        if not loopholes:
            errors.append("loopholes must not be empty")
        for index, raw in enumerate(loopholes):
            item = mapping(raw, f"loopholes[{index}]", errors)
            nonempty_text(item.get("loophole"), f"loopholes[{index}].loophole", errors)
            status = item.get("status")
            if status not in {"CLOSED", "REJECTED", "OPEN"}:
                errors.append(f"loopholes[{index}].status is invalid")
            if status == "OPEN":
                blockers.append(f"loophole {index} remains open")
            else:
                evidence_ids(
                    item.get("evidence_ids"),
                    f"loopholes[{index}].evidence_ids",
                    evidence,
                    errors,
                    require_pass=True,
                    allow_empty=False,
                )
        verification = sequence(
            report.get("verification_plan"), "verification_plan", errors
        )
        if not verification:
            errors.append("verification_plan must not be empty")
        for index, raw in enumerate(verification):
            item = mapping(raw, f"verification_plan[{index}]", errors)
            nonempty_text(
                item.get("proof"), f"verification_plan[{index}].proof", errors
            )
            status = item.get("status")
            if status not in {
                "PASS",
                "PLANNED",
                "NOT_RUN",
                "BLOCKED",
                "NOT_APPLICABLE",
            }:
                errors.append(f"verification_plan[{index}].status is invalid")
            if status == "PASS":
                evidence_ids(
                    item.get("evidence_ids"),
                    f"verification_plan[{index}].evidence_ids",
                    evidence,
                    errors,
                    require_pass=True,
                    allow_empty=False,
                )
            elif status in {"PLANNED", "NOT_APPLICABLE"}:
                nonempty_text(
                    item.get("reason"), f"verification_plan[{index}].reason", errors
                )
                ids = evidence_ids(
                    item.get("evidence_ids", []),
                    f"verification_plan[{index}].evidence_ids",
                    evidence,
                    errors,
                )
                if status == "PLANNED" and ids:
                    errors.append(
                        f"verification_plan[{index}] PLANNED proof cannot cite executed evidence"
                    )
            else:
                nonempty_text(
                    item.get("reason"), f"verification_plan[{index}].reason", errors
                )
                blockers.append(f"verification item {index} is unresolved")
        if delta:
            blockers.append("refinement workflow changed the workspace")

    elif workflow == "simplification":
        candidates = sequence(report.get("candidates"), "candidates", errors)
        if not candidates:
            errors.append("candidates must not be empty")
        applied = 0
        for index, raw in enumerate(candidates):
            item = mapping(raw, f"candidates[{index}]", errors)
            nonempty_text(
                item.get("opportunity"), f"candidates[{index}].opportunity", errors
            )
            status = item.get("status")
            if status not in {"APPLIED", "SKIPPED", "BLOCKED"}:
                errors.append(f"candidates[{index}].status is invalid")
            if status == "APPLIED":
                applied += 1
                nonempty_text(
                    item.get("complexity_removed"),
                    f"candidates[{index}].complexity_removed",
                    errors,
                )
                evidence_ids(
                    item.get("evidence_ids"),
                    f"candidates[{index}].evidence_ids",
                    evidence,
                    errors,
                    require_pass=True,
                    allow_empty=False,
                )
            elif status == "SKIPPED":
                nonempty_text(item.get("reason"), f"candidates[{index}].reason", errors)
            else:
                blockers.append(f"simplification candidate {index} is blocked")
        report["_applied_candidates"] = applied


def validate(
    expected: str, report: JsonObject, baseline: JsonObject, current: JsonObject
) -> list[str]:
    errors: list[str] = []
    blockers: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if report.get("workflow") != expected:
        errors.append(f"workflow must be {expected}")
    if (
        baseline.get("capture_read_only") is not True
        or current.get("capture_read_only") is not True
    ):
        errors.append("both scope bundles must be read-only captures")
    if baseline.get("repo_root") != current.get("repo_root"):
        errors.append("baseline and current bundles target different repositories")
    if baseline.get("paths") != current.get("paths"):
        errors.append("baseline and current bundles use different path scopes")
    if baseline.get("head_sha") != current.get("head_sha"):
        blockers.append("baseline and current HEAD differ")

    target = mapping(report.get("target"), "target", errors)
    if target.get("baseline_fingerprint") != baseline.get("fingerprint"):
        errors.append("target.baseline_fingerprint does not match baseline bundle")
    if target.get("current_fingerprint") != current.get("fingerprint"):
        errors.append("target.current_fingerprint does not match current bundle")
    if target.get("baseline_head_sha") != baseline.get("head_sha"):
        errors.append("target.baseline_head_sha does not match baseline bundle")
    if target.get("current_head_sha") != current.get("head_sha"):
        errors.append("target.current_head_sha does not match current bundle")
    if target.get("paths") != current.get("paths"):
        errors.append("target.paths does not match scope bundles")

    intent = mapping(report.get("intent"), "intent", errors)
    nonempty_text(intent.get("goal"), "intent.goal", errors)
    nonempty_text(intent.get("owner_boundary"), "intent.owner_boundary", errors)
    string_list(
        intent.get("must_not_change"),
        "intent.must_not_change",
        errors,
        allow_empty=False,
    )
    string_list(
        intent.get("invariants"), "intent.invariants", errors, allow_empty=False
    )
    if not isinstance(intent.get("user_visible"), bool):
        errors.append("intent.user_visible must be boolean")

    before = file_map(baseline, "baseline", errors)
    after = file_map(current, "current", errors)
    delta = changed_paths(before, after)
    fingerprints_match = baseline.get("fingerprint") == current.get("fingerprint")
    if delta and fingerprints_match:
        errors.append("scope fingerprint did not change with the file delta")
    elif not delta and not fingerprints_match:
        blockers.append("scope fingerprint changed without a file delta")
    scope = mapping(report.get("scope"), "scope", errors)
    initial_owned = string_list(
        scope.get("initial_owned_paths"), "scope.initial_owned_paths", errors
    )
    current_owned = string_list(
        scope.get("current_owned_paths"), "scope.current_owned_paths", errors
    )
    for path in initial_owned + current_owned:
        if Path(path).is_absolute() or ".." in Path(path).parts:
            errors.append(f"owned path must be repository-relative: {path}")
    outside = delta - set(current_owned)
    if outside:
        blockers.append(f"scope changed outside owned paths: {sorted(outside)}")
    protected = set(before) - set(current_owned)
    modified_protected = {
        path for path in protected if before.get(path) != after.get(path)
    }
    if modified_protected:
        blockers.append(
            f"pre-existing dirty work changed: {sorted(modified_protected)}"
        )
    approved = scope.get("scope_expansion_approved")
    if not isinstance(approved, bool):
        errors.append("scope.scope_expansion_approved must be boolean")
        approved = False
    if expected == "refinement":
        if initial_owned or current_owned:
            errors.append("refinement workflow must use empty owned paths")
        if approved is not False:
            errors.append("refinement workflow requires scope_expansion_approved=false")
    cycle = scope.get("cycle")
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 1:
        errors.append("scope.cycle must be a positive integer")
    elif cycle > 2 and scope.get("new_evidence") is not True:
        blockers.append("workflow exceeded two cycles without new evidence")

    coverage_paths: list[str] = []
    for index, raw in enumerate(
        sequence(report.get("file_coverage"), "file_coverage", errors)
    ):
        item = mapping(raw, f"file_coverage[{index}]", errors)
        path = nonempty_text(item.get("path"), f"file_coverage[{index}].path", errors)
        nonempty_text(item.get("reason"), f"file_coverage[{index}].reason", errors)
        if path:
            coverage_paths.append(path)
    if len(coverage_paths) != len(set(coverage_paths)):
        errors.append("file_coverage repeats a path")
    if set(coverage_paths) != delta:
        errors.append(
            f"file_coverage must equal scope delta; expected {sorted(delta)}, got {sorted(coverage_paths)}"
        )

    evidence: dict[str, JsonObject] = {}
    evidence_items = sequence(report.get("evidence"), "evidence", errors)
    if not evidence_items:
        errors.append("evidence must not be empty")
    plan_evidence = None
    if any(isinstance(raw, dict) and "plan_ref" in raw for raw in evidence_items):
        plan_evidence = load_plan_evidence(report.get("plan_report"), errors)
    for index, raw in enumerate(evidence_items):
        item = mapping(raw, f"evidence[{index}]", errors)
        evidence_id = nonempty_text(item.get("id"), f"evidence[{index}].id", errors)
        if evidence_id in evidence:
            errors.append(f"evidence repeats id {evidence_id}")
        elif evidence_id:
            evidence[evidence_id] = item
        if item.get("status") not in {"PASS", "FAIL", "NOT_RUN"}:
            errors.append(f"evidence[{index}].status is invalid")
        if item.get("classification") not in {
            "TARGET",
            "INTRODUCED",
            "BASELINE",
            "ENVIRONMENT",
            "EXTERNAL",
        }:
            errors.append(f"evidence[{index}].classification is invalid")
        nonempty_text(item.get("detail"), f"evidence[{index}].detail", errors)
        if "plan_ref" in item:
            check_plan_ref(item, f"evidence[{index}]", plan_evidence, current, errors)
        if item.get("status") == "FAIL" and item.get("classification") == "INTRODUCED":
            blockers.append(f"introduced failure {evidence_id}")

    # Refinement may omit scenarios and gates: loopholes and verification_plan
    # (both mandatory) carry that duty for a read-only strategy review.
    scenarios = sequence(report.get("scenarios"), "scenarios", errors)
    if not scenarios and expected != "refinement":
        errors.append("scenarios must not be empty")
    for index, raw in enumerate(scenarios):
        item = mapping(raw, f"scenarios[{index}]", errors)
        nonempty_text(item.get("behavior"), f"scenarios[{index}].behavior", errors)
        status = item.get("status")
        if status not in {"PROVEN", "MISSING_REQUIRED", "OPTIONAL", "NOT_APPLICABLE"}:
            errors.append(f"scenarios[{index}].status is invalid")
        if status == "PROVEN":
            evidence_ids(
                item.get("evidence_ids"),
                f"scenarios[{index}].evidence_ids",
                evidence,
                errors,
                require_pass=True,
                allow_empty=False,
            )
        else:
            nonempty_text(item.get("reason"), f"scenarios[{index}].reason", errors)
            if status == "MISSING_REQUIRED":
                blockers.append(f"required scenario {index} is unproven")

    behavior = mapping(report.get("behavior_proof"), "behavior_proof", errors)
    behavior_status = behavior.get("status")
    if behavior_status not in {"PROVEN", "NOT_PROVEN", "NOT_APPLICABLE"}:
        errors.append("behavior_proof.status is invalid")
    if behavior_status == "PROVEN":
        evidence_ids(
            behavior.get("evidence_ids"),
            "behavior_proof.evidence_ids",
            evidence,
            errors,
            require_pass=True,
            allow_empty=False,
        )
    else:
        nonempty_text(behavior.get("reason"), "behavior_proof.reason", errors)
    if intent.get("user_visible") is True and behavior_status != "PROVEN":
        blockers.append("user-visible behavior is not proven")

    gates = sequence(report.get("gates"), "gates", errors)
    if not gates and expected != "refinement":
        errors.append("gates must not be empty")
    for index, raw in enumerate(gates):
        item = mapping(raw, f"gates[{index}]", errors)
        nonempty_text(item.get("name"), f"gates[{index}].name", errors)
        if not isinstance(item.get("mandatory"), bool):
            errors.append(f"gates[{index}].mandatory must be boolean")
        status = item.get("status")
        if status not in {"PASS", "FAIL", "NOT_RUN", "NOT_APPLICABLE"}:
            errors.append(f"gates[{index}].status is invalid")
        if status == "PASS":
            evidence_ids(
                item.get("evidence_ids"),
                f"gates[{index}].evidence_ids",
                evidence,
                errors,
                require_pass=True,
                allow_empty=False,
            )
        else:
            nonempty_text(item.get("reason"), f"gates[{index}].reason", errors)
        if item.get("mandatory") is True and status != "PASS":
            blockers.append(f"mandatory gate {item.get('name', index)} did not pass")

    for index, raw in enumerate(
        sequence(report.get("external_actions"), "external_actions", errors)
    ):
        item = mapping(raw, f"external_actions[{index}]", errors)
        nonempty_text(item.get("kind"), f"external_actions[{index}].kind", errors)
        requested = item.get("requested")
        if not isinstance(requested, bool):
            errors.append(f"external_actions[{index}].requested must be boolean")
        status = item.get("status")
        if status not in {"NOT_REQUESTED", "DRAFTED", "PUBLISHED", "BLOCKED"}:
            errors.append(f"external_actions[{index}].status is invalid")
        if status == "PUBLISHED":
            if requested is not True:
                errors.append(
                    f"external_actions[{index}] published without explicit request"
                )
            evidence_ids(
                item.get("evidence_ids"),
                f"external_actions[{index}].evidence_ids",
                evidence,
                errors,
                require_pass=True,
                allow_empty=False,
            )
        elif requested is False and status not in {"NOT_REQUESTED", "DRAFTED"}:
            errors.append(
                f"external_actions[{index}] status contradicts requested=false"
            )

    validate_domain(expected, report, evidence, delta, blockers, errors)

    decision = mapping(report.get("decision"), "decision", errors)
    result = decision.get("result")
    if result not in DECISIONS[expected]:
        errors.append(f"decision.result is invalid for {expected}")
    remaining = string_list(decision.get("remaining"), "decision.remaining", errors)
    is_complete = result in COMPLETION[expected]
    if is_complete and blockers:
        errors.append(f"completion contradicts blockers: {sorted(set(blockers))}")
    if is_complete and remaining:
        errors.append("completed decision must not list remaining work")
    if not is_complete and not remaining:
        errors.append("non-complete decision must list remaining work")
    if expected == "simplification":
        applied = report.pop("_applied_candidates", 0)
        if result == "NO_CHANGE" and (delta or applied):
            errors.append("NO_CHANGE contradicts applied candidates or scope delta")
        if result == "SIMPLEST_DEFENSIBLE" and not delta and not applied:
            errors.append("use NO_CHANGE when no simplification was applied")
        if delta and behavior_status != "PROVEN":
            errors.append("changed simplification requires proven behavior")
    return errors


def placeholder_report(workflow: str) -> JsonObject:
    """Refinement skeleton: enum placeholders and empty or null values fail until replaced."""
    return {
        "schema_version": 1,
        "workflow": workflow,
        "target": {},
        "intent": {
            "goal": "",
            "must_not_change": [],
            "invariants": [],
            "owner_boundary": "",
            "user_visible": None,
        },
        "scope": {
            "initial_owned_paths": [],
            "current_owned_paths": [],
            "cycle": 1,
            "scope_expansion_approved": False,
        },
        "file_coverage": [],
        "evidence": [
            {
                "id": "",
                "status": "PASS|FAIL|NOT_RUN",
                "classification": "TARGET|INTRODUCED|BASELINE|ENVIRONMENT|EXTERNAL",
                "detail": "",
            }
        ],
        "claims": [
            {
                "claim": "",
                "status": "FACT|ASSUMPTION|UNKNOWN",
                "material": None,
                "evidence_ids": [],
                "probe": "",
            }
        ],
        "loopholes": [
            {"loophole": "", "status": "CLOSED|REJECTED|OPEN", "evidence_ids": []}
        ],
        "verification_plan": [
            {
                "proof": "",
                "status": "PASS|PLANNED|NOT_RUN|BLOCKED|NOT_APPLICABLE",
                "evidence_ids": [],
                "reason": "",
            }
        ],
        "scenarios": [],
        "behavior_proof": {
            "status": "PROVEN|NOT_PROVEN|NOT_APPLICABLE",
            "evidence_ids": [],
            "reason": "",
        },
        "gates": [],
        "external_actions": [],
        "decision": {"result": "|".join(sorted(DECISIONS[workflow])), "remaining": []},
    }


def carry_forward(workflow: str, prior: JsonObject, report: JsonObject) -> None:
    """Carry intent, scope, and ledger text to a new baseline; evidence never carries.

    Claims, loopholes, and verifications lose their evidence and fall back to
    unproven statuses, so the new baseline must earn every conclusion again.
    """
    if prior.get("workflow") != workflow:
        raise ValueError(f"--from report must be a {workflow} report")
    scope = prior.get("scope")
    cycle = scope.get("cycle") if isinstance(scope, dict) else None
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 1:
        raise ValueError("--from report needs a positive scope.cycle")
    if isinstance(prior.get("intent"), dict):
        report["intent"] = prior["intent"]
    report["scope"]["cycle"] = cycle + 1

    def authored(key: str, field: str) -> list[JsonObject]:
        items = prior.get(key)
        return [
            item
            for item in (items if isinstance(items, list) else [])
            if isinstance(item, dict) and isinstance(item.get(field), str) and item[field]
        ]

    claims = [
        {
            "claim": item["claim"],
            "status": "FACT|ASSUMPTION|UNKNOWN",
            "material": item.get("material") if isinstance(item.get("material"), bool) else None,
            "evidence_ids": [],
            "probe": item.get("probe", ""),
        }
        for item in authored("claims", "claim")
    ]
    loopholes = [
        {"loophole": item["loophole"], "status": "OPEN", "evidence_ids": []}
        for item in authored("loopholes", "loophole")
    ]
    verifications = [
        {
            "proof": item["proof"],
            "status": "NOT_RUN" if item.get("status") == "PASS" else item.get("status"),
            "evidence_ids": [],
            "reason": item.get("reason") or "re-prove on the new baseline",
        }
        for item in authored("verification_plan", "proof")
    ]
    for key, items in (
        ("claims", claims), ("loopholes", loopholes), ("verification_plan", verifications)
    ):
        if items:
            report[key] = items


def scaffold(
    workflow: str,
    baseline: JsonObject,
    current: JsonObject,
    existing: JsonObject | None,
    prior: JsonObject | None = None,
) -> JsonObject:
    errors: list[str] = []
    delta = sorted(
        changed_paths(
            file_map(baseline, "baseline", errors), file_map(current, "current", errors)
        )
    )
    if errors:
        raise ValueError("; ".join(errors))
    report = placeholder_report(workflow)
    if prior is not None:
        carry_forward(workflow, prior, report)
    reasons: dict[str, Any] = {}
    if existing is not None:
        if existing.get("workflow", workflow) != workflow:
            raise ValueError(f"existing report must be a {workflow} report")
        # A refresh keeps its baseline; merging a report from another baseline
        # would keep its stale evidence and decision.
        existing_target = existing.get("target")
        if not isinstance(existing_target, dict) or (
            existing_target.get("baseline_fingerprint"),
            existing_target.get("baseline_head_sha"),
        ) != (baseline.get("fingerprint"), baseline.get("head_sha")):
            raise ValueError(
                "REPORT belongs to another baseline; move it aside and pass --from <moved file>"
            )
        report.update(existing)
        coverage = existing.get("file_coverage")
        for item in coverage if isinstance(coverage, list) else []:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                reasons[item["path"]] = item.get("reason", "")
    report["schema_version"] = 1
    report["workflow"] = workflow
    report["target"] = {
        "baseline_fingerprint": baseline.get("fingerprint"),
        "current_fingerprint": current.get("fingerprint"),
        "baseline_head_sha": baseline.get("head_sha"),
        "current_head_sha": current.get("head_sha"),
        "paths": current.get("paths"),
    }
    report["file_coverage"] = [
        {"path": path, "reason": reasons.get(path, "")} for path in delta
    ]
    return report


def main() -> int:
    expected = WORKFLOWS.get(Path(__file__).resolve().parents[1].name)
    if expected is None:
        print(
            "ERROR: validator is outside a recognized skill directory", file=sys.stderr
        )
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument(
        "--current", type=Path, help="Required to validate; --scaffold defaults it to --baseline."
    )
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Write or refresh REPORT: recompute target and file_coverage, keep authored fields.",
    )
    parser.add_argument(
        "--from",
        dest="prior",
        type=Path,
        help="With --scaffold: carry intent, scope, and ledger text (no evidence) from a prior report; increments scope.cycle.",
    )
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.prior is not None and not args.scaffold:
        parser.error("--from requires --scaffold")
    if args.prior is not None and args.prior.resolve() == args.report.resolve():
        parser.error("--from must name the prior report, not REPORT")
    if args.current is None and not args.scaffold:
        parser.error("--current is required unless --scaffold is used")
    try:
        baseline = load_json(args.baseline)
        current = load_json(args.current) if args.current is not None else baseline
        if args.scaffold:
            existing = load_json(args.report) if args.report.exists() else None
            prior = load_json(args.prior) if args.prior is not None else None
            report = scaffold(expected, baseline, current, existing, prior)
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(
                f"SCAFFOLD: {args.report} ({len(report['file_coverage'])} delta path(s)); "
                "replace every placeholder and empty value, then validate"
            )
            return 0
        report = load_json(args.report)
        errors = validate(expected, report, baseline, current)
    except (OSError, ValueError, json.JSONDecodeError) as exception:
        print(f"ERROR: {exception}", file=sys.stderr)
        return 2
    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1
    print(f"PASS: {expected} report is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
