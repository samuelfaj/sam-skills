#!/usr/bin/env python3
"""Validate a sam-council decision report and its approval invariants."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


STATUSES = {"APPROVED", "APPROVED_WITH_CONDITIONS", "REVISE", "BLOCKED"}
REQUIRED_REVIEWERS = {
    "logic",
    "assumptions",
    "execution",
    "adversarial",
    "alternatives",
    "problem-frame",
}
REQUIRED_VERIFIERS = {"closure-verifier", "system-verifier", "arbiter"}
CONDITIONAL_REVIEWERS = {
    "security-privacy",
    "data-migration",
    "reliability-performance",
    "api-compatibility",
    "testability-release",
    "operations-observability",
    "cost-dependency",
    "product-ux",
    "compliance-governance",
}
ASSUMPTION_STATES = {"VERIFIED", "EXPERIMENT_PLANNED", "UNRESOLVED"}
SEVERITIES = {"BLOCKER", "HIGH", "MEDIUM", "LOW", "UNSUPPORTED"}
OBJECTION_STATUSES = {
    "OPEN",
    "RESOLVED",
    "MITIGATED",
    "ACCEPTED_RISK",
    "UNSUPPORTED",
}
DISPOSITIONS = {"ACCEPT", "PARTIAL", "REJECT", "INVESTIGATE", "ACCEPT_RISK"}
VERDICTS = {
    "CLOSED",
    "STILL_OPEN",
    "NEW_RISK",
    "CONDITION_VALIDATED",
    "NO_MATERIAL_OBJECTION",
}
REVIEWER_VERDICTS = {"OBJECTIONS", "NO_MATERIAL_OBJECTION", "BLOCKED"}
EVIDENCE_ID = re.compile(r"^E-\d{3}$")
ASSUMPTION_ID = re.compile(r"^A-\d{3}$")
THESIS_ID = re.compile(r"^T-\d{3}$")


def mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected object")
        return {}
    return value


def sequence(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path}: expected list")
        return []
    return value


def text(value: Any, path: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: expected non-empty text")
        return ""
    return value.strip()


def integer(value: Any, path: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{path}: expected integer")
        return None
    return value


def text_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    required: bool = False,
) -> list[str]:
    values = sequence(value, path, errors)
    result: list[str] = []
    for index, item in enumerate(values):
        item_text = text(item, f"{path}[{index}]", errors)
        if item_text:
            result.append(item_text)
    if required and not result:
        errors.append(f"{path}: must not be empty")
    if len(result) != len(set(result)):
        errors.append(f"{path}: duplicate values")
    return result


def check_references(
    values: Any,
    known: set[str],
    path: str,
    errors: list[str],
) -> list[str]:
    references = text_list(values, path, errors)
    for reference in references:
        if reference not in known:
            errors.append(f"{path}: unknown reference {reference}")
    return references


def validate_report(report: Any) -> list[str]:
    errors: list[str] = []
    root = mapping(report, "report", errors)
    if root.get("schema_version") != 1:
        errors.append("schema_version: expected 1")

    status = root.get("status")
    if status not in STATUSES:
        errors.append(f"status: expected one of {sorted(STATUSES)}")

    evidence_items = sequence(root.get("evidence"), "evidence", errors)
    evidence_ids: set[str] = set()
    for index, raw_item in enumerate(evidence_items):
        path = f"evidence[{index}]"
        item = mapping(raw_item, path, errors)
        item_id = text(item.get("id"), f"{path}.id", errors)
        if item_id and not EVIDENCE_ID.fullmatch(item_id):
            errors.append(f"{path}.id: expected E-###")
        if item_id in evidence_ids:
            errors.append(f"{path}.id: duplicate {item_id}")
        evidence_ids.add(item_id)
        text(item.get("kind"), f"{path}.kind", errors)
        text(item.get("claim"), f"{path}.claim", errors)
        text(item.get("locator"), f"{path}.locator", errors)
    evidence_ids.discard("")

    thesis = mapping(root.get("thesis"), "thesis", errors)
    thesis_id = text(thesis.get("id"), "thesis.id", errors)
    if thesis_id and not THESIS_ID.fullmatch(thesis_id):
        errors.append("thesis.id: expected T-###")
    text(thesis.get("objective"), "thesis.objective", errors)
    text(thesis.get("problem_frame"), "thesis.problem_frame", errors)
    for field in (
        "scope",
        "constraints",
        "alternatives",
        "steps",
        "success_criteria",
        "test_strategy",
        "rollout",
        "rollback",
        "observability",
        "residual_risks",
        "recheck_triggers",
    ):
        text_list(thesis.get(field), f"thesis.{field}", errors, required=True)

    assumption_items = sequence(thesis.get("assumptions"), "thesis.assumptions", errors)
    if not assumption_items:
        errors.append("thesis.assumptions: must not be empty")
    assumption_ids: set[str] = set()
    assumption_states: dict[str, str] = {}
    for index, raw_assumption in enumerate(assumption_items):
        path = f"thesis.assumptions[{index}]"
        assumption = mapping(raw_assumption, path, errors)
        assumption_id = text(assumption.get("id"), f"{path}.id", errors)
        if assumption_id and not ASSUMPTION_ID.fullmatch(assumption_id):
            errors.append(f"{path}.id: expected A-###")
        if assumption_id in assumption_ids:
            errors.append(f"{path}.id: duplicate {assumption_id}")
        assumption_ids.add(assumption_id)
        text(assumption.get("claim"), f"{path}.claim", errors)
        assumption_state = assumption.get("state")
        if assumption_state not in ASSUMPTION_STATES:
            errors.append(f"{path}.state: expected one of {sorted(ASSUMPTION_STATES)}")
        assumption_states[assumption_id] = assumption_state
        refs = check_references(
            assumption.get("evidence_ids"), evidence_ids, f"{path}.evidence_ids", errors
        )
        if assumption_state == "VERIFIED" and not refs:
            errors.append(f"{path}: VERIFIED requires evidence_ids")
        if assumption_state == "EXPERIMENT_PLANNED":
            text(assumption.get("experiment"), f"{path}.experiment", errors)
            text(assumption.get("owner"), f"{path}.owner", errors)
            text(assumption.get("pass_threshold"), f"{path}.pass_threshold", errors)
    assumption_ids.discard("")

    independence = mapping(root.get("independence"), "independence", errors)
    blind = independence.get("blind_first_pass")
    peer_leak = independence.get("reviewers_saw_peer_reviews_before_submission")
    if not isinstance(blind, bool):
        errors.append("independence.blind_first_pass: expected boolean")
    if not isinstance(peer_leak, bool):
        errors.append(
            "independence.reviewers_saw_peer_reviews_before_submission: expected boolean"
        )
    reviewer_ids = text_list(
        independence.get("reviewer_ids"), "independence.reviewer_ids", errors
    )
    verifier_ids = text_list(
        independence.get("verifier_ids"), "independence.verifier_ids", errors
    )
    conflicts = text_list(
        independence.get("conflicts"), "independence.conflicts", errors
    )
    raw_seat_selection = independence.get("conditional_seat_selection")
    seat_selection: dict[str, Any] = {}
    if status != "BLOCKED" or raw_seat_selection is not None:
        seat_selection = mapping(
            raw_seat_selection,
            "independence.conditional_seat_selection",
            errors,
        )
        if set(seat_selection) != CONDITIONAL_REVIEWERS:
            missing = sorted(CONDITIONAL_REVIEWERS - set(seat_selection))
            extra = sorted(set(seat_selection) - CONDITIONAL_REVIEWERS)
            errors.append(
                "independence.conditional_seat_selection: "
                f"missing {missing}; unexpected {extra}"
            )
        for seat_id, raw_reason in seat_selection.items():
            reason = text(
                raw_reason,
                f"independence.conditional_seat_selection.{seat_id}",
                errors,
            )
            if reason and not reason.startswith(("SELECTED: ", "NOT_APPLICABLE: ")):
                errors.append(
                    f"independence.conditional_seat_selection.{seat_id}: "
                    "expected SELECTED: or NOT_APPLICABLE: reason"
                )
            if reason.startswith("SELECTED: ") and seat_id not in reviewer_ids:
                errors.append(
                    f"independence.conditional_seat_selection.{seat_id}: "
                    "selected seat absent from reviewer_ids"
                )

    rounds = sequence(root.get("rounds"), "rounds", errors)
    if len(rounds) > 3:
        errors.append("rounds: maximum is 3")
    if status != "BLOCKED" and not rounds:
        errors.append("rounds: non-blocked report requires at least one round")

    objection_ids: set[str] = set()
    objection_records: dict[str, tuple[str, str]] = {}
    final_verification_verdicts: list[str] = []
    reviewer_verdicts: list[str] = []
    material_new_risks = 0
    last_output_thesis_id = ""
    final_panel_ids: set[str] = set()
    dispatched_reviewers: set[str] = set()
    for index, raw_round in enumerate(rounds):
        path = f"rounds[{index}]"
        round_item = mapping(raw_round, path, errors)
        previous_output_thesis_id = last_output_thesis_id
        number = integer(round_item.get("number"), f"{path}.number", errors)
        expected_number = index + 1
        if number is not None and number != expected_number:
            errors.append(f"{path}.number: expected {expected_number}")
        input_thesis_id = text(
            round_item.get("input_thesis_id"), f"{path}.input_thesis_id", errors
        )
        last_output_thesis_id = text(
            round_item.get("output_thesis_id"), f"{path}.output_thesis_id", errors
        )
        if input_thesis_id and not THESIS_ID.fullmatch(input_thesis_id):
            errors.append(f"{path}.input_thesis_id: expected T-###")
        if last_output_thesis_id and not THESIS_ID.fullmatch(last_output_thesis_id):
            errors.append(f"{path}.output_thesis_id: expected T-###")
        if index > 0 and input_thesis_id != previous_output_thesis_id:
            errors.append(f"{path}.input_thesis_id: must equal prior round output")
        if input_thesis_id and input_thesis_id == last_output_thesis_id:
            errors.append(f"{path}: input and output thesis IDs must differ")
        round_reviewers = text_list(
            round_item.get("reviewer_ids"),
            f"{path}.reviewer_ids",
            errors,
            required=True,
        )
        dispatched_reviewers.update(round_reviewers)
        if index == 0 and not REQUIRED_REVIEWERS.issubset(set(round_reviewers)):
            missing = sorted(REQUIRED_REVIEWERS - set(round_reviewers))
            errors.append(f"{path}.reviewer_ids: missing required reviewers {missing}")
        for reviewer_id in round_reviewers:
            if reviewer_id not in reviewer_ids:
                errors.append(
                    f"{path}.reviewer_ids: {reviewer_id} absent from independence ledger"
                )

        reviewer_results = sequence(
            round_item.get("reviewer_results"), f"{path}.reviewer_results", errors
        )
        result_ids: list[str] = []
        result_verdict_by_id: dict[str, str] = {}
        for result_index, raw_result in enumerate(reviewer_results):
            result_path = f"{path}.reviewer_results[{result_index}]"
            result = mapping(raw_result, result_path, errors)
            result_id = text(
                result.get("reviewer_id"), f"{result_path}.reviewer_id", errors
            )
            result_ids.append(result_id)
            verdict = result.get("verdict")
            if verdict not in REVIEWER_VERDICTS:
                errors.append(
                    f"{result_path}.verdict: expected one of {sorted(REVIEWER_VERDICTS)}"
                )
            else:
                reviewer_verdicts.append(verdict)
                result_verdict_by_id[result_id] = verdict
            text(result.get("search_summary"), f"{result_path}.search_summary", errors)
            text(
                result.get("disconfirming_evidence"),
                f"{result_path}.disconfirming_evidence",
                errors,
            )
            text(
                result.get("residual_uncertainty"),
                f"{result_path}.residual_uncertainty",
                errors,
            )
        if sorted(result_ids) != sorted(round_reviewers):
            errors.append(
                f"{path}.reviewer_results: require exactly one result per reviewer_id"
            )

        objections = sequence(
            round_item.get("objections"), f"{path}.objections", errors
        )
        objection_reviewers: set[str] = set()
        for objection_index, raw_objection in enumerate(objections):
            objection_path = f"{path}.objections[{objection_index}]"
            objection = mapping(raw_objection, objection_path, errors)
            objection_id = text(objection.get("id"), f"{objection_path}.id", errors)
            expected_prefix = f"O-R{expected_number}-"
            if objection_id and not (
                objection_id.startswith(expected_prefix)
                and len(objection_id[len(expected_prefix) :]) == 3
                and objection_id[len(expected_prefix) :].isdigit()
            ):
                errors.append(f"{objection_path}.id: expected {expected_prefix}###")
            if objection_id in objection_ids:
                errors.append(f"{objection_path}.id: duplicate {objection_id}")
            objection_ids.add(objection_id)
            reviewer_id = text(
                objection.get("reviewer_id"), f"{objection_path}.reviewer_id", errors
            )
            if reviewer_id not in round_reviewers:
                errors.append(
                    f"{objection_path}.reviewer_id: absent from round reviewer_ids"
                )
            supporting_reviewers = text_list(
                objection.get("supporting_reviewer_ids"),
                f"{objection_path}.supporting_reviewer_ids",
                errors,
                required=True,
            )
            if reviewer_id not in supporting_reviewers:
                errors.append(
                    f"{objection_path}.supporting_reviewer_ids: "
                    "must include reviewer_id"
                )
            for supporting_reviewer in supporting_reviewers:
                if supporting_reviewer not in round_reviewers:
                    errors.append(
                        f"{objection_path}.supporting_reviewer_ids: "
                        f"{supporting_reviewer} absent from round reviewer_ids"
                    )
            objection_reviewers.update(supporting_reviewers)
            text(objection.get("claim"), f"{objection_path}.claim", errors)
            text(
                objection.get("failure_mode"), f"{objection_path}.failure_mode", errors
            )
            severity = objection.get("severity")
            if severity not in SEVERITIES:
                errors.append(
                    f"{objection_path}.severity: expected one of {sorted(SEVERITIES)}"
                )
            confidence = integer(
                objection.get("confidence"), f"{objection_path}.confidence", errors
            )
            if confidence is not None and not 0 <= confidence <= 100:
                errors.append(f"{objection_path}.confidence: expected 0-100")
            check_references(
                objection.get("premise_ids"),
                assumption_ids,
                f"{objection_path}.premise_ids",
                errors,
            )
            check_references(
                objection.get("evidence_ids"),
                evidence_ids,
                f"{objection_path}.evidence_ids",
                errors,
            )
            text(
                objection.get("required_proof"),
                f"{objection_path}.required_proof",
                errors,
            )
            text(
                objection.get("smallest_correction"),
                f"{objection_path}.smallest_correction",
                errors,
            )
            objection_status = objection.get("status")
            if objection_status not in OBJECTION_STATUSES:
                errors.append(
                    f"{objection_path}.status: expected one of {sorted(OBJECTION_STATUSES)}"
                )
            if severity == "BLOCKER" and objection_status == "ACCEPTED_RISK":
                errors.append(f"{objection_path}: BLOCKER cannot be accepted as risk")

            response = mapping(
                objection.get("author_response"),
                f"{objection_path}.author_response",
                errors,
            )
            disposition = response.get("disposition")
            if disposition not in DISPOSITIONS:
                errors.append(
                    f"{objection_path}.author_response.disposition: "
                    f"expected one of {sorted(DISPOSITIONS)}"
                )
            text(
                response.get("rationale"),
                f"{objection_path}.author_response.rationale",
                errors,
            )
            check_references(
                response.get("evidence_ids"),
                evidence_ids,
                f"{objection_path}.author_response.evidence_ids",
                errors,
            )
            text(
                response.get("change"),
                f"{objection_path}.author_response.change",
                errors,
            )
            text(
                response.get("validation"),
                f"{objection_path}.author_response.validation",
                errors,
            )
            text(
                response.get("residual_risk"),
                f"{objection_path}.author_response.residual_risk",
                errors,
            )
            if objection_status == "ACCEPTED_RISK" and disposition != "ACCEPT_RISK":
                errors.append(f"{objection_path}: ACCEPTED_RISK requires ACCEPT_RISK")
            if objection_status == "UNSUPPORTED" and disposition != "REJECT":
                errors.append(f"{objection_path}: UNSUPPORTED requires REJECT")
            objection_records[objection_id] = (str(severity), str(objection_status))

        for reviewer_id, verdict in result_verdict_by_id.items():
            if verdict == "OBJECTIONS" and reviewer_id not in objection_reviewers:
                errors.append(
                    f"{path}.reviewer_results: {reviewer_id} reported OBJECTIONS without one"
                )

        verifications = sequence(
            round_item.get("verification"), f"{path}.verification", errors
        )
        if status != "BLOCKED" and not verifications:
            errors.append(f"{path}.verification: must not be empty")
        round_panel_ids: set[str] = set()
        round_verification_verdicts: list[str] = []
        for verification_index, raw_verification in enumerate(verifications):
            verification_path = f"{path}.verification[{verification_index}]"
            verification = mapping(raw_verification, verification_path, errors)
            verifier_id = text(
                verification.get("verifier_id"),
                f"{verification_path}.verifier_id",
                errors,
            )
            if verifier_id not in verifier_ids:
                errors.append(
                    f"{verification_path}.verifier_id: absent from independence ledger"
                )
            round_panel_ids.add(verifier_id)
            verdict = verification.get("verdict")
            if verdict not in VERDICTS:
                errors.append(
                    f"{verification_path}.verdict: expected one of {sorted(VERDICTS)}"
                )
            else:
                round_verification_verdicts.append(verdict)
            check_references(
                verification.get("objection_ids"),
                objection_ids,
                f"{verification_path}.objection_ids",
                errors,
            )
            text(
                verification.get("rationale"),
                f"{verification_path}.rationale",
                errors,
            )
        final_panel_ids = round_panel_ids
        final_verification_verdicts = round_verification_verdicts
        new_count = integer(
            round_item.get("new_material_objections"),
            f"{path}.new_material_objections",
            errors,
        )
        if new_count is not None:
            if new_count < 0:
                errors.append(f"{path}.new_material_objections: cannot be negative")
            material_new_risks += max(new_count, 0)
            has_new_risk_verdict = "NEW_RISK" in round_verification_verdicts
            if (new_count > 0) != has_new_risk_verdict:
                errors.append(
                    f"{path}: NEW_RISK verdict and positive "
                    "new_material_objections must agree"
                )

    if status != "BLOCKED":
        if set(reviewer_ids) != dispatched_reviewers:
            errors.append(
                "independence.reviewer_ids: must equal the dispatched round reviewers"
            )
        selected_seats = {
            seat_id
            for seat_id, reason in seat_selection.items()
            if isinstance(reason, str) and reason.startswith("SELECTED: ")
        }
        missing_selected = sorted(selected_seats - dispatched_reviewers)
        if missing_selected:
            errors.append(
                f"selected conditional seats not dispatched {missing_selected}"
            )

    objection_ids.discard("")
    open_blockers = sorted(
        objection_id
        for objection_id, (severity, objection_status) in objection_records.items()
        if severity == "BLOCKER" and objection_status == "OPEN"
    )
    open_highs = sorted(
        objection_id
        for objection_id, (severity, objection_status) in objection_records.items()
        if severity == "HIGH" and objection_status == "OPEN"
    )
    accepted_risks = sorted(
        objection_id
        for objection_id, (_, objection_status) in objection_records.items()
        if objection_status == "ACCEPTED_RISK"
    )
    accepted_highs = sorted(
        objection_id
        for objection_id, (severity, objection_status) in objection_records.items()
        if severity == "HIGH" and objection_status == "ACCEPTED_RISK"
    )
    experiment_ids = sorted(
        assumption_id
        for assumption_id, assumption_state in assumption_states.items()
        if assumption_state == "EXPERIMENT_PLANNED"
    )
    unresolved_assumptions = sorted(
        assumption_id
        for assumption_id, assumption_state in assumption_states.items()
        if assumption_state == "UNRESOLVED"
    )

    decision = mapping(root.get("decision"), "decision", errors)
    final_thesis_id = text(
        decision.get("final_thesis_id"), "decision.final_thesis_id", errors
    )
    if final_thesis_id and final_thesis_id != thesis_id:
        errors.append("decision.final_thesis_id: must equal thesis.id")
    if rounds and final_thesis_id != last_output_thesis_id:
        errors.append(
            "decision.final_thesis_id: must equal final round output_thesis_id"
        )
    decision_confidence = integer(
        decision.get("confidence"), "decision.confidence", errors
    )
    if decision_confidence is not None and not 0 <= decision_confidence <= 100:
        errors.append("decision.confidence: expected 0-100")
    if decision.get("basis") != "EVIDENCE_AND_RISK":
        errors.append("decision.basis: expected EVIDENCE_AND_RISK")
    text(decision.get("rationale"), "decision.rationale", errors)
    decision_open_blockers = text_list(
        decision.get("open_blocker_ids"), "decision.open_blocker_ids", errors
    )
    decision_open_highs = text_list(
        decision.get("open_high_ids"), "decision.open_high_ids", errors
    )
    conditions = text_list(decision.get("conditions"), "decision.conditions", errors)
    decision_accepted_risks = text_list(
        decision.get("accepted_risk_ids"), "decision.accepted_risk_ids", errors
    )
    decision_experiments = text_list(
        decision.get("required_experiment_ids"),
        "decision.required_experiment_ids",
        errors,
    )
    change_summary = text_list(
        decision.get("change_summary"), "decision.change_summary", errors
    )
    owner_actions = text_list(
        decision.get("decision_owner_actions"),
        "decision.decision_owner_actions",
        errors,
    )
    if sorted(decision_open_blockers) != open_blockers:
        errors.append(
            f"decision.open_blocker_ids: expected exact ledger {open_blockers}"
        )
    if sorted(decision_open_highs) != open_highs:
        errors.append(f"decision.open_high_ids: expected exact ledger {open_highs}")
    if sorted(decision_accepted_risks) != accepted_risks:
        errors.append(
            f"decision.accepted_risk_ids: expected exact ledger {accepted_risks}"
        )
    if sorted(decision_experiments) != experiment_ids:
        errors.append(
            f"decision.required_experiment_ids: expected exact ledger {experiment_ids}"
        )

    blockers = text_list(root.get("blockers"), "blockers", errors)
    historical_record_limitations = text_list(
        root.get("historical_record_limitations"),
        "historical_record_limitations",
        errors,
    )
    approved = status in {"APPROVED", "APPROVED_WITH_CONDITIONS"}
    if status != "BLOCKED" and blockers:
        errors.append("blockers: only BLOCKED may contain blockers")
    if status == "BLOCKED" and not blockers:
        errors.append("blockers: BLOCKED requires at least one blocker")

    if approved:
        if blind is not True:
            errors.append("approval requires blind_first_pass=true")
        if peer_leak is not False:
            errors.append("approval forbids peer reviews before blind submission")
        missing_reviewers = sorted(REQUIRED_REVIEWERS - set(reviewer_ids))
        if missing_reviewers:
            errors.append(f"approval missing required reviewers {missing_reviewers}")
        if len(verifier_ids) < 3:
            errors.append("approval requires at least three fresh verifiers")
        missing_verifiers = sorted(REQUIRED_VERIFIERS - set(verifier_ids))
        if missing_verifiers:
            errors.append(f"approval missing required verifiers {missing_verifiers}")
        missing_final_panel = sorted(REQUIRED_VERIFIERS - final_panel_ids)
        if missing_final_panel:
            errors.append(
                f"approval final panel missing required verifiers {missing_final_panel}"
            )
        overlap = sorted(set(reviewer_ids) & set(verifier_ids))
        if overlap:
            errors.append(f"approval requires fresh verifiers; overlap {overlap}")
        if conflicts:
            errors.append("approval requires every independence conflict resolved")
        if "BLOCKED" in reviewer_verdicts:
            errors.append(
                "approval requires every reviewer result terminal and unblocked"
            )
        if open_blockers or open_highs:
            errors.append("approval forbids open BLOCKER or HIGH objections")
        if any(
            severity == "BLOCKER" and objection_status == "ACCEPTED_RISK"
            for severity, objection_status in objection_records.values()
        ):
            errors.append("approval forbids accepted BLOCKER objections")
        if unresolved_assumptions:
            errors.append(
                f"approval forbids unresolved assumptions {unresolved_assumptions}"
            )
        if (
            "STILL_OPEN" in final_verification_verdicts
            or "NEW_RISK" in final_verification_verdicts
        ):
            errors.append("approval requires final verification closure")
        if rounds and rounds[-1].get("new_material_objections") != 0:
            errors.append("approval requires zero final new_material_objections")
        if not change_summary:
            errors.append("approval requires decision.change_summary")

    if status == "APPROVED":
        if historical_record_limitations:
            errors.append("APPROVED requires complete raw historical records")
        if experiment_ids:
            errors.append("APPROVED requires every assumption VERIFIED")
        if accepted_highs:
            errors.append("APPROVED forbids accepted HIGH objections")
        if conditions:
            errors.append("APPROVED cannot contain decision-owner conditions")

    if status == "APPROVED_WITH_CONDITIONS":
        if not (conditions or accepted_risks or experiment_ids):
            errors.append("APPROVED_WITH_CONDITIONS requires a concrete condition")
        if (accepted_highs or experiment_ids) and not conditions:
            errors.append("accepted HIGH or planned experiment requires conditions")
        if accepted_highs and not owner_actions:
            errors.append("accepted HIGH requires decision_owner_actions")

    if status == "REVISE" and not (
        open_blockers or open_highs or unresolved_assumptions or material_new_risks
    ):
        errors.append("REVISE requires a material open issue")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to council report JSON")
    return parser.parse_args()


def main() -> int:
    path = parse_args().report
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"ERROR: cannot read report: {error}", file=sys.stderr)
        return 1
    errors = validate_report(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 1
    rounds = len(report.get("rounds", []))
    objections = sum(
        len(item.get("objections", [])) for item in report.get("rounds", [])
    )
    print(f"VALID: {report['status']}, {rounds} round(s), {objections} objection(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
