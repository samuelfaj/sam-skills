#!/usr/bin/env python3
"""Create or refresh task-report.json from the real child report files.

Derives request, target, plan block, the plan/refine/work phase records
(status, heads, sha256 fingerprints, validator receipts; refine arguments from
validator-args.json beside the refine report or --refine-arg), and every closure
iteration's head, statuses, profile, and receipts from its cited review and
council reports. Closure and learn phase records mirror the closure and
learning objects (a recorded learning write is kept, never reset). Values it
cannot derive stay "SCAFFOLD: ..." strings, which validate_task_report.py
rejects. Prints one summary line.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "validate_task_report", SCRIPT_DIR / "validate_task_report.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load validate_task_report.py")
V = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(V)

PLAN_VALIDATOR = V.SKILLS_ROOT / "sam-plan" / "scripts" / "validate_plan_report.py"
REFINE_VALIDATOR = V.SKILLS_ROOT / "sam-refine-task" / "scripts" / "validate_report.py"


def fill(what: str) -> str:
    return f"{V.PLACEHOLDER} {what}"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"FAIL: {path} root must be an object")
    return value


def canonical(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def args_beside(report: Path) -> list[str] | None:
    """Validator arguments a phase worker left in validator-args.json beside its report."""
    path = report.parent / "validator-args.json"
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"FAIL: {path} must be a JSON array of strings")
    return value


def run(script: Path, args: list[str], report: Path, cwd: str | None = None) -> str:
    if not script.is_file():
        return fill(f"validator missing at {script}")
    return V.run_script(script, args, report, cwd)[1]


def iteration(
    sequence: int,
    input_fp: str,
    output_fp: str,
    status: Any,
    evidence: str,
    open_items: list[str] | None = None,
    corrections: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "input_fingerprint": input_fp,
        "output_fingerprint": output_fp,
        "status": status,
        "open_required_items": open_items or [],
        "correction_receipts": corrections or [],
        "evidence": [evidence],
    }


def upsert_last(phase: dict[str, Any], entry: dict[str, Any]) -> None:
    """Replace the last iteration when its output matches, else append one."""
    iterations = phase.setdefault("iterations", [])
    if iterations and iterations[-1].get("output_fingerprint") == entry["output_fingerprint"]:
        entry["sequence"] = iterations[-1]["sequence"]
        entry["correction_receipts"] = iterations[-1].get("correction_receipts", [])
        iterations[-1] = entry
        return
    if iterations and not iterations[-1].get("correction_receipts"):
        iterations[-1]["correction_receipts"] = (
            [fill("name the correction for each open item")]
            if iterations[-1].get("open_required_items")
            else ["superseded by a later child report"]
        )
    entry["sequence"] = len(iterations) + 1
    iterations.append(entry)


def phase_record(report: dict[str, Any], phase_id: str, skill: str) -> dict[str, Any]:
    phases = report.setdefault("phases", [])
    for phase in phases:
        if phase.get("id") == phase_id:
            return phase
    phase = {
        "id": phase_id,
        "skill": skill,
        "status": fill("phase status"),
        "current": True,
        "validated_head_sha": None,
        "evidence": [],
        "validator_receipts": [],
        "iterations": [],
    }
    phases.append(phase)
    return phase


def set_receipt(phase: dict[str, Any], receipt: str) -> None:
    receipts = [r for r in phase.get("validator_receipts", []) if not str(r).startswith(V.PLACEHOLDER)]
    if not receipts or receipts[-1] != receipt:
        receipts.append(receipt)
    phase["validator_receipts"] = receipts


def derive_closure(report: dict[str, Any], work: dict[str, Any], final_head: Any) -> None:
    closure = report.setdefault("closure", {})
    closure.setdefault("max_iterations", 5)
    iterations = closure.setdefault("iterations", [])
    work_review = next(
        (p for p in work.get("phases", []) if isinstance(p, dict) and p.get("id") == "review"), {}
    )
    for index, item in enumerate(iterations, start=1):
        item["sequence"] = index
        for key in ("open_findings", "correction_receipts"):
            item.setdefault(key, [])
        item.setdefault("evidence", [fill("closure iteration evidence")])
        review_path = item.get("review_reused_from") or item.get("review_report_path")
        if review_path and Path(review_path).is_file():
            # A superseded iteration keeps what was derived while it was current;
            # its cited file must never change afterwards.
            digest = V.sha256_file(Path(review_path))
            pinned = item.get("review_report_sha256")
            if index < len(iterations) and pinned:
                if pinned != digest:
                    raise SystemExit(
                        f"FAIL: closure iteration {index} cites {review_path}, which changed "
                        "after it was recorded; write every review run to a new path"
                    )
                continue
            item["review_report_sha256"] = digest
            review = load(Path(review_path))
            item["head_sha"] = (review.get("target") or {}).get("head_sha")
            item["review_status"] = V._decision(review)
            if item.get("review_reused_from"):
                item["review_report_path"] = None
                receipts = work_review.get("validator_receipts") or [fill("sam-work review receipt")]
                item["review_receipt"] = receipts[-1]
            else:
                if not item.get("review_validator_args"):
                    item["review_validator_args"] = args_beside(Path(review_path)) or []
                args = [str(a) for a in item["review_validator_args"]]
                item["review_reused_from"] = None
                item["review_receipt"] = run(
                    V.SKILLS_ROOT / "sam-review" / "scripts" / "validate_review.py",
                    args,
                    Path(review_path),
                )
        council_path = item.get("council_report_path")
        if council_path and Path(council_path).is_file():
            council = load(Path(council_path))
            item["council_status"] = council.get("status")
            item["council_profile"] = council.get("profile")
            item["council_receipt"] = run(
                V.SKILLS_ROOT / "sam-council" / "scripts" / "validate_council_report.py",
                [],
                Path(council_path),
                V.repo_cwd(work.get("target") or {}),
            )
        elif not council_path:
            item.update(
                council_status=V.COUNCIL_NOT_RUN,
                council_profile=None,
                council_receipt=None,
                council_report_path=None,
            )
    closure["iterations_used"] = len(iterations)
    last = iterations[-1] if iterations else {}
    clean = (
        bool(last)
        and last.get("review_status") == "APPROVE"
        and last.get("council_status") in V.COUNCIL_PASS
        and not last.get("open_findings")
        and last.get("head_sha") == final_head
    )
    if clean:
        closure["final_status"] = "CLEAN"
    elif closure.get("final_status") not in {"OPEN", "BLOCKED"}:
        closure["final_status"] = "OPEN"

    phase = phase_record(report, "closure", "sam-review+sam-council")
    mirrored = []
    for item in iterations:
        is_clean = item is last and clean
        review_path = item.get("review_reused_from") or item.get("review_report_path")
        input_fp = (
            V.sha256_file(Path(review_path))
            if review_path and Path(review_path).is_file()
            else canonical({"head_sha": item.get("head_sha")})
        )
        status = "CLEAN" if is_clean else ("BLOCKED" if item is last and closure["final_status"] == "BLOCKED" else "OPEN")
        mirrored.append(
            iteration(
                item["sequence"],
                input_fp,
                canonical(item),
                status,
                f"closure iteration {item['sequence']} at {str(item.get('head_sha'))[:12]}",
                list(item.get("open_findings", [])),
                list(item.get("correction_receipts", [])),
            )
        )
    phase["iterations"] = mirrored or phase.get("iterations", [])
    if mirrored:
        phase["status"] = mirrored[-1]["status"]
        phase["validated_head_sha"] = last.get("head_sha")
        phase["evidence"] = [f"{len(mirrored)} closure iteration(s)"]
        receipts = [str(last.get("review_receipt"))]
        if last.get("council_receipt"):
            receipts.append(str(last["council_receipt"]))
        phase["validator_receipts"] = receipts


def derive_learning(report: dict[str, Any], work_file: Path, final_head: Any) -> None:
    learning = report.setdefault("learning", {})
    learning.setdefault("status", fill("LEARNING_AUDITED or BLOCKED"))
    learning["write_policy"] = "PROPOSAL_ONLY"
    learning["audited_head_sha"] = final_head
    learning.setdefault("candidates", [])
    # Never reset: a recorded write must stay visible so the validator rejects it.
    writes = learning.setdefault("writes_performed", [])
    learning.setdefault("evidence", [fill("learning audit receipt")])
    count = len(writes) if isinstance(writes, list) else "?"
    receipt = (
        "PROPOSAL_ONLY: writes_performed is empty"
        if writes == []
        else f"PROPOSAL_ONLY VIOLATED: writes_performed lists {count} write(s)"
    )
    phase = phase_record(report, "learn", "sam-task")
    phase.update(
        {
            "status": learning["status"],
            "validated_head_sha": final_head,
            "evidence": [f"{len(learning['candidates'])} proposal-only candidate(s)"],
            "validator_receipts": [receipt],
            "iterations": [
                iteration(
                    1,
                    V.sha256_file(work_file),
                    canonical(learning),
                    learning["status"],
                    "learning audit on the final head",
                )
            ],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report", help="task-report.json to create or refresh")
    parser.add_argument("--freeze", required=True, help="absolute plan-report.json")
    parser.add_argument("--refine", required=True, help="absolute durable refine report")
    parser.add_argument("--work", required=True, help="absolute work-report.json")
    parser.add_argument("--workflow-id")
    parser.add_argument("--web-surface", choices=["true", "false"])
    parser.add_argument("--web-surface-evidence", action="append")
    parser.add_argument(
        "--refine-arg",
        action="append",
        help="refine validator argument before the report (repeat; use --refine-arg=--flag); "
        "default: validator-args.json beside the refine report",
    )
    args = parser.parse_args()

    out = Path(args.report)
    report = load(out) if out.is_file() else {}
    freeze_file, refine_file, work_file = (Path(p).resolve() for p in (args.freeze, args.refine, args.work))
    freeze, refine, work = load(freeze_file), load(refine_file), load(work_file)
    frozen = freeze.get("frozen") if isinstance(freeze.get("frozen"), dict) else {}
    work_target = work.get("target") if isinstance(work.get("target"), dict) else {}
    final_head = work_target.get("final_head_sha")

    report["schema_version"] = 3
    report["workflow"] = "task"
    report["workflow_id"] = args.workflow_id or report.get("workflow_id") or fill("stable workflow id")
    report.setdefault("status", "IN_PROGRESS")
    request = report.setdefault("request", {})
    request["prompt_sha256"] = frozen.get("prompt_hash")
    request["prompt_summary"] = request.get("prompt_summary") or frozen.get("goal") or fill("short summary")
    request["classification"] = (work.get("request") or {}).get("classification")

    target = report.setdefault("target", {})
    for key in ("repo_root", "base_ref", "base_sha", "final_head_sha", "final_change_fingerprint"):
        target[key] = work_target.get(key)
    if args.web_surface:
        target["web_surface"] = args.web_surface == "true"
    target.setdefault("web_surface", fill("true or false from repo evidence"))
    if args.web_surface_evidence:
        target["web_surface_evidence"] = list(args.web_surface_evidence)
    target.setdefault("web_surface_evidence", [fill("repo evidence for web_surface")])

    plan_receipt = run(PLAN_VALIDATOR, [], freeze_file)
    report["plan"] = {
        "plan_dir": str(freeze_file.parent),
        "depth": freeze.get("depth"),
        "status": freeze.get("status"),
        "validator_receipt": plan_receipt,
        "freeze_path": str(freeze_file),
    }
    report["refine_report_path"] = str(refine_file)
    report["work_report_path"] = str(work_file)

    freeze_fp, refine_fp, work_fp = (V.sha256_file(p) for p in (freeze_file, refine_file, work_file))
    plan_phase = phase_record(report, "plan", "sam-plan")
    upsert_last(plan_phase, iteration(0, str(request["prompt_sha256"]), freeze_fp, freeze.get("status"), f"freeze {freeze_file}"))
    plan_phase.update(status=freeze.get("status"), validated_head_sha=None, current=True, evidence=[f"freeze {freeze_file}"])
    set_receipt(plan_phase, plan_receipt)

    decision = refine.get("decision") if isinstance(refine.get("decision"), dict) else {}
    refine_phase = phase_record(report, "refine", "sam-refine-task")
    remaining = [str(r) for r in decision.get("remaining") or []]
    upsert_last(refine_phase, iteration(0, freeze_fp, refine_fp, decision.get("result"), f"refine report {refine_file}", remaining))
    refine_phase.update(status=decision.get("result"), validated_head_sha=None, current=True, evidence=[f"refine report {refine_file}"])
    known = report.get("refine_validator_args")
    refine_args = list(args.refine_arg or []) or args_beside(refine_file) or (
        known if isinstance(known, list) else None
    )
    if refine_args:
        report["refine_validator_args"] = refine_args
        set_receipt(refine_phase, run(REFINE_VALIDATOR, refine_args, refine_file))
    else:
        report["refine_validator_args"] = fill("validator-args.json beside the refine report, or --refine-arg")
        refine_phase["validator_receipts"] = [fill("sam-refine-task validator line")]

    work_phase = phase_record(report, "work", "sam-work")
    work_status = (work.get("final") or {}).get("result")
    work_receipt = run(V.SKILLS_ROOT / "sam-work" / "scripts" / "validate_work_report.py", [], work_file)
    upsert_last(work_phase, iteration(0, refine_fp, work_fp, work_status, f"work report {work_file}"))
    work_phase.update(status=work_status, validated_head_sha=final_head, current=True, evidence=[f"work report {work_file}"])
    set_receipt(work_phase, work_receipt)

    derive_closure(report, work, final_head)
    derive_learning(report, work_file, final_head)
    order = {phase_id: index for index, phase_id in enumerate(V.PHASE_IDS)}
    report["phases"].sort(key=lambda p: order.get(p.get("id"), 99))
    report.setdefault("advisor_consults", [])
    report.setdefault("residuals", [])
    report.setdefault("blockers", [])

    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    placeholders: list[str] = []
    V.find_placeholders(report, "", placeholders)
    print(
        f"scaffolded {out} head={str(final_head)[:12]} work={work_status} "
        f"closure={report['closure'].get('final_status')} placeholders={len(placeholders)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
