#!/usr/bin/env python3
"""Exercise sam-council report validation against adversarial fixtures."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts/validate_council_report.py"
SCAFFOLD = ROOT / "scripts/scaffold_council_report.py"
REVIEWERS = [
    "logic",
    "assumptions",
    "execution",
    "adversarial",
    "alternatives",
    "problem-frame",
]
VERIFIERS = ["closure-verifier", "system-verifier", "arbiter"]
FAST_REVIEWERS = ["frame-evidence", "delivery-failure", "simplification"]
FAST_VERIFIERS = ["triage-arbiter"]
HEAD_A = "a" * 40
HEAD_B = "b" * 40
CONDITIONAL_SELECTION = {
    "security-privacy": "NOT_APPLICABLE: fixture has no identity boundary.",
    "data-migration": "NOT_APPLICABLE: fixture has no migration.",
    "reliability-performance": "NOT_APPLICABLE: core execution seat covers fixture risk.",
    "api-compatibility": "NOT_APPLICABLE: fixture has no public contract.",
    "testability-release": "NOT_APPLICABLE: fixture has no release action.",
    "operations-observability": "NOT_APPLICABLE: fixture has no operator surface.",
    "cost-dependency": "NOT_APPLICABLE: fixture has no paid dependency.",
    "product-ux": "NOT_APPLICABLE: fixture has no user-facing surface.",
    "compliance-governance": "NOT_APPLICABLE: fixture names no governing regime.",
}


def base_report() -> dict[str, Any]:
    reviewer_results = [
        {
            "reviewer_id": reviewer_id,
            "verdict": "OBJECTIONS"
            if reviewer_id == "logic"
            else "NO_MATERIAL_OBJECTION",
            "search_summary": f"Completed the {reviewer_id} falsification lens.",
            "disconfirming_evidence": "Checked evidence that could reverse the verdict.",
            "residual_uncertainty": "No unreported material uncertainty.",
        }
        for reviewer_id in REVIEWERS
    ]
    return {
        "schema_version": 2,
        "profile": "full",
        "status": "APPROVED",
        "execution_policy": {
            "default_round_limit": 1,
            "hard_round_limit": 3,
            "continuation_authorized": False,
            "max_objections_per_reviewer": 3,
            "max_response_words": 1000,
            "packet_strategy": "RELEVANT_ONLY",
            "parallelism": "MAX_AVAILABLE",
            "initial_effort": "medium",
            "arbiter_effort": "high",
        },
        "thesis": {
            "id": "T-002",
            "objective": "Deliver the capability without losing accepted operations.",
            "problem_frame": "The current synchronous path exceeds its verified budget.",
            "scope": ["One bounded service path"],
            "constraints": ["Preserve backward compatibility"],
            "assumptions": [
                {
                    "id": "A-001",
                    "claim": "Peak load remains within the measured range.",
                    "state": "VERIFIED",
                    "evidence_ids": ["E-001"],
                }
            ],
            "alternatives": ["Retain the current path with a smaller batch"],
            "steps": ["Add the bounded path behind a staged release gate"],
            "success_criteria": ["P95 remains below the measured threshold"],
            "test_strategy": ["Run failure, retry, compatibility, and load scenarios"],
            "rollout": ["Release to an internal cohort before expansion"],
            "rollback": ["Disable the release gate and drain in-flight work"],
            "observability": ["Alert on latency, errors, backlog, and duplicate work"],
            "residual_risks": ["A dependency outage can delay completion"],
            "recheck_triggers": ["Reopen the decision when peak volume doubles"],
        },
        "evidence": [
            {
                "id": "E-001",
                "kind": "TEST",
                "claim": "A controlled load run measured the operating range.",
                "locator": "load-test receipt and command output",
            }
        ],
        "independence": {
            "mode": "single-host",
            "providers": ["portable-host"],
            "provider_runtimes": {
                "portable-host": {
                    "adapter": "host-native-workers",
                    "model": "host-default",
                    "reviewer_effort": "medium",
                    "arbiter_effort": "high",
                    "max_parallel_workers": 6,
                }
            },
            "blind_first_pass": True,
            "reviewers_saw_peer_reviews_before_submission": False,
            "reviewer_ids": REVIEWERS.copy(),
            "verifier_ids": VERIFIERS.copy(),
            "conditional_seat_selection": CONDITIONAL_SELECTION.copy(),
            "batch_plan": [
                {
                    "round": 1,
                    "phase": "blind",
                    "provider": "portable-host",
                    "seat_ids": REVIEWERS.copy(),
                },
                {
                    "round": 1,
                    "phase": "verification",
                    "provider": "portable-host",
                    "seat_ids": VERIFIERS.copy(),
                },
            ],
            "conflicts": [],
        },
        "confrontation": None,
        "rounds": [
            {
                "number": 1,
                "input_thesis_id": "T-001",
                "reviewer_ids": REVIEWERS.copy(),
                "reviewer_results": reviewer_results,
                "objections": [
                    {
                        "id": "O-R1-001",
                        "reviewer_id": "logic",
                        "supporting_reviewer_ids": ["logic"],
                        "claim": "The initial capacity claim did not follow from measured data.",
                        "failure_mode": "The plan could overload during the peak interval.",
                        "severity": "HIGH",
                        "confidence": 90,
                        "premise_ids": ["A-001"],
                        "evidence_ids": ["E-001"],
                        "required_proof": "A controlled peak-load result with thresholds.",
                        "smallest_correction": "Bound the plan to the measured operating range.",
                        "status": "RESOLVED",
                        "author_response": {
                            "disposition": "ACCEPT",
                            "rationale": "The original range was unsupported and is now bounded.",
                            "evidence_ids": ["E-001"],
                            "change": "Added the measured capacity bound and expansion trigger.",
                            "validation": "Compared the bound with the load-test receipt.",
                            "residual_risk": "Volume growth remains a re-evaluation trigger.",
                        },
                    }
                ],
                "output_thesis_id": "T-002",
                "verification": [
                    {
                        "verifier_id": "closure-verifier",
                        "verdict": "CLOSED",
                        "objection_ids": ["O-R1-001"],
                        "rationale": "The revised thesis uses the measured range and a gate.",
                    },
                    {
                        "verifier_id": "system-verifier",
                        "verdict": "NO_MATERIAL_OBJECTION",
                        "objection_ids": [],
                        "rationale": "No displaced failure or disproportionate complexity remains.",
                    },
                    {
                        "verifier_id": "arbiter",
                        "verdict": "CLOSED",
                        "objection_ids": ["O-R1-001"],
                        "rationale": "Evidence supports closure without relying on vote count.",
                    },
                ],
                "new_material_objections": 0,
            }
        ],
        "decision": {
            "final_thesis_id": "T-002",
            "confidence": 86,
            "basis": "EVIDENCE_AND_RISK",
            "rationale": "The load-bearing objection is closed by measured evidence.",
            "open_blocker_ids": [],
            "open_high_ids": [],
            "conditions": [],
            "accepted_risk_ids": [],
            "required_experiment_ids": [],
            "change_summary": [
                "Replaced an unbounded capacity claim with a measured gate"
            ],
            "decision_owner_actions": [],
        },
        "historical_record_limitations": [],
        "blockers": [],
    }


def conditional_experiment() -> dict[str, Any]:
    report = base_report()
    report["status"] = "APPROVED_WITH_CONDITIONS"
    assumption = report["thesis"]["assumptions"][0]
    assumption.update(
        {
            "state": "EXPERIMENT_PLANNED",
            "experiment": "Run a production-like peak-load test before expansion.",
            "owner": "Delivery owner",
            "pass_threshold": "P95 and error rate remain inside the stated guardrails.",
        }
    )
    report["decision"]["conditions"] = [
        "Pass the gated load experiment before expansion"
    ]
    report["decision"]["required_experiment_ids"] = ["A-001"]
    report["decision"]["decision_owner_actions"] = ["Review the experiment receipt"]
    return report


def conditional_accepted_high() -> dict[str, Any]:
    report = base_report()
    report["status"] = "APPROVED_WITH_CONDITIONS"
    objection = report["rounds"][0]["objections"][0]
    objection["status"] = "ACCEPTED_RISK"
    objection["author_response"]["disposition"] = "ACCEPT_RISK"
    report["rounds"][0]["verification"][0]["verdict"] = "CONDITION_VALIDATED"
    report["rounds"][0]["verification"][2]["verdict"] = "CONDITION_VALIDATED"
    report["decision"]["conditions"] = ["Decision owner accepts the bounded peak risk"]
    report["decision"]["accepted_risk_ids"] = ["O-R1-001"]
    report["decision"]["decision_owner_actions"] = ["Authorize the risk before rollout"]
    return report


def revise_report() -> dict[str, Any]:
    report = base_report()
    report["status"] = "REVISE"
    objection = report["rounds"][0]["objections"][0]
    objection["status"] = "OPEN"
    objection["author_response"]["disposition"] = "INVESTIGATE"
    report["rounds"][0]["verification"][0]["verdict"] = "STILL_OPEN"
    report["decision"]["open_high_ids"] = ["O-R1-001"]
    return report


def blocked_report() -> dict[str, Any]:
    report = base_report()
    report["status"] = "BLOCKED"
    report["independence"]["reviewer_ids"] = []
    report["independence"]["verifier_ids"] = []
    report["independence"]["providers"] = []
    report["independence"]["provider_runtimes"] = {}
    report["independence"]["batch_plan"] = []
    report["rounds"] = []
    report["blockers"] = ["The runtime cannot create distinct subagents"]
    return report


def multi_provider_report() -> dict[str, Any]:
    """Two-provider council with namespaced seats and confrontation ledger."""
    providers = ["codex", "grok"]
    namespaced = [
        f"{provider}/{seat}" for provider in providers for seat in REVIEWERS
    ]
    results = []
    for reviewer_id in namespaced:
        provider, seat = reviewer_id.split("/", 1)
        results.append(
            {
                "reviewer_id": reviewer_id,
                "provider": provider,
                "verdict": "OBJECTIONS"
                if reviewer_id == "codex/logic"
                else "NO_MATERIAL_OBJECTION",
                "search_summary": f"Completed the {seat} falsification lens on {provider}.",
                "disconfirming_evidence": "Checked evidence that could reverse the verdict.",
                "residual_uncertainty": "No unreported material uncertainty.",
            }
        )
    return {
        "schema_version": 2,
        "profile": "full",
        "status": "APPROVED",
        "execution_policy": copy.deepcopy(base_report()["execution_policy"]),
        "thesis": base_report()["thesis"],
        "evidence": base_report()["evidence"],
        "independence": {
            "mode": "multi-provider",
            "providers": providers,
            "provider_runtimes": {
                "codex": {
                    "adapter": "native-workers",
                    "model": "host-default",
                    "reviewer_effort": "medium",
                    "arbiter_effort": "high",
                    "max_parallel_workers": 6,
                },
                "grok": {
                    "adapter": "native-workers",
                    "model": "host-default",
                    "reviewer_effort": "medium",
                    "arbiter_effort": "high",
                    "max_parallel_workers": 6,
                },
            },
            "blind_first_pass": True,
            "reviewers_saw_peer_reviews_before_submission": False,
            "reviewer_ids": namespaced,
            "verifier_ids": [
                "closure-verifier",
                "system-verifier",
                "meta-arbiter",
            ],
            "conditional_seat_selection": CONDITIONAL_SELECTION.copy(),
            "batch_plan": [
                {
                    "round": 1,
                    "phase": "blind",
                    "provider": "codex",
                    "seat_ids": [seat for seat in namespaced if seat.startswith("codex/")],
                },
                {
                    "round": 1,
                    "phase": "blind",
                    "provider": "grok",
                    "seat_ids": [seat for seat in namespaced if seat.startswith("grok/")],
                },
                {
                    "round": 1,
                    "phase": "verification",
                    "provider": "codex",
                    "seat_ids": ["closure-verifier", "system-verifier", "meta-arbiter"],
                },
            ],
            "conflicts": [],
        },
        "confrontation": {
            "provider_positions": [
                {
                    "provider": "codex",
                    "stance": "REVISE",
                    "material_objection_ids": ["O-R1-001"],
                    "preferred_correction": "Bound capacity to measured load.",
                },
                {
                    "provider": "grok",
                    "stance": "APPROVE_WITH_CONDITIONS",
                    "material_objection_ids": [],
                    "preferred_correction": "Keep measured load gate as a condition.",
                },
            ],
            "disagreements": [
                {
                    "topic": "capacity bound necessity",
                    "provider_ids": ["codex", "grok"],
                    "summary": "Codex required a bound; Grok preferred a gated condition.",
                }
            ],
            "resolution": "EVIDENCE_WEIGHTED",
            "surviving_claim_ids": ["O-R1-001"],
            "rejected_claim_summaries": [],
            "rationale": "Measured load evidence makes the capacity bound the safer claim.",
        },
        "rounds": [
            {
                "number": 1,
                "input_thesis_id": "T-001",
                "reviewer_ids": namespaced,
                "reviewer_results": results,
                "objections": [
                    {
                        "id": "O-R1-001",
                        "reviewer_id": "codex/logic",
                        "supporting_reviewer_ids": ["codex/logic"],
                        "claim": "The initial capacity claim did not follow from measured data.",
                        "failure_mode": "The plan could overload during the peak interval.",
                        "severity": "HIGH",
                        "confidence": 90,
                        "premise_ids": ["A-001"],
                        "evidence_ids": ["E-001"],
                        "required_proof": "A controlled peak-load result with thresholds.",
                        "smallest_correction": "Bound the plan to the measured operating range.",
                        "status": "RESOLVED",
                        "author_response": {
                            "disposition": "ACCEPT",
                            "rationale": "The original range was unsupported and is now bounded.",
                            "evidence_ids": ["E-001"],
                            "change": "Added the measured capacity bound and expansion trigger.",
                            "validation": "Compared the bound with the load-test receipt.",
                            "residual_risk": "Volume growth remains a re-evaluation trigger.",
                        },
                    }
                ],
                "output_thesis_id": "T-002",
                "verification": [
                    {
                        "verifier_id": "closure-verifier",
                        "verdict": "CLOSED",
                        "objection_ids": ["O-R1-001"],
                        "rationale": "The revised thesis uses the measured range and a gate.",
                    },
                    {
                        "verifier_id": "system-verifier",
                        "verdict": "NO_MATERIAL_OBJECTION",
                        "objection_ids": [],
                        "rationale": "No displaced failure or disproportionate complexity remains.",
                    },
                    {
                        "verifier_id": "meta-arbiter",
                        "verdict": "CLOSED",
                        "objection_ids": ["O-R1-001"],
                        "rationale": "Evidence favors the capacity bound over provider majority.",
                    },
                ],
                "new_material_objections": 0,
            }
        ],
        "decision": {
            "final_thesis_id": "T-002",
            "confidence": 88,
            "basis": "EVIDENCE_AND_RISK",
            "rationale": "Cross-provider confrontation kept the measured-bound claim.",
            "open_blocker_ids": [],
            "open_high_ids": [],
            "conditions": [],
            "accepted_risk_ids": [],
            "required_experiment_ids": [],
            "change_summary": [
                "Replaced an unbounded capacity claim with a measured gate after multi-provider confrontation"
            ],
            "decision_owner_actions": [],
        },
        "historical_record_limitations": [],
        "blockers": [],
    }


def multi_round_report() -> dict[str, Any]:
    report = base_report()
    report["execution_policy"]["continuation_authorized"] = True
    first_round = report["rounds"][0]
    first_round["verification"][1]["verdict"] = "NEW_RISK"
    first_round["new_material_objections"] = 1
    second_objection = copy.deepcopy(first_round["objections"][0])
    second_objection.update(
        {
            "id": "O-R2-001",
            "claim": "The first revision introduced an unbounded recovery path.",
            "failure_mode": "Recovery work can consume all worker capacity.",
            "severity": "HIGH",
            "status": "MITIGATED",
        }
    )
    second_objection["author_response"].update(
        {
            "rationale": "The recovery path is now capped and observable.",
            "change": "Added a recovery concurrency limit and halt threshold.",
            "validation": "Verified the threshold against the measured capacity.",
            "residual_risk": "A prolonged outage can delay recovery.",
        }
    )
    report["rounds"].append(
        {
            "number": 2,
            "input_thesis_id": "T-002",
            "reviewer_ids": ["logic"],
            "reviewer_results": [
                {
                    "reviewer_id": "logic",
                    "verdict": "OBJECTIONS",
                    "search_summary": "Checked the new recovery mechanism.",
                    "disconfirming_evidence": "Compared the new cap with measured capacity.",
                    "residual_uncertainty": "Long outages remain a bounded delay risk.",
                }
            ],
            "objections": [second_objection],
            "output_thesis_id": "T-003",
            "verification": [
                {
                    "verifier_id": "closure-verifier",
                    "verdict": "CLOSED",
                    "objection_ids": ["O-R2-001"],
                    "rationale": "The recovery cap closes the new mechanism.",
                },
                {
                    "verifier_id": "system-verifier",
                    "verdict": "NO_MATERIAL_OBJECTION",
                    "objection_ids": [],
                    "rationale": "No further displaced risk remains.",
                },
                {
                    "verifier_id": "arbiter",
                    "verdict": "CLOSED",
                    "objection_ids": ["O-R2-001"],
                    "rationale": "Final evidence supports closure.",
                },
            ],
            "new_material_objections": 0,
        }
    )
    report["independence"]["batch_plan"].extend(
        [
            {
                "round": 2,
                "phase": "blind",
                "provider": "portable-host",
                "seat_ids": ["logic"],
            },
            {
                "round": 2,
                "phase": "verification",
                "provider": "portable-host",
                "seat_ids": VERIFIERS.copy(),
            },
        ]
    )
    report["thesis"]["id"] = "T-003"
    report["decision"]["final_thesis_id"] = "T-003"
    report["decision"]["change_summary"].append(
        "Bounded recovery concurrency after a verifier found displaced risk"
    )
    return report


def shuffled_experiment_ledger() -> dict[str, Any]:
    report = conditional_experiment()
    report["thesis"]["assumptions"].append(
        {
            "id": "A-002",
            "claim": "Recovery stays inside the measured budget.",
            "state": "EXPERIMENT_PLANNED",
            "evidence_ids": ["E-001"],
            "experiment": "Run recovery under a dependency outage.",
            "owner": "Operations owner",
            "pass_threshold": "Recovery stays inside the capacity guardrail.",
        }
    )
    report["decision"]["required_experiment_ids"] = ["A-002", "A-001"]
    return report


def merged_reviewer_provenance() -> dict[str, Any]:
    report = base_report()
    report["rounds"][0]["reviewer_results"][1]["verdict"] = "OBJECTIONS"
    report["rounds"][0]["objections"][0]["supporting_reviewer_ids"] = [
        "logic",
        "assumptions",
    ]
    return report


def conditional_with_history_limit() -> dict[str, Any]:
    report = conditional_experiment()
    report["historical_record_limitations"] = [
        "One early verifier transcript is unavailable; the open verdict is preserved."
    ]
    return report


def fast_report() -> dict[str, Any]:
    report = base_report()
    report["profile"] = "fast"
    report["status"] = "TRIAGE_PASS"
    report["execution_policy"]["hard_round_limit"] = 1
    report["independence"]["reviewer_ids"] = FAST_REVIEWERS.copy()
    report["independence"]["verifier_ids"] = FAST_VERIFIERS.copy()
    report["independence"]["batch_plan"] = [
        {
            "round": 1,
            "phase": "blind",
            "provider": "portable-host",
            "seat_ids": FAST_REVIEWERS.copy(),
        },
        {
            "round": 1,
            "phase": "verification",
            "provider": "portable-host",
            "seat_ids": FAST_VERIFIERS.copy(),
        },
    ]
    round_item = report["rounds"][0]
    round_item["reviewer_ids"] = FAST_REVIEWERS.copy()
    round_item["reviewer_results"] = [
        {
            "reviewer_id": reviewer_id,
            "verdict": "NO_MATERIAL_OBJECTION",
            "search_summary": f"Completed bounded {reviewer_id} triage.",
            "disconfirming_evidence": "Checked evidence that could trigger full review.",
            "residual_uncertainty": "No material triage uncertainty remains.",
        }
        for reviewer_id in FAST_REVIEWERS
    ]
    round_item["objections"] = []
    round_item["verification"] = [
        {
            "verifier_id": "triage-arbiter",
            "verdict": "NO_MATERIAL_OBJECTION",
            "objection_ids": [],
            "rationale": "No material risk, specialist trigger, or displaced problem found.",
        }
    ]
    report["decision"]["rationale"] = "Bounded triage found no escalation trigger."
    report["decision"]["change_summary"] = []
    return report


def fast_zero_objection_report() -> dict[str, Any]:
    """All fast seats clean: nothing to revise, so the triage-arbiter is skipped."""
    report = fast_report()
    report["independence"]["verifier_ids"] = []
    report["independence"]["batch_plan"] = report["independence"]["batch_plan"][:1]
    report["rounds"][0]["verification"] = []
    report["rounds"][0]["output_thesis_id"] = "T-001"
    report["thesis"]["id"] = "T-001"
    report["decision"]["final_thesis_id"] = "T-001"
    return report


def fast_zero_skip_with_objection() -> dict[str, Any]:
    report = fast_zero_objection_report()
    report["rounds"][0]["reviewer_results"][0]["verdict"] = "OBJECTIONS"
    objection = copy.deepcopy(base_report()["rounds"][0]["objections"][0])
    objection.update(
        reviewer_id="frame-evidence",
        supporting_reviewer_ids=["frame-evidence"],
        severity="MEDIUM",
    )
    report["rounds"][0]["objections"] = [objection]
    return report


def on_head(report: dict[str, Any], head: str = HEAD_A) -> dict[str, Any]:
    report["packet_head"] = head
    return report


def as_delta(report: dict[str, Any]) -> dict[str, Any]:
    """Re-review, on a newer head, of the base's final thesis T-002."""
    report.update(packet_scope="DELTA", base_report="base.json", packet_head=HEAD_B)
    report["rounds"][0].update(input_thesis_id="T-002", output_thesis_id="T-003")
    report["thesis"]["id"] = "T-003"
    report["decision"]["final_thesis_id"] = "T-003"
    return report


