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
        "schema_version": 1,
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
        "work_report_path": "/tmp/repository/work-report.json",
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
    with tempfile.TemporaryDirectory(prefix="sam-task-harness-") as raw:
        root = Path(raw)

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
        missing["phases"] = missing["phases"][:3]
        missing_path = root / "missing.json"
        write(missing_path, missing)
        assert_invalid(missing_path, "exactly plan, refine, work, closure")

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

        print("sam-task harness passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
