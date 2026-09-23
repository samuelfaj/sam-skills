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
    snippet: str | None = None,
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
    # Pin the specific check, so the case fails if that check alone is removed.
    if snippet is not None and snippet not in result.stdout + result.stderr:
        raise AssertionError(f"{name}: missing {snippet!r}\n{result.stdout}{result.stderr}")


def scaffold(
    artifacts: Path,
    name: str,
    before: JsonObject,
    after: JsonObject | None = None,
    existing: JsonObject | None = None,
) -> JsonObject:
    baseline_path = artifacts / f"{name}-baseline.json"
    baseline_path.write_text(json.dumps(before), encoding="utf-8")
    report_path = artifacts / f"{name}-scaffold.json"
    if existing is not None:
        report_path.write_text(json.dumps(existing), encoding="utf-8")
    command = [
        sys.executable,
        "-B",
        str(SKILL_DIR / "scripts/validate_report.py"),
        "--scaffold",
        "--baseline",
        str(baseline_path),
    ]
    if after is not None:
        current_path = artifacts / f"{name}-current.json"
        current_path.write_text(json.dumps(after), encoding="utf-8")
        command.extend(["--current", str(current_path)])
    result = run([*command, str(report_path)], artifacts, check=False)
    if result.returncode != 0 or not result.stdout.startswith("SCAFFOLD:"):
        raise AssertionError(f"{name}: scaffold failed\n{result.stdout}{result.stderr}")
    value = json.loads(report_path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def refinement_extensions(
    repo: Path, artifacts: Path, valid: JsonObject, baseline: JsonObject, current: JsonObject
) -> None:
    """Scaffold, optional scenarios/gates, and re-checked plan-ledger reuse."""
    # Scaffold at freeze time (current defaults to baseline) is fail-closed.
    fresh = scaffold(artifacts, "scaffold-fresh", baseline)
    if fresh["target"] != target(baseline, baseline) or fresh["file_coverage"] != []:
        raise AssertionError("scaffold must derive target and file_coverage from bundles")
    if fresh["scope"] != {
        "initial_owned_paths": [],
        "current_owned_paths": [],
        "cycle": 1,
        "scope_expansion_approved": False,
    }:
        raise AssertionError("scaffold must prefill refinement scope constants")
    validate(artifacts, "scaffold-unfilled", fresh, baseline, current, expected=1)
    # Read-only run: the freeze-time target stays valid against the final capture,
    # so step 5 needs no re-scaffold unless the tree changed.
    filled = {**fresh, **{key: value for key, value in valid.items() if key != "target"}}
    validate(artifacts, "scaffold-filled-at-freeze", filled, baseline, current, expected=0)

    # Cycle 2 in place: re-scaffolding refreshes only target/file_coverage.
    stale = deepcopy(valid)
    stale["target"]["current_fingerprint"] = "0" * 64
    stale["scope"]["cycle"] = 2
    refreshed = scaffold(artifacts, "scaffold-refresh", baseline, current, stale)
    if refreshed["target"] != target(baseline, current):
        raise AssertionError("re-scaffold did not refresh target from the current bundle")
    if refreshed["claims"] != valid["claims"] or refreshed["scope"]["cycle"] != 2:
        raise AssertionError("re-scaffold overwrote authored fields")
    validate(artifacts, "scaffold-refreshed", refreshed, baseline, current, expected=0)

    optional = deepcopy(valid)
    optional["scenarios"] = []
    optional["gates"] = []
    validate(artifacts, "refinement-optional-scenarios-gates", optional, baseline, current, expected=0)
    # Optional means may be [], not absent: the contract documents the keys as required.
    no_keys = deepcopy(valid)
    del no_keys["scenarios"], no_keys["gates"]
    validate(
        artifacts, "refinement-scenarios-key-required", no_keys, baseline, current,
        expected=1, snippet="scenarios must be an array",
    )
    no_verification = deepcopy(optional)
    no_verification["verification_plan"] = []
    validate(artifacts, "refinement-missing-verification", no_verification, baseline, current, expected=1)
    no_material = deepcopy(valid)
    del no_material["claims"][0]["material"]
    validate(artifacts, "claim-without-material", no_material, baseline, current, expected=1)
    # Claims cite evidence by id, so a repeated id would make a citation ambiguous.
    repeated_evidence = deepcopy(valid)
    repeated_evidence["evidence"].append(deepcopy(repeated_evidence["evidence"][0]))
    validate(
        artifacts, "evidence-repeats-id", repeated_evidence, baseline, current,
        expected=1, snippet="evidence repeats id",
    )

    # Plan-ledger reuse: cite a plan FACT only after re-checking its locator.
    plan_path = artifacts / "plan-report.json"

    def write_plan(locator: str, classification: str = "FACT", workflow: str = "plan") -> None:
        plan = {
            "schema_version": 1,
            "workflow": workflow,
            "evidence": [
                {
                    "id": "E-001",
                    "kind": "CODE",
                    "classification": classification,
                    "claim": "app.txt holds the original value",
                    "locator": locator,
                }
            ],
        }
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

    reused = deepcopy(valid)
    reused["plan_report"] = str(plan_path)
    reused["evidence"].append(
        {
            "id": "E_PLAN",
            "status": "PASS",
            "classification": "TARGET",
            "detail": "Re-read app.txt:1; plan E-001 still holds",
            "plan_ref": "E-001",
            "locator": "app.txt:1",
        }
    )
    reused["claims"][0]["evidence_ids"] = ["E_PLAN"]
    write_plan("app.txt:1")
    validate(artifacts, "plan-ledger-reuse", reused, baseline, current, expected=0)

    def reject(name: str, report: JsonObject, snippet: str) -> None:
        validate(artifacts, name, report, baseline, current, expected=1, snippet=snippet)

    def with_locator(locator: str) -> JsonObject:
        case = deepcopy(reused)
        case["evidence"][-1]["locator"] = locator
        return case

    no_plan = deepcopy(reused)
    del no_plan["plan_report"]
    reject("plan-ref-without-plan-report", no_plan, "plan_report must be an absolute path")
    relative_plan = deepcopy(reused)
    relative_plan["plan_report"] = plan_path.name
    reject("plan-ref-relative-plan-report", relative_plan, "plan_report must be an absolute path")
    not_rechecked = deepcopy(reused)
    not_rechecked["evidence"][-1]["status"] = "NOT_RUN"
    reject("plan-ref-not-rechecked", not_rechecked, "plan_ref evidence must be PASS")
    # A locator differing from the plan's is a new claim, not a reused FACT.
    reject("plan-ref-locator-differs", with_locator("app.txt"), "must equal the locator of plan E-001")
    write_plan("app.txt:1", workflow="refinement")
    reject("plan-ref-not-a-plan", reused, "plan_report must be a plan freeze")
    write_plan("app.txt:1", classification="ASSUMPTION")
    reject("plan-ref-not-fact", reused, "is not a FACT in plan_report")
    write_plan("app.txt:9")
    reject("plan-ref-stale-locator", with_locator("app.txt:9"), "line 9 is out of range")
    write_plan("missing.txt:1")
    reject("plan-ref-missing-file", with_locator("missing.txt:1"), "does not resolve in the captured tree")
    # An existing file outside the repository never supports a claim about it.
    (repo.parent / "outside.txt").write_text("outside\n", encoding="utf-8")
    write_plan("../outside.txt")
    reject("plan-ref-outside-repo", with_locator("../outside.txt"), "does not resolve in the captured tree")
    # A decision locator names no file to re-read; the contract documents it as
    # exempt, so only its equality with the plan's locator is checked.
    write_plan("user decision: keep app.txt unchanged")
    validate(
        artifacts, "plan-ref-decision-locator",
        with_locator("user decision: keep app.txt unchanged"), baseline, current, expected=0,
    )
    if not (repo / "app.txt").is_file():
        raise AssertionError("fixture app.txt missing; plan-ledger cases are vacuous")
    pinned_plan_ref_checks(repo.parent / "pinned", artifacts, reused, write_plan)
    scaffold_baseline_checks(repo.parent / "rebased", artifacts, valid)


def pinned_plan_ref_checks(
    repo: Path, artifacts: Path, reused: JsonObject, write_plan: Any
) -> None:
    """Parents re-validate the refine report after implementation commits, so a
    locator is checked against the capture, never the live tree."""
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    (repo / "app.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    git(repo, "add", "app.txt")
    git(repo, "commit", "-qm", "baseline")
    (repo / "notes.txt").write_text("dirty one\ndirty two\n", encoding="utf-8")
    bundle = capture(repo)
    report = deepcopy(reused)
    report["target"] = target(bundle, bundle)

    def check(name: str, locator: str, expected: int, snippet: str | None = None) -> None:
        case = deepcopy(report)
        case["evidence"][-1]["locator"] = locator
        write_plan(locator)
        validate(artifacts, name, case, bundle, bundle, expected=expected, snippet=snippet)

    check("plan-ref-pinned-before", "app.txt:4", 0)
    check("plan-ref-dirty-captured", "notes.txt:2", 0)
    # A later commit shrinks the cited file: the captured answer stands.
    (repo / "app.txt").write_text("one\n", encoding="utf-8")
    git(repo, "commit", "-qam", "implementation")
    check("plan-ref-pinned-after-commit", "app.txt:4", 0)
    check("plan-ref-pinned-stale", "app.txt:5", 1, "line 5 is out of range (4 lines)")
    # A dirty file edited after capture no longer matches its captured bytes.
    (repo / "notes.txt").write_text("changed\n", encoding="utf-8")
    check("plan-ref-dirty-changed", "notes.txt:2", 1, "does not resolve in the captured tree")


def scaffold_baseline_checks(repo: Path, artifacts: Path, valid: JsonObject) -> None:
    """A re-scaffold on a new baseline never keeps evidence or conclusions."""
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    (repo / "app.txt").write_text("first\n", encoding="utf-8")
    git(repo, "add", "app.txt")
    git(repo, "commit", "-qm", "first")
    old = capture(repo)
    (repo / "app.txt").write_text("second\n", encoding="utf-8")
    git(repo, "commit", "-qam", "second")
    new = capture(repo)
    report = deepcopy(valid)
    report["target"] = target(old, old)
    old_path = artifacts / "rebased-old.json"
    new_path = artifacts / "rebased-new.json"
    report_path = artifacts / "rebased-report.json"
    prior_path = artifacts / "rebased-prior.json"
    old_path.write_text(json.dumps(old), encoding="utf-8")
    new_path.write_text(json.dumps(new), encoding="utf-8")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    command = [
        sys.executable, "-B", str(SKILL_DIR / "scripts/validate_report.py"),
        "--scaffold", "--baseline", str(new_path),
    ]
    refused = run([*command, str(report_path)], artifacts, check=False)
    if refused.returncode != 2 or "belongs to another baseline" not in refused.stderr:
        raise AssertionError(f"scaffold merged a report from another baseline: {refused.stderr}")
    if json.loads(report_path.read_text(encoding="utf-8")) != report:
        raise AssertionError("refused scaffold rewrote the existing report")
    report_path.rename(prior_path)
    carried = run([*command, "--from", str(prior_path), str(report_path)], artifacts, check=False)
    if carried.returncode != 0:
        raise AssertionError(f"--from scaffold failed: {carried.stderr}")
    fresh = json.loads(report_path.read_text(encoding="utf-8"))
    if fresh["intent"] != valid["intent"] or fresh["scope"]["cycle"] != 2:
        raise AssertionError("--from must carry intent and advance the cycle")
    if fresh["claims"][0]["claim"] != valid["claims"][0]["claim"] or any(
        item.get("evidence_ids") for key in ("claims", "loopholes", "verification_plan")
        for item in fresh[key]
    ):
        raise AssertionError("--from must keep ledger text but drop every evidence citation")
    if {item["status"] for item in fresh["loopholes"]} != {"OPEN"} or any(
        item["status"] == "PASS" for item in fresh["verification_plan"]
    ) or "|" not in fresh["decision"]["result"] or fresh["evidence"][0]["id"]:
        raise AssertionError("--from must reset loopholes, verifications, evidence, and decision")
    validate(artifacts, "rebased-carry-unproven", fresh, new, new, expected=1)


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
            closed_not_run = deepcopy(valid)
            closed_not_run["evidence"].append(
                {
                    "id": "E_NOT_RUN",
                    "status": "NOT_RUN",
                    "classification": "TARGET",
                    "detail": "Never executed",
                }
            )
            closed_not_run["loopholes"][0]["evidence_ids"] = ["E_NOT_RUN"]
            validate(
                artifacts,
                "closed-loophole-without-pass",
                closed_not_run,
                baseline,
                current,
                expected=1,
            )
            unknown_no_probe = deepcopy(valid)
            unknown_no_probe["claims"] = [
                {
                    "claim": "Maybe the approach works",
                    "status": "UNKNOWN",
                    "material": False,
                    "evidence_ids": [],
                }
            ]
            validate(
                artifacts,
                "unknown-claim-without-probe",
                unknown_no_probe,
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
            refinement_extensions(repo, artifacts, valid, baseline, current)
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
        "external action, scaffold, optional scenarios/gates, plan-ledger reuse"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