def delta_base() -> dict[str, Any]:
    return on_head(fast_report())


def delta_report() -> dict[str, Any]:
    return as_delta(fast_report())


def full_delta_report() -> dict[str, Any]:
    return as_delta(base_report())


def fast_escalation_report() -> dict[str, Any]:
    report = fast_report()
    report["status"] = "ESCALATE_TO_FULL"
    report["thesis"]["assumptions"][0]["state"] = "UNRESOLVED"
    report["thesis"]["assumptions"][0]["evidence_ids"] = []
    report["decision"]["rationale"] = "A critical capacity assumption requires full review."
    return report


def fast_specialist_escalation_report() -> dict[str, Any]:
    report = fast_report()
    report["status"] = "ESCALATE_TO_FULL"
    report["independence"]["conditional_seat_selection"]["security-privacy"] = (
        "ESCALATE: the plan changes an authorization boundary."
    )
    report["decision"]["rationale"] = "A security specialist is required."
    return report


def provider_report(provider: str) -> dict[str, Any]:
    report = base_report()
    runtime = report["independence"]["provider_runtimes"].pop("portable-host")
    runtime["model"] = f"{provider}-reported-model"
    report["independence"]["providers"] = [provider]
    report["independence"]["provider_runtimes"] = {provider: runtime}
    for batch in report["independence"]["batch_plan"]:
        batch["provider"] = provider
    return report


