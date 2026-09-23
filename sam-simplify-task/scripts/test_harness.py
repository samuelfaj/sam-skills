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
import time
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
    # Agents read only this stderr line, so it must describe the exact bundle.
    summary = (
        f"scope: head={value['head_sha']} fingerprint={value['fingerprint']} "
        f"files={value['file_count']}"
    )
    if result.stderr.strip() != summary:
        raise AssertionError(f"capture summary does not match bundle: {result.stderr}")
    return value


def racy_index_check(root: Path) -> None:
    """A same-size edit in the same second as the index write must still count.

    Git re-hashes a racily clean entry only when the index keeps its own mtime,
    so the temporary index copy must preserve it or the edit reads as clean.
    """
    repo = root / "racy"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "core.checkStat", "minimal")
    git(repo, "config", "core.trustctime", "false")
    source = repo / "a.txt"
    stamp = int(time.time()) - 60
    source.write_text("v1\n", encoding="utf-8")
    os.utime(source, (stamp, stamp))
    git(repo, "add", "a.txt")
    git(repo, "commit", "-qm", "baseline")
    source.write_text("v2\n", encoding="utf-8")
    os.utime(source, (stamp, stamp))
    os.utime(repo / ".git/index", (stamp, stamp))
    if capture(repo)["file_count"] != 1:
        raise AssertionError("racily clean same-size edit was captured as clean")


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


