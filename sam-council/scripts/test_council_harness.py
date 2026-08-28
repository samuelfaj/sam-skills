#!/usr/bin/env python3
"""Exercise sam-council report validation against adversarial fixtures."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts/validate_council_report.py"
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


def run_validator(report: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="sam-council-") as temporary:
        path = Path(temporary) / "report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(VALIDATOR), str(path)],
            cwd=ROOT,
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
    for name, report, should_pass in cases:
        result = run_validator(report)
        passed = result.returncode == 0
        if passed != should_pass:
            detail = (result.stderr or result.stdout).strip().splitlines()
            failures.append(f"{name}: {detail[-1] if detail else 'no output'}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"FAILED: {len(failures)}/{len(cases)} scenarios", file=sys.stderr)
        return 1
    print(f"PASS: {len(cases)} sam-council harness scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
