#!/usr/bin/env python3
"""Exercise orchestration validation and neutrality conformance."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from validate_orchestration import neutrality_violations

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_orchestration.py"
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent
SUITE_VALIDATOR = REPO_ROOT / "scripts" / "validate_skill_suite.py"


def evidence(
    evidence_id: str,
    task_id: str,
    requirement: str,
    *,
    evidence_type: str = "OBSERVATION",
    status: str = "PASS",
    classification: str = "TARGET",
) -> dict[str, Any]:
    return {
        "id": evidence_id,
        "task_id": task_id,
        "requirement": requirement,
        "type": evidence_type,
        "status": status,
        "classification": classification,
        "detail": f"Evidence for {task_id}: {requirement}",
    }


DEFAULT_HOST = "grok"

RUNTIME_BY_CAPABILITY = {
    "LIGHT": {
        "host": DEFAULT_HOST,
        "role": "fast_scan",
        "model": "grok-4.6",
        "effort": "medium",
        "fallback_reason": None,
    },
    "STANDARD": {
        "host": DEFAULT_HOST,
        "role": "routine_worker",
        "model": "grok-4.6",
        "effort": "high",
        "fallback_reason": None,
    },
    "DEEP": {
        "host": DEFAULT_HOST,
        "role": "deep_worker",
        "model": "grok-4.6",
        "effort": "xhigh",
        "fallback_reason": None,
    },
    "REVIEWER": {
        "host": DEFAULT_HOST,
        "role": "reviewer",
        "model": "grok-4.6",
        "effort": "high",
        "fallback_reason": None,
    },
}


def node(
    node_id: str,
    *,
    kind: str,
    owner: str,
    capability: str,
    objective: str,
    requirement: str,
    depends_on: list[str] | None = None,
    writable_paths: list[str] | None = None,
    artifact_classes: list[str] | None = None,
    status: str = "COMPLETE",
    evidence_ids: list[str] | None = None,
    direct_action_reason: str | None = None,
    blocker: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = ...,  # type: ignore[assignment]
) -> dict[str, Any]:
    if runtime is ...:
        if kind in {"EXECUTION", "REVIEW"}:
            bound = copy.deepcopy(RUNTIME_BY_CAPABILITY[capability])
        else:
            bound = None
    else:
        bound = runtime
    return {
        "id": node_id,
        "kind": kind,
        "owner": owner,
        "capability": capability,
        "runtime": bound,
        "depends_on": [] if depends_on is None else depends_on,
        "objective": objective,
        "no_go": ["Do not change unrelated surfaces"],
        "proof_requirements": [requirement],
        "artifact_classes": [] if artifact_classes is None else artifact_classes,
        "writable_paths": [] if writable_paths is None else writable_paths,
        "direct_action_reason": direct_action_reason,
        "status": status,
        "evidence_ids": [] if evidence_ids is None else evidence_ids,
        "blocker": blocker,
    }


def valid_t0() -> dict[str, Any]:
    requirement = "Document diff matches the assigned scope"
    return {
        "schema_version": 2,
        "task": {
            "classification": "T0",
            "goal": "Update one bounded document",
            "success_criteria": ["Document contains the requested correction"],
            "constraints": ["Preserve unrelated content"],
            "no_go": ["Do not edit other files"],
            "risk_flags": [],
            "active_host": DEFAULT_HOST,
            "changed_artifacts": ["DOCS"],
            "changed_files": [
                {
                    "path": "docs/guide.md",
                    "artifact_class": "DOCS",
                    "producer_task_id": "E1",
                }
            ],
            "review_requested": False,
        },
        "dag": [
            node(
                "E1",
                kind="EXECUTION",
                owner="worker-1",
                capability="LIGHT",
                objective="Update the requested sentence",
                requirement=requirement,
                writable_paths=["docs/guide.md"],
                artifact_classes=["DOCS"],
                evidence_ids=["V1"],
            )
        ],
        "evidence": [evidence("V1", "E1", requirement, evidence_type="DIFF")],
        "review_gate": {
            "required": False,
            "reasons": ["Documentation-only mechanical change"],
            "status": "NOT_REQUIRED",
            "review_task_id": None,
        },
        "decision": {"result": "COMPLETE", "remaining_task_ids": []},
    }


def valid_t0_code_absolute_certainty() -> dict[str, Any]:
    """T0 micro CODE change with 100% controller certainty — no REVIEWER."""
    requirement = "One-line fix stays in the assigned file"
    return {
        "schema_version": 2,
        "task": {
            "classification": "T0",
            "goal": "Fix a typo in one constant",
            "success_criteria": ["Constant spelling corrected"],
            "constraints": ["Touch only the constant line"],
            "no_go": ["Do not refactor"],
            "risk_flags": [],
            "active_host": DEFAULT_HOST,
            "changed_artifacts": ["CODE"],
            "changed_files": [
                {
                    "path": "src/labels.py",
                    "artifact_class": "CODE",
                    "producer_task_id": "E1",
                }
            ],
            "review_requested": False,
            "controller_certainty": "absolute",
        },
        "dag": [
            node(
                "E1",
                kind="EXECUTION",
                owner="worker-1",
                capability="LIGHT",
                objective="Correct the typo",
                requirement=requirement,
                writable_paths=["src/labels.py"],
                artifact_classes=["CODE"],
                evidence_ids=["V1"],
            )
        ],
        "evidence": [evidence("V1", "E1", requirement, evidence_type="DIFF")],
        "review_gate": {
            "required": False,
            "reasons": ["micro_task_absolute_certainty"],
            "status": "NOT_REQUIRED",
            "review_task_id": None,
        },
        "decision": {"result": "COMPLETE", "remaining_task_ids": []},
    }


def valid_t1_code_high_certainty() -> dict[str, Any]:
    """T1 single STANDARD slice with high certainty — no REVIEWER."""
    requirement = "Bounded service change stays in scope"
    return {
        "schema_version": 2,
        "task": {
            "classification": "T1",
            "goal": "Adjust one service helper",
            "success_criteria": ["Helper behavior updated"],
            "constraints": ["Single file only"],
            "no_go": ["Do not expand API surface"],
            "risk_flags": [],
            "active_host": DEFAULT_HOST,
            "changed_artifacts": ["CODE"],
            "changed_files": [
                {
                    "path": "src/helper.py",
                    "artifact_class": "CODE",
                    "producer_task_id": "E1",
                }
            ],
            "review_requested": False,
            "controller_certainty": "high",
        },
        "dag": [
            node(
                "E1",
                kind="EXECUTION",
                owner="worker-1",
                capability="STANDARD",
                objective="Update the helper",
                requirement=requirement,
                writable_paths=["src/helper.py"],
                artifact_classes=["CODE"],
                evidence_ids=["V1"],
            )
        ],
        "evidence": [evidence("V1", "E1", requirement, evidence_type="DIFF")],
        "review_gate": {
            "required": False,
            "reasons": ["micro_task_high_certainty"],
            "status": "NOT_REQUIRED",
            "review_task_id": None,
        },
        "decision": {"result": "COMPLETE", "remaining_task_ids": []},
    }


def valid_t2() -> dict[str, Any]:
    runtime_requirement = "Runtime diff matches the assigned scope"
    test_requirement = "Focused regression tests pass"
    review_requirement = "Independent review finds no required correction"
    return {
        "schema_version": 2,
        "task": {
            "classification": "T2",
            "goal": "Deliver coordinated runtime changes",
            "success_criteria": ["Focused tests and independent review pass"],
            "constraints": [],
            "no_go": ["Do not change unrelated files"],
            "risk_flags": [],
            "active_host": DEFAULT_HOST,
            "changed_artifacts": ["CODE", "TEST"],
            "changed_files": [
                {
                    "path": "src/service.py",
                    "artifact_class": "CODE",
                    "producer_task_id": "E1",
                },
                {
                    "path": "tests/test_service.py",
                    "artifact_class": "TEST",
                    "producer_task_id": "E2",
                },
            ],
            "review_requested": False,
        },
        "dag": [
            node(
                "E1",
                kind="EXECUTION",
                owner="worker-1",
                capability="STANDARD",
                objective="Implement the runtime change",
                requirement=runtime_requirement,
                writable_paths=["src/service.py"],
                artifact_classes=["CODE"],
                evidence_ids=["V1"],
            ),
            node(
                "E2",
                kind="EXECUTION",
                owner="worker-2",
                capability="STANDARD",
                objective="Add regression coverage",
                requirement=test_requirement,
                writable_paths=["tests/test_service.py"],
                artifact_classes=["TEST"],
                evidence_ids=["V2"],
            ),
            node(
                "R1",
                kind="REVIEW",
                owner="reviewer-1",
                capability="REVIEWER",
                objective="Review the combined result",
                requirement=review_requirement,
                depends_on=["E1", "E2"],
                evidence_ids=["V3"],
            ),
        ],
        "evidence": [
            evidence("V1", "E1", runtime_requirement, evidence_type="DIFF"),
            evidence("V2", "E2", test_requirement, evidence_type="COMMAND"),
            evidence("V3", "R1", review_requirement),
        ],
        "review_gate": {
            "required": True,
            "reasons": ["Code and tests changed", "Multiple producers contributed"],
            "status": "PASS",
            "review_task_id": "R1",
            "rounds": 1,
        },
        "decision": {"result": "COMPLETE", "remaining_task_ids": []},
    }


def valid_review_cap_blocked() -> dict[str, Any]:
    """Third review round still fails: stop for a user decision, never a 4th round."""
    report = valid_t2()
    review = report["dag"][2]
    requirement = review["proof_requirements"][0]
    review["status"] = "BLOCKED"
    review["evidence_ids"] = ["V3", "B1"]
    review["blocker"] = {
        "kind": "USER_DECISION",
        "source": "review round cap reached",
        "evidence_ids": ["B1"],
    }
    report["evidence"][2]["status"] = "FAIL"
    report["evidence"].append(
        evidence(
            "B1",
            "R1",
            requirement,
            evidence_type="USER",
            status="INFO",
            classification="EXTERNAL",
        )
    )
    report["review_gate"].update(status="FAIL", rounds=3)
    report["decision"] = {"result": "BLOCKED", "remaining_task_ids": ["R1"]}
    return report


SCAFFOLD = SCRIPT_DIR / "scaffold_report.py"


def scaffold_spec(active_host: str | None) -> dict[str, Any]:
    """Judgment-only input; every mechanical field is left to the scaffold."""
    task: dict[str, Any] = {
        "classification": "T2",
        "goal": "Deliver coordinated runtime changes",
        "success_criteria": ["Focused tests and independent review pass"],
        "no_go": ["Do not change unrelated files"],
    }
    if active_host is not None:
        task["active_host"] = active_host
    base_node = {"kind": "EXECUTION", "capability": "STANDARD", "no_go": ["Stay in scope"]}
    return {
        "task": task,
        "files": {"src/service.py": "CODE"},
        "nodes": [
            {**base_node, "id": "E1", "objective": "Runtime change",
             "proof_requirements": ["Runtime diff matches scope"],
             "writable_paths": ["src"], "status": "COMPLETE"},
            {**base_node, "id": "E2", "objective": "Regression coverage",
             "proof_requirements": ["Focused tests pass"], "writable_paths": ["tests"],
             "artifact_classes": ["TEST"], "status": "COMPLETE"},
            {"id": "R1", "kind": "REVIEW", "capability": "REVIEWER",
             "objective": "Independent review", "no_go": ["Read-only"],
             "proof_requirements": ["Review finds no required correction"],
             "depends_on": ["E1", "E2"], "status": "COMPLETE"},
        ],
        "evidence": [
            {"id": f"V{index}", "task_id": task_id, "type": "COMMAND", "status": "PASS",
             "classification": "TARGET", "detail": f"{task_id} proof exited 0"}
            for index, task_id in enumerate(("E1", "E2", "R1"), start=1)
        ],
        "review_rounds": 1,
    }


def scaffold_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCAFFOLD), *args],
        check=False, capture_output=True, text=True,
    )


def run_scaffold(
    spec: dict[str, Any], freeze: Path, out: Path
) -> subprocess.CompletedProcess[str]:
    spec_path = out.parent / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return scaffold_cli("--spec", str(spec_path), "--out", str(out), "--freeze", str(freeze))


def scaffold_manifest(out: Path) -> dict[str, tuple[str, str]]:
    report = json.loads(out.read_text(encoding="utf-8"))
    return {f["path"]: (f["producer_task_id"], f["artifact_class"])
            for f in report["task"]["changed_files"]}


def validate_scaffold(active_host: str | None) -> None:
    """Mechanical fields come from real files and the matrix, and the result validates."""
    with tempfile.TemporaryDirectory(prefix="sam-orchestrate-scaffold-") as temp_dir:
        root = Path(temp_dir)
        repo, run = root / "repo", root / "run"
        (repo / "src").mkdir(parents=True)
        run.mkdir()
        for name in ("service.py", "other.py"):
            (repo / "src" / name).write_text("OLD = 1\n", encoding="utf-8")
        git = ["git", "-C", str(repo), "-c", "user.email=h@example.invalid", "-c", "user.name=h"]

        def sh(*args: str) -> None:
            subprocess.run([*git, *args], check=True, capture_output=True)

        for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "base"]):
            sh(*args)
        # User work that predates the run sits inside E1's writable scope.
        (repo / "src" / "other.py").write_text("USER_WIP = 1\n", encoding="utf-8")
        (repo / "src" / "notes.py").write_text("draft\n", encoding="utf-8")
        freeze = run / "freeze.json"
        # Any path inside the repository resolves to its root, so paths stay root-relative.
        frozen = scaffold_cli("--freeze-out", str(freeze), "--repo", str(repo / "src"))
        if frozen.returncode != 0 or not frozen.stdout.startswith("FROZE"):
            raise AssertionError(f"freeze failed\nstderr={frozen.stderr}")
        # Review round 1 reviewed its own diff beside the freeze.
        (run / "review-1.diff").write_text("round 1\n", encoding="utf-8")
        # The run: E1 edits and checkpoint-commits; E2 adds an untracked test.
        (repo / "src" / "service.py").write_text("NEW = 2\n", encoding="utf-8")
        sh("add", "src/service.py")
        sh("commit", "-qm", "checkpoint")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_service.py").write_text("pass\n", encoding="utf-8")
        out = run / "report.json"
        result = run_scaffold(scaffold_spec(active_host), freeze, out)
        if result.returncode != 0:
            raise AssertionError(f"scaffold failed\nstderr={result.stderr}")
        report = json.loads(out.read_text(encoding="utf-8"))
        run_validator(report, True)
        # Owners are neutral and derived; runtime is the matrix row, never typed.
        if [n["owner"] for n in report["dag"]] != ["worker-1", "worker-2", "reviewer-1"]:
            raise AssertionError("scaffold must derive neutral owner ids by kind")
        if report["dag"][0]["runtime"] != RUNTIME_BY_CAPABILITY["STANDARD"]:
            raise AssertionError("scaffold must bind the STANDARD matrix row")
        if report["dag"][2]["runtime"] != RUNTIME_BY_CAPABILITY["REVIEWER"]:
            raise AssertionError("scaffold must bind the REVIEWER matrix row")
        # Only changes made after the freeze are credited: the pre-existing user work
        # in E1's scope is not, the checkpoint commit does not hide E1's edit, and the
        # untracked test is found and attributed to its only producer.
        if scaffold_manifest(out) != {"src/service.py": ("E1", "CODE"),
                                      "tests/test_service.py": ("E2", "TEST")}:
            raise AssertionError(f"scaffold manifest is wrong: {scaffold_manifest(out)}")
        gate = report["review_gate"]
        if not gate["required"] or "multiple producers contributed" not in gate["reasons"]:
            raise AssertionError("scaffold must derive the multi-producer review trigger")
        if report["decision"]["result"] != "COMPLETE":
            raise AssertionError("scaffold must derive COMPLETE from settled nodes")
        # A listed path that did not change after the freeze is an invented claim,
        # including untouched pre-existing user work.
        for ghost in ("src/ghost.py", "src/other.py"):
            spec = scaffold_spec(active_host)
            spec["files"][ghost] = "CODE"
            rejected = run_scaffold(spec, freeze, out)
            if rejected.returncode == 0 or "did not change after the freeze" not in rejected.stderr:
                raise AssertionError(f"scaffold must reject unchanged listed path {ghost}")
        # An unrelated change outside every writable scope is rejected, not absorbed.
        (repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
        rejected = run_scaffold(scaffold_spec(active_host), freeze, out)
        if rejected.returncode == 0 or "outside every writable scope" not in rejected.stderr:
            raise AssertionError("scaffold must reject changes outside writable scopes")
        (repo / "unrelated.txt").unlink()
        # Fail closed: with no review diff on disk and no typed count, no round
        # is credited and the validator rejects the passing gate.
        (run / "review-1.diff").rename(run / "held-round.txt")
        spec = scaffold_spec(active_host)
        del spec["review_rounds"]
        if run_scaffold(spec, freeze, out).returncode != 0:
            raise AssertionError("scaffold must still write a report without review_rounds")
        run_validator(
            json.loads(out.read_text(encoding="utf-8")),
            False,
            "review_gate.rounds must record at least 1 completed review round",
        )
        (run / "held-round.txt").rename(run / "review-1.diff")
        # Nodes without a recorded status stay PENDING, so nothing is claimed done.
        spec = scaffold_spec(active_host)
        for entry in spec["nodes"]:
            entry.pop("status")
        run_scaffold(spec, freeze, out)
        if json.loads(out.read_text(encoding="utf-8"))["decision"]["result"] == "COMPLETE":
            raise AssertionError("scaffold must not default nodes to COMPLETE")
        # The review diff shows uncommitted and new run files, never pre-existing work.
        first = scaffold_cli("--freeze", str(freeze), "--diff-out", str(run / "review-1.diff"))
        diff = (run / "review-1.diff").read_text(encoding="utf-8")
        if first.returncode != 0 or "NEW = 2" not in diff or "tests/test_service.py" not in diff:
            raise AssertionError(f"review diff must hold every run change\n{first.stderr}{diff}")
        if "USER_WIP" in diff or "notes.py" in diff:
            raise AssertionError("review diff must exclude work that predates the freeze")
        reviewed = first.stdout.split("tree=")[1].split()[0]
        # The workspace tree fingerprints proof inputs: stable until something changes.
        if scaffold_cli("--tree", "--repo", str(repo)).stdout.strip() != f"tree={reviewed}":
            raise AssertionError("an unchanged workspace must keep its tree id")
        (repo / "tests" / "test_service.py").write_text("assert True\n", encoding="utf-8")
        if scaffold_cli("--tree", "--repo", str(repo)).stdout.strip() == f"tree={reviewed}":
            raise AssertionError("a workspace change must change the tree id")
        # Round 2 reviews only the correction delta since the reviewed tree.
        delta = scaffold_cli("--freeze", str(freeze), "--diff-out", str(run / "review-2.diff"),
                             "--since", reviewed)
        diff = (run / "review-2.diff").read_text(encoding="utf-8")
        if delta.returncode != 0 or "assert True" not in diff or "src/service.py" in diff:
            raise AssertionError(f"delta diff must hold only the correction\n{delta.stderr}{diff}")
        # A run change to pre-existing dirty work is captured, never silently dropped.
        (repo / "src" / "other.py").write_text("USER_WIP = 1\nRUN = 2\n", encoding="utf-8")
        spec = scaffold_spec(active_host)
        spec["nodes"][0]["artifact_classes"] = ["CODE"]
        spec["review_rounds"] = 2
        if run_scaffold(spec, freeze, out).returncode != 0 or (
            scaffold_manifest(out).get("src/other.py") != ("E1", "CODE")
        ):
            raise AssertionError("a run change to a pre-existing dirty file must be credited")
        # The round count is the review diffs on disk; a typed count cannot hide rounds.
        spec["review_rounds"] = 1
        understated = run_scaffold(spec, freeze, out)
        if understated.returncode == 0 or "disagrees with 2 review-<n>.diff" not in understated.stderr:
            raise AssertionError("scaffold must refuse a review_rounds count below the diffs on disk")
        for extra in (3, 4):
            (run / f"review-{extra}.diff").write_text(f"round {extra}\n", encoding="utf-8")
        del spec["review_rounds"]
        if run_scaffold(spec, freeze, out).returncode != 0:
            raise AssertionError("scaffold must derive the round count from the diffs")
        run_validator(json.loads(out.read_text(encoding="utf-8")), False, "exceeds the 3-round review cap")
        # Snapshots never touch the user's index.
        staged = subprocess.run([*git, "diff", "--cached", "--name-only"], check=True,
                                capture_output=True, text=True).stdout
        if staged.strip():
            raise AssertionError(f"scaffold must not stage files: {staged}")
        # A same-size edit in the same second as the last index write (checkpoint
        # commit, then an immediate edit) still reaches the tree and the review diff.
        # Pinned mtimes make that one second deterministic; ctime is ignored so the
        # mtimes alone decide, as they do when both land in the same second.
        sh("config", "core.trustctime", "false")
        service, stamp = repo / "src" / "service.py", int(time.time()) - 5
        service.write_text("X = 22\n", encoding="utf-8")
        os.utime(service, (stamp, stamp))
        sh("add", "src/service.py")
        sh("commit", "-qm", "racy checkpoint")
        checkpoint = scaffold_cli("--tree", "--repo", str(repo)).stdout.strip()
        service.write_text("X = 33\n", encoding="utf-8")
        os.utime(service, (stamp, stamp))
        os.utime(repo / ".git" / "index", (stamp, stamp))
        edited = scaffold_cli("--tree", "--repo", str(repo)).stdout.strip()
        racy = scaffold_cli("--freeze", str(freeze), "--diff-out", str(run / "racy.diff"))
        diff = (run / "racy.diff").read_text(encoding="utf-8")
        if edited == checkpoint or racy.returncode != 0 or "+X = 33" not in diff:
            raise AssertionError(f"a same-second edit must reach tree and diff\n{racy.stderr}{diff}")
        # --since takes only a tree id; an option-shaped value never reaches git.
        smuggled = run / "smuggled.txt"
        bad = scaffold_cli("--freeze", str(freeze), "--diff-out", str(run / "bad.diff"),
                           f"--since=--output={smuggled}")
        if bad.returncode == 0 or smuggled.exists() or "not a tree id" not in bad.stderr:
            raise AssertionError("scaffold must reject a --since that is not a tree id")
        # A failed diff (unknown tree id) leaves no review-<n>.diff to count as a round.
        failed = scaffold_cli("--freeze", str(freeze), "--diff-out", str(run / "review-9.diff"),
                              "--since", "0" * 40)
        if failed.returncode == 0 or list(run.glob("*review-9.diff*")):
            raise AssertionError("a failed --diff-out must leave no review diff behind")
        # Assume-unchanged and skip-worktree bits never hide an edit from the snapshot.
        for flag, name in (("--assume-unchanged", "service.py"), ("--skip-worktree", "flagged.py")):
            (repo / "src" / name).write_text("FLAG = 0\n", encoding="utf-8")
            sh("add", f"src/{name}")
            sh("commit", "-qm", f"track {name}")
            sh("update-index", flag, f"src/{name}")
            before = scaffold_cli("--tree", "--repo", str(repo)).stdout.strip()
            (repo / "src" / name).write_text("FLAG = 1\n", encoding="utf-8")
            hidden = scaffold_cli("--freeze", str(freeze), "--diff-out", str(run / "flag.diff"))
            diff = (run / "flag.diff").read_text(encoding="utf-8")
            if scaffold_cli("--tree", "--repo", str(repo)).stdout.strip() == before or (
                hidden.returncode != 0 or "+FLAG = 1" not in diff
            ):
                raise AssertionError(f"a {flag} edit must reach tree and diff\n{hidden.stderr}{diff}")


def valid_direct_integration() -> dict[str, Any]:
    report = valid_t2()
    report["dag"][1] = node(
        "O1",
        kind="ORCHESTRATION",
        owner="controller-1",
        capability="STANDARD",
        objective="Integrate the worker artifact",
        requirement="Integration diff matches the declared scope",
        depends_on=["E1"],
        writable_paths=["integration/result.md"],
        artifact_classes=["DOCS"],
        direct_action_reason="Only the controller can reconcile the returned boundary",
        evidence_ids=["V2"],
    )
    report["dag"][2]["depends_on"] = ["E1", "O1"]
    report["task"]["changed_artifacts"] = ["CODE", "DOCS"]
    report["task"]["changed_files"][1] = {
        "path": "integration/result.md",
        "artifact_class": "DOCS",
        "producer_task_id": "O1",
    }
    report["evidence"][1] = evidence(
        "V2", "O1", "Integration diff matches the declared scope", evidence_type="DIFF"
    )
    return report


def valid_blocked() -> dict[str, Any]:
    report = valid_t0()
    report["task"]["changed_artifacts"] = []
    report["task"]["changed_files"] = []
    report["dag"][0]["status"] = "BLOCKED"
    report["dag"][0]["blocker"] = {
        "kind": "USER_DECISION",
        "source": "required user choice",
        "evidence_ids": ["B1"],
    }
    requirement = report["dag"][0]["proof_requirements"][0]
    report["dag"][0]["evidence_ids"] = ["B1"]
    report["evidence"] = [
        evidence(
            "B1",
            "E1",
            requirement,
            evidence_type="USER",
            status="INFO",
            classification="EXTERNAL",
        )
    ]
    report["decision"] = {"result": "BLOCKED", "remaining_task_ids": ["E1"]}
    return report


def valid_dependency_blocked() -> dict[str, Any]:
    report = valid_blocked()
    upstream_requirement = "External prerequisite is available"
    report["dag"].insert(
        0,
        node(
            "O1",
            kind="ORCHESTRATION",
            owner="controller-1",
            capability="STANDARD",
            objective="Verify the external prerequisite",
            requirement=upstream_requirement,
            status="BLOCKED",
            evidence_ids=["B0"],
            blocker={
                "kind": "EXTERNAL",
                "source": "external prerequisite",
                "evidence_ids": ["B0"],
            },
        ),
    )
    report["dag"][1]["depends_on"] = ["O1"]
    report["dag"][1]["blocker"] = {
        "kind": "DEPENDENCY",
        "source": "O1",
        "evidence_ids": ["B1"],
    }
    report["evidence"].insert(
        0,
        evidence(
            "B0",
            "O1",
            upstream_requirement,
            status="INFO",
            classification="EXTERNAL",
        ),
    )
    report["decision"] = {
        "result": "BLOCKED",
        "remaining_task_ids": ["O1", "E1"],
    }
    return report


def valid_in_progress() -> dict[str, Any]:
    report = valid_t0()
    report["task"]["changed_artifacts"] = []
    report["task"]["changed_files"] = []
    report["dag"][0]["status"] = "PENDING"
    report["dag"][0]["evidence_ids"] = []
    report["evidence"] = []
    report["decision"] = {
        "result": "IN_PROGRESS",
        "remaining_task_ids": ["E1"],
    }
    return report


def run_validator(
    report: dict[str, Any],
    expected_success: bool,
    expected_error: str | None = None,
) -> None:
    with tempfile.TemporaryDirectory(prefix="sam-orchestrate-test-") as temp_dir:
        report_path = Path(temp_dir) / "report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-B", str(VALIDATOR), str(report_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    if (result.returncode == 0) != expected_success:
        raise AssertionError(
            f"validator expectation mismatch\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    if expected_error is not None and expected_error not in result.stderr:
        raise AssertionError(
            f"validator missed expected error {expected_error!r}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )


def validate_neutrality_adversaries() -> None:
    for label in (
        "canonical/SKILL.md",
        "reference/routing-policy.md",
        "metadata/agent.yaml",
    ):
        violations = neutrality_violations({label: "model: named-route"})
        if not violations:
            raise AssertionError(f"semantic neutrality scan missed {label}")
    # Matrix and output contract may document approved host runtimes.
    if neutrality_violations(
        {"canonical/references/host-runtime-matrix.md": "model = gpt-5.6-luna"}
    ):
        raise AssertionError("host matrix document must be excluded from free-form scan")

    if not SUITE_VALIDATOR.is_file():
        raise AssertionError("repository portability validator is missing")
    # Use a provider name still forbidden after sam-orchestrate replacements.
    forbidden_identity = "Gem" + "ini"
    relative_targets = (
        Path("sam-orchestrate/SKILL.md"),
        Path("sam-orchestrate/references/routing-policy.md"),
        Path("sam-orchestrate/agents/openai.yaml"),
    )
    with tempfile.TemporaryDirectory(prefix="sam-orchestrate-neutrality-") as temp_dir:
        baseline_root = Path(temp_dir) / "baseline"
        shutil.copytree(SKILL_DIR, baseline_root / SKILL_DIR.name)
        baseline = subprocess.run(
            [sys.executable, "-B", str(SUITE_VALIDATOR), str(baseline_root)],
            check=False,
            capture_output=True,
            text=True,
        )
        if baseline.returncode != 0:
            raise AssertionError(
                f"neutrality baseline must pass\nstdout={baseline.stdout}\nstderr={baseline.stderr}"
            )
        for index, relative_target in enumerate(relative_targets):
            case_root = Path(temp_dir) / f"case-{index}"
            shutil.copytree(baseline_root, case_root)
            target = case_root / relative_target
            target.write_text(
                target.read_text(encoding="utf-8")
                + f"\nRouting identity: {forbidden_identity}\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-B", str(SUITE_VALIDATOR), str(case_root)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                raise AssertionError(
                    f"portability scan missed named routing in {relative_target}"
                )
            if "forbidden" not in result.stderr:
                raise AssertionError(
                    f"portability case failed for the wrong reason in {relative_target}\n"
                    f"stdout={result.stdout}\nstderr={result.stderr}"
                )


def expect_failure(
    mutator: Any,
    expected_error: str,
    base: Any = valid_t2,
) -> None:
    report = copy.deepcopy(base())
    mutator(report)
    run_validator(report, False, expected_error)


def main() -> int:
    # Codex keeps every producer on Luna and accepts independent Astra review.
    codex_report = valid_t2()
    codex_report["task"]["active_host"] = "codex"
    for entry in codex_report["dag"]:
        review = entry["kind"] == "REVIEW"
        entry["runtime"] = {
            "host": "codex",
            "role": "reviewer" if review else "routine_worker",
            "model": "gpt-6-astra" if review else "gpt-5.6-luna",
            "effort": "medium" if review else "xhigh",
            "fallback_reason": None,
        }
    run_validator(codex_report, True)
    codex_report["dag"][0]["runtime"].update(
        role="genius_worker", model="gpt-5.6-luna", effort="max"
    )
    run_validator(codex_report, True)
    wrong_worker = copy.deepcopy(codex_report)
    wrong_worker["dag"][0]["runtime"].update(
        model="gpt-6-astra", fallback_reason="Luna unavailable"
    )
    run_validator(wrong_worker, False, "must match host-runtime-matrix model")
    codex_report["dag"][-1]["runtime"]["model"] = "gpt-5.6-sol"
    run_validator(codex_report, False, "must match host-runtime-matrix")

    for report in (
        valid_t0(),
        valid_t0_code_absolute_certainty(),
        valid_t1_code_high_certainty(),
        valid_t2(),
        valid_direct_integration(),
        valid_blocked(),
        valid_dependency_blocked(),
        valid_in_progress(),
        valid_review_cap_blocked(),
    ):
        run_validator(report, True)

    # Review rounds are capped: a completed review must be counted, and a failing
    # third round must stop for a user decision instead of looping.
    expect_failure(
        lambda report: report["review_gate"].pop("rounds"),
        "review_gate.rounds must record at least 1 completed review round",
    )
    expect_failure(
        lambda report: report["review_gate"].update(rounds=4),
        "exceeds the 3-round review cap",
    )

    def keep_looping_at_cap(report: dict[str, Any]) -> None:
        report["dag"][2].update(status="PENDING", blocker=None, evidence_ids=["V3"])
        report["evidence"].pop()
        report["decision"] = {"result": "IN_PROGRESS", "remaining_task_ids": ["R1"]}

    expect_failure(
        keep_looping_at_cap,
        "review round cap reached with a failing gate requires the review node BLOCKED",
        valid_review_cap_blocked,
    )
    expect_failure(
        lambda report: report["review_gate"].update(rounds=1),
        "non-required review gate must not record review rounds",
        valid_t0,
    )
    validate_scaffold(DEFAULT_HOST)

    # Absolute certainty without the T0 micro-task prerequisites must fail closed.
    expect_failure(
        lambda report: report["task"].update({"controller_certainty": "absolute"}),
        "controller_certainty=absolute only for T0",
        valid_t2,
    )
    # DEEP without T3/risk is forbidden (cheap-first).
    def force_deep_on_t1(report: dict[str, Any]) -> None:
        report["dag"][0]["capability"] = "DEEP"
        report["dag"][0]["runtime"] = {
            "host": DEFAULT_HOST,
            "role": "deep_worker",
            "model": "grok-4.6",
            "effort": "xhigh",
            "fallback_reason": None,
        }

    expect_failure(
        force_deep_on_t1,
        "DEEP capability requires T3",
        valid_t1_code_high_certainty,
    )

    expect_failure(
        lambda report: report["dag"][0].pop("objective"),
        "missing keys: objective",
        valid_t0,
    )
    expect_failure(
        lambda report: report["dag"][0].update({"no_go": []}),
        "dag[0].no_go must not be empty",
        valid_t0,
    )
    expect_failure(
        lambda report: report["dag"][0].update({"proof_requirements": []}),
        "dag[0].proof_requirements must not be empty",
        valid_t0,
    )

    expect_failure(
        lambda report: report["evidence"][0].update({"classification": "BASELINE"}),
        "complete node E1 lacks dedicated TARGET/PASS proof",
        valid_t0,
    )
    expect_failure(
        lambda report: report["dag"][1].update({"evidence_ids": ["V1"]}),
        "node E2 cannot reference evidence dedicated to E1",
    )

    def break_dependency_state(report: dict[str, Any]) -> None:
        report["dag"].insert(
            0,
            node(
                "O1",
                kind="ORCHESTRATION",
                owner="controller-1",
                capability="STANDARD",
                objective="Prepare a prerequisite",
                requirement="Prerequisite is ready",
                status="PENDING",
            ),
        )
        report["dag"][1]["depends_on"] = ["O1"]
        report["decision"] = {
            "result": "IN_PROGRESS",
            "remaining_task_ids": ["O1"],
        }

    expect_failure(
        break_dependency_state,
        "COMPLETE node E1 requires COMPLETE dependency O1",
        valid_t0,
    )

    def break_running_state(report: dict[str, Any]) -> None:
        report["dag"].insert(
            0,
            node(
                "O1",
                kind="ORCHESTRATION",
                owner="controller-1",
                capability="STANDARD",
                objective="Prepare a prerequisite",
                requirement="Prerequisite is ready",
                status="PENDING",
            ),
        )
        report["dag"][1]["depends_on"] = ["O1"]
        report["dag"][1]["status"] = "RUNNING"
        report["decision"]["remaining_task_ids"] = ["O1", "E1"]

    expect_failure(
        break_running_state,
        "RUNNING node E1 requires COMPLETE dependency O1",
        valid_in_progress,
    )
    expect_failure(
        lambda report: report["dag"][0].update({"blocker": None}),
        "blocked node E1 requires blocker provenance",
        valid_blocked,
    )
    expect_failure(
        lambda report: report["evidence"][0].update(
            {"classification": "TARGET", "status": "PASS"}
        ),
        "must have blocker provenance classification",
        valid_blocked,
    )
    expect_failure(
        lambda report: report["dag"][1]["blocker"].update({"source": "E1"}),
        "dependency blocker must name a direct dependency",
        valid_dependency_blocked,
    )

    def leave_runnable_work(report: dict[str, Any]) -> None:
        report["dag"].append(
            node(
                "O2",
                kind="ORCHESTRATION",
                owner="controller-2",
                capability="LIGHT",
                objective="Reconcile controller state",
                requirement="Controller state is current",
                status="PENDING",
            )
        )
        report["decision"]["remaining_task_ids"].append("O2")

    expect_failure(
        leave_runnable_work,
        "BLOCKED decision is invalid while runnable tasks remain",
        valid_blocked,
    )
    expect_failure(
        lambda report: report["decision"].update({"result": "IN_PROGRESS"}),
        "IN_PROGRESS decision requires a RUNNING or dependency-ready PENDING node",
        valid_dependency_blocked,
    )

    expect_failure(
        lambda report: report["dag"][1].update({"direct_action_reason": None}),
        "writable orchestration requires direct_action_reason",
        valid_direct_integration,
    )
    expect_failure(
        lambda report: report["task"]["changed_files"].pop(),
        "complete producer O1 must own at least one changed file",
        valid_direct_integration,
    )
    expect_failure(
        lambda report: report["dag"][2].update({"depends_on": ["E1"]}),
        "review task must depend on producer node O1",
        valid_direct_integration,
    )
    expect_failure(
        lambda report: report["task"].update({"changed_artifacts": ["DOCS"]}),
        "task.changed_artifacts must equal the classes in task.changed_files",
    )
    expect_failure(
        lambda report: report["task"]["changed_files"][0].update(
            {"path": "outside/service.py"}
        ),
        "path is outside producer E1 writable scope",
    )
    expect_failure(
        lambda report: report["task"]["changed_files"][0].update(
            {"producer_task_id": "R1"}
        ),
        "producer_task_id must reference a producer",
    )

    expect_failure(
        lambda report: report["dag"][2].update({"depends_on": ["E1"]}),
        "review task must depend on producer node E2",
    )
    expect_failure(
        lambda report: report["evidence"][2].update({"classification": "BASELINE"}),
        "complete node R1 lacks dedicated TARGET/PASS proof",
    )
    expect_failure(
        lambda report: report["dag"][2].update(
            {"writable_paths": ["src/review-fix"], "artifact_classes": ["CODE"]}
        ),
        "review nodes must be read-only",
    )
    expect_failure(
        lambda report: report["dag"][0].update({"owner": "model-x-worker"}),
        "owner must use the neutral",
        valid_t0,
    )
    expect_failure(
        lambda report: report["dag"][0]["runtime"].update(
            {"model": "not-a-matrix-model", "fallback_reason": None}
        ),
        "runtime must match host-runtime-matrix",
        valid_t0,
    )
    expect_failure(
        lambda report: report["task"].update({"active_host": "unknown-host"}),
        "task.active_host must be codex, claude-code, or grok",
        valid_t0,
    )

    def hide_review_trigger(report: dict[str, Any]) -> None:
        report["task"]["changed_artifacts"] = ["DOCS"]
        report["review_gate"] = {
            "required": False,
            "reasons": [],
            "status": "NOT_REQUIRED",
            "review_task_id": None,
        }
        report["dag"] = report["dag"][:2]
        report["evidence"] = report["evidence"][:2]

    expect_failure(
        hide_review_trigger,
        "review_gate.required must be true for recorded triggers",
    )

    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    if "Exclusive top pipeline" not in skill:
        raise AssertionError("sam-orchestrate must declare Exclusive top pipeline")
    if "Fix forward" not in skill:
        raise AssertionError("sam-orchestrate must fix forward instead of restarting")

    validate_neutrality_adversaries()
    print("PASS: orchestration contract, adversarial fixtures, and neutrality conformance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
