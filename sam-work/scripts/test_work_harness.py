#!/usr/bin/env python3
"""Run adversarial checks against the sam-work report validator."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "validate_work_report", SCRIPT_DIR / "validate_work_report.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load sam-work validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

HEAD = "a" * 40
BASE = "b" * 40
FP = "c" * 64


def iteration(status: str) -> dict[str, Any]:
    return {
        "sequence": 1,
        "input_fingerprint": "d" * 64,
        "output_fingerprint": "e" * 64,
        "status": status,
        "open_required_items": [],
        "correction_receipts": [],
        "evidence": [f"receipt for {status}"],
    }


def phase(
    phase_id: str,
    skill: str,
    status: str,
    *,
    applicability: str = "REQUIRED",
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": phase_id,
        "skill": skill,
        "applicability": applicability,
        "status": status,
        "current": True,
        "validated_head_sha": HEAD,
        "not_applicable_reason": reason,
        "evidence": [f"evidence for {phase_id}"],
        "validator_receipts": [f"PASS: {phase_id}"],
        "iterations": [iteration(status)],
    }


def environment() -> dict[str, Any]:
    return {
        "kind": "DEVELOPMENT",
        "identity_verified": True,
        "identity_evidence": ["verified isolated development database"],
        "real_data": True,
        "dedicated_data": True,
        "cleanup_status": "COMPLETE",
        "privacy_review": "PASS",
    }


def artifact(phase_id: str, suffix: str) -> dict[str, Any]:
    extension = "webm" if phase_id == "playwright" else "mp4"
    return {
        "phase": phase_id,
        "local_path": f"/tmp/{phase_id}-{suffix}.{extension}",
        "sha256": ("1" if phase_id == "playwright" else "2") * 64,
        "uploaded_url": f"https://example.test/assets/{phase_id}-{suffix}",
        "upload_receipt": f"uploaded {phase_id}-{suffix}",
        "player_verified": True,
        "readback_evidence": [f"rendered player for {phase_id}-{suffix}"],
    }


def valid_report(*, web: bool = True, classification: str = "BUG") -> dict[str, Any]:
    implementation_skill = "sam-fix-bug" if classification == "BUG" else "sam-create-feature"
    playwright = (
        phase("playwright", "sam-create-playwright-tests", "COMPLETE")
        if web
        else phase(
            "playwright",
            "sam-create-playwright-tests",
            "NOT_APPLICABLE",
            applicability="NOT_APPLICABLE",
            reason="repository exposes no browser-accessible runtime",
        )
    )
    artifacts = [artifact("demo", "one")]
    if web:
        artifacts.insert(0, artifact("playwright", "one"))
    report = {
        "schema_version": 1,
        "workflow_id": "work-001",
        "request": {
            "prompt_sha256": "3" * 64,
            "classification": classification,
            "web_system": web,
            "classification_evidence": ["expected existing behavior is broken"],
        },
        "authorization": {
            "create_or_update_proposal": True,
            "publish_playwright_videos": True,
            "publish_demo_video": True,
            "merge": False,
            "deploy": False,
        },
        "target": {
            "repo_root": "/tmp/repository",
            "base_ref": "main",
            "base_sha": BASE,
            "final_head_sha": HEAD,
            "final_change_fingerprint": FP,
        },
        "phases": [
            phase("implementation", implementation_skill, "COMPLETE"),
            phase("refine", "sam-refine-task", "HIGH_CONFIDENCE"),
            phase("review", "sam-review", "APPROVE"),
            phase("simplify", "sam-simplify-task", "SIMPLEST_DEFENSIBLE"),
            phase("coverage", "sam-create-test-coverage", "FULL"),
            phase("proposal", "sam-pr-description", "READY"),
            playwright,
            phase("demo", "sam-create-task-demo-video", "PUBLISHED"),
        ],
        "proposal": {
            "platform": "example",
            "url": "https://example.test/proposals/1",
            "proposal_id": "1",
            "created_by_workflow": True,
            "description_validated": True,
            "description_receipt": "PASS: proposal body",
            "remote_head_sha": HEAD,
            "rendered_readback_evidence": ["read back description and players"],
            "required_ci_status": "PASS",
        },
        "environments": {
            "demo": environment(),
            "playwright": environment() if web else None,
        },
        "video_inventory": {
            "playwright_discovered": 1 if web else 0,
            "playwright_uploaded": 1 if web else 0,
            "demo_discovered": 1,
            "demo_uploaded": 1,
        },
        "artifacts": artifacts,
        "final": {
            "result": "COMPLETE",
            "completed_phase_ids": list(VALIDATOR.PHASE_IDS),
            "blockers": [],
            "final_head_sha": HEAD,
            "final_change_fingerprint": FP,
        },
    }
    return report


def expect_valid(name: str, report: dict[str, Any]) -> None:
    errors = VALIDATOR.validate(report)
    if errors:
        raise AssertionError(f"{name}: expected valid report, got {errors}")


def expect_invalid(
    name: str,
    report: dict[str, Any],
    expected_fragment: str,
) -> None:
    errors = VALIDATOR.validate(report)
    if not any(expected_fragment in error for error in errors):
        raise AssertionError(
            f"{name}: expected error containing {expected_fragment!r}, got {errors}"
        )


def mutate(report: dict[str, Any], fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    changed = copy.deepcopy(report)
    fn(changed)
    return changed


def main() -> int:
    bug_web = valid_report(web=True, classification="BUG")
    feature_nonweb = valid_report(web=False, classification="FEATURE")
    expect_valid("bug web happy path", bug_web)
    expect_valid("feature non-web happy path", feature_nonweb)

    cases: list[tuple[str, dict[str, Any], str]] = [
        (
            "missing phase",
            mutate(bug_web, lambda r: r["phases"].pop(2)),
            "exactly all eight",
        ),
        (
            "wrong implementation router",
            mutate(
                bug_web,
                lambda r: r["phases"][0].update(skill="sam-create-feature"),
            ),
            "must use sam-fix-bug",
        ),
        (
            "review not closed",
            mutate(
                bug_web,
                lambda r: (
                    r["phases"][2].update(status="CHANGES_REQUIRED"),
                    r["phases"][2]["iterations"][0].update(
                        status="CHANGES_REQUIRED",
                        open_required_items=["authorization gap"],
                        correction_receipts=["pending correction"],
                    ),
                ),
            ),
            "does not have an accepted final status",
        ),
        (
            "stale refinement",
            mutate(
                bug_web,
                lambda r: r["phases"][1].update(validated_head_sha=BASE),
            ),
            "proof is stale",
        ),
        (
            "missing child validator",
            mutate(
                bug_web,
                lambda r: r["phases"][4].update(validator_receipts=[]),
            ),
            "requires validator receipts",
        ),
        (
            "web Playwright skipped",
            mutate(
                bug_web,
                lambda r: r["phases"][6].update(
                    applicability="NOT_APPLICABLE",
                    status="NOT_APPLICABLE",
                    not_applicable_reason="too difficult",
                ),
            ),
            "must be REQUIRED",
        ),
        (
            "non-web without applicability proof",
            mutate(
                feature_nonweb,
                lambda r: r["phases"][6].update(not_applicable_reason=""),
            ),
            "requires a concrete reason",
        ),
        (
            "unverified development environment",
            mutate(
                bug_web,
                lambda r: r["environments"]["playwright"].update(
                    identity_verified=False
                ),
            ),
            "identity must be verified",
        ),
        (
            "missing browser upload",
            mutate(
                bug_web,
                lambda r: r["video_inventory"].update(playwright_uploaded=0),
            ),
            "every discovered Playwright video",
        ),
        (
            "unverified player",
            mutate(
                bug_web,
                lambda r: r["artifacts"][0].update(player_verified=False),
            ),
            "verified rendered video player",
        ),
        (
            "demo is not MP4",
            mutate(
                bug_web,
                lambda r: r["artifacts"][1].update(local_path="/tmp/demo.webm"),
            ),
            "demo video must be an MP4",
        ),
        (
            "proposal head drift",
            mutate(
                bug_web,
                lambda r: r["proposal"].update(remote_head_sha=BASE),
            ),
            "remote head does not match",
        ),
        (
            "merge authorization widened",
            mutate(
                bug_web,
                lambda r: r["authorization"].update(merge=True),
            ),
            "write boundary",
        ),
        (
            "blocked declared complete",
            mutate(
                bug_web,
                lambda r: r["final"].update(blockers=["demo upload failed"]),
            ),
            "cannot have blockers",
        ),
    ]
    for name, report, fragment in cases:
        expect_invalid(name, report, fragment)

    print(f"PASS: {2 + len(cases)} sam-work harness scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