def over_objection_cap_report() -> dict[str, Any]:
    report = base_report()
    original = report["rounds"][0]["objections"][0]
    for number in range(2, 5):
        objection = copy.deepcopy(original)
        objection["id"] = f"O-R1-{number:03d}"
        objection["claim"] = f"Distinct material mechanism {number}."
        report["rounds"][0]["objections"].append(objection)
    return report


def run_validator(
    report: dict[str, Any], base: dict[str, Any] | None = None, cwd: Path = ROOT
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="sam-council-") as temporary:
        path = Path(temporary) / "report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        if base is not None:
            (Path(temporary) / "base.json").write_text(json.dumps(base), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(VALIDATOR), str(path)],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )


def mutate(
    source: Callable[[], dict[str, Any]],
    operation: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    report = copy.deepcopy(source())
    operation(report)
    return report


def scaffold(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCAFFOLD), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=harness",
         "-c", "user.email=harness@example.invalid", "-c", "commit.gpgsign=false", *args],
        text=True, capture_output=True, check=True,
    ).stdout.strip()


def fill_fast(path: Path, output_thesis_id: str, verification: list[Any]) -> None:
    """Author the judgment fields of an init skeleton from the fast fixture."""
    report = json.loads(path.read_text(encoding="utf-8"))
    fixture = fast_report()
    report["status"] = fixture["status"]
    report["thesis"] = {**fixture["thesis"], "id": output_thesis_id}
    report["evidence"] = fixture["evidence"]
    report["independence"]["conditional_seat_selection"] = CONDITIONAL_SELECTION.copy()
    report["rounds"][0].update(
        output_thesis_id=output_thesis_id,
        reviewer_results=fixture["rounds"][0]["reviewer_results"],
        verification=verification,
    )
    report["decision"].update(confidence=80, rationale="Clean triage.")
    write_json(path, report)


