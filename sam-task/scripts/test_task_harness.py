#!/usr/bin/env python3
"""Adversarial checks for the sam-task report validator and scaffold.

The real validator and scaffold are copied into a temporary skills tree whose
sibling validators (sam-work, sam-review, sam-council, sam-plan,
sam-refine-task) are stubs, so cited-report re-validation runs for real.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_task_report.py"
SCAFFOLD = ROOT / "scripts/scaffold_task_report.py"
HEAD = "a" * 40
BASE = "b" * 40
FP = "c" * 64
PROMPT = "d" * 64
IN_FP = "e" * 64
OUT_FP = "f" * 64
OLD_HEAD = "1" * 40
WORK_PATH = "/tmp/repository/work-report.json"
WORK_REVIEW_PATH = "/tmp/repository/work-review.json"
COUNCIL_PATH = "/tmp/repository/council.json"
WORK_RECEIPT = "PASS: stub sam-work"
REVIEW_RECEIPT = "PASS: stub sam-review"
COUNCIL_RECEIPT = "PASS: stub sam-council"
REFINE_RECEIPT = "PASS: stub sam-refine-task"
PLAN_RECEIPT = "PASS: stub sam-plan"
STUB = """import json, os, sys
report = json.load(open(sys.argv[-1], encoding="utf-8"))
if report.get("expect_cwd") and os.path.realpath(os.getcwd()) != os.path.realpath(report["expect_cwd"]):
    print("FAIL: validator ran outside the target repo", file=sys.stderr)
    sys.exit(1)
if report.get("stub_invalid"):
    print("FAIL: stub rejects report", file=sys.stderr)
    sys.exit(1)
if report.get("stub_bytes"):
    sys.stderr.buffer.write(b"FAIL: non-UTF-8 caf\\xe9\\n")
    sys.exit(1)
