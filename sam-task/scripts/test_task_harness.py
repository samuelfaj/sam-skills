#!/usr/bin/env python3
"""Adversarial checks for the sam-task report validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_task_report.py"
HEAD = "a" * 40
BASE = "b" * 40
FP = "c" * 64
PROMPT = "d" * 64
IN_FP = "e" * 64
OUT_FP = "f" * 64
WORK_PATH = "/tmp/repository/work-report.json"


def work_report(
    *,
    web_system: bool = True,
    playwright_discovered: int = 2,
    playwright_uploaded: int = 2,
    demo_uploaded: int = 1,
    result: str = "COMPLETE",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "workflow_id": "work-001",
        "request": {
            "prompt_sha256": PROMPT,
            "classification": "BUG",
            "web_system": web_system,
        },
        "video_inventory": {
            "playwright_discovered": playwright_discovered,
            "playwright_uploaded": playwright_uploaded,
            "demo_discovered": demo_uploaded,
            "demo_uploaded": demo_uploaded,
        },
        "final": {"result": result},
    }


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
        "schema_version": 2,
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
        },
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
            "iterations": [
                {
                    "sequence": 1,
                    "head_sha": HEAD,
                    "review_status": "APPROVE",
                    "council_profile": "fast",
                    "council_status": "TRIAGE_PASS",
                    "open_findings": [],
                    "correction_receipts": [],
                    "review_receipt": "VALID",
                    "council_receipt": "VALID",
                    "evidence": ["clean review and council pair"],
                }
            ],
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


def main() -> int:
    global WORK_PATH
    with tempfile.TemporaryDirectory(prefix="sam-task-harness-") as raw:
        root = Path(raw)
        WORK_PATH = str(root / "work-report.json")
        write(Path(WORK_PATH), work_report())

        good = root / "good.json"
        write(good, valid_report())
        assert_valid(good)

        # multi-iteration closure that ends clean
        multi = valid_report()
        multi["closure"] = {
            "max_iterations": 5,
            "iterations_used": 2,
            "final_status": "CLEAN",
            "iterations": [
                {
                    "sequence": 1,
                    "head_sha": HEAD,
                    "review_status": "CHANGES_REQUIRED",
                    "council_profile": "fast",
                    "council_status": "TRIAGE_PASS",
                    "open_findings": ["missing null guard test"],
                    "correction_receipts": ["added regression test"],
                    "review_receipt": "VALID",
                    "council_receipt": "VALID",
                    "evidence": ["review found gap"],
                },
                {
                    "sequence": 2,
                    "head_sha": HEAD,
                    "review_status": "APPROVE",
                    "council_profile": "fast",
                    "council_status": "TRIAGE_PASS",
                    "open_findings": [],
                    "correction_receipts": [],
                    "review_receipt": "VALID",
                    "council_receipt": "VALID",
                    "evidence": ["re-review clean"],
                },
            ],
        }
        multi_path = root / "multi.json"
        write(multi_path, multi)
        assert_valid(multi_path)

        # COMPLETE but review not approve
        bad_review = valid_report()
        bad_review["closure"]["iterations"][0]["review_status"] = "CHANGES_REQUIRED"
        bad_review["closure"]["iterations"][0]["open_findings"] = ["x"]
        bad_path = root / "bad-review.json"
        write(bad_path, bad_review)
        assert_invalid(bad_path, "APPROVE")

        # COMPLETE with open blockers
        blockers = valid_report()
        blockers["blockers"] = ["still broken"]
        blockers_path = root / "blockers.json"
        write(blockers_path, blockers)
        assert_invalid(blockers_path, "forbids non-empty blockers")

        # stale work head
        stale = valid_report()
        stale["phases"][2]["validated_head_sha"] = "1" * 40
        stale_path = root / "stale.json"
        write(stale_path, stale)
        assert_invalid(stale_path, "stale for the final head")

        # missing phase
        missing = valid_report()
        missing["phases"] = missing["phases"][:4]
        missing_path = root / "missing.json"
        write(missing_path, missing)
        assert_invalid(missing_path, "exactly plan, refine, work, closure, learn")

        # council fail on final
        council_fail = valid_report()
        council_fail["closure"]["iterations"][0]["council_status"] = "REVISE"
        council_fail_path = root / "council-fail.json"
        write(council_fail_path, council_fail)
        assert_invalid(council_fail_path, "accepted pass status")

        # valid BLOCKED
        blocked = valid_report()
        blocked["status"] = "BLOCKED"
        blocked["blockers"] = ["closure exhausted at 5 iterations"]
        blocked["closure"]["final_status"] = "OPEN"
        blocked["closure"]["iterations"][0] = {
            "sequence": 1,
            "head_sha": HEAD,
            "review_status": "CHANGES_REQUIRED",
            "council_profile": "fast",
            "council_status": "TRIAGE_PASS",
            "open_findings": ["unresolved finding"],
            "correction_receipts": [],
            "review_receipt": "VALID",
            "council_receipt": "VALID",
            "evidence": ["still open"],
        }
        blocked["phases"][3]["status"] = "OPEN"
        blocked["phases"][3]["iterations"] = [iteration("OPEN", open_items=["unresolved finding"])]
        # last iteration OPEN with open items is ok for non-COMPLETE
        blocked["phases"][3]["iterations"][0]["open_required_items"] = ["unresolved finding"]
        blocked_path = root / "blocked.json"
        write(blocked_path, blocked)
        assert_valid(blocked_path)

        # empty BLOCKED invalid
        empty_blocked = deepcopy(blocked)
        empty_blocked["blockers"] = []
        empty_blocked["residuals"] = []
        empty_path = root / "empty-blocked.json"
        write(empty_path, empty_blocked)
        assert_invalid(empty_path, "requires residuals or blockers")

        # exceeded max iterations
        over = valid_report()
        over["closure"]["max_iterations"] = 1
        over["closure"]["iterations_used"] = 2
        over["closure"]["iterations"] = multi["closure"]["iterations"]
        over_path = root / "over.json"
        write(over_path, over)
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
        write(learned_path, learned)
        assert_valid(learned_path)

        # learning candidates cannot mutate durable context automatically
        auto_write = deepcopy(learned)
        auto_write["learning"]["writes_performed"] = ["updated AGENTS.md"]
        auto_write_path = root / "auto-write.json"
        write(auto_write_path, auto_write)
        assert_invalid(auto_write_path, "writes_performed must be empty")

        # candidate evidence and revalidation conditions are mandatory
        weak_learning = deepcopy(learned)
        weak_learning["learning"]["candidates"][0]["evidence"] = []
        weak_learning["learning"]["candidates"][0]["revalidate_when"] = ""
        weak_learning_path = root / "weak-learning.json"
        write(weak_learning_path, weak_learning)
        assert_invalid(weak_learning_path, "evidence requires at least one receipt")
        assert_invalid(weak_learning_path, "revalidate_when is required")

        # a COMPLETE workflow cannot skip its learning audit
        skipped_learning = valid_report()
        skipped_learning["learning"]["status"] = "BLOCKED"
        skipped_learning["phases"][4]["status"] = "BLOCKED"
        skipped_learning["phases"][4]["iterations"] = [iteration("BLOCKED")]
        skipped_learning_path = root / "skipped-learning.json"
        write(skipped_learning_path, skipped_learning)
        assert_invalid(skipped_learning_path, "LEARNING_AUDITED")

        # a web system cannot complete without an uploaded Playwright video
        no_video = valid_report()
        no_video_work = root / "work-no-video.json"
        write(no_video_work, work_report(playwright_discovered=0, playwright_uploaded=0))
        no_video["work_report_path"] = str(no_video_work)
        no_video_path = root / "no-video.json"
        write(no_video_path, no_video)
        assert_invalid(no_video_path, "at least one uploaded Playwright video")

        # every discovered browser video must be uploaded
        partial_video = valid_report()
        partial_work = root / "work-partial-video.json"
        write(partial_work, work_report(playwright_discovered=2, playwright_uploaded=1))
        partial_video["work_report_path"] = str(partial_work)
        partial_path = root / "partial-video.json"
        write(partial_path, partial_video)
        assert_invalid(partial_path, "every discovered Playwright video must be uploaded")

        # the demo video is required on every run
        no_demo = valid_report()
        no_demo_work = root / "work-no-demo.json"
        write(no_demo_work, work_report(demo_uploaded=0))
        no_demo["work_report_path"] = str(no_demo_work)
        no_demo_path = root / "no-demo.json"
        write(no_demo_path, no_demo)
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
        write(downgrade_path, downgrade)
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
        write(non_web_path, non_web)
        assert_valid(non_web_path)

        # COMPLETE cannot cite a work report that does not exist
        absent = valid_report()
        absent["work_report_path"] = str(root / "missing-work-report.json")
        absent_path = root / "absent-work.json"
        write(absent_path, absent)
        assert_invalid(absent_path, "readable work report")

        # the child terminal itself must be COMPLETE
        child_open = valid_report()
        child_open_work = root / "work-in-progress.json"
        write(child_open_work, work_report(result="IN_PROGRESS"))
        child_open["work_report_path"] = str(child_open_work)
        child_open_path = root / "child-open.json"
        write(child_open_path, child_open)
        assert_invalid(child_open_path, "final.result COMPLETE")

        # web_surface must be decided, not omitted
        undecided = valid_report()
        del undecided["target"]["web_surface"]
        undecided_path = root / "undecided.json"
        write(undecided_path, undecided)
        assert_invalid(undecided_path, "requires boolean target.web_surface")

        # a recorded advisor consult is evidence and does not break completion
        advised = valid_report()
        advised["advisor_consults"] = [advisor_consult()]
        advised_path = root / "advised.json"
        write(advised_path, advised)
        assert_valid(advised_path)

        # advisors cannot be attached to the sam-work phase
        advised_work = valid_report()
        advised_work["advisor_consults"] = [advisor_consult(phase="work")]
        advised_work_path = root / "advised-work.json"
        write(advised_work_path, advised_work)
        assert_invalid(advised_work_path, "owned by sam-work")

        # a consult must name an advisor skill, not an arbitrary child
        wrong_skill = valid_report()
        wrong_skill["advisor_consults"] = [{**advisor_consult(), "advisor": "sam-review"}]
        wrong_skill_path = root / "wrong-advisor-skill.json"
        write(wrong_skill_path, wrong_skill)
        assert_invalid(wrong_skill_path, "must name a sam-<runtime>-advisor skill")

        # a failed consult needs a reason and must surface as a residual
        advisor_failed = valid_report()
        advisor_failed["advisor_consults"] = [advisor_consult(status="FAILED")]
        advisor_failed_path = root / "advisor-failed.json"
        write(advisor_failed_path, advisor_failed)
        assert_invalid(advisor_failed_path, "FAILED requires a failure_reason")
        assert_invalid(advisor_failed_path, "must be recorded in residuals")

        # a failed consult is a residual, never a blocker, and still completes
        advisor_residual = valid_report()
        advisor_residual["advisor_consults"] = [
            advisor_consult(status="FAILED", failure_reason="advisor CLI unavailable")
        ]
        advisor_residual["residuals"] = ["advisor consult A-001 unavailable"]
        advisor_residual_path = root / "advisor-residual.json"
        write(advisor_residual_path, advisor_residual)
        assert_valid(advisor_residual_path)

        # the per-run consult cap is enforced
        too_many = valid_report()
        too_many["advisor_consults"] = [
            {**advisor_consult(), "id": f"A-00{index}"} for index in range(1, 5)
        ]
        too_many_path = root / "too-many-advisors.json"
        write(too_many_path, too_many)
        assert_invalid(too_many_path, "exceeds 3 per run")

        print("sam-task harness passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