def run_validator(artifacts: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(
        [sys.executable, "-B", str(SKILL_DIR / "scripts/validate_report.py"), *args],
        artifacts,
        check=False,
    )


def scaffold_checks(
    artifacts: Path, valid: JsonObject, before: JsonObject, after: JsonObject
) -> None:
    """The scaffold replaces hand-typed hashes and paths, so it must derive them
    exactly, keep authored work, carry only frozen intent, and never validate
    while a placeholder remains."""
    baseline_path = artifacts / "scaffold-baseline.json"
    current_path = artifacts / "scaffold-current.json"
    baseline_path.write_text(json.dumps(before), encoding="utf-8")
    current_path.write_text(json.dumps(after), encoding="utf-8")
    bundles = ["--baseline", str(baseline_path), "--current", str(current_path)]

    def write_scaffold(
        path: Path, *extra: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        result = run_validator(artifacts, "--scaffold", *extra, str(path))
        if result.returncode != expected:
            raise AssertionError(
                f"scaffold {path.name}: expected {expected}, got {result.returncode}\n"
                f"{result.stdout}{result.stderr}"
            )
        return result

    fresh_path = artifacts / "scaffold-fresh.json"
    write_scaffold(fresh_path, *bundles)
    fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
    if fresh["target"] != target(before, after) or [
        item["path"] for item in fresh["file_coverage"]
    ] != delta_paths(before, after):
        raise AssertionError("scaffold did not derive target and the exact delta")
    if any(item["reason"] for item in fresh["file_coverage"]):
        raise AssertionError("scaffold invented file_coverage reasons")
    validate(artifacts, "scaffold-untouched", fresh, before, after, expected=1)

    early_path = artifacts / "scaffold-baseline-only.json"
    write_scaffold(early_path, "--baseline", str(baseline_path))
    early = json.loads(early_path.read_text(encoding="utf-8"))
    if early["target"] != target(before, before) or early["file_coverage"]:
        raise AssertionError("baseline-only scaffold must target the baseline alone")

    # Step 5 refresh of a step 1 scaffold: same baseline, new current capture.
    merged_path = artifacts / "scaffold-merged.json"
    authored = {
        key: deepcopy(value)
        for key, value in valid.items()
        if key not in {"schema_version", "workflow"}
    }
    authored["target"] = target(before, before)
    authored["file_coverage"] = valid["file_coverage"] + [
        {"path": "no-longer-changed.txt", "reason": "stale entry"}
    ]
    merged_path.write_text(json.dumps(authored), encoding="utf-8")
    write_scaffold(merged_path, *bundles)
    merged = json.loads(merged_path.read_text(encoding="utf-8"))
    if merged != valid:
        raise AssertionError("scaffold refresh lost authored fields or kept stale paths")
    validate(artifacts, "scaffold-merged", merged, before, after, expected=0)

    # A report left by an earlier iteration (another baseline) must never absorb
    # a new baseline: its evidence, statuses, and cycle would pass as fresh.
    stale_path = artifacts / "scaffold-stale-baseline.json"
    stale_report = deepcopy(valid)
    stale_report["target"] = target(after, after)
    stale_path.write_text(json.dumps(stale_report), encoding="utf-8")
    refused = write_scaffold(
        stale_path, "--baseline", str(baseline_path), expected=2
    )
    if json.loads(stale_path.read_text(encoding="utf-8")) != stale_report:
        raise AssertionError("scaffold merged a report from another baseline")
    # A parent may already cite that report, so the recovery the refusal names
    # first must leave it in place: a new report path carried with --from.
    if "scaffold a new report path with --from REPORT" not in refused.stderr:
        raise AssertionError(f"stale-baseline refusal lacks the new-path recovery: {refused.stderr}")

    prior_path = artifacts / "scaffold-prior.json"
    prior_path.write_text(json.dumps(valid), encoding="utf-8")
    carried_path = artifacts / "scaffold-carried.json"
    write_scaffold(carried_path, "--from", str(prior_path), *bundles)
    carried = json.loads(carried_path.read_text(encoding="utf-8"))
    if (
        carried["intent"] != valid["intent"]
        or carried["scope"]["cycle"] != valid["scope"]["cycle"] + 1
        or carried["scope"]["current_owned_paths"]
        != valid["scope"]["current_owned_paths"]
    ):
        raise AssertionError("--from must carry intent and ownership and bump cycle")
    if carried["evidence"][0]["status"] != "PASS|FAIL|NOT_RUN" or "|" not in str(
        carried["decision"]["result"]
    ):
        raise AssertionError("--from must never carry evidence or a decision")
    if WORKFLOW == "bugfix" and (
        carried["bug"]["root_cause"] != valid["bug"]["root_cause"]
        or carried["bug"]["root_cause_evidence_ids"]
    ):
        raise AssertionError("--from must carry bug text but not its evidence")
    if WORKFLOW == "feature" and (
        [item["id"] for item in carried["requirements"]]
        != [item["id"] for item in valid["requirements"]]
        or any(item["evidence_ids"] for item in carried["requirements"])
        or any("|" not in item["status"] for item in carried["requirements"])
    ):
        raise AssertionError("--from must carry requirement text, not status or evidence")
    validate(artifacts, "scaffold-carried", carried, before, after, expected=1)
    write_scaffold(prior_path, "--from", str(prior_path), *bundles, expected=2)
    if json.loads(prior_path.read_text(encoding="utf-8")) != valid:
        raise AssertionError("--from onto itself must not rewrite the prior report")

    wrong_path = artifacts / "scaffold-wrong-workflow.json"
    wrong_path.write_text(json.dumps({**valid, "workflow": "other"}), encoding="utf-8")
    write_scaffold(
        artifacts / "scaffold-unused.json", "--from", str(wrong_path), *bundles, expected=2
    )
    corrupt_path = artifacts / "scaffold-corrupt.json"
    corrupt_path.write_text("{not json", encoding="utf-8")
    write_scaffold(corrupt_path, *bundles, expected=2)
    if corrupt_path.read_text(encoding="utf-8") != "{not json":
        raise AssertionError("scaffold overwrote an unreadable existing report")


def gate_and_reuse_checks(
    artifacts: Path, valid: JsonObject, before: JsonObject, after: JsonObject
) -> None:
    """Parent-owned gates and reused evidence skip work, so each is accepted only
    under its exact mechanical condition."""
    parent_owned = deepcopy(valid)
    parent_owned["gates"].append(
        {
            "name": "code-review",
            "mandatory": True,
            "status": "NOT_APPLICABLE",
            "evidence_ids": [],
            "reason": "owned by parent phase",
        }
    )
    # Only implementation children hand review and coverage to the parent;
    # a simplification cannot skip a mandatory gate this way.
    validate(
        artifacts,
        "parent-owned-gate",
        parent_owned,
        before,
        after,
        expected=1 if WORKFLOW == "simplification" else 0,
    )
    skipped_mandatory = deepcopy(parent_owned)
    skipped_mandatory["gates"][-1]["reason"] = "not needed"
    validate(
        artifacts, "skipped-mandatory-gate", skipped_mandatory, before, after, expected=1
    )
    # The parent takes over only a gate that never ran here: a mandatory gate
    # that FAILED or was NOT_RUN still blocks, whatever its reason says.
    for status in ("FAIL", "NOT_RUN"):
        ran_owned = deepcopy(parent_owned)
        ran_owned["gates"][-1]["status"] = status
        validate(
            artifacts, f"parent-owned-{status.lower()}-gate", ran_owned, before, after, expected=1
        )
    # Only review, coverage, and browser-proof gates move to the parent; the
    # child's own proof gate can never be handed off.
    core_gate = deepcopy(valid)
    core_gate["gates"][0].update(
        {
            "mandatory": True,
            "status": "NOT_APPLICABLE",
            "evidence_ids": [],
            "reason": "owned by parent phase",
        }
    )
    validate(artifacts, "parent-owned-core-gate", core_gate, before, after, expected=1)

    def reuse_report(
        name: str, prior: JsonObject, report: JsonObject, reused_id: str = "E_GREEN"
    ) -> JsonObject:
        prior_path = artifacts / f"{name}-prior.json"
        prior_path.write_text(json.dumps(prior), encoding="utf-8")
        report = deepcopy(report)
        report["evidence"].append(
            {
                "id": "E_REUSED",
                "status": "PASS",
                "classification": "TARGET",
                "detail": "Pre-edit checks passed in the prior phase",
                "reused_from": str(prior_path),
                "reused_id": reused_id,
            }
        )
        return report

    # A completed report whose final state is exactly this baseline and which
    # cites E_GREEN as gate and scenario proof of that state.
    matching = deepcopy(valid)
    matching["target"] = target(before, before)
    no_delta = deepcopy(valid)
    no_delta["target"] = target(before, before)
    no_delta["file_coverage"] = []
    if WORKFLOW == "simplification":
        no_delta["candidates"] = [
            {
                "opportunity": "Inline a helper",
                "status": "SKIPPED",
                "reason": "Subjective polish",
            }
        ]
        no_delta["decision"] = {"result": "NO_CHANGE", "remaining": []}
    validate(artifacts, "no-delta-honest", no_delta, before, before, expected=0)

    if WORKFLOW != "simplification":
        # Implementation children always run their own proof.
        validate(
            artifacts,
            "reuse-outside-simplification",
            reuse_report("reuse-outside", matching, valid),
            before,
            after,
            expected=1,
        )
        return

    implementation = deepcopy(matching)
    implementation["workflow"] = "bugfix"
    implementation["decision"]["result"] = "COMPLETE"
    accepted = (
        ("reuse-matching-baseline", matching),
        ("reuse-from-implementation", implementation),
    )
    for name, prior in accepted:
        validate(
            artifacts, name, reuse_report(name, prior, valid), before, after, expected=0
        )

    # Identical state (no delta): reused proof still proves the current state.
    identical = reuse_report("reuse-identical-state", matching, no_delta)
    identical["behavior_proof"]["evidence_ids"] = ["E_REUSED"]
    identical["scenarios"][0]["evidence_ids"] = ["E_REUSED"]
    validate(
        artifacts, "reuse-identical-state-proof", identical, before, before, expected=0
    )

    # After an edit, reused evidence records only the baseline: every slot that
    # proves the current state must cite fresh evidence.
    post_edit_slots = {
        "behavior": lambda r: r["behavior_proof"],
        "scenario": lambda r: r["scenarios"][0],
        "gate": lambda r: r["gates"][0],
        "candidate": lambda r: r["candidates"][0],
    }
    for slot, locate in post_edit_slots.items():
        cited = reuse_report(f"reuse-post-edit-{slot}", matching, valid)
        locate(cited)["evidence_ids"] = ["E_REUSED"]
        validate(
            artifacts,
            f"reuse-cited-as-post-edit-{slot}",
            cited,
            before,
            after,
            expected=1,
        )

    stub = {
        "workflow": "bugfix",
        "target": {
            "current_head_sha": before["head_sha"],
            "current_fingerprint": before["fingerprint"],
        },
        "decision": {"result": "COMPLETE", "remaining": []},
    }
    other_workflow = deepcopy(matching)
    other_workflow["workflow"] = "refinement"
    other_workflow["decision"]["result"] = "HIGH_CONFIDENCE"
    stale = deepcopy(matching)
    stale["target"]["current_fingerprint"] = "0" * 64
    other_paths = deepcopy(matching)
    other_paths["target"]["paths"] = ["elsewhere"]
    unfinished = deepcopy(matching)
    unfinished["decision"] = {"result": "BLOCKED", "remaining": ["x"]}
    chained = deepcopy(matching)
    next(item for item in chained["evidence"] if item["id"] == "E_GREEN")[
        "reused_from"
    ] = str(artifacts / "earlier-report.json")
    no_schema = deepcopy(matching)
    del no_schema["schema_version"]
    # The validator does not re-validate the prior, so a prior that still cites
    # a failed check as PASS gate/scenario proof must not lend it as a pass.
    source_failed = deepcopy(matching)
    next(item for item in source_failed["evidence"] if item["id"] == "E_GREEN")[
        "status"
    ] = "FAIL"
    rejected = [
        ("reuse-from-stub", stub, "E_GREEN"),
        ("reuse-other-workflow", other_workflow, "E_GREEN"),
        ("reuse-stale-state", stale, "E_GREEN"),
        ("reuse-other-paths", other_paths, "E_GREEN"),
        ("reuse-incomplete-prior", unfinished, "E_GREEN"),
        ("reuse-unknown-id", matching, "E_MISSING"),
        # E_REQ passed but the prior never cited it as proof of its final state.
        ("reuse-uncited-id", matching, "E_REQ"),
        ("reuse-chained", chained, "E_GREEN"),
        ("reuse-prior-no-schema", no_schema, "E_GREEN"),
        ("reuse-source-not-pass", source_failed, "E_GREEN"),
    ]
    for name, prior, reused_id in rejected:
        validate(
            artifacts,
            name,
            reuse_report(name, prior, valid, reused_id),
            before,
            after,
            expected=1,
        )
    not_pass = reuse_report("reuse-entry-not-pass", matching, valid)
    next(item for item in not_pass["evidence"] if item["id"] == "E_REUSED")[
        "status"
    ] = "NOT_RUN"
    validate(artifacts, "reuse-entry-not-pass", not_pass, before, after, expected=1)
    self_citation = deepcopy(no_delta)
    self_citation["evidence"].append(
        {
            "id": "E_SELF",
            "status": "PASS",
            "classification": "TARGET",
            "detail": "Circular reuse",
            "reused_from": str(artifacts / "reuse-self-citation-report.json"),
            "reused_id": "E_GREEN",
        }
    )
    validate(
        artifacts, "reuse-self-citation", self_citation, before, before, expected=1
    )

    # A simplification claim needs both an applied candidate and a real change.
    applied_without_delta = deepcopy(no_delta)
    applied_without_delta["candidates"] = deepcopy(valid["candidates"])
    applied_without_delta["decision"] = {
        "result": "SIMPLEST_DEFENSIBLE",
        "remaining": [],
    }
    validate(
        artifacts,
        "simplest-without-delta",
        applied_without_delta,
        before,
        before,
        expected=1,
    )
    delta_without_applied = deepcopy(valid)
    delta_without_applied["candidates"] = deepcopy(no_delta["candidates"])
    validate(
        artifacts,
        "simplest-without-applied",
        delta_without_applied,
        before,
        after,
        expected=1,
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
        racy_index_check(root)

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

        scaffold_checks(artifacts, valid, baseline, current)
        gate_and_reuse_checks(artifacts, valid, baseline, current)

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
        "external action, capture summary, scaffold and stale-baseline refusal, "
        "parent-owned gates, baseline-only evidence reuse"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