print("PASS: stub {name}")
"""
STUB_VALIDATORS = [
    ("sam-work", "validate_work_report.py"),
    ("sam-review", "validate_review.py"),
    ("sam-council", "validate_council_report.py"),
    ("sam-plan", "validate_plan_report.py"),
    ("sam-refine-task", "validate_report.py"),
]


def build_tree(root: Path) -> None:
    """Copy the real scripts next to stub siblings and point the harness at them."""
    global VALIDATOR, SCAFFOLD
    scripts = root / "skills" / "sam-task" / "scripts"
    scripts.mkdir(parents=True)
    for source in (VALIDATOR, SCAFFOLD):
        shutil.copy2(source, scripts / source.name)
    for skill, script in STUB_VALIDATORS:
        path = root / "skills" / skill / "scripts" / script
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(STUB.format(name=skill), encoding="utf-8")
    VALIDATOR = scripts / "validate_task_report.py"
    SCAFFOLD = scripts / "scaffold_task_report.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review_report(*, head: str = HEAD, base: str = BASE, result: str = "APPROVE") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": {"mode": "branch", "base_sha": base, "head_sha": head, "bundle_fingerprint": FP},
        "decision": {"result": result},
    }


def work_report(
    *,
    web_system: bool = True,
    playwright_discovered: int = 2,
    playwright_uploaded: int = 2,
    demo_uploaded: int = 1,
    result: str = "COMPLETE",
    head: str = HEAD,
    stub_invalid: bool = False,
) -> dict[str, Any]:
    report = {
        "schema_version": 2,
        "workflow_id": "work-001",
        "request": {
            "prompt_sha256": PROMPT,
            "classification": "BUG",
            "web_system": web_system,
        },
        "target": {
            "repo_root": "/tmp/repository",
            "base_ref": "main",
            "base_sha": BASE,
            "final_head_sha": head,
            "final_change_fingerprint": FP,
        },
        "phases": [
            {
                "id": "review",
                "report_path": WORK_REVIEW_PATH,
                "validator_receipts": [REVIEW_RECEIPT],
            }
        ],
        "video_inventory": {
            "playwright_discovered": playwright_discovered,
            "playwright_uploaded": playwright_uploaded,
            "demo_discovered": demo_uploaded,
            "demo_uploaded": demo_uploaded,
        },
        "final": {"result": result, "final_head_sha": head},
    }
    if stub_invalid:
        report["stub_invalid"] = True
    return report


def advisor_consult(
    *,
    phase: str = "refine",
    status: str = "ANSWERED",
    failure_reason: Any = None,
) -> dict[str, Any]:
    return {
        "id": "A-001",
        "advisor": "sam-example-advisor",
        "phase": phase,
        "model": "advisor-model",
        "effort": "high",
        "effort_source": "MATRIX_DEFAULT",
        "question": "Is the frozen rollback path safe under partial writes?",
        "status": status,
        "caller_decision": "ACCEPTED",
        "decision_reason": "Confirmed against the migration receipts.",
        "failure_reason": failure_reason,
        "evidence": ["consult receipt"],
    }


def run_validate(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(VALIDATOR), str(path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )


def iteration(status: str, *, open_items: list[str] | None = None, corrections: list[str] | None = None) -> dict[str, Any]:
    return {
        "sequence": 1,
        "input_fingerprint": IN_FP,
        "output_fingerprint": OUT_FP,
        "status": status,
        "open_required_items": open_items or [],
        "correction_receipts": corrections or [],
        "evidence": [f"receipt for {status}"],
    }


def closure_iteration(
    sequence: int,
    *,
    review_status: str = "APPROVE",
    council: bool = True,
    council_status: str = "TRIAGE_PASS",
    open_findings: list[str] | None = None,
    corrections: list[str] | None = None,
    head: str = HEAD,
    evidence: str = "clean review and council pair",
    review_path: str | None = None,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "head_sha": head,
        "review_status": review_status,
        "review_report_path": None,
        "review_reused_from": review_path or WORK_REVIEW_PATH,
        "review_validator_args": [],
        "council_profile": "fast" if council else None,
        "council_status": council_status if council else "NOT_RUN",
        "council_report_path": COUNCIL_PATH if council else None,
        "open_findings": open_findings or [],
        "correction_receipts": corrections or [],
        "review_receipt": REVIEW_RECEIPT,
        "council_receipt": COUNCIL_RECEIPT if council else None,
        "evidence": [evidence],
    }


def phase(
    phase_id: str,
    skill: str,
    status: str,
    *,
    head: str | None,
    iterations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": phase_id,
        "skill": skill,
        "status": status,
        "current": True,
        "validated_head_sha": head,
        "evidence": [f"evidence for {phase_id}"],
        "validator_receipts": [f"VALID:{phase_id}"],
        "iterations": iterations
        or [
            {
                **iteration(status),
                "sequence": 1,
            }
        ],
    }


def valid_report() -> dict[str, Any]:
    return {
        "schema_version": 3,
        "workflow": "task",
        "workflow_id": "task-001",
        "status": "COMPLETE",
        "request": {
            "prompt_sha256": PROMPT,
            "prompt_summary": "Deliver the invoicing fix end to end",
            "classification": "BUG",
        },
        "target": {
            "repo_root": "/tmp/repository",
            "base_ref": "main",
            "base_sha": BASE,
            "final_head_sha": HEAD,
            "final_change_fingerprint": FP,
            "web_surface": True,
            "web_surface_evidence": ["dev server script and routed pages"],
        },
        "plan": {
            "plan_dir": "/tmp/repository/plan",
            "depth": "simple",
            "status": "READY_TO_EXECUTE",
            "validator_receipt": "VALID",
            "freeze_path": "/tmp/repository/plan/plan-report.json",
        },
        "refine_report_path": "/tmp/repository/plan/refine-report.json",
        "phases": [
            phase("plan", "sam-plan", "READY_TO_EXECUTE", head=None),
            phase("refine", "sam-refine-task", "HIGH_CONFIDENCE", head=None),
            phase("work", "sam-work", "COMPLETE", head=HEAD),
            phase("closure", "sam-review+sam-council", "CLEAN", head=HEAD),
            phase("learn", "sam-task", "LEARNING_AUDITED", head=HEAD),
        ],
        "closure": {
            "max_iterations": 5,
            "iterations_used": 1,
            "final_status": "CLEAN",
            "iterations": [closure_iteration(1)],
        },
        "learning": {
            "status": "LEARNING_AUDITED",
            "write_policy": "PROPOSAL_ONLY",
            "audited_head_sha": HEAD,
            "candidates": [],
            "writes_performed": [],
            "evidence": ["learning audit found no durable candidate"],
        },
        "work_report_path": WORK_PATH,
        "advisor_consults": [],
        "residuals": [],
        "blockers": [],
    }


def write(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def assert_valid(path: Path) -> None:
    result = run_validate(path)
    if result.returncode != 0 or "VALID" not in result.stdout:
        raise AssertionError(f"expected VALID: {result.stdout}{result.stderr}")


def assert_invalid(path: Path, snippet: str) -> None:
    result = run_validate(path)
    if result.returncode == 0:
        raise AssertionError(f"expected INVALID containing {snippet!r}")
    if snippet not in result.stdout:
        raise AssertionError(f"missing {snippet!r} in:\n{result.stdout}")


def run_scaffold(out: Path, freeze_path: Path, refine_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, "-B", str(SCAFFOLD), str(out),
            "--freeze", str(freeze_path), "--refine", str(refine_path), "--work", WORK_PATH, *extra,
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )


def scaffold_round_trip(root: Path, freeze_path: Path, refine_path: Path) -> None:
    """The scaffold derives every mechanical field; only typed decisions remain."""
    # Nothing recorded yet: the learning audit stays fail-closed, never presumed done.
    empty = root / "rt-empty-task-report.json"
    run_scaffold(empty, freeze_path, refine_path)
    if not str(json.loads(empty.read_text(encoding="utf-8"))["learning"]["status"]).startswith("SCAFFOLD:"):
        raise AssertionError("scaffold must not presume LEARNING_AUDITED")

    out = root / "rt-task-report.json"
    write(
        out,
        {
            "closure": {
                "iterations": [
                    {
                        "review_reused_from": WORK_REVIEW_PATH,
                        "council_report_path": COUNCIL_PATH,
                        "open_findings": [],
                        "correction_receipts": [],
                        "evidence": ["closure iteration 1 cites the sam-work review"],
                    }
                ]
            },
            "learning": {"status": "LEARNING_AUDITED", "candidates": []},
        },
    )
    result = run_scaffold(
        out, freeze_path, refine_path,
        "--workflow-id", "task-rt",
        "--web-surface", "true",
        "--web-surface-evidence", "dev server script and routed pages",
    )
    if result.returncode != 0 or "closure=CLEAN" not in result.stdout:
        raise AssertionError(f"scaffold failed: {result.stdout}{result.stderr}")
    report = json.loads(out.read_text(encoding="utf-8"))
    closure = report["closure"]["iterations"][0]
    if closure["head_sha"] != HEAD or closure["council_receipt"] != COUNCIL_RECEIPT:
        raise AssertionError("scaffold did not derive closure head and receipts from files")
    if report["phases"][2]["iterations"][-1]["output_fingerprint"] != sha256(Path(WORK_PATH)):
        raise AssertionError("scaffold did not pin the work report fingerprint")
    if report["phases"][1]["validator_receipts"] != [REFINE_RECEIPT] or not report["refine_validator_args"]:
        raise AssertionError("scaffold did not derive the refine receipt from validator-args.json")
    assert_invalid(out, "unfilled scaffold placeholder")
    report["learning"]["evidence"] = ["learning audit found no durable candidate"]
    report["status"] = "COMPLETE"
    write(out, report)
    assert_valid(out)

    # A recorded learning write survives a refresh, so the validator rejects it.
    violated = deepcopy(report)
    violated["learning"]["writes_performed"] = ["edited AGENTS.md"]
    violated_path = root / "rt-learning-write.json"
    write(violated_path, violated)
    run_scaffold(violated_path, freeze_path, refine_path)
    refreshed = json.loads(violated_path.read_text(encoding="utf-8"))
    if refreshed["learning"]["writes_performed"] != ["edited AGENTS.md"]:
        raise AssertionError("scaffold refresh erased a recorded learning write")
    if "VIOLATED" not in refreshed["phases"][4]["validator_receipts"][0]:
        raise AssertionError("scaffold learn receipt must reflect the recorded write")
    assert_invalid(violated_path, "writes_performed must be empty")

    # A fresh closure review: the scaffold takes its validator arguments from
    # validator-args.json beside the review report and re-derives the receipt.
    review_dir = root / "run" / "closure-1"
    review_dir.mkdir(parents=True)
    fresh_review = review_dir / "review.json"
    write(fresh_review, review_report())
    (review_dir / "validator-args.json").write_text(
        json.dumps(["--bundle", str(review_dir / "bundle.json")]), encoding="utf-8"
    )
    iteration_one = report["closure"]["iterations"][0]
    iteration_one.update(review_reused_from=None, review_report_path=str(fresh_review), review_receipt=None)
    iteration_one.pop("review_validator_args", None)
    write(out, report)
    rerun = run_scaffold(out, freeze_path, refine_path)
    refreshed = json.loads(out.read_text(encoding="utf-8"))["closure"]["iterations"][0]
    if rerun.returncode != 0 or refreshed["review_validator_args"] != ["--bundle", str(review_dir / "bundle.json")]:
        raise AssertionError(f"scaffold did not read validator-args.json: {rerun.stdout}{rerun.stderr}")
    if refreshed["review_receipt"] != REVIEW_RECEIPT:
        raise AssertionError("scaffold did not re-derive the fresh review receipt")
    assert_valid(out)


def scaffold_history(root: Path, freeze_path: Path, refine_path: Path, first_review: str) -> None:
    """A post-fix refresh appends an iteration; the superseded one keeps its head."""
    out = root / "rt-history.json"
    first = {
        "review_reused_from": first_review,
        "open_findings": ["missing null guard test"],
        "correction_receipts": ["fixed missing null guard test via regression"],
        "evidence": ["closure iteration 1 cites the pre-fix sam-work review"],
    }
    write(out, {"closure": {"iterations": [first]}})
    if run_scaffold(out, freeze_path, refine_path).returncode != 0:
        raise AssertionError("scaffold failed on the first closure iteration")
    report = json.loads(out.read_text(encoding="utf-8"))
    report["closure"]["iterations"].append(
        {
            "review_reused_from": WORK_REVIEW_PATH,
            "council_report_path": COUNCIL_PATH,
            "open_findings": [],
            "correction_receipts": [],
            "evidence": ["closure iteration 2 cites the refreshed review"],
        }
    )
    write(out, report)
    result = run_scaffold(out, freeze_path, refine_path)
    iterations = json.loads(out.read_text(encoding="utf-8"))["closure"]["iterations"]
    heads = [(item["head_sha"], item["review_status"]) for item in iterations]
    if result.returncode != 0 or heads != [(OLD_HEAD, "CHANGES_REQUIRED"), (HEAD, "APPROVE")]:
        raise AssertionError(f"closure history was rewritten: {heads} {result.stderr}")
    # Overwriting a superseded iteration's review in place is refused loudly.
    write(Path(first_review), review_report())
    refused = run_scaffold(out, freeze_path, refine_path)
    if refused.returncode == 0 or "changed after it was recorded" not in refused.stderr + refused.stdout:
        raise AssertionError("scaffold accepted an overwritten superseded review")
    write(Path(first_review), review_report(head=OLD_HEAD, result="CHANGES_REQUIRED"))


def scaffold_rejected_plan(root: Path, freeze_path: Path, refine_path: Path) -> None:
    """A freeze sam-plan rejects cannot reach COMPLETE, although the scaffold records
    the validator's last line (here a failure line) as the plan receipt."""
    plan_stub = VALIDATOR.parents[2] / "sam-plan" / "scripts" / "validate_plan_report.py"
    original = plan_stub.read_text(encoding="utf-8")
    # Real sam-plan semantics: INVALID plus error lines on stdout, exit 1.
    plan_stub.write_text('print("INVALID\\n- frozen.thesis is required")\nraise SystemExit(1)\n', encoding="utf-8")
    try:
        out = root / "rt-plan-rejected.json"
        write(
            out,
            {
                "closure": {
                    "iterations": [
                        {
                            "review_reused_from": WORK_REVIEW_PATH,
                            "council_report_path": COUNCIL_PATH,
                            "open_findings": [],
                            "correction_receipts": [],
                            "evidence": ["closure iteration 1 cites the sam-work review"],
                        }
                    ]
                },
                "learning": {"status": "LEARNING_AUDITED", "candidates": [], "evidence": ["none"]},
            },
        )
        result = run_scaffold(
            out, freeze_path, refine_path,
            "--workflow-id", "task-plan-rejected",
            "--web-surface", "true",
            "--web-surface-evidence", "dev server script and routed pages",
        )
        report = json.loads(out.read_text(encoding="utf-8"))
        if result.returncode != 0 or report["plan"]["validator_receipt"] != "- frozen.thesis is required":
            raise AssertionError(f"scaffold did not record the plan validator line: {result.stdout}{result.stderr}")
        report["status"] = "COMPLETE"
        write(out, report)
        assert_invalid(out, "plan freeze failed the sam-plan validator: - frozen.thesis is required")
    finally:
        plan_stub.write_text(original, encoding="utf-8")