def prefix_only(selection: dict[str, Any]) -> dict[str, str]:
    """Edit init's seat entries the way the validator's prefix error invites:
    drop a TODO marker and the unchosen ESCALATE alternative, add no reason."""
    return {
        seat: str(value).replace("TODO ", "").replace("ESCALATE|", "")
        for seat, value in selection.items()
    }


def scaffold_checks() -> tuple[int, list[str]]:
    """Scaffold output must satisfy the validator's mechanical invariants.

    The agent authors judgment fields only; init/finalize derive constants, seat
    IDs, minimum batches, and ledgers. Placeholders must fail closed. Reuse must
    require an identical, genuine, VALID, non-BLOCKED packet on the same clean
    commit, because seats read cited repository files that change with the head.
    A DELTA must extend a VALID passing base of the same thesis on an ancestor.
    """
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory(prefix="sam-council-scaffold-") as temporary:
        root = Path(temporary).resolve()
        ceiling = os.environ.get("GIT_CEILING_DIRECTORIES")
        os.environ["GIT_CEILING_DIRECTORIES"] = str(root)
        try:
            return _scaffold_checks(root, checks)
        finally:
            if ceiling is None:
                os.environ.pop("GIT_CEILING_DIRECTORIES", None)
            else:
                os.environ["GIT_CEILING_DIRECTORIES"] = ceiling


