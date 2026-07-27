#!/usr/bin/env python3
"""Validate a deterministic sam-orchestrate-claude-grok execution report."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

TASK_CLASSES = {"T0", "T1", "T2", "T3"}
ARTIFACTS = {"CODE", "TEST", "DOCS", "CONFIG", "DATA", "RELEASE", "OTHER"}
KINDS = {"EXECUTION", "ORCHESTRATION", "REVIEW"}
CAPABILITIES = {"LIGHT", "STANDARD", "DEEP", "REVIEWER"}
# Controller is always Claude Code; producers are Grok by default. Hybrid profile.
CONTROLLER_HOST = "claude-code"
WORKER_HOSTS = {"claude-code", "grok"}
RUNTIME_ROLES = {
    "fast_scan",
    "routine_worker",
    "deep_worker",
    "genius_worker",
    "ultra_worker",
    "reviewer",
}
NODE_STATUSES = {"PENDING", "RUNNING", "COMPLETE", "BLOCKED"}
BLOCKER_KINDS = {"EXTERNAL", "AUTHORITY", "USER_DECISION", "DEPENDENCY"}
EVIDENCE_TYPES = {"COMMAND", "DIFF", "FILE", "REMOTE", "USER", "OBSERVATION"}
EVIDENCE_STATUSES = {"PASS", "FAIL", "NOT_RUN", "INFO"}
EVIDENCE_CLASSES = {"TARGET", "BASELINE", "ENVIRONMENT", "EXTERNAL"}
GATE_STATUSES = {"PASS", "FAIL", "NOT_RUN", "NOT_REQUIRED"}
DECISIONS = {"COMPLETE", "BLOCKED", "IN_PROGRESS"}
OWNER_PATTERNS = {
    "EXECUTION": re.compile(r"worker-[1-9][0-9]*\Z"),
    "ORCHESTRATION": re.compile(r"controller-[1-9][0-9]*\Z"),
    "REVIEW": re.compile(r"reviewer-[1-9][0-9]*\Z"),
}
# Free-form owner/identity routing remains forbidden. Structured runtime fields
# and the host matrix document are validated separately.
OWNER_ROUTING = re.compile(
    r"\b(?:model|provider|vendor)[_ -]?(?:name|id)?\s*(?::|=|->)\s*[^\s#]+",
    re.IGNORECASE,
)
PACKAGE_DIR = Path(__file__).resolve().parent.parent
# capability -> (host, role, model, effort)
PROFILE_MATRIX: dict[str, tuple[str, str, str, str]] = {
    "LIGHT": ("grok", "fast_scan", "grok-4.5", "medium"),
    "STANDARD": ("grok", "routine_worker", "grok-4.5", "high"),
    "DEEP": ("grok", "deep_worker", "grok-4.5", "high"),
    "REVIEWER": ("claude-code", "reviewer", "opus", "high"),
    "GENIUS": ("claude-code", "genius_worker", "opus", "xhigh"),
}
MATRIX_MODELS = {row[2] for row in PROFILE_MATRIX.values()}
MATRIX_EFFORTS = {row[3] for row in PROFILE_MATRIX.values()}
MATRIX_HOSTS = {row[0] for row in PROFILE_MATRIX.values()}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON report: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("report root must be an object")
    return value


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


def string_list(
    value: Any, label: str, errors: list[str], *, nonempty: bool = False
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        errors.append(f"{label} must be a list of non-empty strings")
        return []
    if nonempty and not value:
        errors.append(f"{label} must not be empty")
    if len(set(value)) != len(value):
        errors.append(f"{label} must not contain duplicates")
    return value


def object_list(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        errors.append(f"{label} must be a list of objects")
        return []
    return value


def normalized_path(
    value: str, label: str, errors: list[str]
) -> tuple[str, ...] | None:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or "." in path.parts
        or ".." in path.parts
        or path.as_posix() != value
    ):
        errors.append(f"{label} must be a normalized repository-relative path: {value}")
        return None
    return path.parts


def paths_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    size = min(len(left), len(right))
    return left[:size] == right[:size]


def path_within(path: tuple[str, ...], scope: tuple[str, ...]) -> bool:
    return len(path) >= len(scope) and path[: len(scope)] == scope


def neutrality_violations(texts: dict[str, str]) -> list[str]:
    """Return free-form model/provider identity routing outside structured runtime."""
    errors: list[str] = []
    for label, text in texts.items():
        if label.endswith("host-runtime-matrix.md") or label.endswith(
            "output-contract.md"
        ):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if OWNER_ROUTING.search(line):
                errors.append(f"named routing in {label}:{line_number}")
    return errors


def package_neutrality_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for root_name, root in (("canonical", PACKAGE_DIR),):
        candidates = [root / "SKILL.md"]
        for directory, suffix in (("references", ".md"), ("agents", ".yaml")):
            resource_root = root / directory
            if resource_root.is_dir():
                candidates.extend(resource_root.rglob(f"*{suffix}"))
        for path in sorted(set(candidates)):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if relative in {
                "references/host-runtime-matrix.md",
                "references/output-contract.md",
            }:
                continue
            try:
                texts[f"{root_name}/{relative}"] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                texts[f"{root_name}/{relative}"] = "model: unreadable-package-resource"
    return texts


def normalize_role(role: str) -> str:
    if role == "ultra_worker":
        return "genius_worker"
    return role


def validate_runtime_binding(
    runtime: Any,
    *,
    label: str,
    capability: Any,
    active_host: Any,
    errors: list[str],
) -> None:
    if not isinstance(runtime, dict):
        errors.append(f"{label}.runtime must be an object")
        return
    required = {"host", "role", "model", "effort", "fallback_reason"}
    require_keys(runtime, required, required, f"{label}.runtime", errors)
    host = runtime.get("host")
    role = runtime.get("role")
    model = runtime.get("model")
    effort = runtime.get("effort")
    fallback = runtime.get("fallback_reason")
    if host not in WORKER_HOSTS:
        errors.append(f"{label}.runtime.host is invalid for claude-grok profile")
    # Hybrid profile: worker host need not equal controller active_host
    # (active_host is validated on task separately).
    _ = active_host
    if role not in RUNTIME_ROLES:
        errors.append(f"{label}.runtime.role is invalid")
    if not isinstance(model, str) or not model.strip():
        errors.append(f"{label}.runtime.model must be a non-empty string")
    if not isinstance(effort, str) or not effort.strip():
        errors.append(f"{label}.runtime.effort must be a non-empty string")
    if fallback is not None and (
        not isinstance(fallback, str) or not fallback.strip()
    ):
        errors.append(
            f"{label}.runtime.fallback_reason must be null or a non-empty string"
        )
    if capability not in PROFILE_MATRIX:
        return
    expected_host, expected_role, expected_model, expected_effort = PROFILE_MATRIX[
        capability
    ]
    normalized_role = normalize_role(role) if isinstance(role, str) else role
    genius_host, genius_role, genius_model, genius_effort = PROFILE_MATRIX["GENIUS"]
    matches_capability = (
        host == expected_host
        and normalized_role == expected_role
        and model == expected_model
        and effort == expected_effort
    )
    matches_genius = (
        capability in {"STANDARD", "DEEP"}
        and host == genius_host
        and normalized_role == genius_role
        and model == genius_model
        and effort == genius_effort
        and isinstance(fallback, str)
        and bool(fallback.strip())
    )
    if matches_capability or matches_genius:
        return
    if isinstance(fallback, str) and fallback.strip():
        if model not in MATRIX_MODELS:
            errors.append(
                f"{label}.runtime.model is outside the approved claude-grok matrix"
            )
        if effort not in MATRIX_EFFORTS:
            errors.append(
                f"{label}.runtime.effort is outside the approved claude-grok matrix"
            )
        if host not in MATRIX_HOSTS:
            errors.append(
                f"{label}.runtime.host is outside the approved claude-grok matrix"
            )
        return
    errors.append(
        f"{label}.runtime must match host-runtime-matrix for capability {capability}"
    )


def validate(report: dict[str, Any]) -> list[str]:
    errors = neutrality_violations(package_neutrality_texts())
    require_keys(
        report,
        {"schema_version", "task", "dag", "evidence", "review_gate", "decision"},
        {"schema_version", "task", "dag", "evidence", "review_gate", "decision"},
        "report",
        errors,
    )
    if report.get("schema_version") != 2:
        errors.append("schema_version must be 2")

    task = report.get("task")
    if not isinstance(task, dict):
        errors.append("task must be an object")
        task = {}
    task_keys_required = {
        "classification",
        "goal",
        "success_criteria",
        "constraints",
        "no_go",
        "risk_flags",
        "active_host",
        "changed_artifacts",
        "changed_files",
        "review_requested",
    }
    # Optional certainty budget: absolute|high|medium|low (null/omitted → medium).
    task_keys_allowed = task_keys_required | {"controller_certainty"}
    require_keys(task, task_keys_required, task_keys_allowed, "task", errors)
    classification = task.get("classification")
    if classification not in TASK_CLASSES:
        errors.append("task.classification must be T0, T1, T2, or T3")
    active_host = task.get("active_host")
    if active_host != CONTROLLER_HOST:
        errors.append(
            "task.active_host must be claude-code for the claude-grok profile"
        )
    if not isinstance(task.get("goal"), str) or not task.get("goal", "").strip():
        errors.append("task.goal must be a non-empty string")
    string_list(
        task.get("success_criteria"), "task.success_criteria", errors, nonempty=True
    )
    string_list(task.get("constraints"), "task.constraints", errors)
    string_list(task.get("no_go"), "task.no_go", errors, nonempty=True)
    risk_flags = string_list(task.get("risk_flags"), "task.risk_flags", errors)
    review_requested = task.get("review_requested")
    if not isinstance(review_requested, bool):
        errors.append("task.review_requested must be boolean")
        review_requested = False
    controller_certainty_raw = task.get("controller_certainty")
    if controller_certainty_raw is None:
        controller_certainty = "medium"
    elif controller_certainty_raw in {"absolute", "high", "medium", "low"}:
        controller_certainty = controller_certainty_raw
    else:
        errors.append(
            'task.controller_certainty must be omitted, null, or one of '
            '"absolute", "high", "medium", "low"'
        )
        controller_certainty = "medium"
    artifacts = string_list(
        task.get("changed_artifacts"), "task.changed_artifacts", errors
    )
    invalid_artifacts = sorted(set(artifacts) - ARTIFACTS)
    if invalid_artifacts:
        errors.append(
            f"task.changed_artifacts has invalid values: {', '.join(invalid_artifacts)}"
        )

    dag = object_list(report.get("dag"), "dag", errors)
    if not dag:
        errors.append("dag must contain at least one node")
    nodes: dict[str, dict[str, Any]] = {}
    node_paths: dict[str, list[tuple[str, ...]]] = {}
    node_artifacts: dict[str, list[str]] = {}
    node_requirements: dict[str, list[str]] = {}
    node_keys = {
        "id",
        "kind",
        "owner",
        "capability",
        "runtime",
        "depends_on",
        "objective",
        "no_go",
        "proof_requirements",
        "artifact_classes",
        "writable_paths",
        "direct_action_reason",
        "status",
        "evidence_ids",
        "blocker",
    }
    for index, node in enumerate(dag):
        label = f"dag[{index}]"
        require_keys(node, node_keys, node_keys, label, errors)
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"{label}.id must be a non-empty string")
            continue
        if node_id in nodes:
            errors.append(f"duplicate DAG node id: {node_id}")
            continue
        nodes[node_id] = node
        kind = node.get("kind")
        if kind not in KINDS:
            errors.append(f"{label}.kind is invalid")
        owner = node.get("owner")
        if not isinstance(owner, str) or not owner:
            errors.append(f"{label}.owner must be a non-empty string")
        elif kind in OWNER_PATTERNS and not OWNER_PATTERNS[kind].fullmatch(owner):
            errors.append(
                f"{label}.owner must use the neutral {OWNER_PATTERNS[kind].pattern} identity format"
            )
        capability = node.get("capability")
        if capability not in CAPABILITIES:
            errors.append(f"{label}.capability is invalid")
        if kind == "REVIEW" and capability != "REVIEWER":
            errors.append(f"{label} review nodes must use REVIEWER capability")
        if kind != "REVIEW" and capability == "REVIEWER":
            errors.append(f"{label} REVIEWER capability is reserved for review nodes")
        runtime = node.get("runtime")
        if kind in {"EXECUTION", "REVIEW"}:
            validate_runtime_binding(
                runtime,
                label=label,
                capability=capability,
                active_host=active_host,
                errors=errors,
            )
        elif runtime is not None:
            errors.append(f"{label}.runtime must be null for controller orchestration")
        if node.get("status") not in NODE_STATUSES:
            errors.append(f"{label}.status is invalid")
        if (
            not isinstance(node.get("objective"), str)
            or not node.get("objective", "").strip()
        ):
            errors.append(f"{label}.objective must be a non-empty string")
        string_list(node.get("depends_on"), f"{label}.depends_on", errors)
        string_list(node.get("no_go"), f"{label}.no_go", errors, nonempty=True)
        requirements = string_list(
            node.get("proof_requirements"),
            f"{label}.proof_requirements",
            errors,
            nonempty=True,
        )
        node_requirements[node_id] = requirements
        artifact_classes = string_list(
            node.get("artifact_classes"), f"{label}.artifact_classes", errors
        )
        invalid_classes = sorted(set(artifact_classes) - ARTIFACTS)
        if invalid_classes:
            errors.append(
                f"{label}.artifact_classes has invalid values: {', '.join(invalid_classes)}"
            )
        node_artifacts[node_id] = artifact_classes
        writable = string_list(
            node.get("writable_paths"), f"{label}.writable_paths", errors
        )
        parsed_paths: list[tuple[str, ...]] = []
        for path_index, path in enumerate(writable):
            parsed = normalized_path(
                path, f"{label}.writable_paths[{path_index}]", errors
            )
            if parsed is not None:
                parsed_paths.append(parsed)
        node_paths[node_id] = parsed_paths
        if kind == "REVIEW" and parsed_paths:
            errors.append(f"{label} review nodes must be read-only")
        if parsed_paths and kind != "REVIEW" and not artifact_classes:
            errors.append(f"{label} writable nodes must declare artifact_classes")
        if not parsed_paths and artifact_classes:
            errors.append(f"{label} read-only nodes must have empty artifact_classes")
        direct_reason = node.get("direct_action_reason")
        has_reason = isinstance(direct_reason, str) and bool(direct_reason.strip())
        if kind == "ORCHESTRATION" and parsed_paths:
            if not has_reason:
                errors.append(
                    f"{label} writable orchestration requires direct_action_reason"
                )
        elif direct_reason is not None:
            errors.append(
                f"{label}.direct_action_reason must be null outside writable orchestration"
            )
        string_list(node.get("evidence_ids"), f"{label}.evidence_ids", errors)

    dependencies: dict[str, list[str]] = {}
    for node_id, node in nodes.items():
        raw_dependencies = node.get("depends_on")
        dependencies[node_id] = (
            [value for value in raw_dependencies if isinstance(value, str)]
            if isinstance(raw_dependencies, list)
            else []
        )
        for dependency in dependencies[node_id]:
            if dependency not in nodes:
                errors.append(f"node {node_id} depends on unknown node {dependency}")
            if dependency == node_id:
                errors.append(f"node {node_id} cannot depend on itself")

    visit_state: dict[str, int] = {}

    def visit(node_id: str) -> None:
        state = visit_state.get(node_id, 0)
        if state == 1:
            errors.append(f"DAG contains a cycle at node {node_id}")
            return
        if state == 2:
            return
        visit_state[node_id] = 1
        for dependency in dependencies.get(node_id, []):
            if dependency in nodes:
                visit(dependency)
        visit_state[node_id] = 2

    for node_id in nodes:
        visit(node_id)

    def depends_transitively(
        node_id: str, candidate: str, seen: set[str] | None = None
    ) -> bool:
        current_seen = set() if seen is None else seen
        if node_id in current_seen:
            return False
        current_seen.add(node_id)
        for dependency in dependencies.get(node_id, []):
            if dependency == candidate or depends_transitively(
                dependency, candidate, current_seen
            ):
                return True
        return False

    for node_id, node in nodes.items():
        if node.get("status") not in {"RUNNING", "COMPLETE"}:
            continue
        for dependency in dependencies[node_id]:
            if dependency in nodes and nodes[dependency].get("status") != "COMPLETE":
                errors.append(
                    f"{node.get('status')} node {node_id} requires COMPLETE dependency {dependency}"
                )

    execution_nodes = [node for node in dag if node.get("kind") == "EXECUTION"]
    producer_ids = [
        node_id
        for node_id, node in nodes.items()
        if node.get("kind") != "REVIEW" and bool(node_paths.get(node_id))
    ]
    producer_nodes = [nodes[node_id] for node_id in producer_ids]
    if classification in {"T0", "T1"} and len(execution_nodes) != 1:
        errors.append(f"{classification} requires exactly one execution node")
    if classification in {"T2", "T3"} and not execution_nodes:
        errors.append(f"{classification} requires at least one execution node")
    if classification in {"T2", "T3"} and len(execution_nodes) > 3:
        errors.append(f"{classification} allows at most 3 execution nodes (fan-out hard cap)")
    if (
        classification == "T0"
        and execution_nodes
        and execution_nodes[0].get("capability") != "LIGHT"
    ):
        errors.append("T0 execution must use LIGHT capability")
    if (
        classification == "T1"
        and execution_nodes
        and execution_nodes[0].get("capability") not in {"LIGHT", "STANDARD"}
    ):
        errors.append("T1 execution must use LIGHT or STANDARD capability")
    if classification == "T3" and not any(
        node.get("capability") == "DEEP" for node in execution_nodes
    ):
        errors.append("T3 requires a DEEP execution node for the risky slice")
    deep_without_need = [
        node.get("id")
        for node in execution_nodes
        if node.get("capability") == "DEEP"
        and classification != "T3"
        and not risk_flags
    ]
    if deep_without_need:
        errors.append(
            "DEEP capability requires T3 classification or non-empty risk_flags "
            f"(nodes: {', '.join(str(i) for i in deep_without_need)})"
        )

    writable_node_ids = [node_id for node_id, paths in node_paths.items() if paths]
    for left_index, left_id in enumerate(writable_node_ids):
        for right_id in writable_node_ids[left_index + 1 :]:
            overlap = any(
                paths_overlap(left, right)
                for left in node_paths[left_id]
                for right in node_paths[right_id]
            )
            ordered = depends_transitively(left_id, right_id) or depends_transitively(
                right_id, left_id
            )
            if overlap and not ordered:
                errors.append(
                    f"overlapping writable scopes require dependency ordering: {left_id}, {right_id}"
                )

    changed_files = object_list(task.get("changed_files"), "task.changed_files", errors)
    manifest_paths: set[str] = set()
    manifest_by_producer: dict[str, list[dict[str, Any]]] = {
        node_id: [] for node_id in producer_ids
    }
    manifest_classes: set[str] = set()
    changed_file_keys = {"path", "artifact_class", "producer_task_id"}
    for index, item in enumerate(changed_files):
        label = f"task.changed_files[{index}]"
        require_keys(item, changed_file_keys, changed_file_keys, label, errors)
        path_value = item.get("path")
        parsed_path = None
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"{label}.path must be a non-empty string")
        else:
            parsed_path = normalized_path(path_value, f"{label}.path", errors)
            if path_value in manifest_paths:
                errors.append(f"duplicate changed-file path: {path_value}")
            manifest_paths.add(path_value)
        artifact_class = item.get("artifact_class")
        if artifact_class not in ARTIFACTS:
            errors.append(f"{label}.artifact_class is invalid")
        else:
            manifest_classes.add(artifact_class)
        producer_id = item.get("producer_task_id")
        if not isinstance(producer_id, str) or producer_id not in producer_ids:
            errors.append(f"{label}.producer_task_id must reference a producer")
            continue
        manifest_by_producer[producer_id].append(item)
        if artifact_class not in node_artifacts.get(producer_id, []):
            errors.append(
                f"{label}.artifact_class is not declared by producer {producer_id}"
            )
        if parsed_path is not None and not any(
            path_within(parsed_path, scope) for scope in node_paths[producer_id]
        ):
            errors.append(
                f"{label}.path is outside producer {producer_id} writable scope"
            )
    if set(artifacts) != manifest_classes:
        errors.append(
            "task.changed_artifacts must equal the classes in task.changed_files"
        )
    for producer_id in producer_ids:
        if nodes[producer_id].get("status") != "COMPLETE":
            continue
        entries = manifest_by_producer[producer_id]
        if not entries:
            errors.append(
                f"complete producer {producer_id} must own at least one changed file"
            )
            continue
        actual_classes = {
            item.get("artifact_class")
            for item in entries
            if item.get("artifact_class") in ARTIFACTS
        }
        if actual_classes != set(node_artifacts[producer_id]):
            errors.append(
                f"complete producer {producer_id} manifest classes must match artifact_classes"
            )

    evidence = object_list(report.get("evidence"), "evidence", errors)
    evidence_by_id: dict[str, dict[str, Any]] = {}
    evidence_keys = {
        "id",
        "task_id",
        "requirement",
        "type",
        "status",
        "classification",
        "detail",
    }
    for index, item in enumerate(evidence):
        label = f"evidence[{index}]"
        require_keys(item, evidence_keys, evidence_keys, label, errors)
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"{label}.id must be a non-empty string")
            continue
        if evidence_id in evidence_by_id:
            errors.append(f"duplicate evidence id: {evidence_id}")
            continue
        evidence_by_id[evidence_id] = item
        task_id = item.get("task_id")
        if not isinstance(task_id, str) or task_id not in nodes:
            errors.append(f"{label}.task_id must reference an existing DAG node")
        requirement = item.get("requirement")
        if not isinstance(requirement, str) or not requirement:
            errors.append(f"{label}.requirement must be a non-empty string")
        elif isinstance(task_id, str) and task_id in nodes:
            if requirement not in node_requirements.get(task_id, []):
                errors.append(f"{label}.requirement is not declared by node {task_id}")
        if item.get("type") not in EVIDENCE_TYPES:
            errors.append(f"{label}.type is invalid")
        if item.get("status") not in EVIDENCE_STATUSES:
            errors.append(f"{label}.status is invalid")
        if item.get("classification") not in EVIDENCE_CLASSES:
            errors.append(f"{label}.classification is invalid")
        if (
            not isinstance(item.get("detail"), str)
            or not item.get("detail", "").strip()
        ):
            errors.append(f"{label}.detail must be a non-empty string")

    referenced_evidence: set[str] = set()
    for node_id, node in nodes.items():
        raw_ids = node.get("evidence_ids")
        evidence_ids = (
            [value for value in raw_ids if isinstance(value, str)]
            if isinstance(raw_ids, list)
            else []
        )
        referenced_evidence.update(evidence_ids)
        for evidence_id in evidence_ids:
            referenced_item = evidence_by_id.get(evidence_id)
            if referenced_item is None:
                errors.append(
                    f"node {node_id} references unknown evidence {evidence_id}"
                )
            elif referenced_item.get("task_id") != node_id:
                errors.append(
                    f"node {node_id} cannot reference evidence dedicated to {referenced_item.get('task_id')}"
                )
        if node.get("status") == "COMPLETE":
            if not evidence_ids:
                errors.append(f"complete node {node_id} must reference evidence")
            for requirement in node_requirements.get(node_id, []):
                passed = any(
                    evidence_by_id.get(evidence_id, {}).get("task_id") == node_id
                    and evidence_by_id.get(evidence_id, {}).get("requirement")
                    == requirement
                    and evidence_by_id.get(evidence_id, {}).get("classification")
                    == "TARGET"
                    and evidence_by_id.get(evidence_id, {}).get("status") == "PASS"
                    for evidence_id in evidence_ids
                )
                if not passed:
                    errors.append(
                        f"complete node {node_id} lacks dedicated TARGET/PASS proof for: {requirement}"
                    )
    for evidence_id, item in evidence_by_id.items():
        if evidence_id not in referenced_evidence:
            errors.append(
                f"evidence {evidence_id} is not referenced by its task {item.get('task_id')}"
            )

    for node_id, node in nodes.items():
        blocker = node.get("blocker")
        if node.get("status") != "BLOCKED":
            if blocker is not None:
                errors.append(f"non-blocked node {node_id} must use null blocker")
            continue
        if not isinstance(blocker, dict):
            errors.append(f"blocked node {node_id} requires blocker provenance")
            continue
        blocker_keys = {"kind", "source", "evidence_ids"}
        require_keys(
            blocker, blocker_keys, blocker_keys, f"node {node_id}.blocker", errors
        )
        blocker_kind = blocker.get("kind")
        if blocker_kind not in BLOCKER_KINDS:
            errors.append(f"node {node_id}.blocker.kind is invalid")
        source = blocker.get("source")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"node {node_id}.blocker.source must be a non-empty string")
        blocker_evidence_ids = string_list(
            blocker.get("evidence_ids"),
            f"node {node_id}.blocker.evidence_ids",
            errors,
            nonempty=True,
        )
        node_evidence_ids = node.get("evidence_ids")
        owned_ids = (
            set(node_evidence_ids) if isinstance(node_evidence_ids, list) else set()
        )
        for evidence_id in blocker_evidence_ids:
            blocker_item = evidence_by_id.get(evidence_id)
            if blocker_item is None:
                errors.append(
                    f"node {node_id}.blocker references unknown evidence {evidence_id}"
                )
            elif evidence_id not in owned_ids:
                errors.append(
                    f"node {node_id}.blocker evidence {evidence_id} is not owned by the node"
                )
            elif blocker_item.get("classification") not in {
                "ENVIRONMENT",
                "EXTERNAL",
            }:
                errors.append(
                    f"node {node_id}.blocker evidence {evidence_id} must have blocker provenance classification"
                )
        if blocker_kind == "DEPENDENCY":
            if source not in dependencies[node_id]:
                errors.append(
                    f"node {node_id} dependency blocker must name a direct dependency"
                )
            elif source not in nodes or nodes[source].get("status") != "BLOCKED":
                errors.append(
                    f"node {node_id} dependency blocker source must itself be BLOCKED"
                )
        elif blocker_kind in BLOCKER_KINDS:
            for dependency in dependencies[node_id]:
                if (
                    dependency in nodes
                    and nodes[dependency].get("status") != "COMPLETE"
                ):
                    errors.append(
                        f"node {node_id} terminal blocker requires COMPLETE dependencies"
                    )

    target_unproven = any(
        item.get("classification") == "TARGET" and item.get("status") != "PASS"
        for item in evidence
    )
    review_nodes = [node for node in dag if node.get("kind") == "REVIEW"]
    trigger_artifacts = set(artifacts)
    for producer_id in producer_ids:
        trigger_artifacts.update(node_artifacts[producer_id])
    producer_caps = {node.get("capability") for node in producer_nodes}
    # Certainty skips (token-efficient): absolute T0 micro, or high T0/T1 single slice.
    certainty_skip_absolute = (
        controller_certainty == "absolute"
        and classification == "T0"
        and not risk_flags
        and len(producer_nodes) <= 1
        and not target_unproven
        and not review_requested
    )
    certainty_skip_high = (
        controller_certainty == "high"
        and classification in {"T0", "T1"}
        and not risk_flags
        and len(producer_nodes) <= 1
        and not target_unproven
        and not review_requested
        and producer_caps <= {"LIGHT", "STANDARD"}
    )
    certainty_skip_eligible = certainty_skip_absolute or certainty_skip_high
    if controller_certainty == "absolute" and not certainty_skip_absolute:
        errors.append(
            "controller_certainty=absolute only for T0 micro-tasks with one "
            "producer, empty risk_flags, all TARGET proof PASS, and "
            "review_requested=false"
        )
    if controller_certainty == "high" and not certainty_skip_high:
        # high is allowed as a plain budget label even when skip is not used,
        # except when CODE/TEST would be skipped incorrectly — only error if they
        # claim skip via gate reason without eligibility (checked below).
        pass
    base_review_triggers = bool(
        {"DATA", "RELEASE"}.intersection(trigger_artifacts)
        or risk_flags
        or len(producer_nodes) > 1
        or target_unproven
        or classification == "T3"
        or review_requested
        or (
            bool({"CODE", "TEST"}.intersection(trigger_artifacts))
            and not certainty_skip_eligible
        )
    )
    review_required = bool(
        review_nodes or base_review_triggers
    )

    gate = report.get("review_gate")
    if not isinstance(gate, dict):
        errors.append("review_gate must be an object")
        gate = {}
    gate_keys = {"required", "reasons", "status", "review_task_id"}
    require_keys(gate, gate_keys, gate_keys, "review_gate", errors)
    if not isinstance(gate.get("required"), bool):
        errors.append("review_gate.required must be boolean")
    if gate.get("required") != review_required:
        errors.append(
            f"review_gate.required must be {str(review_required).lower()} for recorded triggers"
        )
    reasons = string_list(gate.get("reasons"), "review_gate.reasons", errors)
    if review_required and not reasons:
        errors.append("required review gate must record at least one reason")
    if certainty_skip_eligible and not review_nodes:
        if gate.get("status") != "NOT_REQUIRED":
            errors.append(
                "certainty micro-task skip requires review_gate.status NOT_REQUIRED"
            )
        if certainty_skip_absolute and "micro_task_absolute_certainty" not in reasons:
            errors.append(
                "absolute-certainty micro-task skip must record reason "
                "micro_task_absolute_certainty"
            )
        if certainty_skip_high and not certainty_skip_absolute:
            if "micro_task_high_certainty" not in reasons:
                errors.append(
                    "high-certainty micro-task skip must record reason "
                    "micro_task_high_certainty"
                )
    if (
        "micro_task_absolute_certainty" in reasons
        and not certainty_skip_absolute
    ):
        errors.append(
            "micro_task_absolute_certainty reason requires eligible absolute skip"
        )
    if "micro_task_high_certainty" in reasons and not certainty_skip_high:
        errors.append(
            "micro_task_high_certainty reason requires eligible high skip"
        )
    if gate.get("status") not in GATE_STATUSES:
        errors.append("review_gate.status is invalid")
    review_task_id = gate.get("review_task_id")
    if review_required:
        if gate.get("status") == "NOT_REQUIRED":
            errors.append("required review gate cannot be NOT_REQUIRED")
        if not isinstance(review_task_id, str) or review_task_id not in nodes:
            errors.append("required review gate must reference an existing review task")
        else:
            review_node = nodes[review_task_id]
            if review_node.get("kind") != "REVIEW":
                errors.append("review_gate.review_task_id must reference a REVIEW node")
            producer_owners = {node.get("owner") for node in producer_nodes}
            if review_node.get("owner") in producer_owners:
                errors.append(
                    "review task owner must be independent from producer owners"
                )
            for producer_id in producer_ids:
                if not depends_transitively(review_task_id, producer_id):
                    errors.append(
                        f"review task must depend on producer node {producer_id}"
                    )
            if gate.get("status") == "PASS":
                if review_node.get("status") != "COMPLETE":
                    errors.append("passing review gate requires a complete review task")
                review_evidence = review_node.get("evidence_ids")
                review_evidence_ids = (
                    review_evidence if isinstance(review_evidence, list) else []
                )
                if not any(
                    evidence_by_id.get(evidence_id, {}).get("task_id") == review_task_id
                    and evidence_by_id.get(evidence_id, {}).get("classification")
                    == "TARGET"
                    and evidence_by_id.get(evidence_id, {}).get("status") == "PASS"
                    for evidence_id in review_evidence_ids
                ):
                    errors.append(
                        "passing review gate requires dedicated TARGET/PASS review evidence"
                    )
                if target_unproven:
                    errors.append(
                        "passing review gate is invalid while target evidence is unproven"
                    )
    else:
        if gate.get("status") != "NOT_REQUIRED":
            errors.append("non-required review gate must have NOT_REQUIRED status")
        if review_task_id is not None:
            errors.append("non-required review gate must use null review_task_id")

    decision = report.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
        decision = {}
    decision_keys = {"result", "remaining_task_ids"}
    require_keys(decision, decision_keys, decision_keys, "decision", errors)
    result = decision.get("result")
    if result not in DECISIONS:
        errors.append("decision.result is invalid")
    remaining = string_list(
        decision.get("remaining_task_ids"), "decision.remaining_task_ids", errors
    )
    for node_id in remaining:
        if node_id not in nodes:
            errors.append(f"decision references unknown remaining task {node_id}")
    incomplete_ids = sorted(
        node_id for node_id, node in nodes.items() if node.get("status") != "COMPLETE"
    )
    if result == "COMPLETE":
        if remaining:
            errors.append("COMPLETE decision cannot have remaining tasks")
        if incomplete_ids:
            errors.append(
                f"COMPLETE decision has incomplete DAG nodes: {', '.join(incomplete_ids)}"
            )
        if target_unproven:
            errors.append("COMPLETE decision requires all target evidence to pass")
        if review_required and gate.get("status") != "PASS":
            errors.append("COMPLETE decision requires the review gate to pass")
    elif result in {"BLOCKED", "IN_PROGRESS"}:
        if not remaining:
            errors.append(f"{result} decision must list remaining task IDs")
        if sorted(set(remaining)) != sorted(set(incomplete_ids)):
            errors.append(
                f"{result} remaining_task_ids must match incomplete DAG nodes"
            )

        blocked_ids = {
            node_id
            for node_id, node in nodes.items()
            if node.get("status") == "BLOCKED"
        }

        def has_blocked_ancestor(node_id: str, seen: set[str] | None = None) -> bool:
            current_seen = set() if seen is None else seen
            if node_id in current_seen:
                return False
            current_seen.add(node_id)
            for dependency in dependencies.get(node_id, []):
                if dependency in blocked_ids or has_blocked_ancestor(
                    dependency, current_seen
                ):
                    return True
            return False

        runnable_ids = {
            node_id
            for node_id in incomplete_ids
            if nodes[node_id].get("status") == "RUNNING"
            or (
                nodes[node_id].get("status") == "PENDING"
                and all(
                    dependency in nodes
                    and nodes[dependency].get("status") == "COMPLETE"
                    for dependency in dependencies[node_id]
                )
            )
        }
        if result == "BLOCKED":
            if not blocked_ids:
                errors.append("BLOCKED decision requires at least one BLOCKED node")
            if runnable_ids:
                errors.append(
                    "BLOCKED decision is invalid while runnable tasks remain: "
                    + ", ".join(sorted(runnable_ids))
                )
            for node_id in incomplete_ids:
                if nodes[node_id].get(
                    "status"
                ) == "PENDING" and not has_blocked_ancestor(node_id):
                    errors.append(
                        f"BLOCKED pending node {node_id} must descend from blocked work"
                    )
        elif not runnable_ids:
            errors.append(
                "IN_PROGRESS decision requires a RUNNING or dependency-ready PENDING node"
            )

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_orchestration.py <report.json>", file=sys.stderr)
        return 2
    try:
        report = load_json(Path(sys.argv[1]))
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    errors = validate(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAIL: {len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("PASS: orchestration report is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