def main() -> int:
    global WORK_PATH, WORK_REVIEW_PATH, COUNCIL_PATH
    with tempfile.TemporaryDirectory(prefix="sam-task-harness-") as raw:
        root = Path(raw)
        build_tree(root)
        WORK_PATH = str(root / "work-report.json")
        WORK_REVIEW_PATH = str(root / "work-review.json")
        COUNCIL_PATH = str(root / "council.json")
        write(Path(WORK_PATH), work_report())
        write(Path(WORK_REVIEW_PATH), review_report())
        write(Path(COUNCIL_PATH), {"status": "TRIAGE_PASS", "profile": "fast", "packet_head": HEAD})
        # The superseded sam-work review of the pre-fix head keeps its own file.
        first_review = str(root / "work-review-1.json")
        write(Path(first_review), review_report(head=OLD_HEAD, result="CHANGES_REQUIRED"))

        plan_dir = root / "plan"
        plan_dir.mkdir()
        freeze_path = plan_dir / "plan-report.json"
        refine_dir = root / "run" / "refine"
        refine_dir.mkdir(parents=True)
        refine_path = refine_dir / "report.json"
        refine_args = ["--baseline", str(refine_dir / "baseline.json"), "--current", str(refine_dir / "current.json")]
        (refine_dir / "validator-args.json").write_text(json.dumps(refine_args), encoding="utf-8")
        good_freeze = {
            "schema_version": 1,
            "workflow": "plan",
            "status": "READY_TO_EXECUTE",
            "depth": "simple",
            "frozen": {
                "prompt_hash": PROMPT,
                "goal": "Deliver the invoicing fix end to end",
            },
        }
        good_refine = {
            "schema_version": 1,
            "workflow": "refinement",
            "decision": {"result": "HIGH_CONFIDENCE", "remaining": []},
        }
        write(freeze_path, good_freeze)
        write(refine_path, good_refine)

        def with_child_paths(report: dict[str, Any]) -> dict[str, Any]:
            """Cite the real child files and pin their sha256 like the scaffold does."""
            report = deepcopy(report)
            report["plan"]["plan_dir"] = str(plan_dir)
            report["plan"]["freeze_path"] = str(freeze_path)
            report["refine_report_path"] = str(refine_path)
            work_file = Path(str(report.get("work_report_path", "")))
            pins = {0: freeze_path, 1: refine_path, 2: work_file}
            for index, path in pins.items():
                if path.is_file():
                    report["phases"][index]["iterations"][-1]["output_fingerprint"] = sha256(path)
            report["phases"][2]["validator_receipts"] = [WORK_RECEIPT]
            report["phases"][1]["validator_receipts"] = [REFINE_RECEIPT]
            report["phases"][0]["validator_receipts"] = [PLAN_RECEIPT]
            report["plan"]["validator_receipt"] = PLAN_RECEIPT
            report["refine_validator_args"] = list(refine_args)
            return report

        good = root / "good.json"
        write(good, with_child_paths(valid_report()))
        assert_valid(good)

        # The council validator runs from the target repo: a DELTA council's
        # ancestry check asks git there and passes silently anywhere else.
        target_repo = root / "target-repo"
        target_repo.mkdir()
        cwd_work = work_report()
        cwd_work["target"]["repo_root"] = str(target_repo)
        write(root / "work-cwd.json", cwd_work)
        cwd_council = {"status": "TRIAGE_PASS", "profile": "fast", "packet_head": HEAD, "expect_cwd": str(target_repo)}
        write(root / "council-cwd.json", cwd_council)
        cwd_case = valid_report()
        cwd_case["target"]["repo_root"] = str(target_repo)
        cwd_case["work_report_path"] = str(root / "work-cwd.json")
        cwd_case["closure"]["iterations"][0]["council_report_path"] = str(root / "council-cwd.json")
        write(root / "council-cwd-task.json", with_child_paths(cwd_case))
        assert_valid(root / "council-cwd-task.json")

        # multi-iteration closure that ends clean; council waits for review APPROVE
        multi = valid_report()
        multi["closure"] = {
            "max_iterations": 5,
            "iterations_used": 2,
            "final_status": "CLEAN",
            "iterations": [
                closure_iteration(
                    1,
                    review_status="CHANGES_REQUIRED",
                    council=False,
                    open_findings=["missing null guard test"],
                    corrections=["fixed missing null guard test via regression"],
                    head=OLD_HEAD,
                    evidence="review found gap",
                    review_path=first_review,
                ),
                closure_iteration(2, evidence="re-review clean"),
            ],
        }
        multi_path = root / "multi.json"
        write(multi_path, with_child_paths(multi))
        assert_valid(multi_path)

        # A superseded iteration whose cited review was overwritten in place (the
        # post-fix refresh reused the path) no longer describes that iteration.
        rewritten = deepcopy(multi)
        rewritten["closure"]["iterations"][0]["review_reused_from"] = WORK_REVIEW_PATH
        rewritten_path = root / "closure-rewritten.json"
        write(rewritten_path, with_child_paths(rewritten))
        assert_invalid(rewritten_path, "closure iteration 1 cited review changed after it was recorded")
        retyped = deepcopy(multi)
        retyped["closure"]["iterations"][0]["review_status"] = "COMMENT_ONLY"
        retyped_path = root / "closure-status-drift.json"
        write(retyped_path, with_child_paths(retyped))
        assert_invalid(retyped_path, "closure iteration 1 cited review changed after it was recorded")
        pinned = deepcopy(multi)
        pinned["closure"]["iterations"][0]["review_report_sha256"] = "0" * 64
        pinned_path = root / "closure-pin-drift.json"
        write(pinned_path, with_child_paths(pinned))
        assert_invalid(pinned_path, "closure iteration 1 cited review changed after it was recorded")

        # COMPLETE but review not approve
        bad_review = valid_report()
        bad_review["closure"]["iterations"][0]["review_status"] = "CHANGES_REQUIRED"
        bad_review["closure"]["iterations"][0]["open_findings"] = ["x"]
        bad_path = root / "bad-review.json"
        write(bad_path, with_child_paths(bad_review))
        assert_invalid(bad_path, "APPROVE")

        # COMPLETE with open blockers
        blockers = valid_report()
        blockers["blockers"] = ["still broken"]
        blockers_path = root / "blockers.json"
        write(blockers_path, with_child_paths(blockers))
        assert_invalid(blockers_path, "forbids non-empty blockers")

        # stale work head
        stale = valid_report()
        stale["phases"][2]["validated_head_sha"] = "1" * 40
        stale_path = root / "stale.json"
        write(stale_path, with_child_paths(stale))
        assert_invalid(stale_path, "stale for the final head")

        # missing phase
        missing = valid_report()
        missing["phases"] = missing["phases"][:4]
        missing_path = root / "missing.json"
        write(missing_path, with_child_paths(missing))
        assert_invalid(missing_path, "exactly plan, refine, work, closure, learn")

        # council fail on final
        council_fail = valid_report()
        council_fail["closure"]["iterations"][0]["council_status"] = "REVISE"
        council_fail_path = root / "council-fail.json"
        write(council_fail_path, with_child_paths(council_fail))
        assert_invalid(council_fail_path, "accepted pass status")

        # valid BLOCKED
        blocked = valid_report()
        blocked["status"] = "BLOCKED"
        blocked["blockers"] = ["closure exhausted at 5 iterations"]
        blocked["closure"]["final_status"] = "OPEN"
        blocked["closure"]["iterations"][0] = closure_iteration(
            1,
            review_status="CHANGES_REQUIRED",
            council=False,
            open_findings=["unresolved finding"],
            evidence="still open",
        )
        blocked["phases"][3]["status"] = "OPEN"
        blocked["phases"][3]["iterations"] = [iteration("OPEN", open_items=["unresolved finding"])]
        # last iteration OPEN with open items is ok for non-COMPLETE
        blocked["phases"][3]["iterations"][0]["open_required_items"] = ["unresolved finding"]
        blocked_path = root / "blocked.json"
        write(blocked_path, with_child_paths(blocked))
        assert_valid(blocked_path)

        # empty BLOCKED invalid
        empty_blocked = deepcopy(blocked)
        empty_blocked["blockers"] = []
        empty_blocked["residuals"] = []
        empty_path = root / "empty-blocked.json"
        write(empty_path, with_child_paths(empty_blocked))
        assert_invalid(empty_path, "requires residuals or blockers")

        # exceeded max iterations
        over = valid_report()
        over["closure"]["max_iterations"] = 1
        over["closure"]["iterations_used"] = 2
        over["closure"]["iterations"] = multi["closure"]["iterations"]
        over_path = root / "over.json"
        write(over_path, with_child_paths(over))
        assert_invalid(over_path, "exceeded max_iterations")

        # evidence-backed learning proposal is valid but performs no write
        learned = valid_report()
        learned["learning"]["candidates"] = [
            {
                "id": "L-001",
                "observation": "Two current-head retries failed for the same stale receipt.",
                "proposed_rule": "Recompute the receipt after every head change.",
                "scope": ["sam-task freshness checks"],
                "evidence": ["closure iterations 1 and 2"],
                "destination": "SKILL",
                "revalidate_when": "the report freshness contract changes",
                "sensitivity": "INTERNAL",
                "status": "PROPOSED",
                "decision_reason": "The pattern repeated with current-run evidence.",
            }
        ]
        learned_path = root / "learned.json"
        write(learned_path, with_child_paths(learned))
        assert_valid(learned_path)

        # learning candidates cannot mutate durable context automatically
        auto_write = deepcopy(learned)
        auto_write["learning"]["writes_performed"] = ["updated AGENTS.md"]
        auto_write_path = root / "auto-write.json"
        write(auto_write_path, with_child_paths(auto_write))
        assert_invalid(auto_write_path, "writes_performed must be empty")

        # candidate evidence and revalidation conditions are mandatory
        weak_learning = deepcopy(learned)
        weak_learning["learning"]["candidates"][0]["evidence"] = []
        weak_learning["learning"]["candidates"][0]["revalidate_when"] = ""
        weak_learning_path = root / "weak-learning.json"
        write(weak_learning_path, with_child_paths(weak_learning))
        assert_invalid(weak_learning_path, "evidence requires at least one receipt")
        assert_invalid(weak_learning_path, "revalidate_when is required")

        # a COMPLETE workflow cannot skip its learning audit
        skipped_learning = valid_report()
        skipped_learning["learning"]["status"] = "BLOCKED"
        skipped_learning["phases"][4]["status"] = "BLOCKED"
        skipped_learning["phases"][4]["iterations"] = [iteration("BLOCKED")]
        skipped_learning_path = root / "skipped-learning.json"
        write(skipped_learning_path, with_child_paths(skipped_learning))
        assert_invalid(skipped_learning_path, "LEARNING_AUDITED")

        # a web system cannot complete without an uploaded Playwright video
        no_video = valid_report()
        no_video_work = root / "work-no-video.json"
        write(no_video_work, work_report(playwright_discovered=0, playwright_uploaded=0))
        no_video["work_report_path"] = str(no_video_work)
        no_video_path = root / "no-video.json"
        write(no_video_path, with_child_paths(no_video))
        assert_invalid(no_video_path, "at least one uploaded Playwright video")

        # every discovered browser video must be uploaded
        partial_video = valid_report()
        partial_work = root / "work-partial-video.json"
        write(partial_work, work_report(playwright_discovered=2, playwright_uploaded=1))
        partial_video["work_report_path"] = str(partial_work)
        partial_path = root / "partial-video.json"
        write(partial_path, with_child_paths(partial_video))
        assert_invalid(partial_path, "every discovered Playwright video must be uploaded")

        # the demo video is required on every run
        no_demo = valid_report()
        no_demo_work = root / "work-no-demo.json"
        write(no_demo_work, work_report(demo_uploaded=0))
        no_demo["work_report_path"] = str(no_demo_work)
        no_demo_path = root / "no-demo.json"
        write(no_demo_path, with_child_paths(no_demo))
        assert_invalid(no_demo_path, "at least one uploaded demo video")

        # the child cannot silently downgrade a web system to skip Playwright
        downgrade = valid_report()
        downgrade_work = root / "work-downgraded.json"
        write(
            downgrade_work,
            work_report(web_system=False, playwright_discovered=0, playwright_uploaded=0),
        )
        downgrade["work_report_path"] = str(downgrade_work)
        downgrade_path = root / "downgrade.json"
        write(downgrade_path, with_child_paths(downgrade))
        assert_invalid(downgrade_path, "must match work report request.web_system")

        # a proven non-web workflow completes with zero Playwright videos
        non_web = valid_report()
        non_web["target"]["web_surface"] = False
        non_web["target"]["web_surface_evidence"] = ["CLI entrypoint only, no HTTP server"]
        non_web_work = root / "work-non-web.json"
        write(
            non_web_work,
            work_report(web_system=False, playwright_discovered=0, playwright_uploaded=0),
        )
        non_web["work_report_path"] = str(non_web_work)
        non_web_path = root / "non-web.json"
        write(non_web_path, with_child_paths(non_web))
        assert_valid(non_web_path)

        # COMPLETE cannot cite a work report that does not exist
        absent = valid_report()
        absent["work_report_path"] = str(root / "missing-work-report.json")
        absent_path = root / "absent-work.json"
        write(absent_path, with_child_paths(absent))
        assert_invalid(absent_path, "readable work report")

        # the child terminal itself must be COMPLETE
        child_open = valid_report()
        child_open_work = root / "work-in-progress.json"
        write(child_open_work, work_report(result="IN_PROGRESS"))
        child_open["work_report_path"] = str(child_open_work)
        child_open_path = root / "child-open.json"
        write(child_open_path, with_child_paths(child_open))
        assert_invalid(child_open_path, "final.result COMPLETE")

        # web_surface must be decided, not omitted
        undecided = valid_report()
        del undecided["target"]["web_surface"]
        undecided_path = root / "undecided.json"
        write(undecided_path, with_child_paths(undecided))
        assert_invalid(undecided_path, "requires boolean target.web_surface")

        # a recorded advisor consult is evidence and does not break completion
        advised = valid_report()
        advised["advisor_consults"] = [advisor_consult()]
        advised_path = root / "advised.json"
        write(advised_path, with_child_paths(advised))
        assert_valid(advised_path)

        # advisors cannot be attached to the sam-work phase
        advised_work = valid_report()
        advised_work["advisor_consults"] = [advisor_consult(phase="work")]
        advised_work_path = root / "advised-work.json"
        write(advised_work_path, with_child_paths(advised_work))
        assert_invalid(advised_work_path, "owned by sam-work")

        # a consult must name an advisor skill, not an arbitrary child
        wrong_skill = valid_report()
        wrong_skill["advisor_consults"] = [{**advisor_consult(), "advisor": "sam-review"}]
        wrong_skill_path = root / "wrong-advisor-skill.json"
        write(wrong_skill_path, with_child_paths(wrong_skill))
        assert_invalid(wrong_skill_path, "must name a sam-<runtime>-advisor skill")

        # a failed consult needs a reason and must surface as a residual
        advisor_failed = valid_report()
        advisor_failed["advisor_consults"] = [advisor_consult(status="FAILED")]
        advisor_failed_path = root / "advisor-failed.json"
        write(advisor_failed_path, with_child_paths(advisor_failed))
        assert_invalid(advisor_failed_path, "FAILED requires a failure_reason")
        assert_invalid(advisor_failed_path, "must be recorded in residuals")

        # a failed consult is a residual, never a blocker, and still completes
        advisor_residual = valid_report()
        advisor_residual["advisor_consults"] = [
            advisor_consult(status="FAILED", failure_reason="advisor CLI unavailable")
        ]
        advisor_residual["residuals"] = ["advisor consult A-001 unavailable"]
        advisor_residual_path = root / "advisor-residual.json"
        write(advisor_residual_path, with_child_paths(advisor_residual))
        assert_valid(advisor_residual_path)

        # the per-run consult cap is enforced
        too_many = valid_report()
        too_many["advisor_consults"] = [
            {**advisor_consult(), "id": f"A-00{index}"} for index in range(1, 5)
        ]
        too_many_path = root / "too-many-advisors.json"
        write(too_many_path, with_child_paths(too_many))
        assert_invalid(too_many_path, "exceeds 3 per run")

        # P0: receipt VALID but freeze on disk is NOT_CONFIDENT
        disk_bad = with_child_paths(valid_report())
        write(
            freeze_path,
            {
                "schema_version": 1,
                "workflow": "plan",
                "status": "NOT_CONFIDENT",
                "frozen": {"prompt_hash": PROMPT, "goal": "x"},
            },
        )
        disk_bad_path = root / "disk-not-confident.json"
        write(disk_bad_path, disk_bad)
        assert_invalid(disk_bad_path, "READY_TO_EXECUTE")
        write(freeze_path, good_freeze)

        # P0: prompt hash mismatch
        hash_bad = with_child_paths(valid_report())
        write(
            freeze_path,
            {
                "schema_version": 1,
                "workflow": "plan",
                "status": "READY_TO_EXECUTE",
                "frozen": {"prompt_hash": "0" * 64, "goal": "x"},
            },
        )
        hash_path = root / "hash-mismatch.json"
        write(hash_path, hash_bad)
        assert_invalid(hash_path, "prompt_hash must match")
        write(freeze_path, good_freeze)

        # The plan receipt is a fresh sam-plan validator run on the freeze, not a typed line.
        plan_typed = with_child_paths(valid_report())
        plan_typed["plan"]["validator_receipt"] = "VALID"
        plan_typed["phases"][0]["validator_receipts"] = ["VALID"]
        plan_typed_path = root / "plan-typed.json"
        write(plan_typed_path, plan_typed)
        assert_invalid(plan_typed_path, "plan freeze receipt does not match a fresh sam-plan validator run")
        plan_split = with_child_paths(valid_report())
        plan_split["phases"][0]["validator_receipts"] = ["VALID:plan"]
        plan_split_path = root / "plan-receipt-split.json"
        write(plan_split_path, plan_split)
        assert_invalid(plan_split_path, "plan.validator_receipt must equal the plan phase's last validator receipt")

        # P0: missing refine_report_path
        no_refine = with_child_paths(valid_report())
        del no_refine["refine_report_path"]
        no_refine_path = root / "no-refine-path.json"
        write(no_refine_path, no_refine)
        assert_invalid(no_refine_path, "refine_report_path")

        # P0: refine not HIGH_CONFIDENCE
        write(
            refine_path,
            {
                "schema_version": 1,
                "workflow": "refinement",
                "decision": {"result": "NOT_CONFIDENT", "remaining": ["gap"]},
            },
        )
        refine_bad = with_child_paths(valid_report())
        refine_bad_path = root / "refine-not-confident.json"
        write(refine_bad_path, refine_bad)
        assert_invalid(refine_bad_path, "HIGH_CONFIDENCE")
        write(refine_path, good_refine)

        # P2: finding disappears without named correction
        orphan_finding = with_child_paths(valid_report())
        orphan_finding["closure"] = {
            "max_iterations": 5,
            "iterations_used": 2,
            "final_status": "CLEAN",
            "iterations": [
                closure_iteration(
                    1,
                    review_status="CHANGES_REQUIRED",
                    council=False,
                    open_findings=["missing auth check"],
                    corrections=["touched unrelated tests"],
                    evidence="review found gap",
                ),
                closure_iteration(2, evidence="re-review clean"),
            ],
        }
        orphan_path = root / "orphan-finding.json"
        write(orphan_path, orphan_finding)
        assert_invalid(orphan_path, "without named correction")

        # Closure ordering: council runs only after review APPROVE on that head.
        early_council = deepcopy(multi)
        early_council["closure"]["iterations"][0] = closure_iteration(
            1,
            review_status="CHANGES_REQUIRED",
            open_findings=["missing null guard test"],
            corrections=["fixed missing null guard test via regression"],
            head=OLD_HEAD,
            review_path=first_review,
        )
        early_council_path = root / "early-council.json"
        write(early_council_path, with_child_paths(early_council))
        assert_invalid(early_council_path, "ran council before review APPROVE")

        # Reuse: a fresh closure review is also accepted and re-validated.
        fresh_review_path = root / "closure-review.json"
        write(fresh_review_path, review_report())
        fresh = valid_report()
        fresh["closure"]["iterations"][0].update(
            review_reused_from=None,
            review_report_path=str(fresh_review_path),
            review_validator_args=["--bundle", str(root / "bundle.json")],
        )
        fresh_path = root / "fresh-review.json"
        write(fresh_path, with_child_paths(fresh))
        assert_valid(fresh_path)

        # The cited path is compared after resolving symlinks (/tmp vs /private/tmp).
        resolved = valid_report()
        resolved["closure"]["iterations"][0]["review_reused_from"] = str(Path(WORK_REVIEW_PATH).resolve())
        resolved_path = root / "reuse-resolved.json"
        write(resolved_path, with_child_paths(resolved))
        assert_valid(resolved_path)

        # Reuse must cite the sam-work review itself, not any review file.
        wrong_source = deepcopy(fresh)
        wrong_source["closure"]["iterations"][0].update(
            review_report_path=None, review_reused_from=str(fresh_review_path)
        )
        wrong_source_path = root / "reuse-wrong-source.json"
        write(wrong_source_path, with_child_paths(wrong_source))
        assert_invalid(wrong_source_path, "must cite the sam-work review report")

        # Reuse needs the identical key: a sam-work review of an older head fails.
        old_review_path = root / "work-review-old.json"
        write(old_review_path, review_report(head=OLD_HEAD))
        old_work = root / "work-old-review.json"
        old_work_body = work_report()
        old_work_body["phases"][0]["report_path"] = str(old_review_path)
        write(old_work, old_work_body)
        key_drift = valid_report()
        key_drift["work_report_path"] = str(old_work)
        key_drift["closure"]["iterations"][0]["review_reused_from"] = str(old_review_path)
        key_drift_path = root / "reuse-key-drift.json"
        write(key_drift_path, with_child_paths(key_drift))
        assert_invalid(key_drift_path, "reused review key")

        # Reuse also needs branch mode: a local-mode sam-work review is another key.
        local_work_review = root / "work-review-local.json"
        local_body = review_report()
        local_body["target"]["mode"] = "local"
        write(local_work_review, local_body)
        local_work = root / "work-local-review.json"
        local_work_body = work_report()
        local_work_body["phases"][0]["report_path"] = str(local_work_review)
        write(local_work, local_work_body)
        mode_drift = valid_report()
        mode_drift["work_report_path"] = str(local_work)
        mode_drift["closure"]["iterations"][0]["review_reused_from"] = str(local_work_review)
        mode_drift_path = root / "reuse-mode-drift.json"
        write(mode_drift_path, with_child_paths(mode_drift))
        assert_invalid(mode_drift_path, "reused review key (branch mode, head, base)")

        # A council report packaged for another head cannot close this head.
        old_council = root / "council-old-head.json"
        write(old_council, {"status": "TRIAGE_PASS", "profile": "fast", "packet_head": OLD_HEAD})
        council_head = valid_report()
        council_head["closure"]["iterations"][0]["council_report_path"] = str(old_council)
        council_head_path = root / "council-head-drift.json"
        write(council_head_path, with_child_paths(council_head))
        assert_invalid(council_head_path, "council packet_head must equal head_sha")
        # A council packet with no commit head is bound to no head, so it cannot close one.
        unbound_council = root / "council-no-head.json"
        write(unbound_council, {"status": "TRIAGE_PASS", "profile": "fast", "packet_head": "none"})
        council_unbound = valid_report()
        council_unbound["closure"]["iterations"][0]["council_report_path"] = str(unbound_council)
        council_unbound_path = root / "council-unbound.json"
        write(council_unbound_path, with_child_paths(council_unbound))
        assert_invalid(council_unbound_path, "council packet_head must equal head_sha")

        # Exactly one review source per closure iteration.
        both = valid_report()
        both["closure"]["iterations"][0]["review_report_path"] = str(fresh_review_path)
        both_path = root / "both-review-sources.json"
        write(both_path, with_child_paths(both))
        assert_invalid(both_path, "exactly one")

        # A fresh closure review from another head is stale.
        stale_review_path = root / "closure-review-stale.json"
        write(stale_review_path, review_report(head=OLD_HEAD))
        stale_review = deepcopy(fresh)
        stale_review["closure"]["iterations"][0]["review_report_path"] = str(stale_review_path)
        stale_review_task = root / "stale-closure-review.json"
        write(stale_review_task, with_child_paths(stale_review))
        assert_invalid(stale_review_task, "review report head does not match")

        # The cited work report must itself pass the sam-work validator.
        rejected_work = root / "work-rejected.json"
        write(rejected_work, work_report(stub_invalid=True))
        rejected = valid_report()
        rejected["work_report_path"] = str(rejected_work)
        rejected_path = root / "work-rejected-task.json"
        write(rejected_path, with_child_paths(rejected))
        assert_invalid(rejected_path, "failed the sam-work validator")

        # A typed work receipt is not a fresh validator run.
        typed_receipt = with_child_paths(valid_report())
        typed_receipt["phases"][2]["validator_receipts"] = ["PASS: trust me"]
        typed_receipt_path = root / "typed-work-receipt.json"
        write(typed_receipt_path, typed_receipt)
        assert_invalid(typed_receipt_path, "does not match a fresh sam-work validator run")

        # The work report must be for the same final head as the task.
        head_drift_work = root / "work-head-drift.json"
        write(head_drift_work, work_report(head=OLD_HEAD))
        head_drift = valid_report()
        head_drift["work_report_path"] = str(head_drift_work)
        head_drift_path = root / "work-head-drift-task.json"
        write(head_drift_path, with_child_paths(head_drift))
        assert_invalid(head_drift_path, "work report target.final_head_sha must equal")

        # A work report rewritten after the task report cited it is caught.
        pinned = with_child_paths(valid_report())
        pinned["phases"][2]["iterations"][-1]["output_fingerprint"] = "0" * 64
        pinned_path = root / "work-fingerprint-drift.json"
        write(pinned_path, pinned)
        assert_invalid(pinned_path, "output_fingerprint must equal sha256")

        # The council report must pass its validator with the recorded receipt.
        council_typed = with_child_paths(valid_report())
        council_typed["closure"]["iterations"][0]["council_receipt"] = "VALID: typed"
        council_typed_path = root / "council-typed.json"
        write(council_typed_path, council_typed)
        assert_invalid(council_typed_path, "does not match a fresh sam-council validator run")

        # The task and work ledgers must be for the same frozen prompt.
        prompt_drift_work = root / "work-prompt-drift.json"
        prompt_drift_body = work_report()
        prompt_drift_body["request"]["prompt_sha256"] = "0" * 64
        write(prompt_drift_work, prompt_drift_body)
        prompt_drift = valid_report()
        prompt_drift["work_report_path"] = str(prompt_drift_work)
        prompt_drift_path = root / "work-prompt-drift-task.json"
        write(prompt_drift_path, with_child_paths(prompt_drift))
        assert_invalid(prompt_drift_path, "work report request.prompt_sha256 must equal")

        # A fresh closure review must use the frozen base in branch mode.
        local_review_path = root / "closure-review-local.json"
        local_body = review_report()
        local_body["target"]["mode"] = "local"
        write(local_review_path, local_body)
        local_review = deepcopy(fresh)
        local_review["closure"]["iterations"][0]["review_report_path"] = str(local_review_path)
        local_review_task = root / "local-closure-review.json"
        write(local_review_task, with_child_paths(local_review))
        assert_invalid(local_review_task, "fresh review must be branch mode against target.base_sha")

        # Review validator arguments cannot make the child rewrite its report.
        rewrite_args = deepcopy(fresh)
        rewrite_args["closure"]["iterations"][0]["review_validator_args"] = ["--scaffold", "--bundle", "rel.json"]
        rewrite_args_path = root / "review-args-rewrite.json"
        write(rewrite_args_path, with_child_paths(rewrite_args))
        assert_invalid(rewrite_args_path, "review_validator_args must be")

        # The refine receipt is a fresh validator run, not a typed line.
        refine_typed = with_child_paths(valid_report())
        refine_typed["phases"][1]["validator_receipts"] = ["PASS: typed"]
        refine_typed_path = root / "refine-typed.json"
        write(refine_typed_path, refine_typed)
        assert_invalid(refine_typed_path, "does not match a fresh sam-refine-task validator run")

        refine_relative = with_child_paths(valid_report())
        refine_relative["refine_validator_args"] = ["--baseline=baseline.json", "--current", "/abs/current.json"]
        refine_relative_path = root / "refine-relative-args.json"
        write(refine_relative_path, refine_relative)
        assert_invalid(refine_relative_path, "refine_validator_args must be")

        # Non-UTF-8 child validator output is an INVALID line, never a traceback.
        bytes_work = root / "work-bytes.json"
        write(bytes_work, {**work_report(), "stub_bytes": True})
        bytes_task = valid_report()
        bytes_task["work_report_path"] = str(bytes_work)
        bytes_path = root / "work-bytes-task.json"
        write(bytes_path, with_child_paths(bytes_task))
        assert_invalid(bytes_path, "failed the sam-work validator: FAIL: non-UTF-8 caf")

        # Scaffold placeholders are fail-closed.
        unfilled = with_child_paths(valid_report())
        unfilled["learning"]["evidence"] = ["SCAFFOLD: learning audit receipt"]
        unfilled_path = root / "unfilled.json"
        write(unfilled_path, unfilled)
        assert_invalid(unfilled_path, "unfilled scaffold placeholder")

        scaffold_round_trip(root, freeze_path, refine_path)
        scaffold_history(root, freeze_path, refine_path, first_review)
        scaffold_rejected_plan(root, freeze_path, refine_path)

        print("sam-task harness passed")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