def _scaffold_checks(
    root: Path, checks: list[tuple[str, bool]]
) -> tuple[int, list[str]]:
    repo = root / "repo"
    (repo / "src").mkdir(parents=True)
    cited = repo / "src/foo.py"
    cited.write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "one")
    head1 = git(repo, "rev-parse", "HEAD")
    packet = root / "packet.md"
    original_packet = "T-001 thesis, evidence, src/foo.py:1-1\n"
    packet.write_text(original_packet, encoding="utf-8")
    runtime_args = ["--model", "host-default", "--reviewer-effort", "medium", "--arbiter-effort", "high"]
    fast_args = [
        "--packet", str(packet), "--profile", "fast", "--provider",
        "portable-host", "--max-parallel", "2", *runtime_args, "--repo", str(repo),
    ]
    run1 = root / "run1/council-report.json"
    init = scaffold("init", "--out", str(run1), *fast_args)
    checks.append(("init writes skeleton", init.returncode == 0 and run1.is_file()))
    if not run1.is_file():
        return len(checks), [f"init: {init.stderr.strip()}"]
    report = json.loads(run1.read_text(encoding="utf-8"))
    checks.append((
        "init requires runtime facts instead of defaulting them",
        scaffold("init", "--out", str(root / "no-runtime.json"), *fast_args[:8], *fast_args[-2:])
        .returncode != 0,
    ))
    checks.append((
        "reuse and DELTA need an explicit --repo",
        scaffold(
            "init", "--out", str(root / "no-repo.json"), *fast_args[:-2],
            "--reuse-dir", str(root),
        ).returncode != 0,
    ))
    checks.append((
        "init derives the head from a clean repository",
        report.get("packet_head") == head1 and "packet_fingerprint" in report,
    ))
    checks.append((
        "init constants match fast policy",
        report["execution_policy"] == fast_report()["execution_policy"]
        and set(report["independence"]["conditional_seat_selection"])
        == set(CONDITIONAL_SELECTION),
    ))
    checks.append((
        "unfilled placeholders fail closed",
        scaffold("finalize", str(run1)).returncode != 0,
    ))
    fill_fast(run1, "T-002", fast_report()["rounds"][0]["verification"])
    final = scaffold("finalize", str(run1))
    derived = json.loads(run1.read_text(encoding="utf-8"))
    blind = [b for b in derived["independence"]["batch_plan"] if b["phase"] == "blind"]
    checks.append((
        "finalize derives minimum batches and final thesis",
        final.returncode == 0
        and len(blind) == 2
        and derived["independence"]["verifier_ids"] == FAST_VERIFIERS
        and derived["decision"]["final_thesis_id"] == "T-002",
    ))
    # Every specialist needs a system-specific reason; a prefix left as init
    # wrote it (minus the markers) must not validate as a recorded decision.
    seats_only = copy.deepcopy(derived)
    seats_only["independence"]["conditional_seat_selection"] = prefix_only(
        report["independence"]["conditional_seat_selection"]
    )
    write_json(root / "seats-only/council-report.json", seats_only)
    seats_final = scaffold("finalize", str(root / "seats-only/council-report.json"))
    checks.append((
        "fast: conditional seats with only init's prefix edited fail closed",
        seats_final.returncode != 0
        and "conditional_seat_selection" in seats_final.stdout + seats_final.stderr,
    ))
    checks.append((
        "validator rejects a typed fingerprint and an unreadable packet",
        run_validator({**derived, "packet_fingerprint": "0" * 64}).returncode != 0
        and run_validator({**derived, "packet_path": str(root / "missing.md")}).returncode
        != 0,
    ))

    run2 = root / "run2/council-report.json"
    reuse = scaffold("init", "--out", str(run2), *fast_args, "--reuse-dir", str(root))
    checks.append((
        "identical VALID packet is reused",
        reuse.stdout.startswith(f"REUSE {run1.resolve()}")
        and "validator: VALID: TRIAGE_PASS" in reuse.stdout
        and not run2.exists(),
    ))
    checks.append((
        "repo run with --head none or a foreign head fails closed",
        scaffold("init", "--out", str(run2), *fast_args, "--head", "none").returncode != 0
        and scaffold("init", "--out", str(run2), *fast_args, "--head", "0" * 40).returncode
        != 0
        and not run2.exists(),
    ))
    blocked = copy.deepcopy(derived)
    blocked.update(status="BLOCKED", blockers=["Distinct workers became unavailable."])
    write_json(root / "blocked/council-report.json", blocked)
    blocked_valid = run_validator(blocked).returncode == 0
    not_blocked = scaffold(
        "init", "--out", str(run2), *fast_args, "--reuse-dir", str(root / "blocked")
    )
    checks.append((
        "VALID BLOCKED report is never reused",
        blocked_valid and not_blocked.stdout.startswith("INIT "),
    ))
    cited.write_text("VALUE = 2\n", encoding="utf-8")
    dirty_path = root / "dirty/council-report.json"
    dirty = scaffold("init", "--out", str(dirty_path), *fast_args, "--reuse-dir", str(root))
    dirty_report = json.loads(dirty_path.read_text(encoding="utf-8")) if dirty_path.is_file() else {}
    checks.append((
        "dirty work tree is never reused and records no fingerprint",
        dirty.stdout.startswith("INIT ")
        and dirty_report.get("packet_head") == head1
        and "packet_fingerprint" not in dirty_report,
    ))
    cited.write_text("VALUE = 1\n", encoding="utf-8")
    packet.write_text("T-001 thesis, evidence, changed excerpt\n", encoding="utf-8")
    run3 = root / "run3/council-report.json"
    changed = scaffold("init", "--out", str(run3), *fast_args, "--reuse-dir", str(root))
    checks.append(("changed packet is not reused", changed.stdout.startswith("INIT ")))
    forged = copy.deepcopy(derived)
    forged["packet_fingerprint"] = changed.stdout.split("fingerprint=", 1)[-1].strip()
    forged["packet_path"] = str(root / "forged/packet.md")
    write_json(root / "forged/council-report.json", forged)
    (root / "forged/packet.md").write_text(original_packet, encoding="utf-8")
    run4 = root / "run4/council-report.json"
    forged_run = scaffold(
        "init", "--out", str(run4), *fast_args, "--reuse-dir", str(root / "forged")
    )
    checks.append((
        "typed fingerprint without a matching packet is not reused",
        forged_run.stdout.startswith("INIT "),
    ))

    packet.write_text(original_packet, encoding="utf-8")
    cited.write_text("VALUE = 3\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "two")
    head2 = git(repo, "rev-parse", "HEAD")
    run5 = root / "run5/council-report.json"
    moved = scaffold("init", "--out", str(run5), *fast_args, "--reuse-dir", str(root))
    checks.append((
        "same packet on a different head is not reused",
        moved.stdout.startswith("INIT ") and f"head={head2}" in moved.stdout,
    ))

    delta_path = root / "delta/council-report.json"
    delta_init = scaffold(
        "init", "--out", str(delta_path), *fast_args, "--base-report", str(run1)
    )
    delta = json.loads(delta_path.read_text(encoding="utf-8")) if delta_path.is_file() else {}
    linked = (
        delta_init.returncode == 0
        and delta.get("packet_scope") == "DELTA"
        and delta["rounds"][0]["input_thesis_id"] == "T-002"
        and delta["thesis"]["objective"] == fast_report()["thesis"]["objective"]
    )
    if delta_path.is_file():
        fill_fast(delta_path, "T-002", [])
    delta_unanchored = scaffold("finalize", str(delta_path))
    delta_foreign = scaffold("finalize", str(delta_path), "--repo", str(root))
    delta_final = scaffold("finalize", str(delta_path), "--repo", str(repo))
    delta_derived = (
        json.loads(delta_path.read_text(encoding="utf-8")) if delta_path.is_file() else {}
    )
    checks.append((
        "DELTA init links the base thesis and validates on an ancestor head",
        linked
        and delta_final.returncode == 0
        and run_validator(delta_derived, cwd=repo).returncode == 0,
    ))
    # scaffold() runs from this skill's directory, a repository that lacks the
    # temp commits: without --repo the validator's ancestry check would pass
    # silently there, so finalize must refuse a DELTA without the target repo.
    unknown_base = root / "unknown-base/council-report.json"
    write_json(unknown_base, on_head(delta_report(), head2))
    write_json(unknown_base.parent / "base.json", on_head(fast_report(), "c" * 40))
    delta_unknown = scaffold("finalize", str(unknown_base), "--repo", str(repo))
    checks.append((
        "DELTA finalize needs --repo holding both packet_heads",
        all(
            result.returncode != 0 and "--repo" in result.stderr
            for result in (delta_unanchored, delta_foreign, delta_unknown)
        ),
    ))
    ancestry = root / "ancestry/council-report.json"
    write_json(ancestry, on_head(delta_report(), head1))
    write_json(ancestry.parent / "base.json", on_head(fast_report(), head2))
    not_ancestor = scaffold("finalize", str(ancestry), "--repo", str(repo))
    chained = scaffold(
        "init", "--out", str(root / "d3.json"), *fast_args, "--base-report", str(ancestry)
    )
    # A reuse candidate for this packet and head whose base sits on a parentless
    # side commit: VALID outside the repository, a broken chain inside it.
    side = git(repo, "commit-tree", f"{head2}^{{tree}}", "-m", "side")
    candidate = on_head(delta_report(), head2)
    candidate.update(
        packet_path=str(packet),
        packet_fingerprint=moved.stdout.split("fingerprint=", 1)[-1].strip(),
    )
    write_json(root / "reuse-delta/council-report.json", candidate)
    write_json(root / "reuse-delta/base.json", on_head(fast_report(), side))
    unanchored_reuse = scaffold(
        "init", "--out", str(root / "r6.json"), *fast_args,
        "--reuse-dir", str(root / "reuse-delta"),
    )
    checks.append((
        "init, reuse, and finalize run the DELTA ancestry check in --repo",
        not_ancestor.returncode != 0
        and "not an ancestor" in not_ancestor.stderr
        and chained.returncode != 0
        and "not an ancestor" in chained.stderr
        and not (root / "d3.json").exists()
        and run_validator(candidate, on_head(fast_report(), side)).returncode == 0
        and unanchored_reuse.stdout.startswith("INIT "),
    ))
    checks.append((
        "DELTA base that is not an ancestor is rejected in the repository",
        run_validator(on_head(delta_report(), head2), on_head(fast_report(), head1), repo)
        .returncode == 0
        and run_validator(
            on_head(delta_report(), head1), on_head(fast_report(), head2), repo
        ).returncode != 0,
    ))
    checks.append((
        "DELTA init refuses a profile change or a same-head base",
        scaffold(
            "init", "--out", str(root / "d1.json"), *fast_args[:4], "full",
            *fast_args[5:], "--base-report", str(run1),
        ).returncode != 0
        and scaffold(
            "init", "--out", str(root / "d2.json"), *fast_args,
            "--base-report", str(delta_path),
        ).returncode != 0,
    ))
    # Runtime labels are recorded evidence; init never invents a default for
    # any one of them (the case above drops all three at once).
    checks.append((
        "init requires --model and each effort flag individually",
        all(
            scaffold(
                "init", "--out", str(root / "m.json"),
                *[arg for index, arg in enumerate(fast_args)
                  if index not in (drop, drop + 1)],
            ).returncode != 0
            for drop in (
                fast_args.index("--model"),
                fast_args.index("--reviewer-effort"),
                fast_args.index("--arbiter-effort"),
            )
        )
        and not (root / "m.json").exists(),
    ))

    norepo = root / "norepo"
    norepo.mkdir()
    loose_args = [*fast_args[:-1], str(norepo)]
    loose = root / "loose/council-report.json"
    loose_init = scaffold("init", "--out", str(loose), *loose_args)
    if loose.is_file():
        fill_fast(loose, "T-002", fast_report()["rounds"][0]["verification"])
    loose_valid = scaffold("finalize", str(loose)).returncode == 0
    loose_again = scaffold(
        "init", "--out", str(root / "loose2.json"), *loose_args,
        "--reuse-dir", str(loose.parent),
    )
    checks.append((
        "outside a repository nothing is reused and --head must be a full SHA",
        loose_init.returncode == 0
        and loose_valid
        and loose_again.stdout.startswith("INIT ")
        and scaffold(
            "init", "--out", str(root / "loose3.json"), *loose_args, "--head", "abc123"
        ).returncode != 0,
    ))

    # A typed head outside the repository never becomes a reuse key inside it.
    typed = root / "typed/council-report.json"
    typed_init = scaffold("init", "--out", str(typed), *loose_args, "--head", head2)
    if typed.is_file():
        fill_fast(typed, "T-002", fast_report()["rounds"][0]["verification"])
    typed_valid = scaffold("finalize", str(typed)).returncode == 0
    typed_report = json.loads(typed.read_text(encoding="utf-8")) if typed.is_file() else {}
    typed_again = scaffold(
        "init", "--out", str(root / "typed2.json"), *fast_args, "--reuse-dir", str(typed.parent)
    )
    checks.append((
        "a report made outside the repository is never reused inside it",
        typed_init.returncode == 0
        and typed_valid
        and "packet_fingerprint" not in typed_report
        and typed_again.stdout.startswith("INIT "),
    ))

    # BLOCKED before dispatch: the author fills judgment fields only, leaves
    # rounds as [], and finalize derives final_thesis_id from the thesis.
    early = root / "early-blocked/council-report.json"
    early_init = scaffold(
        "init", "--out", str(early), "--packet", str(packet), "--profile", "full",
        "--provider", "portable-host", "--max-parallel", "4", *runtime_args,
        "--repo", str(repo),
    )
    early_ok = early_placeholder_fails = False
    if early.is_file():
        blocked_early = json.loads(early.read_text(encoding="utf-8"))
        blocked_early.update(
            status="BLOCKED", rounds=[], evidence=base_report()["evidence"],
            blockers=["The runtime cannot create distinct subagents."],
            thesis={**base_report()["thesis"], "id": "T-001"},
        )
        blocked_early["independence"]["conditional_seat_selection"] = (
            CONDITIONAL_SELECTION.copy()
        )
        blocked_early["decision"].update(confidence=90, rationale="Blocked before dispatch.")
        write_json(early, blocked_early)
        early_final = scaffold("finalize", str(early))
        early_ok = (
            early_final.returncode == 0
            and "VALID: BLOCKED" in early_final.stdout
            and json.loads(early.read_text(encoding="utf-8"))["decision"]["final_thesis_id"]
            == "T-001"
        )
        blocked_early["thesis"]["id"] = "TODO"
        write_json(early, blocked_early)
        early_placeholder_fails = scaffold("finalize", str(early)).returncode != 0
    checks.append((
        "BLOCKED before dispatch finalizes with rounds [] and a derived final thesis",
        early_init.returncode == 0 and early_ok and early_placeholder_fails,
    ))

    revise = revise_report()
    revise["decision"].update(open_high_ids=[], final_thesis_id="")
    revise["independence"].update(reviewer_ids=[], verifier_ids=[], batch_plan=[])
    write_json(root / "revise.json", revise)
    revise_final = scaffold("finalize", str(root / "revise.json"))
    revise_derived = json.loads((root / "revise.json").read_text(encoding="utf-8"))
    checks.append((
        "finalize derives exact decision ledgers",
        revise_final.returncode == 0
        and revise_derived["decision"]["open_high_ids"] == ["O-R1-001"],
    ))

    multi_path = root / "multi/council-report.json"
    multi_init = scaffold(
        "init", "--out", str(multi_path), "--packet", str(packet), "--profile",
        "full", "--provider", "codex", "--provider", "grok", "--max-parallel", "6",
        *runtime_args, "--repo", str(repo),
    )
    multi = json.loads(multi_path.read_text(encoding="utf-8")) if multi_path.is_file() else {}
    runtimes = multi.get("independence", {}).get("provider_runtimes", {})
    checks.append((
        "init records runtime only for the first provider",
        runtimes.get("codex", {}).get("model") == "host-default"
        and runtimes.get("grok", {}).get("reviewer_effort") == "TODO"
        and runtimes.get("grok", {}).get("max_parallel_workers")
        != runtimes.get("codex", {}).get("max_parallel_workers"),
    ))
    unfilled = scaffold("finalize", str(multi_path)) if multi_path.is_file() else None
    checks.append((
        "an unfilled second-provider runtime fails closed",
        unfilled is not None and unfilled.returncode != 0,
    ))
    source = multi_provider_report()
    # Only the second provider's adapter/model/capacity stay as init wrote
    # them; every other field matches the passing report below. A leftover
    # placeholder, or the controller's capacity copied onto another provider,
    # must not validate as a recorded runtime.
    partial_output = ""
    seats_output = ""
    if runtimes:
        partial = copy.deepcopy(multi)
        partial["independence"]["provider_runtimes"]["grok"] = {
            **runtimes["codex"],
            "adapter": runtimes["grok"].get("adapter"),
            "model": runtimes["grok"].get("model"),
            "max_parallel_workers": runtimes["grok"].get("max_parallel_workers"),
        }
        for key in ("status", "thesis", "evidence", "confrontation", "rounds", "decision"):
            partial[key] = source[key]
        full_seats = prefix_only(multi["independence"]["conditional_seat_selection"])
        partial["independence"]["conditional_seat_selection"] = CONDITIONAL_SELECTION.copy()
        partial_path = root / "multi-partial/council-report.json"
        write_json(partial_path, partial)
        partial_final = scaffold("finalize", str(partial_path))
        if partial_final.returncode != 0:
            partial_output = partial_final.stdout + partial_final.stderr
        # Full profile: every runtime filled, seats left as init wrote them.
        partial["independence"]["provider_runtimes"]["grok"] = dict(runtimes["codex"])
        partial["independence"]["conditional_seat_selection"] = full_seats
        write_json(partial_path, partial)
        seats_final = scaffold("finalize", str(partial_path))
        if seats_final.returncode != 0:
            seats_output = seats_final.stdout + seats_final.stderr
    checks.append((
        "a second-provider adapter/model/capacity left as init wrote it fails closed",
        "grok.adapter" in partial_output
        and "grok.model" in partial_output
        and "grok.max_parallel_workers" in partial_output,
    ))
    checks.append((
        "full: conditional seats with only init's prefix edited fail closed",
        "conditional_seat_selection" in seats_output
        and "grok." not in seats_output,
    ))
    if runtimes:
        runtimes["grok"] = dict(runtimes["codex"])
    for key in ("status", "thesis", "evidence", "confrontation", "rounds", "decision"):
        multi[key] = source[key]
    multi.setdefault("independence", {})["conditional_seat_selection"] = (
        CONDITIONAL_SELECTION.copy()
    )
    write_json(multi_path, multi)
    checks.append((
        "multi-provider finalize derives namespaced batches",
        multi_init.returncode == 0 and scaffold("finalize", str(multi_path)).returncode == 0,
    ))
    checks.append((
        "init rejects fast multi-provider and fast specialist selection",
        scaffold(
            "init", "--out", str(root / "x.json"), "--packet", str(packet),
            "--profile", "fast", "--provider", "codex", "--provider", "grok",
            "--max-parallel", "6",
        ).returncode != 0
        and scaffold(
            "init", "--out", str(root / "y.json"), *fast_args,
            "--select", "security-privacy",
        ).returncode != 0,
    ))
    return len(checks), [f"scaffold: {name}" for name, ok in checks if not ok]


def main() -> int:
    cases: list[tuple[str, dict[str, Any], bool]] = [
        ("approved", base_report(), True),
        ("fast triage pass", fast_report(), True),
        ("fast material escalation", fast_escalation_report(), True),
        ("fast specialist escalation", fast_specialist_escalation_report(), True),
        ("codex portable runtime", provider_report("codex"), True),
        ("claude-code portable runtime", provider_report("claude-code"), True),
        ("grok portable runtime", provider_report("grok"), True),
        ("unlisted portable runtime", provider_report("future-agent"), True),
        (
            "host default effort fallback",
            mutate(
                base_report,
                lambda r: r["independence"]["provider_runtimes"]["portable-host"].update(
                    reviewer_effort="host-default", arbiter_effort="host-default"
                ),
            ),
            True,
        ),
        ("conditional experiment", conditional_experiment(), True),
        ("conditional accepted high", conditional_accepted_high(), True),
        ("multi-round historical new risk", multi_round_report(), True),
        ("multi-provider confrontation", multi_provider_report(), True),
        ("unordered experiment ledger", shuffled_experiment_ledger(), True),
        ("merged reviewer provenance", merged_reviewer_provenance(), True),
        ("conditional history limitation", conditional_with_history_limit(), True),
        ("revise", revise_report(), True),
        ("blocked", blocked_report(), True),
        (
            "schema v1 rejected",
            mutate(base_report, lambda r: r.update(schema_version=1)),
            False,
        ),
        (
            "fast cannot approve",
            mutate(fast_report, lambda r: r.update(status="APPROVED")),
            False,
        ),
        (
            "full cannot triage pass",
            mutate(base_report, lambda r: r.update(status="TRIAGE_PASS")),
            False,
        ),
        (
            "fast missing reviewer",
            mutate(
                fast_report,
                lambda r: (
                    r["rounds"][0]["reviewer_ids"].pop(),
                    r["rounds"][0]["reviewer_results"].pop(),
                    r["independence"]["reviewer_ids"].pop(),
                    r["independence"]["batch_plan"][0]["seat_ids"].pop(),
                ),
            ),
            False,
        ),
        (
            "fast pass with unresolved assumption",
            mutate(
                fast_report,
                lambda r: r["thesis"]["assumptions"][0].update(
                    state="UNRESOLVED", evidence_ids=[]
                ),
            ),
            False,
        ),
        (
            "fast escalation without reason",
            mutate(fast_report, lambda r: r.update(status="ESCALATE_TO_FULL")),
            False,
        ),
        (
            "fast reviewer blocked under nonblocked status",
            mutate(
                fast_report,
                lambda r: r["rounds"][0]["reviewer_results"][0].update(
                    verdict="BLOCKED"
                ),
            ),
            False,
        ),
        (
            "fast multi-provider",
            mutate(
                fast_report,
                lambda r: r["independence"].update(mode="multi-provider"),
            ),
            False,
        ),
        (
            "invalid provider slug",
            provider_report("Invalid Provider"),
            False,
        ),
        (
            "invalid runtime effort",
            mutate(
                base_report,
                lambda r: r["independence"]["provider_runtimes"]["portable-host"].update(
                    reviewer_effort="turbo"
                ),
            ),
            False,
        ),
        (
            "batch exceeds capacity",
            mutate(
                base_report,
                lambda r: r["independence"]["provider_runtimes"]["portable-host"].update(
                    max_parallel_workers=2
                ),
            ),
            False,
        ),
        (
            "missing batch seat",
            mutate(
                base_report,
                lambda r: r["independence"]["batch_plan"][0]["seat_ids"].pop(),
            ),
            False,
        ),
        (
            "nonminimal batch plan",
            mutate(
                base_report,
                lambda r: r["independence"].update(
                    batch_plan=[
                        {
                            "round": 1,
                            "phase": "blind",
                            "provider": "portable-host",
                            "seat_ids": REVIEWERS[:3],
                        },
                        {
                            "round": 1,
                            "phase": "blind",
                            "provider": "portable-host",
                            "seat_ids": REVIEWERS[3:],
                        },
                        {
                            "round": 1,
                            "phase": "verification",
                            "provider": "portable-host",
                            "seat_ids": VERIFIERS.copy(),
                        },
                    ]
                ),
            ),
            False,
        ),
        ("reviewer objection cap", over_objection_cap_report(), False),
        (
            "wrong effort policy",
            mutate(
                base_report,
                lambda r: r["execution_policy"].update(initial_effort="high"),
            ),
            False,
        ),
        (
            "continuation not authorized",
            mutate(
                multi_round_report,
                lambda r: r["execution_policy"].update(continuation_authorized=False),
            ),
            False,
        ),
        (
            "approved history limitation",
            mutate(
                base_report,
                lambda r: r.update(
                    historical_record_limitations=["A raw transcript is unavailable."]
                ),
            ),
            False,
        ),
        (
            "missing conditional seat ledger",
            mutate(
                base_report,
                lambda r: r["independence"].pop("conditional_seat_selection"),
            ),
            False,
        ),
        (
            "selected conditional seat not dispatched",
            mutate(
                base_report,
                lambda r: r["independence"]["conditional_seat_selection"].update(
                    {"security-privacy": "SELECTED: identity boundary exists."}
                ),
            ),
            False,
        ),
        (
            "missing core reviewer",
            mutate(
                base_report, lambda r: r["rounds"][0]["reviewer_ids"].remove("logic")
            ),
            False,
        ),
        (
            "multi-provider without confrontation",
            mutate(
                multi_provider_report,
                lambda r: r.update(confrontation=None),
            ),
            False,
        ),
        (
            "multi-provider majority-style resolution",
            mutate(
                multi_provider_report,
                lambda r: r["confrontation"].update(resolution="MAJORITY"),
            ),
            False,
        ),
        (
            "blind review disabled",
            mutate(
                base_report, lambda r: r["independence"].update(blind_first_pass=False)
            ),
            False,
        ),
        (
            "peer review leak",
            mutate(
                base_report,
                lambda r: r["independence"].update(
                    reviewers_saw_peer_reviews_before_submission=True
                ),
            ),
            False,
        ),
        (
            "verifier overlap",
            mutate(
                base_report,
                lambda r: r["independence"]["verifier_ids"].append("logic"),
            ),
            False,
        ),
        (
            "missing arbiter ledger",
            mutate(
                base_report,
                lambda r: r["independence"]["verifier_ids"].remove("arbiter"),
            ),
            False,
        ),
        (
            "missing final verifier result",
            mutate(base_report, lambda r: r["rounds"][0]["verification"].pop()),
            False,
        ),
        (
            "missing reviewer result",
            mutate(base_report, lambda r: r["rounds"][0]["reviewer_results"].pop()),
            False,
        ),
        (
            "objection result without objection",
            mutate(base_report, lambda r: r["rounds"][0].update(objections=[])),
            False,
        ),
        (
            "missing supporting reviewer provenance",
            mutate(
                base_report,
                lambda r: r["rounds"][0]["objections"][0].pop(
                    "supporting_reviewer_ids"
                ),
            ),
            False,
        ),
        (
            "unknown supporting reviewer",
            mutate(
                base_report,
                lambda r: r["rounds"][0]["objections"][0].update(
                    supporting_reviewer_ids=["logic", "unknown-seat"]
                ),
            ),
            False,
        ),
        (
            "accepted blocker",
            mutate(
                conditional_accepted_high,
                lambda r: r["rounds"][0]["objections"][0].update(severity="BLOCKER"),
            ),
            False,
        ),
        (
            "approved open high",
            mutate(
                revise_report,
                lambda r: r.update(status="APPROVED"),
            ),
            False,
        ),
        (
            "approved unresolved assumption",
            mutate(
                base_report,
                lambda r: r["thesis"]["assumptions"][0].update(state="UNRESOLVED"),
            ),
            False,
        ),
        (
            "conditional without condition",
            mutate(base_report, lambda r: r.update(status="APPROVED_WITH_CONDITIONS")),
            False,
        ),
        (
            "experiment without threshold",
            mutate(
                conditional_experiment,
                lambda r: r["thesis"]["assumptions"][0].pop("pass_threshold"),
            ),
            False,
        ),
        (
            "unknown evidence reference",
            mutate(
                base_report,
                lambda r: r["rounds"][0]["objections"][0].update(
                    evidence_ids=["E-999"]
                ),
            ),
            False,
        ),
        (
            "too many rounds",
            mutate(
                base_report,
                lambda r: r["rounds"].extend(copy.deepcopy(r["rounds"]) * 3),
            ),
            False,
        ),
        (
            "new final risk",
            mutate(
                base_report,
                lambda r: (
                    r["rounds"][0].update(new_material_objections=1),
                    r["rounds"][0]["verification"][1].update(verdict="NEW_RISK"),
                ),
            ),
            False,
        ),
        (
            "new risk count without verdict",
            mutate(
                base_report,
                lambda r: r["rounds"][0].update(new_material_objections=1),
            ),
            False,
        ),
        (
            "new risk verdict without count",
            mutate(
                base_report,
                lambda r: r["rounds"][0]["verification"][1].update(verdict="NEW_RISK"),
            ),
            False,
        ),
        (
            "broken thesis chain",
            mutate(
                multi_round_report,
                lambda r: r["rounds"][1].update(input_thesis_id="T-099"),
            ),
            False,
        ),
        (
            "invalid thesis id",
            mutate(base_report, lambda r: r["thesis"].update(id="final-thesis")),
            False,
        ),
        (
            "final verifier still open",
            mutate(
                base_report,
                lambda r: r["rounds"][0]["verification"][0].update(
                    verdict="STILL_OPEN"
                ),
            ),
            False,
        ),
        (
            "missing rollback",
            mutate(base_report, lambda r: r["thesis"].update(rollback=[])),
            False,
        ),
        (
            "decision ledger drift",
            mutate(
                base_report,
                lambda r: r["decision"].update(open_high_ids=["O-R1-001"]),
            ),
            False,
        ),
        (
            "confidence out of range",
            mutate(base_report, lambda r: r["decision"].update(confidence=101)),
            False,
        ),
        (
            "revise without material issue",
            mutate(base_report, lambda r: r.update(status="REVISE")),
            False,
        ),
        (
            "blocked without blocker",
            mutate(blocked_report, lambda r: r.update(blockers=[])),
            False,
        ),
        (
            "unsupported wrong disposition",
            mutate(
                base_report,
                lambda r: r["rounds"][0]["objections"][0].update(
                    severity="UNSUPPORTED", status="UNSUPPORTED"
                ),
            ),
            False,
        ),
        ("fast zero-objection pass skips arbiter", fast_zero_objection_report(), True),
        (
            "arbiter skip cannot hide an objection",
            fast_zero_skip_with_objection(),
            False,
        ),
        (
            "all-clean seats cannot hide a recorded objection",
            mutate(
                fast_zero_objection_report,
                lambda r: r["rounds"][0].update(
                    objections=[
                        {
                            **copy.deepcopy(base_report()["rounds"][0]["objections"][0]),
                            "reviewer_id": "frame-evidence",
                            "supporting_reviewer_ids": ["frame-evidence"],
                            "severity": "LOW",
                        }
                    ]
                ),
            ),
            False,
        ),
        (
            "arbiter skip cannot revise the thesis",
            mutate(
                fast_zero_objection_report,
                lambda r: (
                    r["rounds"][0].update(output_thesis_id="T-002"),
                    r["thesis"].update(id="T-002"),
                    r["decision"].update(final_thesis_id="T-002"),
                ),
            ),
            False,
        ),
        (
            "arbiter skip cannot escalate",
            mutate(
                fast_zero_objection_report,
                lambda r: (
                    r.update(status="ESCALATE_TO_FULL"),
                    r["thesis"]["assumptions"][0].update(
                        state="UNRESOLVED", evidence_ids=[]
                    ),
                ),
            ),
            False,
        ),
        (
            "arbiter skip keeps no verifier ledger",
            mutate(
                fast_zero_objection_report,
                lambda r: r["independence"].update(verifier_ids=["triage-arbiter"]),
            ),
            False,
        ),
        (
            "full cannot skip verification",
            mutate(
                base_report,
                lambda r: (
                    r["rounds"][0].update(verification=[]),
                    r["independence"].update(
                        verifier_ids=[],
                        batch_plan=r["independence"]["batch_plan"][:1],
                    ),
                ),
            ),
            False,
        ),
        (
            "unknown packet scope",
            mutate(fast_report, lambda r: r.update(packet_scope="PARTIAL")),
            False,
        ),
        (
            "delta without base report",
            mutate(delta_report, lambda r: r.pop("base_report")),
            False,
        ),
        ("delta on passing base", delta_report(), True, delta_base()),
        ("delta on escalated base", delta_report(), False, on_head(fast_escalation_report())),
        (
            "delta on invalid base",
            delta_report(),
            False,
            mutate(delta_base, lambda r: r.update(schema_version=1)),
        ),
        ("delta profile differs from base", delta_report(), False, on_head(base_report())),
        ("full delta on fast triage base", full_delta_report(), False, delta_base()),
        ("full delta on full base", full_delta_report(), True, on_head(base_report())),
        ("self-referential delta base", delta_report(), False, delta_report()),
        (
            "delta on unrelated base objective",
            delta_report(),
            False,
            mutate(delta_base, lambda r: r["thesis"].update(objective="Another goal.")),
        ),
        (
            "delta skips the base final thesis",
            mutate(delta_report, lambda r: r["rounds"][0].update(input_thesis_id="T-001")),
            False,
            delta_base(),
        ),
        ("delta base without commit head", delta_report(), False, on_head(fast_report(), "none")),
        (
            "delta on the base head",
            mutate(delta_report, lambda r: r.update(packet_head=HEAD_A)),
            False,
            delta_base(),
        ),
        (
            "packet head must be none or a full commit SHA",
            mutate(fast_report, lambda r: r.update(packet_head="abc123")),
            False,
        ),
    ]

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if "author" not in skill.lower() or "not authorization" not in skill:
        print(
            "FAIL: council SKILL must treat author-revised theses as not authorization",
            file=sys.stderr,
        )
        return 1
    if "continuation_authorized" not in skill:
        print(
            "FAIL: council SKILL must bind extra rounds to continuation_authorized",
            file=sys.stderr,
        )
        return 1

    failures: list[str] = []
    for name, report, should_pass, *base in cases:
        result = run_validator(report, base[0] if base else None)
        passed = result.returncode == 0
        if passed != should_pass:
            detail = (result.stderr or result.stdout).strip().splitlines()
            failures.append(f"{name}: {detail[-1] if detail else 'no output'}")
    scaffold_count, scaffold_failures = scaffold_checks()
    failures.extend(scaffold_failures)
    total = len(cases) + scaffold_count
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"FAILED: {len(failures)}/{total} scenarios", file=sys.stderr)
        return 1
    print(f"PASS: {total} sam-council harness scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
