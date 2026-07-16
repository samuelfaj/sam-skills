#!/usr/bin/env python3
"""Exercise scope capture and report validation with adversarial fixtures."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


JsonObject = dict[str, Any]
SKILL_DIR = Path(__file__).resolve().parents[1]
WORKFLOW = {
    "sam-create-feature": "feature",
    "sam-fix-bug": "bugfix",
    "sam-refine-task": "refinement",
    "sam-simplify-task": "simplification",
}[SKILL_DIR.name]


def run(
    command: list[str],
    cwd: Path,
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git(repo: Path, *args: str) -> str:
    return run(["git", *args], repo).stdout


def file_hash(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def capture_result(
    repo: Path, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-B",
            str(SKILL_DIR / "scripts/capture_scope.py"),
            "--repo",
            str(repo),
        ],
        repo,
        check=False,
        env=env,
    )


def capture(repo: Path, *, env: dict[str, str] | None = None) -> JsonObject:
    result = capture_result(repo, env=env)
    if result.returncode != 0:
        raise AssertionError(f"capture failed: {result.stdout}{result.stderr}")
    value = json.loads(result.stdout)
    assert isinstance(value, dict)
    return value


def write_probe(path: Path, marker: Path) -> None:
    path.write_text(
        f"#!/bin/sh\nprintf executed > {marker!s}\nexit 0\n", encoding="utf-8"
    )
    path.chmod(0o755)


def safe_status(repo: Path) -> str:
    return git(
        repo,
        "-c",
        "core.fsmonitor=false",
        "-c",
        "diff.external=",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )


def security_checks(repo: Path, artifacts: Path) -> None:
    nested = repo / "nested"
    nested.mkdir()
    marker = artifacts / "git-integration-executed"
    probe = repo / "git-probe"
    write_probe(probe, marker)
    fake_bin = repo / "repo-bin"
    fake_bin.mkdir()
    fake_git_marker = artifacts / "repo-git-executed"
    write_probe(fake_bin / "git", fake_git_marker)
    (repo / ".gitattributes").write_text("*.txt diff=evil\n", encoding="utf-8")
    git(repo, "config", "core.fsmonitor", str(probe))
    git(repo, "config", "diff.external", str(probe))
    git(repo, "config", "diff.evil.command", str(probe))
    git(repo, "config", "diff.evil.textconv", str(probe))

    temporary_indexes = repo / "temporary-indexes"
    temporary_indexes.mkdir()
    redirected_config = artifacts / "redirected-gitconfig"
    redirected_config.write_text(
        f'[filter "redirected"]\n\tclean = {probe!s}\n', encoding="utf-8"
    )
    inherited = os.environ.copy()
    inherited.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{inherited.get('PATH', '')}",
            "TMPDIR": str(temporary_indexes),
            "GIT_DIR": str(artifacts / "redirected.git"),
            "GIT_WORK_TREE": str(artifacts / "redirected-worktree"),
            "GIT_INDEX_FILE": str(artifacts / "attacker-index"),
            "GIT_OBJECT_DIRECTORY": str(artifacts / "attacker-objects"),
            "GIT_EXTERNAL_DIFF": str(probe),
            "GIT_CONFIG_SYSTEM": str(redirected_config),
            "GIT_CONFIG_COUNT": "3",
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": str(probe),
            "GIT_CONFIG_KEY_1": "diff.external",
            "GIT_CONFIG_VALUE_1": str(probe),
            "GIT_CONFIG_KEY_2": "filter.inherited.clean",
            "GIT_CONFIG_VALUE_2": str(probe),
        }
    )
    index_path = repo / ".git" / "index"
    status_before = safe_status(repo)
    index_before = index_path.read_bytes()
    index_mtime = index_path.stat().st_mtime_ns
    captured = capture(nested, env=inherited)
    if captured["repo_root"] != str(repo.resolve()):
        raise AssertionError("nested repository input resolved the wrong root")
    if marker.exists() or fake_git_marker.exists():
        raise AssertionError("repository-controlled Git integration executed")
    if (
        index_path.read_bytes() != index_before
        or index_path.stat().st_mtime_ns != index_mtime
    ):
        raise AssertionError("scope capture mutated the real Git index")
    if safe_status(repo) != status_before:
        raise AssertionError("scope capture mutated Git status")
    if any(temporary_indexes.iterdir()):
        raise AssertionError("temporary copied index was not cleaned up")

    git(repo, "config", "filter.evil.clean", str(probe))
    blocked = capture_result(nested, env=inherited)
    if (
        blocked.returncode != 2
        or "configured clean/process filters" not in blocked.stderr
    ):
        raise AssertionError("configured clean filter did not fail closed")
    if marker.exists() or fake_git_marker.exists():
        raise AssertionError("blocked clean filter or fake Git executed")
    git(repo, "config", "--unset", "filter.evil.clean")

    external = artifacts / "external-sentinel.txt"
    external.write_text("one\ntwo\nthree\n", encoding="utf-8")
    link = repo / "external-link.txt"
    link.symlink_to(external)
    first = capture(repo, env=inherited)
    external.write_text("changed\n" * 20, encoding="utf-8")
    second = capture(repo, env=inherited)
    first_record = maps(first)["external-link.txt"]
    second_record = maps(second)["external-link.txt"]
    if (
        first_record != second_record
        or first["non_test_changed_lines"] != second["non_test_changed_lines"]
    ):
        raise AssertionError("scope capture followed an external symlink")
    if marker.exists() or fake_git_marker.exists():
        raise AssertionError("Git integration executed during symlink capture")
    if any(temporary_indexes.iterdir()):
        raise AssertionError("later temporary copied index was not cleaned up")
    link.unlink()

    for key in (
        "core.fsmonitor",
        "diff.external",
        "diff.evil.command",
        "diff.evil.textconv",
    ):
        git(repo, "config", "--unset", key)
    (repo / ".gitattributes").unlink()
    (fake_bin / "git").unlink()
    fake_bin.rmdir()
    probe.unlink()
    temporary_indexes.rmdir()
    nested.rmdir()


def maps(bundle: JsonObject) -> dict[str, JsonObject]:
    return {item["path"]: item for item in bundle["files"]}


def delta_paths(before: JsonObject, after: JsonObject) -> list[str]:
    left = maps(before)
    right = maps(after)
    return sorted(
        path for path in left.keys() | right.keys() if left.get(path) != right.get(path)
    )


def target(before: JsonObject, after: JsonObject) -> JsonObject:
    return {
        "baseline_fingerprint": before["fingerprint"],
        "current_fingerprint": after["fingerprint"],
        "baseline_head_sha": before["head_sha"],
        "current_head_sha": after["head_sha"],
        "paths": after["paths"],
    }


def base_report(before: JsonObject, after: JsonObject) -> JsonObject:
    owned = [] if WORKFLOW == "refinement" else ["app.txt"]
    complete = {
        "feature": "COMPLETE",
        "bugfix": "COMPLETE",
        "refinement": "HIGH_CONFIDENCE",
        "simplification": "SIMPLEST_DEFENSIBLE",
    }[WORKFLOW]
    report: JsonObject = {
        "schema_version": 1,
        "workflow": WORKFLOW,
        "target": target(before, after),
        "intent": {
            "goal": "Prove the requested workflow contract",
            "must_not_change": ["unrelated.txt"],
            "invariants": ["observable behavior remains correct"],
            "owner_boundary": "app.txt",
            "user_visible": True,
        },
        "scope": {
            "initial_owned_paths": owned,
            "current_owned_paths": owned,
            "cycle": 1,
            "scope_expansion_approved": False,
        },
        "file_coverage": [
            {"path": path, "reason": "Owned workflow change"}
            for path in delta_paths(before, after)
        ],
        "evidence": [
            {
                "id": "E_REQ",
                "status": "PASS",
                "classification": "TARGET",
                "detail": "Intent confirmed",
            },
            {
                "id": "E_RED",
                "status": "FAIL",
                "classification": "TARGET",
                "detail": "Expected pre-change failure",
            },
            {
                "id": "E_GREEN",
                "status": "PASS",
                "classification": "TARGET",
                "detail": "Targeted proof passed",
            },
            {
                "id": "E_RUNTIME",
                "status": "PASS",
                "classification": "TARGET",
                "detail": "Observable behavior passed",
            },
        ],
        "scenarios": [
            {
                "behavior": "Requested behavior",
                "status": "PROVEN",
                "evidence_ids": ["E_GREEN"],
            }
        ],
        "behavior_proof": {"status": "PROVEN", "evidence_ids": ["E_RUNTIME"]},
        "gates": [
            {
                "name": "targeted-proof",
                "mandatory": True,
                "status": "PASS",
                "evidence_ids": ["E_GREEN"],
            }
        ],
        "external_actions": [],
        "decision": {"result": complete, "remaining": []},
    }
    if WORKFLOW == "feature":
        report.update(
            {
                "requirements": [
                    {
                        "id": "R1",
                        "text": "Deliver requested behavior",
                        "status": "CONFIRMED",
                        "material": True,
                        "evidence_ids": ["E_REQ"],
                    }
                ],
                "tdd": {
                    "status": "RED_GREEN",
                    "red_evidence_ids": ["E_RED"],
                    "green_evidence_ids": ["E_GREEN"],
                },
            }
        )
    elif WORKFLOW == "bugfix":
        report.update(
            {
                "bug": {
                    "observed": "Incorrect result",
                    "expected": "Correct result",
                    "root_cause": "Owning rule was wrong",
                    "fix_boundary": "app.txt",
                    "root_cause_evidence_ids": ["E_REQ"],
                },
                "reproduction": {"status": "REPRODUCED", "evidence_ids": ["E_RED"]},
                "regression_proof": {
                    "status": "DIFFERENTIAL",
                    "failing_evidence_ids": ["E_RED"],
                    "passing_evidence_ids": ["E_GREEN"],
                },
            }
        )
    elif WORKFLOW == "refinement":
        report.update(
            {
                "claims": [
                    {
                        "claim": "Strategy matches the contract",
                        "status": "FACT",
                        "material": True,
                        "evidence_ids": ["E_REQ"],
                    }
                ],
                "loopholes": [
                    {
                        "loophole": "Proof could be missing",
                        "status": "CLOSED",
                        "evidence_ids": ["E_GREEN"],
                    }
                ],
                "verification_plan": [
                    {
                        "proof": "Run targeted validation",
                        "status": "PASS",
                        "evidence_ids": ["E_GREEN"],
                    }
                ],
            }
        )
    else:
        report["candidates"] = [
            {
                "opportunity": "Remove redundant wrapper",
                "status": "APPLIED",
                "complexity_removed": "One pass-through layer",
                "evidence_ids": ["E_GREEN"],
            }
        ]
    return report


def validate(
    artifacts: Path,
    name: str,
    report: JsonObject,
    before: JsonObject,
    after: JsonObject,
    *,
    expected: int,
) -> None:
    baseline_path = artifacts / f"{name}-baseline.json"
    current_path = artifacts / f"{name}-current.json"
    report_path = artifacts / f"{name}-report.json"
    baseline_path.write_text(json.dumps(before), encoding="utf-8")
    current_path.write_text(json.dumps(after), encoding="utf-8")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = run(
        [
            sys.executable,
            str(SKILL_DIR / "scripts/validate_report.py"),
            "--baseline",
            str(baseline_path),
            "--current",
            str(current_path),
            str(report_path),
        ],
        artifacts,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"{name}: expected {expected}, got {result.returncode}\n{result.stdout}{result.stderr}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix=f"{WORKFLOW}-harness-") as raw:
        root = Path(raw)
        repo = root / "repo"
        artifacts = root / "artifacts"
        repo.mkdir()
        artifacts.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "fixture@example.invalid")
        git(repo, "config", "user.name", "Fixture")
        (repo / "app.txt").write_text("original\n", encoding="utf-8")
        git(repo, "add", "app.txt")
        git(repo, "commit", "-qm", "baseline")
        (repo / "unrelated.txt").write_text("user work\n", encoding="utf-8")
        if WORKFLOW == "simplification":
            (repo / "app.txt").write_text("wrapper\noriginal\n", encoding="utf-8")

        security_checks(repo, artifacts)

        status_before = git(repo, "status", "--porcelain=v1", "-z")
        index_before = file_hash(repo / ".git/index")
        baseline = capture(repo)
        assert git(repo, "status", "--porcelain=v1", "-z") == status_before
        assert file_hash(repo / ".git/index") == index_before

        if WORKFLOW == "simplification":
            (repo / "app.txt").write_text("original\n", encoding="utf-8")
        elif WORKFLOW != "refinement":
            (repo / "app.txt").write_text(f"{WORKFLOW}\n", encoding="utf-8")
        current = capture(repo)
        valid = base_report(baseline, current)
        validate(artifacts, "valid", valid, baseline, current, expected=0)

        head_drift_current = deepcopy(current)
        head_drift_current["head_sha"] = "f" * 40
        head_drift_current["fingerprint"] = "f" * 64
        head_drift = deepcopy(valid)
        head_drift["target"] = target(baseline, head_drift_current)
        validate(
            artifacts,
            "head-drift",
            head_drift,
            baseline,
            head_drift_current,
            expected=1,
        )
        if delta_paths(baseline, current):
            stale_fingerprint_current = deepcopy(current)
            stale_fingerprint_current["fingerprint"] = baseline["fingerprint"]
            stale_fingerprint = deepcopy(valid)
            stale_fingerprint["target"] = target(baseline, stale_fingerprint_current)
            validate(
                artifacts,
                "stale-fingerprint-with-file-delta",
                stale_fingerprint,
                baseline,
                stale_fingerprint_current,
                expected=1,
            )

        if WORKFLOW in {"feature", "bugfix"}:
            fake_red = deepcopy(valid)
            next(item for item in fake_red["evidence"] if item["id"] == "E_RED")[
                "status"
            ] = "PASS"
            validate(
                artifacts, "fake-red-pass", fake_red, baseline, current, expected=1
            )
            not_run_red = deepcopy(valid)
            next(item for item in not_run_red["evidence"] if item["id"] == "E_RED")[
                "status"
            ] = "NOT_RUN"
            validate(
                artifacts,
                "fake-red-not-run",
                not_run_red,
                baseline,
                current,
                expected=1,
            )
            if WORKFLOW == "feature":
                duplicate_requirement = deepcopy(valid)
                repeated = deepcopy(duplicate_requirement["requirements"][0])
                repeated["text"] = "A second requirement with the same identifier"
                duplicate_requirement["requirements"].append(repeated)
                validate(
                    artifacts,
                    "duplicate-requirement-id",
                    duplicate_requirement,
                    baseline,
                    current,
                    expected=1,
                )
        elif WORKFLOW == "refinement":
            no_loopholes = deepcopy(valid)
            no_loopholes["loopholes"] = []
            validate(
                artifacts,
                "missing-loophole-analysis",
                no_loopholes,
                baseline,
                current,
                expected=1,
            )
            nonempty_owned_paths = deepcopy(valid)
            nonempty_owned_paths["scope"]["initial_owned_paths"] = ["app.txt"]
            nonempty_owned_paths["scope"]["current_owned_paths"] = ["app.txt"]
            validate(
                artifacts,
                "refinement-owned-paths",
                nonempty_owned_paths,
                baseline,
                current,
                expected=1,
            )
            approved_expansion = deepcopy(valid)
            approved_expansion["scope"]["scope_expansion_approved"] = True
            validate(
                artifacts,
                "refinement-approved-expansion",
                approved_expansion,
                baseline,
                current,
                expected=1,
            )
            fingerprint_drift_current = deepcopy(current)
            fingerprint_drift_current["fingerprint"] = "e" * 64
            fingerprint_drift = deepcopy(valid)
            fingerprint_drift["target"] = target(baseline, fingerprint_drift_current)
            validate(
                artifacts,
                "refinement-fingerprint-drift",
                fingerprint_drift,
                baseline,
                fingerprint_drift_current,
                expected=1,
            )
            planned_verification = deepcopy(valid)
            planned_verification["verification_plan"][0] = {
                "proof": "Run the mapped proof after implementation",
                "status": "PLANNED",
                "evidence_ids": [],
                "reason": "The strategy is read-only and the proof is executable later",
            }
            validate(
                artifacts,
                "planned-future-verification",
                planned_verification,
                baseline,
                current,
                expected=0,
            )
            planned_with_evidence = deepcopy(planned_verification)
            planned_with_evidence["verification_plan"][0]["evidence_ids"] = ["E_GREEN"]
            validate(
                artifacts,
                "planned-verification-with-executed-evidence",
                planned_with_evidence,
                baseline,
                current,
                expected=1,
            )
            unresolved_verification = deepcopy(planned_verification)
            unresolved_verification["verification_plan"][0]["status"] = "NOT_RUN"
            validate(
                artifacts,
                "unresolved-future-verification",
                unresolved_verification,
                baseline,
                current,
                expected=1,
            )
        else:
            failed_application = deepcopy(valid)
            failed_application["candidates"][0]["evidence_ids"] = ["E_RED"]
            validate(
                artifacts,
                "applied-with-failed-proof",
                failed_application,
                baseline,
                current,
                expected=1,
            )

        scope_drift = deepcopy(valid)
        scope_drift["scope"]["current_owned_paths"] = (
            ["a.txt", "b.txt", "c.txt"] if WORKFLOW == "refinement" else []
        )
        validate(artifacts, "scope-drift", scope_drift, baseline, current, expected=1)

        missing_proof = deepcopy(valid)
        missing_proof["scenarios"][0] = {
            "behavior": "Requested behavior",
            "status": "MISSING_REQUIRED",
            "evidence_ids": [],
            "reason": "Required proof is absent",
        }
        validate(
            artifacts, "missing-proof", missing_proof, baseline, current, expected=1
        )
        incomplete = deepcopy(missing_proof)
        incomplete["decision"] = {
            "result": {
                "feature": "CHANGES_REQUIRED",
                "bugfix": "CHANGES_REQUIRED",
                "refinement": "NOT_CONFIDENT",
                "simplification": "BLOCKED",
            }[WORKFLOW],
            "remaining": ["Prove the required scenario"],
        }
        validate(
            artifacts, "honest-incomplete", incomplete, baseline, current, expected=0
        )

        contradictory = deepcopy(valid)
        contradictory["gates"][0].update(
            {"status": "FAIL", "evidence_ids": [], "reason": "Mandatory gate failed"}
        )
        validate(
            artifacts,
            "contradictory-completion",
            contradictory,
            baseline,
            current,
            expected=1,
        )

        unauthorized = deepcopy(valid)
        unauthorized["external_actions"] = [
            {
                "kind": "change-request",
                "requested": False,
                "status": "PUBLISHED",
                "evidence_ids": ["E_GREEN"],
            }
        ]
        validate(
            artifacts,
            "unauthorized-action",
            unauthorized,
            baseline,
            current,
            expected=1,
        )

        (repo / "unrelated.txt").write_text(
            "agent changed user work\n", encoding="utf-8"
        )
        dirty_current = capture(repo)
        dirty = deepcopy(valid)
        dirty["target"] = target(baseline, dirty_current)
        dirty["file_coverage"] = [
            {"path": path, "reason": "Observed delta"}
            for path in delta_paths(baseline, dirty_current)
        ]
        validate(
            artifacts, "dirty-work-mutation", dirty, baseline, dirty_current, expected=1
        )

    print(
        f"PASS: {WORKFLOW} harness; valid, honest incomplete, HEAD and fingerprint "
        "invariants, unique requirement IDs, refinement read-only scope, planned "
        "verification, scope drift, missing proof, contradictory completion, Git "
        "isolation, counterfactual proof, dirty-work preservation, unauthorized "
        "external action"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
