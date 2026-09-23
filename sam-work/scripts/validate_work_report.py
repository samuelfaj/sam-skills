#!/usr/bin/env python3
"""Validate a sam-work completion report.

Freshness is checked against real files, not typed claims: every phase report is
re-opened, its head and status compared, its sha256 pinned to the final
iteration, and its child validator re-run from the sibling skill directory.
Capture-based proof (implementation, refine, simplify) is anchored at the commit
that holds the child's captured delta, then carried only across test-only deltas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PHASE_IDS = [
    "implementation",
    "refine",
    "review",
    "simplify",
    "coverage",
    "proposal",
    "playwright",
    "demo",
]

FIXED_SKILLS = {
    "refine": "sam-refine-task",
    "review": "sam-review",
    "simplify": "sam-simplify-task",
    "coverage": "sam-create-test-coverage",
    "proposal": "sam-pr-description",
    "playwright": "sam-create-playwright-tests",
    "demo": "sam-create-task-demo-video",
}

CHILD_VALIDATORS = {
    "implementation": "validate_report.py",
    "refine": "validate_report.py",
    "review": "validate_review.py",
    "simplify": "validate_report.py",
    "coverage": "validate_coverage_report.py",
    "proposal": "validate_description.py",
    "playwright": "validate_e2e_report.py",
    "demo": "validate_demo_report.py",
}

FINAL_STATUSES = {
    "implementation": {"COMPLETE"},
    "refine": {"HIGH_CONFIDENCE"},
    "review": {"APPROVE"},
    "simplify": {"SIMPLEST_DEFENSIBLE", "NO_CHANGE"},
    "coverage": {"FULL"},
    "proposal": {"READY"},
    "playwright": {"COMPLETE", "NOT_APPLICABLE"},
    "demo": {"PUBLISHED"},
}

ITERATION_STATUSES = {
    "implementation": {"COMPLETE", "CHANGES_REQUIRED", "BLOCKED"},
    "refine": {"HIGH_CONFIDENCE", "NOT_CONFIDENT", "BLOCKED"},
    "review": {"APPROVE", "CHANGES_REQUIRED", "COMMENT_ONLY", "BLOCKED"},
    "simplify": {
        "SIMPLEST_DEFENSIBLE",
        "NO_CHANGE",
        "CHANGES_APPLIED",
        "BLOCKED",
    },
    "coverage": {"FULL", "PARTIAL", "BLOCKED"},
    "proposal": {"READY", "BLOCKED"},
    "playwright": {"COMPLETE", "PARTIAL", "NOT_APPLICABLE", "BLOCKED"},
    "demo": {"PUBLISHED", "READY_LOCAL", "BLOCKED"},
}

# Phases whose inputs are production code only: their proof may carry forward
# to a later head when the git delta touches test paths only. They validate
# against scope captures, so their proof is anchored at the commit holding the
# captured delta (committed_head_sha) when the child ran on uncommitted work.
CARRY_FORWARD_PHASES = {"implementation", "refine", "simplify"}
# Child-validator flags a parent may pass (each takes one absolute path).
# --scaffold/--from are excluded: they make a child validator rewrite the report.
VALIDATOR_FLAGS = {
    "implementation": {"--baseline", "--current"},
    "refine": {"--baseline", "--current"},
    "review": {"--bundle"},
    "simplify": {"--baseline", "--current"},
    "coverage": {"--baseline", "--bundle"},
    "proposal": {"--context"},
    "playwright": {"--baseline", "--bundle"},
    "demo": {"--manifest"},
}
# Conservative on purpose: a miss only forces a re-run. `spec`/`specs`/`e2e`
# directories, `*Test.java`-style names, `*_test.py`/`*_test.rb` (e.g. `ab_test.py`,
# `app/models/ab_test.rb`), and test-looking config or contract files
# (`openapi.spec.yaml`, `schema_spec.sql`, `app.test.env`) also hold production inputs.
TEST_DIRS = {
    "test",
    "tests",
    "__tests__",
    "__snapshots__",
    "__mocks__",
    "testdata",
}
TEST_FILE = re.compile(
    r"^test_[^/]*\.py$|^conftest\.py$|_test\.(?:go|exs)$|_spec\.rb$"
    r"|\.(?:test|spec)\.(?:[cm]?[jt]s|[jt]sx)$"
)
DELEGATED_BROWSER_PROOF = "delegated to playwright phase"
PLACEHOLDER = "SCAFFOLD:"
SKILLS_ROOT = Path(__file__).resolve().parents[2]
CHILD_TIMEOUT_SECONDS = 300

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


def is_https_url(value: Any) -> bool:
    if not nonempty_string(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nested(value: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def child_head(report: dict[str, Any]) -> str | None:
    for keys in (("target", "current_head_sha"), ("target", "head_sha"), ("head_sha",)):
        value = nested(report, *keys)
        if isinstance(value, str) and REVISION.fullmatch(value):
            return value
    return None


def child_status(report: dict[str, Any]) -> str | None:
    decision = report.get("decision")
    if isinstance(decision, dict) and nonempty_string(decision.get("result")):
        return str(decision["result"])
    if nonempty_string(decision):
        return str(decision)
    for key in ("status", "result"):
        if nonempty_string(report.get(key)):
            return str(report[key])
    return None


def child_input_fingerprint(report: dict[str, Any]) -> str | None:
    for keys in (
        ("target", "current_fingerprint"),
        ("target", "bundle_fingerprint"),
        ("target", "context_fingerprint"),
        ("bundle_fingerprint",),
        ("manifest_fingerprint",),
    ):
        value = nested(report, *keys)
        if isinstance(value, str) and HEX64.fullmatch(value):
            return value
    return None


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    if any(part.lower() in TEST_DIRS for part in parts[:-1]):
        return True
    return bool(TEST_FILE.search(parts[-1]))


def git(repo_root: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git; decode bytes with os.fsdecode (no newline translation) so non-UTF-8 paths never crash."""
    result = subprocess.run(
        ["git", "-C", repo_root, *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return subprocess.CompletedProcess(
        result.args, result.returncode, os.fsdecode(result.stdout), os.fsdecode(result.stderr)
    )


def change_fingerprint(repo_root: str, base_sha: str, head_sha: str) -> str | None:
    """sha256 of the raw `git diff --binary` bytes (no decoding, no newline translation); None if git fails."""
    try:
        patch = subprocess.run(
            ["git", "-C", repo_root, "diff", "--binary", "--no-color", "--no-ext-diff", "--no-renames"]
            + [base_sha, head_sha],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    return hashlib.sha256(patch.stdout).hexdigest() if patch.returncode == 0 else None


def carry_forward_errors(
    prefix: str, repo_root: Any, from_sha: str, final_head: Any
) -> list[str]:
    if not nonempty_string(repo_root) or not REVISION.fullmatch(str(final_head or "")):
        return [f"{prefix} carry-forward needs target.repo_root and final head"]
    try:
        ancestor = git(str(repo_root), "merge-base", "--is-ancestor", from_sha, str(final_head))
        diff = git(
            str(repo_root), "diff", "--name-only", "--no-renames", "-z", from_sha, str(final_head)
        )
    except OSError as exc:
        return [f"{prefix} cannot verify carry-forward: {exc}"]
    for result in (ancestor, diff):
        if result.returncode not in (0, 1) or (result is diff and result.returncode):
            detail = (result.stderr.strip().splitlines() or ["git failed"])[-1]
            return [f"{prefix} cannot verify carry-forward: {detail}"]
    if ancestor.returncode != 0:
        return [f"{prefix} carried_forward_from is not an ancestor of the final head"]
    production = [path for path in diff.stdout.split("\0") if path and not is_test_path(path)]
    if production:
        shown = ", ".join(production[:5])
        return [
            f"{prefix} carry-forward rejected: production paths changed since "
            f"{from_sha[:12]}: {shown}"
        ]
    return []


def parse_validator_args(args: Any, allowed: set[str]) -> dict[str, str] | None:
    """Return {flag: absolute path} for `--flag value` / `--flag=value` pairs, else None."""
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        return None
    parsed: dict[str, str] = {}
    index = 0
    while index < len(args):
        flag, sep, value = args[index].partition("=")
        if not sep:
            if index + 1 >= len(args):
                return None
            value = args[index + 1]
            index += 1
        index += 1
        if flag not in allowed or flag in parsed or not Path(value).is_absolute():
            return None
        parsed[flag] = value
    return parsed


def load_capture(path: str) -> dict[str, Any] | None:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or not isinstance(value.get("files"), list):
        return None
    return value


def capture_files(capture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["path"]): item
        for item in capture["files"]
        if isinstance(item, dict) and nonempty_string(item.get("path"))
    }


def blob_sha256(repo_root: str, revision: str, path: str) -> str | None:
    """sha256 of the blob at revision:path (symlink blobs hold the target), None if absent."""
    result = subprocess.run(
        ["git", "-C", repo_root, "cat-file", "blob", f"{revision}:{path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def committed_capture_errors(
    prefix: str,
    phase_id: str,
    repo_root: Any,
    child_head_sha: str,
    committed: Any,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Prove committed_head_sha holds exactly the child's captured uncommitted delta."""
    if not nonempty_string(repo_root) or Path(str(current.get("repo_root", ""))).resolve() != Path(
        str(repo_root)
    ).resolve():
        return [f"{prefix} --current capture is for another repository than target.repo_root"]
    if current.get("head_sha") != child_head_sha:
        return [f"{prefix} --current capture head does not match the child report head"]
    before, after = capture_files(baseline), capture_files(current)
    delta = {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}
    if committed is None:
        if delta:
            return [
                f"{prefix} child delta is not committed; committed_head_sha must name the commit "
                f"holding it: {', '.join(sorted(delta)[:5])}"
            ]
        return []
    if not REVISION.fullmatch(str(committed)):
        return [f"{prefix} committed_head_sha must be a revision"]
    try:
        ancestor = git(str(repo_root), "merge-base", "--is-ancestor", child_head_sha, str(committed))
        diff = git(
            str(repo_root), "diff", "--name-only", "--no-renames", "-z", child_head_sha, str(committed)
        )
    except OSError as exc:
        return [f"{prefix} cannot verify committed_head_sha: {exc}"]
    if ancestor.returncode not in (0, 1) or diff.returncode:
        failed = ancestor if ancestor.returncode not in (0, 1) else diff
        detail = (failed.stderr.strip().splitlines() or ["git failed"])[-1]
        return [f"{prefix} cannot verify committed_head_sha: {detail}"]
    if ancestor.returncode != 0:
        return [f"{prefix} child report head is not an ancestor of committed_head_sha"]
    committed_paths = {path for path in diff.stdout.split("\0") if path}
    # Refine is read-only: its proof covered every dirty file, so the commit may
    # hold any of them. Implementation/simplify own only their captured delta.
    owned = delta | (set(after) if phase_id == "refine" else set())
    mismatched = []
    for path in sorted(delta | committed_paths):
        record = after.get(path)
        if path in committed_paths and path not in owned:
            ok = False
        elif record is None:
            ok = path not in committed_paths
        elif record.get("state") == "deleted":
            ok = blob_sha256(str(repo_root), str(committed), path) is None
        elif record.get("state") in {"file", "symlink"}:
            ok = blob_sha256(str(repo_root), str(committed), path) == record.get("worktree_sha256")
        else:
            ok = False
        if not ok:
            mismatched.append(path)
    if mismatched:
        return [
            f"{prefix} committed_head_sha does not match the child's captured delta: "
            f"{', '.join(mismatched[:5])}"
        ]
    return []


def run_child_validator(
    phase_id: str, skill: str, args: list[str], report_path: Path
) -> tuple[int, str]:
    script = SKILLS_ROOT / skill / "scripts" / CHILD_VALIDATORS[phase_id]
    if not script.is_file():
        return 127, f"child validator is missing: {script}"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(script), *args, str(report_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=CHILD_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 124, f"child validator did not finish: {exc}"
    # Decode bytes with replacement: non-UTF-8 child output never raises or breaks printing.
    lines = result.stdout.decode("utf-8", "replace").strip().splitlines()
    if result.returncode != 0:
        lines = result.stderr.decode("utf-8", "replace").strip().splitlines() or lines
    return result.returncode, (lines[-1].strip() if lines else "no output")


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
    if status not in ITERATION_STATUSES[phase_id]:
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
    if open_items and not corrections:
        errors.append(f"{prefix} with open items requires correction receipts")
    if is_last:
        if open_items:
            errors.append(f"{prefix} cannot finish with open required items")
        if status not in FINAL_STATUSES[phase_id]:
            errors.append(f"{prefix} is not an accepted terminal status")
    elif not open_items and not corrections:
        errors.append(
            f"{prefix} must record either corrected findings or a later invalidation"
        )


def validate_child_report(
    phase: dict[str, Any],
    expected_id: str,
    expected_skill: str,
    repo_root: Any,
    final_head: Any,
    errors: list[str],
) -> dict[str, Any] | None:
    """Re-open the phase's child report and prove it backs the phase record."""
    prefix = f"phase {expected_id}"
    raw_path = phase.get("report_path")
    if not nonempty_string(raw_path) or not Path(str(raw_path)).is_absolute():
        errors.append(f"{prefix} report_path must be an absolute path to the child report")
        return None
    path = Path(str(raw_path))
    if not path.is_file():
        errors.append(f"{prefix} child report is missing: {path}")
        return None
    try:
        child = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{prefix} child report is unreadable: {exc}")
        return None
    if not isinstance(child, dict):
        errors.append(f"{prefix} child report root must be an object")
        return None

    args = phase.get("validator_args")
    flags = parse_validator_args(args, VALIDATOR_FLAGS[expected_id])
    if flags is None:
        errors.append(
            f"{prefix} validator_args must be `--flag <absolute path>` pairs using only "
            f"{', '.join(sorted(VALIDATOR_FLAGS[expected_id]))}"
        )
    carried = phase.get("carried_forward_from")
    committed = phase.get("committed_head_sha")
    head = child_head(child)
    if head is None:
        errors.append(f"{prefix} child report records no head revision")
    else:
        if expected_id in CARRY_FORWARD_PHASES:
            captures = [
                load_capture(flags[flag]) if flags and flag in flags else None
                for flag in ("--baseline", "--current")
            ]
            if None in captures:
                errors.append(
                    f"{prefix} validator_args must name readable --baseline and --current scope captures"
                )
            else:
                errors.extend(
                    committed_capture_errors(prefix, expected_id, repo_root, head, committed, *captures)
                )
        elif committed is not None:
            errors.append(
                f"{prefix} committed_head_sha is allowed only for implementation, refine, simplify"
            )
        anchor = committed if committed is not None else head
        expected_head = phase.get("validated_head_sha")
        if carried is not None:
            if expected_id not in CARRY_FORWARD_PHASES:
                errors.append(
                    f"{prefix} carry-forward is allowed only for implementation, refine, simplify"
                )
            elif carried != anchor:
                errors.append(
                    f"{prefix} carried_forward_from must equal committed_head_sha or the child report head"
                )
            else:
                errors.extend(carry_forward_errors(prefix, repo_root, str(carried), final_head))
        elif anchor != expected_head:
            label = "committed_head_sha" if committed is not None else "child report head"
            errors.append(f"{prefix} {label} {str(anchor)[:12]} does not match {str(expected_head)[:12]}")
    status = child_status(child)
    if status is not None and status != phase.get("status"):
        errors.append(f"{prefix} status must match the child report status {status!r}")

    iterations = phase.get("iterations")
    last = iterations[-1] if isinstance(iterations, list) and iterations else None
    if isinstance(last, dict):
        if last.get("output_fingerprint") != sha256_file(path):
            errors.append(f"{prefix} final iteration output_fingerprint must equal sha256 of report_path")
        input_fingerprint = child_input_fingerprint(child)
        if input_fingerprint is not None and last.get("input_fingerprint") != input_fingerprint:
            errors.append(
                f"{prefix} final iteration input_fingerprint must equal the child report input fingerprint"
            )

    if flags is None:
        return child
    code, line = run_child_validator(expected_id, expected_skill, args, path)
    if code != 0:
        errors.append(f"{prefix} child validator failed: {line}")
    else:
        receipts = phase.get("validator_receipts")
        if isinstance(receipts, list) and receipts and receipts[-1] != line:
            errors.append(
                f"{prefix} validator receipt does not match a fresh child validator run ({line})"
            )
    return child


def validate_phase(
    phase: Any,
    expected_id: str,
    classification: Any,
    web_system: Any,
    repo_root: Any,
    final_head: Any,
    errors: list[str],
) -> dict[str, Any] | None:
    prefix = f"phase {expected_id}"
    if not isinstance(phase, dict):
        errors.append(f"{prefix} must be an object")
        return None
    if phase.get("id") != expected_id:
        errors.append(f"{prefix} is missing or out of order")

    expected_skill = FIXED_SKILLS.get(expected_id)
    if expected_id == "implementation":
        expected_skill = "sam-fix-bug" if classification == "BUG" else "sam-create-feature"
    if phase.get("skill") != expected_skill:
        errors.append(f"{prefix} must use {expected_skill}")

    applicability = phase.get("applicability")
    status = phase.get("status")
    not_applicable = expected_id == "playwright" and web_system is False
    if not_applicable:
        if applicability != "NOT_APPLICABLE" or status != "NOT_APPLICABLE":
            errors.append("non-web Playwright phase must be explicitly NOT_APPLICABLE")
        if not nonempty_string(phase.get("not_applicable_reason")):
            errors.append("non-web Playwright phase requires a concrete reason")
        if phase.get("report_path") is not None:
            errors.append("non-web Playwright phase cannot cite a child report")
    else:
        if applicability != "REQUIRED":
            errors.append(f"{prefix} must be REQUIRED")
        if phase.get("not_applicable_reason") is not None:
            errors.append(f"{prefix} cannot have a not-applicable reason")
        if status not in FINAL_STATUSES[expected_id] or status == "NOT_APPLICABLE":
            errors.append(f"{prefix} does not have an accepted final status")

    if phase.get("current") is not True:
        errors.append(f"{prefix} proof must be current")
    if phase.get("validated_head_sha") != final_head:
        errors.append(f"{prefix} proof is stale for the final head")
    if not string_list(phase.get("evidence"), nonempty=True):
        errors.append(f"{prefix} requires evidence")
    if not string_list(phase.get("validator_receipts"), nonempty=True):
        errors.append(f"{prefix} requires validator receipts")

    iterations = phase.get("iterations")
    if not isinstance(iterations, list) or not iterations:
        errors.append(f"{prefix} requires at least one iteration")
        return None
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
    if not_applicable:
        return None
    return validate_child_report(
        phase, expected_id, str(expected_skill), repo_root, final_head, errors
    )


def validate_environment(name: str, value: Any, errors: list[str]) -> None:
    prefix = f"environment {name}"
    if not isinstance(value, dict):
        errors.append(f"{prefix} is required")
        return
    if value.get("kind") != "DEVELOPMENT":
        errors.append(f"{prefix} must be verified DEVELOPMENT")
    if value.get("identity_verified") is not True:
        errors.append(f"{prefix} identity must be verified")
    if not string_list(value.get("identity_evidence"), nonempty=True):
        errors.append(f"{prefix} requires identity evidence")
    if value.get("real_data") is not True:
        errors.append(f"{prefix} must use real development data")
    if value.get("dedicated_data") is not True:
        errors.append(f"{prefix} must use dedicated data")
    if value.get("cleanup_status") != "COMPLETE":
        errors.append(f"{prefix} cleanup must be COMPLETE")
    if value.get("privacy_review") != "PASS":
        errors.append(f"{prefix} privacy review must PASS")


def validate_proposal(value: Any, final_head: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("proposal receipt is required")
        return
    if not nonempty_string(value.get("platform")):
        errors.append("proposal platform is required")
    if not is_https_url(value.get("url")):
        errors.append("proposal URL must be HTTPS")
    if not nonempty_string(value.get("proposal_id")):
        errors.append("proposal ID is required")
    if not isinstance(value.get("created_by_workflow"), bool):
        errors.append("proposal created_by_workflow must be boolean")
    if value.get("description_validated") is not True:
        errors.append("proposal description must be validated")
    if not nonempty_string(value.get("description_receipt")):
        errors.append("proposal description receipt is required")
    if value.get("remote_head_sha") != final_head:
        errors.append("proposal remote head does not match final head")
    if not string_list(value.get("rendered_readback_evidence"), nonempty=True):
        errors.append("proposal rendered readback evidence is required")
    if value.get("required_ci_status") not in {"PASS", "NOT_CONFIGURED"}:
        errors.append("proposal required CI must PASS or be NOT_CONFIGURED")


def validate_videos(report: dict[str, Any], web_system: Any, errors: list[str]) -> None:
    inventory = report.get("video_inventory")
    if not isinstance(inventory, dict):
        errors.append("video_inventory is required")
        return
    keys = (
        "playwright_discovered",
        "playwright_uploaded",
        "demo_discovered",
        "demo_uploaded",
    )
    for key in keys:
        value = inventory.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"video_inventory {key} must be a non-negative integer")

    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be an array")
        return
    counts = {"playwright": 0, "demo": 0}
    identities: set[tuple[Any, Any, Any]] = set()
    for index, artifact in enumerate(artifacts, start=1):
        prefix = f"artifact {index}"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be an object")
            continue
        phase = artifact.get("phase")
        if phase not in counts:
            errors.append(f"{prefix} phase must be playwright or demo")
            continue
        counts[phase] += 1
        local_path = artifact.get("local_path")
        if not nonempty_string(local_path) or not Path(local_path).is_absolute():
            errors.append(f"{prefix} local_path must be absolute")
        elif phase == "demo" and Path(local_path).suffix.lower() != ".mp4":
            errors.append(f"{prefix} demo video must be an MP4")
        if not HEX64.fullmatch(str(artifact.get("sha256", ""))):
            errors.append(f"{prefix} sha256 must be 64 lowercase hex characters")
        if not is_https_url(artifact.get("uploaded_url")):
            errors.append(f"{prefix} uploaded_url must be HTTPS")
        if not nonempty_string(artifact.get("upload_receipt")):
            errors.append(f"{prefix} upload receipt is required")
        if artifact.get("player_verified") is not True:
            errors.append(f"{prefix} must have a verified rendered video player")
        if not string_list(artifact.get("readback_evidence"), nonempty=True):
            errors.append(f"{prefix} requires player readback evidence")
        identity = (local_path, artifact.get("sha256"), artifact.get("uploaded_url"))
        if identity in identities:
            errors.append(f"{prefix} duplicates another video artifact")
        identities.add(identity)

    playwright_discovered = inventory.get("playwright_discovered")
    playwright_uploaded = inventory.get("playwright_uploaded")
    demo_discovered = inventory.get("demo_discovered")
    demo_uploaded = inventory.get("demo_uploaded")
    if web_system is True:
        if not isinstance(playwright_discovered, int) or playwright_discovered < 1:
            errors.append("web workflow requires at least one Playwright video")
        if playwright_uploaded != playwright_discovered:
            errors.append("every discovered Playwright video must be uploaded")
    elif playwright_discovered != 0 or playwright_uploaded != 0:
        errors.append("non-web workflow cannot claim Playwright videos")
    if demo_discovered is None or not isinstance(demo_discovered, int) or demo_discovered < 1:
        errors.append("workflow requires at least one demo video")
    if demo_uploaded != demo_discovered:
        errors.append("every discovered demo video must be uploaded")
    if counts["playwright"] != playwright_uploaded:
        errors.append("Playwright artifact count must equal uploaded inventory")
    if counts["demo"] != demo_uploaded:
        errors.append("demo artifact count must equal uploaded inventory")


def find_placeholders(value: Any, path: str, found: list[str]) -> None:
    if isinstance(value, str) and value.startswith(PLACEHOLDER):
        found.append(path or "$")
    elif isinstance(value, dict):
        for key, item in value.items():
            find_placeholders(item, f"{path}.{key}" if path else str(key), found)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            find_placeholders(item, f"{path}[{index}]", found)


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    placeholders: list[str] = []
    find_placeholders(report, "", placeholders)
    for location in placeholders[:10]:
        errors.append(f"unfilled scaffold placeholder at {location}")
    if report.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    if not nonempty_string(report.get("workflow_id")):
        errors.append("workflow_id is required")

    request = report.get("request")
    if not isinstance(request, dict):
        errors.append("request object is required")
        request = {}
    classification = request.get("classification")
    web_system = request.get("web_system")
    if classification not in {"BUG", "FEATURE"}:
        errors.append("request classification must be BUG or FEATURE")
    if not isinstance(web_system, bool):
        errors.append("request web_system must be boolean")
    if not HEX64.fullmatch(str(request.get("prompt_sha256", ""))):
        errors.append("request prompt_sha256 must be 64 lowercase hex characters")
    if not string_list(request.get("classification_evidence"), nonempty=True):
        errors.append("request classification evidence is required")

    authorization = report.get("authorization")
    expected_authorization = {
        "create_or_update_proposal": True,
        "publish_playwright_videos": True,
        "publish_demo_video": True,
        "merge": False,
        "deploy": False,
    }
    if authorization != expected_authorization:
        errors.append("authorization must exactly match the sam-work write boundary")

    target = report.get("target")
    if not isinstance(target, dict):
        errors.append("target object is required")
        target = {}
    repo_root = target.get("repo_root")
    if not nonempty_string(repo_root) or not Path(repo_root).is_absolute():
        errors.append("target repo_root must be absolute")
    if not nonempty_string(target.get("base_ref")):
        errors.append("target base_ref is required")
    for field in ("base_sha", "final_head_sha"):
        if not REVISION.fullmatch(str(target.get(field, ""))):
            errors.append(f"target {field} must be a 40- or 64-character revision")
    final_head = target.get("final_head_sha")
    fingerprint = target.get("final_change_fingerprint")
    if not HEX64.fullmatch(str(fingerprint or "")):
        errors.append("target final_change_fingerprint must be 64 lowercase hex characters")
    elif (
        nonempty_string(repo_root)
        and Path(repo_root).is_absolute()
        and REVISION.fullmatch(str(target.get("base_sha", "")))
        and REVISION.fullmatch(str(final_head or ""))
    ):
        actual = change_fingerprint(repo_root, str(target["base_sha"]), str(final_head))
        if actual is None:
            errors.append(
                "cannot verify target final_change_fingerprint: git diff base_sha..final_head_sha failed"
            )
        elif actual != fingerprint:
            errors.append(
                "target final_change_fingerprint must equal sha256 of "
                "git diff --binary --no-color --no-ext-diff --no-renames base_sha final_head_sha"
            )

    phases = report.get("phases")
    children: dict[str, dict[str, Any] | None] = {}
    if not isinstance(phases, list) or len(phases) != len(PHASE_IDS):
        errors.append("phases must contain exactly all eight canonical phases")
    else:
        for phase, phase_id in zip(phases, PHASE_IDS):
            children[phase_id] = validate_phase(
                phase,
                phase_id,
                classification,
                web_system,
                repo_root,
                final_head,
                errors,
            )
        coverage = children.get("coverage") or {}
        proof = coverage.get("real_system_proof")
        delegated = (
            isinstance(proof, dict)
            and proof.get("status") == "NOT_APPLICABLE"
            and DELEGATED_BROWSER_PROOF in json.dumps(proof).lower()
        )
        playwright = phases[PHASE_IDS.index("playwright")]
        if delegated and (
            not isinstance(playwright, dict)
            or playwright.get("status") != "COMPLETE"
            or children.get("playwright") is None
            or playwright.get("validated_head_sha") != final_head
        ):
            errors.append(
                "coverage delegated browser proof to the playwright phase, "
                "so playwright must be COMPLETE on the final head"
            )

    validate_proposal(report.get("proposal"), final_head, errors)

    environments = report.get("environments")
    if not isinstance(environments, dict):
        errors.append("environments object is required")
        environments = {}
    validate_environment("demo", environments.get("demo"), errors)
    if web_system is True:
        validate_environment("playwright", environments.get("playwright"), errors)
    elif environments.get("playwright") not in (None, {}):
        errors.append("non-web workflow must not claim a Playwright environment")

    validate_videos(report, web_system, errors)

    final = report.get("final")
    if not isinstance(final, dict):
        errors.append("final object is required")
    else:
        if final.get("result") != "COMPLETE":
            errors.append("final result must be COMPLETE")
        if final.get("completed_phase_ids") != PHASE_IDS:
            errors.append("final completed_phase_ids must list every phase in order")
        if final.get("blockers") != []:
            errors.append("complete workflow cannot have blockers")
        if final.get("final_head_sha") != final_head:
            errors.append("final head must match target final head")
        if final.get("final_change_fingerprint") != target.get(
            "final_change_fingerprint"
        ):
            errors.append("final change fingerprint must match target")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = load_json(Path(args.report))
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    errors = validate(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAIL: {len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("PASS: sam-work report proves every required phase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
