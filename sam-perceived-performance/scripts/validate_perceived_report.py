#!/usr/bin/env python3
"""Validate a perceived-performance report against scope bundles and receipts.

A report is VALID only if the illusion is measured, honest, and reversible:

- every timing claim recomputes against the same budget table the gate executed;
- every measurement and test is backed by a run_checked.py receipt;
- an optimistic outcome carries a proven rollback and a real failure surface;
- determinate progress is derived from a real signal, never synthesized;
- the real interaction did not get slower in order to feel faster;
- the workspace changed only inside owned paths.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Import siblings without leaving bytecode inside the installed skill package.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from classify_latency import (  # noqa: E402
    INSTANT_FEEDBACK_MS,
    MAX_ADDED_DELAY_MS,
    MIN_SAMPLES,
    budget_errors,
    classify,
    regression_budget_ms,
)
from verify_receipts import verify_commands  # noqa: E402

JsonObject = dict[str, Any]

DECISIONS = {"PERCEIVED_INSTANT", "IMPROVED", "NO_CHANGE", "BLOCKED"}
COMPLETION = {"PERCEIVED_INSTANT", "IMPROVED", "NO_CHANGE"}
# Only executed proof can close a gate; an inspection is context, not evidence.
RECEIPTED_KINDS = {"MEASUREMENT", "TEST"}
EVIDENCE_KINDS = RECEIPTED_KINDS | {"INSPECTION"}
CLASSIFICATIONS = {"TARGET", "INTRODUCED", "BASELINE", "ENVIRONMENT", "EXTERNAL"}
ENVIRONMENT_KINDS = {"unknown", "local", "test", "dev", "staging", "production"}
METRIC_FIELDS = ("feedback_ms", "meaningful_ms", "settled_ms", "dead_time_ms")
REQUIRED_GATES = (
    "honest-feedback",
    "real-latency-non-regression",
    "failure-path-proof",
    "accessibility-announcement",
)
PROGRESS_SIGNALS = {"REAL", "SYNTHETIC", "NONE"}
PROGRESS_PRESENTATIONS = {"DETERMINATE", "INDETERMINATE", "NONE"}


def load_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
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


def integer(value: Any, label: str, errors: list[str]) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors.append(f"{label} must be a non-negative integer")
        return 0
    return value


def boolean(value: Any, label: str, errors: list[str]) -> bool:
    if not isinstance(value, bool):
        errors.append(f"{label} must be boolean")
        return False
    return value


def table(
    report: JsonObject, name: str, prefix: str, errors: list[str]
) -> dict[str, JsonObject]:
    result: dict[str, JsonObject] = {}
    items = sequence(report.get(name), name, errors)
    for index, raw in enumerate(items):
        item = mapping(raw, f"{name}[{index}]", errors)
        item_id = item.get("id")
        if not isinstance(item_id, str) or not re.fullmatch(
            rf"{re.escape(prefix)}\d{{3,}}", item_id
        ):
            errors.append(f"invalid {name} id: {item_id!r}")
            continue
        if item_id in result:
            errors.append(f"duplicate {name} id: {item_id}")
            continue
        result[item_id] = item
    return result


def file_map(bundle: JsonObject, label: str, errors: list[str]) -> dict[str, JsonObject]:
    result: dict[str, JsonObject] = {}
    for index, raw in enumerate(sequence(bundle.get("files"), f"{label}.files", errors)):
        item = mapping(raw, f"{label}.files[{index}]", errors)
        path = nonempty_text(item.get("path"), f"{label}.files[{index}].path", errors)
        if path:
            result[path] = item
    return result


def cited(
    value: Any,
    label: str,
    evidence: dict[str, JsonObject],
    errors: list[str],
    *,
    require_pass: bool = False,
    allow_empty: bool = True,
) -> list[str]:
    """Resolve evidence citations; proof citations must be executed and passing."""
    ids = string_list(value, label, errors, allow_empty=allow_empty)
    for evidence_id in ids:
        item = evidence.get(evidence_id)
        if item is None:
            errors.append(f"{label} references unknown evidence {evidence_id}")
            continue
        if require_pass:
            if item.get("kind") not in RECEIPTED_KINDS:
                errors.append(
                    f"{label} cites {evidence_id} of kind {item.get('kind')!r}; proof "
                    "requires executed MEASUREMENT or TEST evidence"
                )
            if item.get("status") != "PASS":
                errors.append(f"{label} requires passing evidence {evidence_id}")
    return ids


def owned_by(path: str, owned: list[str]) -> bool:
    candidate = Path(path)
    for entry in owned:
        if path == entry:
            return True
        try:
            candidate.relative_to(Path(entry))
        except ValueError:
            continue
        return True
    return False


def validate_metrics(
    block: Any,
    label: str,
    evidence: dict[str, JsonObject],
    errors: list[str],
    *,
    enforce_budget: bool = True,
) -> dict[str, int]:
    item = mapping(block, label, errors)
    values = {
        field: integer(item.get(field), f"{label}.{field}", errors)
        for field in METRIC_FIELDS
    }
    samples = integer(item.get("samples"), f"{label}.samples", errors)
    if samples < MIN_SAMPLES:
        errors.append(
            f"{label}.samples is {samples}; timing claims need at least {MIN_SAMPLES} "
            "samples to survive wall-clock noise"
        )
    cited(
        item.get("evidence_ids"),
        f"{label}.evidence_ids",
        evidence,
        errors,
        require_pass=True,
        allow_empty=False,
    )
    errors.extend(
        budget_errors(
            label,
            values["settled_ms"],
            values["feedback_ms"],
            values["dead_time_ms"],
            values["meaningful_ms"],
            enforce_budget=enforce_budget,
        )
    )
    values["samples"] = samples
    return values


def validate_techniques(
    techniques: dict[str, JsonObject],
    interaction_ids: set[str],
    evidence: dict[str, JsonObject],
    owned: list[str],
    delta: set[str],
    errors: list[str],
    blockers: list[str],
) -> dict[str, set[str]]:
    """Check every technique and return applied/optimistic id sets."""
    applied: set[str] = set()
    optimistic_applied: set[str] = set()
    for technique_id, item in sorted(techniques.items()):
        nonempty_text(item.get("name"), f"{technique_id}.name", errors)
        status = item.get("status")
        if status not in {"APPLIED", "REJECTED", "BLOCKED"}:
            errors.append(f"{technique_id}.status is invalid")
        for linked_id in string_list(
            item.get("interaction_ids"),
            f"{technique_id}.interaction_ids",
            errors,
            allow_empty=False,
        ):
            if linked_id not in interaction_ids:
                errors.append(
                    f"{technique_id} references unknown interaction {linked_id}"
                )
        is_optimistic = boolean(item.get("optimistic"), f"{technique_id}.optimistic", errors)
        irreversible = boolean(
            item.get("irreversible_effect"), f"{technique_id}.irreversible_effect", errors
        )
        signal = item.get("progress_signal")
        presentation = item.get("progress_presentation")
        if signal not in PROGRESS_SIGNALS:
            errors.append(f"{technique_id}.progress_signal is invalid")
        if presentation not in PROGRESS_PRESENTATIONS:
            errors.append(f"{technique_id}.progress_presentation is invalid")
        if presentation == "DETERMINATE" and signal != "REAL":
            errors.append(
                f"{technique_id} presents determinate progress from a "
                f"{signal!r} signal; fake progress is never allowed"
            )
        if signal == "NONE" and presentation != "NONE":
            errors.append(
                f"{technique_id} shows progress with no underlying signal"
            )
        added_delay = integer(item.get("added_delay_ms"), f"{technique_id}.added_delay_ms", errors)
        if added_delay > MAX_ADDED_DELAY_MS:
            errors.append(
                f"{technique_id} adds {added_delay}ms of artificial delay; the "
                f"anti-flicker ceiling is {MAX_ADDED_DELAY_MS}ms"
            )
        if added_delay > 0:
            nonempty_text(
                item.get("added_delay_reason"),
                f"{technique_id}.added_delay_reason",
                errors,
            )

        if status != "APPLIED":
            nonempty_text(item.get("reason"), f"{technique_id}.reason", errors)
            if status == "BLOCKED":
                blockers.append(f"technique {technique_id} is blocked")
            continue

        applied.add(technique_id)
        paths = string_list(item.get("paths"), f"{technique_id}.paths", errors, allow_empty=False)
        for path in paths:
            if Path(path).is_absolute() or ".." in Path(path).parts:
                errors.append(f"{technique_id} path must be repository-relative: {path}")
            elif not owned_by(path, owned):
                blockers.append(f"{technique_id} changed unowned path {path}")
            elif path not in delta:
                errors.append(
                    f"{technique_id} is APPLIED but {path} did not change"
                )
        nonempty_text(item.get("accessibility"), f"{technique_id}.accessibility", errors)
        cited(
            item.get("evidence_ids"),
            f"{technique_id}.evidence_ids",
            evidence,
            errors,
            require_pass=True,
            allow_empty=False,
        )
        if not is_optimistic:
            continue
        optimistic_applied.add(technique_id)
        for field in ("failure_mode", "rollback", "on_failure_ui"):
            nonempty_text(item.get(field), f"{technique_id}.{field}", errors)
        if not boolean(item.get("reversible"), f"{technique_id}.reversible", errors):
            errors.append(
                f"{technique_id} shows an unconfirmed outcome it cannot take back"
            )
        if irreversible:
            errors.append(
                f"{technique_id} shows an unconfirmed outcome for an irreversible "
                "effect; reject the optimistic path instead"
            )
        cited(
            item.get("failure_path_evidence_ids"),
            f"{technique_id}.failure_path_evidence_ids",
            evidence,
            errors,
            require_pass=True,
            allow_empty=False,
        )
    return {"applied": applied, "optimistic": optimistic_applied}


def validate_interactions(
    interactions: dict[str, JsonObject],
    techniques: dict[str, JsonObject],
    applied: set[str],
    evidence: dict[str, JsonObject],
    errors: list[str],
    blockers: list[str],
) -> set[str]:
    improved: set[str] = set()
    for interaction_id, item in sorted(interactions.items()):
        for field in ("name", "entry_point", "trigger", "blocking_work"):
            nonempty_text(item.get(field), f"{interaction_id}.{field}", errors)
        linked = string_list(item.get("technique_ids"), f"{interaction_id}.technique_ids", errors)
        for technique_id in linked:
            technique = techniques.get(technique_id)
            if technique is None:
                errors.append(f"{interaction_id} references unknown technique {technique_id}")
                continue
            backlinks = technique.get("interaction_ids")
            if not isinstance(backlinks, list) or interaction_id not in backlinks:
                errors.append(
                    f"{interaction_id} -> {technique_id} missing reciprocal "
                    "interaction_ids link"
                )
        linked_applied = [technique_id for technique_id in linked if technique_id in applied]

        status = item.get("status")
        if status not in {"IMPROVED", "UNCHANGED", "BLOCKED"}:
            errors.append(f"{interaction_id}.status is invalid")
            continue
        if status == "BLOCKED":
            # An unmeasurable interaction cannot be asked for passing measurements;
            # it blocks the decision instead.
            nonempty_text(item.get("reason"), f"{interaction_id}.reason", errors)
            blockers.append(f"{interaction_id} is blocked")
            continue

        baseline = validate_metrics(
            item.get("baseline"),
            f"{interaction_id}.baseline",
            evidence,
            errors,
            enforce_budget=False,
        )
        after = validate_metrics(
            item.get("after"), f"{interaction_id}.after", evidence, errors
        )
        increase = after["settled_ms"] - baseline["settled_ms"]
        allowed = regression_budget_ms(baseline["settled_ms"])
        if increase > allowed:
            blockers.append(
                f"{interaction_id} real latency regressed by {increase}ms; budget is "
                f"{allowed}ms"
            )

        if status == "IMPROVED":
            improved.add(interaction_id)
            if not linked_applied:
                errors.append(f"{interaction_id} claims IMPROVED with no applied technique")
            if after["feedback_ms"] >= baseline["feedback_ms"]:
                errors.append(
                    f"{interaction_id} claims IMPROVED but first feedback did not get "
                    f"earlier ({baseline['feedback_ms']}ms -> {after['feedback_ms']}ms)"
                )
        else:
            nonempty_text(item.get("reason"), f"{interaction_id}.reason", errors)
            if linked_applied:
                errors.append(
                    f"{interaction_id} claims UNCHANGED while citing applied "
                    f"technique(s) {sorted(linked_applied)}"
                )
    return improved


def validate_gates(
    report: JsonObject,
    evidence: dict[str, JsonObject],
    applied: set[str],
    optimistic: set[str],
    errors: list[str],
    blockers: list[str],
) -> None:
    seen: dict[str, JsonObject] = {}
    for index, raw in enumerate(sequence(report.get("gates"), "gates", errors)):
        item = mapping(raw, f"gates[{index}]", errors)
        name = nonempty_text(item.get("name"), f"gates[{index}].name", errors)
        if name in seen:
            errors.append(f"gates repeats {name}")
        elif name:
            seen[name] = item
        status = item.get("status")
        if status not in {"PASS", "FAIL", "NOT_RUN", "NOT_APPLICABLE"}:
            errors.append(f"gates[{index}].status is invalid")
        if status == "PASS":
            cited(
                item.get("evidence_ids"),
                f"gates[{index}].evidence_ids",
                evidence,
                errors,
                require_pass=True,
                allow_empty=False,
            )
        else:
            nonempty_text(item.get("reason"), f"gates[{index}].reason", errors)
        if boolean(item.get("mandatory"), f"gates[{index}].mandatory", errors):
            if status in {"FAIL", "NOT_RUN"}:
                blockers.append(f"mandatory gate {name or index} did not pass")

    # Applicability is derived, so a gate cannot be waived by declaring it moot.
    applicable = {
        "honest-feedback": True,
        "real-latency-non-regression": True,
        "failure-path-proof": bool(optimistic),
        "accessibility-announcement": bool(applied),
    }
    for name in REQUIRED_GATES:
        item = seen.get(name)
        if item is None:
            errors.append(f"gates must include the mandatory gate {name}")
            continue
        if item.get("mandatory") is not True:
            errors.append(f"gate {name} must be declared mandatory")
        if applicable[name] and item.get("status") == "NOT_APPLICABLE":
            errors.append(
                f"gate {name} is applicable to this change and cannot be "
                "NOT_APPLICABLE"
            )


def validate(report: JsonObject, baseline: JsonObject, current: JsonObject) -> list[str]:
    errors: list[str] = []
    blockers: list[str] = []

    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if report.get("workflow") != "perceived-performance":
        errors.append("workflow must be perceived-performance")
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
    if target.get("paths") != current.get("paths"):
        errors.append("target.paths does not match scope bundles")

    intent = mapping(report.get("intent"), "intent", errors)
    nonempty_text(intent.get("goal"), "intent.goal", errors)
    nonempty_text(intent.get("owner_boundary"), "intent.owner_boundary", errors)
    string_list(intent.get("must_not_change"), "intent.must_not_change", errors, allow_empty=False)
    string_list(intent.get("invariants"), "intent.invariants", errors, allow_empty=False)

    environment = mapping(report.get("environment"), "environment", errors)
    if environment.get("kind") not in ENVIRONMENT_KINDS:
        errors.append("environment.kind is invalid")
    for field in ("identity", "device_profile", "network_profile"):
        nonempty_text(environment.get(field), f"environment.{field}", errors)

    evidence = table(report, "evidence", "E-", errors)
    if not evidence:
        errors.append("evidence must not be empty")
    receipted: list[JsonObject] = []
    for evidence_id, item in sorted(evidence.items()):
        kind = item.get("kind")
        if kind not in EVIDENCE_KINDS:
            errors.append(f"{evidence_id}.kind is invalid")
        if item.get("status") not in {"PASS", "FAIL", "NOT_RUN"}:
            errors.append(f"{evidence_id}.status is invalid")
        if item.get("classification") not in CLASSIFICATIONS:
            errors.append(f"{evidence_id}.classification is invalid")
        nonempty_text(item.get("detail"), f"{evidence_id}.detail", errors)
        if item.get("status") == "NOT_RUN":
            nonempty_text(item.get("reason"), f"{evidence_id}.reason", errors)
        if kind in RECEIPTED_KINDS:
            receipted.append(item)
        elif item.get("receipt"):
            errors.append(f"{evidence_id} is an INSPECTION and cannot cite a receipt")
        if item.get("status") == "FAIL" and item.get("classification") == "INTRODUCED":
            blockers.append(f"introduced failure {evidence_id}")
    # Recompute every receipt: a typed PASS never closes a gate on its own.
    receipts = verify_commands(receipted, errors)

    before = file_map(baseline, "baseline", errors)
    after_files = file_map(current, "current", errors)
    delta = {
        path
        for path in before.keys() | after_files.keys()
        if before.get(path) != after_files.get(path)
    }
    fingerprints_match = baseline.get("fingerprint") == current.get("fingerprint")
    if delta and fingerprints_match:
        errors.append("scope fingerprint did not change with the file delta")
    elif not delta and not fingerprints_match:
        blockers.append("scope fingerprint changed without a file delta")

    scope = mapping(report.get("scope"), "scope", errors)
    initial_owned = string_list(scope.get("initial_owned_paths"), "scope.initial_owned_paths", errors)
    owned = string_list(scope.get("current_owned_paths"), "scope.current_owned_paths", errors)
    for path in initial_owned + owned:
        if Path(path).is_absolute() or ".." in Path(path).parts:
            errors.append(f"owned path must be repository-relative: {path}")
    outside = {path for path in delta if not owned_by(path, owned)}
    if outside:
        blockers.append(f"scope changed outside owned paths: {sorted(outside)}")
    modified_protected = {
        path
        for path in before
        if not owned_by(path, owned) and before.get(path) != after_files.get(path)
    }
    if modified_protected:
        blockers.append(f"pre-existing dirty work changed: {sorted(modified_protected)}")
    approved = boolean(scope.get("scope_expansion_approved"), "scope.scope_expansion_approved", errors)
    if len(owned) > 2 * max(1, len(initial_owned)) and not approved:
        blockers.append("owned scope expanded beyond two times the frozen baseline")
    cycle = scope.get("cycle")
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 1:
        errors.append("scope.cycle must be a positive integer")
    elif cycle > 2 and scope.get("new_evidence") is not True:
        blockers.append("workflow exceeded two cycles without new evidence")

    coverage: list[str] = []
    for index, raw in enumerate(sequence(report.get("file_coverage"), "file_coverage", errors)):
        item = mapping(raw, f"file_coverage[{index}]", errors)
        path = nonempty_text(item.get("path"), f"file_coverage[{index}].path", errors)
        nonempty_text(item.get("reason"), f"file_coverage[{index}].reason", errors)
        if path:
            coverage.append(path)
    if len(coverage) != len(set(coverage)):
        errors.append("file_coverage repeats a path")
    if set(coverage) != delta:
        errors.append(
            f"file_coverage must equal the scope delta; expected {sorted(delta)}, "
            f"got {sorted(set(coverage))}"
        )

    techniques = table(report, "techniques", "T-", errors)
    interactions = table(report, "interactions", "I-", errors)
    if not interactions:
        errors.append("interactions must not be empty")
    sets = validate_techniques(
        techniques, set(interactions), evidence, owned, delta, errors, blockers
    )
    applied, optimistic = sets["applied"], sets["optimistic"]
    improved = validate_interactions(
        interactions, techniques, applied, evidence, errors, blockers
    )
    validate_gates(report, evidence, applied, optimistic, errors, blockers)
    if delta and not applied:
        errors.append("the workspace changed but no technique is APPLIED")

    decision = mapping(report.get("decision"), "decision", errors)
    result = decision.get("result")
    if result not in DECISIONS:
        errors.append("decision.result is invalid")
    remaining = string_list(decision.get("remaining"), "decision.remaining", errors)
    complete = result in COMPLETION
    if complete and blockers:
        errors.append(f"completion contradicts blockers: {sorted(set(blockers))}")
    if complete and remaining:
        errors.append("completed decision must not list remaining work")
    if not complete and not remaining:
        errors.append("non-complete decision must list remaining work")
    if result in {"PERCEIVED_INSTANT", "IMPROVED"}:
        if not improved:
            errors.append(f"{result} requires at least one IMPROVED interaction")
        if receipts["flaky"]:
            errors.append(
                f"{result} rests on flaky evidence: " + ", ".join(receipts["flaky"])
            )
        if receipts["unstable_target"]:
            errors.append(
                f"{result} requires repeated stable TARGET proof; unstable: "
                + ", ".join(receipts["unstable_target"])
            )
    if result == "PERCEIVED_INSTANT":
        for interaction_id in sorted(improved):
            raw_block = interactions[interaction_id].get("after")
            block = raw_block if isinstance(raw_block, dict) else {}
            if not isinstance(block.get("feedback_ms"), int) or block.get("feedback_ms") > INSTANT_FEEDBACK_MS:
                errors.append(
                    f"PERCEIVED_INSTANT requires first feedback within "
                    f"{INSTANT_FEEDBACK_MS}ms for {interaction_id}"
                )
            if block.get("dead_time_ms") != 0:
                errors.append(
                    f"PERCEIVED_INSTANT requires zero unacknowledged pending time for "
                    f"{interaction_id}"
                )
        for interaction_id, item in sorted(interactions.items()):
            if item.get("status") == "BLOCKED":
                errors.append(f"PERCEIVED_INSTANT contradicts blocked {interaction_id}")
    if result == "NO_CHANGE":
        if delta or applied:
            errors.append("NO_CHANGE contradicts applied techniques or a scope delta")
        if improved:
            errors.append("NO_CHANGE contradicts an IMPROVED interaction")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(
            load_json(args.report), load_json(args.baseline), load_json(args.current)
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1
    print("PASS: perceived-performance report is measured, honest, and in scope")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
