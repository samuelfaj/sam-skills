#!/usr/bin/env python3
"""Validate a workflow report against immutable baseline/current scope bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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
    if len(current_owned) > 2 * max(1, len(initial_owned)) and not approved:
        blockers.append("owned scope expanded beyond two times the frozen baseline")
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
        if item.get("status") == "FAIL" and item.get("classification") == "INTRODUCED":
            blockers.append(f"introduced failure {evidence_id}")

    scenarios = sequence(report.get("scenarios"), "scenarios", errors)
    if not scenarios:
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
    if not gates:
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


def main() -> int:
    expected = WORKFLOWS.get(Path(__file__).resolve().parents[1].name)
    if expected is None:
        print(
            "ERROR: validator is outside a recognized skill directory", file=sys.stderr
        )
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        report = load_json(args.report)
        baseline = load_json(args.baseline)
        current = load_json(args.current)
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
