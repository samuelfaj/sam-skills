#!/usr/bin/env python3
"""Scaffold work-report.json from real files instead of typed values.

init      write a skeleton: constants, target from git, fail-closed placeholders.
record    re-run one phase's child validator (arguments from --validator-arg or
          validator-args.json beside the report) and record the report as the
          phase's latest iteration (head, status, fingerprints, receipt).
finalize  recompute the final head and change fingerprint from git; for
          implementation/refine/simplify find the commit holding the child's
          captured delta (committed_head_sha) and carry it forward only across
          test-only deltas; mark other off-head phases stale; hash local videos.

Every command prints one summary line. Values it cannot derive stay as
"SCAFFOLD: ..." strings, which validate_work_report.py rejects.
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
    "validate_work_report", SCRIPT_DIR / "validate_work_report.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load validate_work_report.py")
V = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(V)

AUTHORIZATION = {
    "create_or_update_proposal": True,
    "publish_playwright_videos": True,
    "publish_demo_video": True,
    "merge": False,
    "deploy": False,
}


def fill(what: str) -> str:
    return f"{V.PLACEHOLDER} {what}"


def load(path: Path) -> dict[str, Any]:
    return V.load_json(path)


def save(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def git_out(repo: str, *args: str) -> str:
    result = V.git(repo, *args)
    if result.returncode != 0:
        detail = (result.stderr.strip().splitlines() or ["git failed"])[-1]
        raise SystemExit(f"FAIL: git {' '.join(args)}: {detail}")
    return result.stdout


def change_fingerprint(repo: str, base_sha: str, head_sha: str) -> str:
    fingerprint = V.change_fingerprint(repo, base_sha, head_sha)
    if fingerprint is None:
        raise SystemExit(f"FAIL: git diff {base_sha}..{head_sha} failed")
    return fingerprint


def phase_skill(phase_id: str, classification: str) -> str:
    if phase_id == "implementation":
        return "sam-fix-bug" if classification == "BUG" else "sam-create-feature"
    return V.FIXED_SKILLS[phase_id]


def environment() -> dict[str, Any]:
    return {
        "kind": "DEVELOPMENT",
        "identity_verified": fill("true after identity check"),
        "identity_evidence": [fill("effective host, database or tenant identity")],
        "real_data": fill("true only for verified real development data"),
        "dedicated_data": fill("true only for dedicated, non-shared task data"),
        "cleanup_status": fill("COMPLETE after cleanup receipt"),
        "privacy_review": fill("PASS after redaction review"),
    }


def cmd_init(args: argparse.Namespace) -> int:
    repo = str(Path(args.repo).resolve())
    base_sha = args.base_sha or git_out(repo, "rev-parse", args.base_ref).strip()
    head = git_out(repo, "rev-parse", "HEAD").strip()
    web = args.web_system == "true"
    fingerprint = change_fingerprint(repo, base_sha, head)
    phases = []
    for phase_id in V.PHASE_IDS:
        not_applicable = phase_id == "playwright" and not web
        phases.append(
            {
                "id": phase_id,
                "skill": phase_skill(phase_id, args.classification),
                "applicability": "NOT_APPLICABLE" if not_applicable else "REQUIRED",
                "status": "NOT_APPLICABLE" if not_applicable else fill("run phase"),
                "current": not_applicable,
                "validated_head_sha": head if not_applicable else None,
                "not_applicable_reason": fill("repository/runtime evidence of no browser surface")
                if not_applicable
                else None,
                "report_path": None,
                "validator_args": [],
                "carried_forward_from": None,
                "committed_head_sha": None,
                "evidence": [fill("non-web evidence")] if not_applicable else [],
                "validator_receipts": [fill("applicability decision")] if not_applicable else [],
                "iterations": [
                    {
                        "sequence": 1,
                        "input_fingerprint": fingerprint,
                        "output_fingerprint": fingerprint,
                        "status": "NOT_APPLICABLE",
                        "open_required_items": [],
                        "correction_receipts": [],
                        "evidence": [fill("applicability evidence")],
                    }
                ]
                if not_applicable
                else [],
            }
        )
    report = {
        "schema_version": 2,
        "workflow_id": args.workflow_id,
        "request": {
            "prompt_sha256": args.prompt_sha256,
            "classification": args.classification,
            "web_system": web,
            "classification_evidence": [fill("expected behavior and observed break, or new capability")],
        },
        "authorization": dict(AUTHORIZATION),
        "target": {
            "repo_root": repo,
            "base_ref": args.base_ref,
            "base_sha": base_sha,
            "final_head_sha": head,
            "final_change_fingerprint": fingerprint,
        },
        "phases": phases,
        "proposal": {
            "platform": fill("host name or adapter"),
            "url": fill("https proposal URL"),
            "proposal_id": fill("platform ID"),
            "created_by_workflow": fill("true if created, false if an existing proposal was updated"),
            "description_validated": fill("true after the description validator passed"),
            "description_receipt": fill("sam-pr-description validator line"),
            "remote_head_sha": fill("read back remote head"),
            "rendered_readback_evidence": [fill("description and player readback")],
            "required_ci_status": fill("PASS or NOT_CONFIGURED"),
        },
        "environments": {"demo": environment(), "playwright": environment() if web else None},
        "video_inventory": {
            "playwright_discovered": 0,
            "playwright_uploaded": 0,
            "demo_discovered": 0,
            "demo_uploaded": 0,
        },
        "artifacts": [],
        "final": {
            "result": "IN_PROGRESS",
            "completed_phase_ids": list(V.PHASE_IDS),
            "blockers": [],
            "final_head_sha": head,
            "final_change_fingerprint": fingerprint,
        },
    }
    out = Path(args.out)
    save(out, report)
    print(f"initialized {out} head={head[:12]} base={base_sha[:12]} web={str(web).lower()}")
    return 0


def open_items(child: dict[str, Any]) -> list[str] | None:
    for keys in (
        ("decision", "remaining_corrections"),
        ("decision", "remaining"),
        ("open_required_items",),
    ):
        value = V.nested(child, *keys)
        if isinstance(value, list):
            return [str(item) for item in value]
    return None


def cmd_record(args: argparse.Namespace) -> int:
    report_file = Path(args.report)
    report = load(report_file)
    phase_id = args.phase
    phases = {p.get("id"): p for p in report.get("phases", []) if isinstance(p, dict)}
    phase = phases.get(phase_id)
    if phase is None:
        raise SystemExit(f"FAIL: phase {phase_id} is not in {report_file}")
    child_path = Path(args.child).resolve()
    child = load(child_path)
    validator_args = list(args.validator_arg or [])
    args_file = child_path.parent / "validator-args.json"
    if not validator_args and args_file.is_file():
        loaded = json.loads(args_file.read_text(encoding="utf-8"))
        if not isinstance(loaded, list) or not all(isinstance(a, str) for a in loaded):
            raise SystemExit(f"FAIL: {args_file} must be a JSON array of strings")
        validator_args = loaded
    if V.parse_validator_args(validator_args, V.VALIDATOR_FLAGS[phase_id]) is None:
        raise SystemExit(
            f"FAIL: {phase_id} validator arguments must be `--flag <absolute path>` pairs using only "
            f"{', '.join(sorted(V.VALIDATOR_FLAGS[phase_id]))}"
        )
    skill = phase_skill(phase_id, report["request"]["classification"])
    code, receipt = V.run_child_validator(phase_id, skill, validator_args, child_path)
    head = V.child_head(child)
    status = V.child_status(child)
    if status is None:
        status = sorted(V.FINAL_STATUSES[phase_id])[0] if code == 0 else "BLOCKED"
    output_fp = V.sha256_file(child_path)
    input_fp = V.child_input_fingerprint(child) or hashlib.sha256(str(head).encode()).hexdigest()
    items = open_items(child)
    terminal = status in V.FINAL_STATUSES[phase_id]
    if items is None:
        items = [] if terminal else [fill("list open required items")]

    iterations = phase.setdefault("iterations", [])
    if iterations and iterations[-1].get("output_fingerprint") == output_fp:
        entry = iterations[-1]
    else:
        if iterations:
            previous = iterations[-1]
            if not previous.get("correction_receipts"):
                previous["correction_receipts"] = (
                    [fill("name the correction for each open item")]
                    if previous.get("open_required_items")
                    else [f"superseded: re-run at head {str(head)[:12]}"]
                )
        entry = {"sequence": len(iterations) + 1}
        iterations.append(entry)
    entry.update(
        {
            "input_fingerprint": input_fp,
            "output_fingerprint": output_fp,
            "status": status,
            "open_required_items": items,
            "correction_receipts": entry.get("correction_receipts", []),
            "evidence": [f"child report {child_path} head {str(head)[:12]}: {receipt}"],
        }
    )
    receipts = [r for r in phase.get("validator_receipts", []) if not str(r).startswith(V.PLACEHOLDER)]
    if not receipts or receipts[-1] != receipt:
        receipts.append(receipt)
    evidence = [e for e in phase.get("evidence", []) if not str(e).startswith(V.PLACEHOLDER)]
    evidence = [e for e in evidence if not str(e).startswith("child report ")]
    phase.update(
        {
            "applicability": "REQUIRED",
            "not_applicable_reason": None,
            "status": status,
            "current": head == report["target"].get("final_head_sha"),
            "validated_head_sha": head,
            "report_path": str(child_path),
            "validator_args": validator_args,
            "carried_forward_from": None,
            "committed_head_sha": None,
            "evidence": [f"child report {child_path}"] + evidence,
            "validator_receipts": receipts,
        }
    )
    save(report_file, report)
    print(
        f"recorded {phase_id}: {status} head={str(head)[:12]} validator_rc={code} "
        f"open={len(items)} receipt={receipt}"
    )
    return 0 if code == 0 else 1


def derive_anchor(
    phase_id: str, phase: dict[str, Any], child_head: str, repo: str, head: str
) -> tuple[str | None, str | None] | None:
    """(committed_head_sha, carried_forward_from) proving a capture phase for head, or None."""
    flags = V.parse_validator_args(phase.get("validator_args"), V.VALIDATOR_FLAGS[phase_id])
    captures = [
        V.load_capture(flags[flag]) if flags and flag in flags else None
        for flag in ("--baseline", "--current")
    ]
    if None in captures:
        return None
    listing = V.git(repo, "rev-list", "--reverse", "--ancestry-path", f"{child_head}..{head}")
    candidates = [child_head] + (listing.stdout.split() if listing.returncode == 0 else [])
    for candidate in candidates:
        commit = None if candidate == child_head else candidate
        if V.committed_capture_errors("", phase_id, repo, child_head, commit, *captures):
            continue
        if candidate == head:
            return commit, None
        if not V.carry_forward_errors("", repo, candidate, head):
            return commit, candidate
    return None


def cmd_finalize(args: argparse.Namespace) -> int:
    report_file = Path(args.report)
    report = load(report_file)
    target = report["target"]
    repo = target["repo_root"]
    head = git_out(repo, "rev-parse", "HEAD").strip()
    fingerprint = change_fingerprint(repo, target["base_sha"], head)
    target["final_head_sha"] = head
    target["final_change_fingerprint"] = fingerprint
    final = report.setdefault("final", {})
    final.update(
        {
            "completed_phase_ids": list(V.PHASE_IDS),
            "final_head_sha": head,
            "final_change_fingerprint": fingerprint,
        }
    )
    stale: list[str] = []
    carried: list[str] = []
    committed: list[str] = []
    for phase in report.get("phases", []):
        if phase.get("applicability") == "NOT_APPLICABLE":
            phase["validated_head_sha"] = head
            phase["current"] = True
            continue
        path = phase.get("report_path")
        if not path or not Path(path).is_file():
            stale.append(str(phase.get("id")))
            continue
        child_head = V.child_head(load(Path(path)))
        anchor = None
        if phase.get("id") in V.CARRY_FORWARD_PHASES and child_head:
            anchor = derive_anchor(str(phase["id"]), phase, child_head, repo, head)
        elif child_head == head:
            anchor = (None, None)
        if anchor is None:
            phase.update(
                validated_head_sha=child_head,
                current=False,
                committed_head_sha=None,
                carried_forward_from=None,
            )
            stale.append(str(phase.get("id")))
            continue
        phase.update(
            validated_head_sha=head,
            current=True,
            committed_head_sha=anchor[0],
            carried_forward_from=anchor[1],
        )
        if anchor[0]:
            committed.append(str(phase["id"]))
        if anchor[1]:
            carried.append(str(phase["id"]))
    for artifact in report.get("artifacts", []):
        local = Path(str(artifact.get("local_path", "")))
        if local.is_absolute() and local.is_file():
            artifact["sha256"] = V.sha256_file(local)
    save(report_file, report)
    placeholders: list[str] = []
    V.find_placeholders(report, "", placeholders)
    print(
        f"finalized head={head[:12]} fingerprint={fingerprint[:12]} "
        f"stale={','.join(stale) or 'none'} committed={','.join(committed) or 'none'} "
        f"carried={','.join(carried) or 'none'} "
        f"placeholders={len(placeholders)}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--out", required=True)
    init.add_argument("--repo", required=True)
    init.add_argument("--base-ref", required=True)
    init.add_argument("--base-sha")
    init.add_argument("--classification", choices=["BUG", "FEATURE"], required=True)
    init.add_argument("--web-system", choices=["true", "false"], required=True)
    init.add_argument("--prompt-sha256", required=True)
    init.add_argument("--workflow-id", required=True)
    record = sub.add_parser("record")
    record.add_argument("report")
    record.add_argument("--phase", choices=V.PHASE_IDS, required=True)
    record.add_argument("--child", required=True, help="absolute child report path")
    record.add_argument(
        "--validator-arg",
        action="append",
        help="one child-validator argument before the report (repeat; use --validator-arg=--flag); "
        "default: validator-args.json beside the child report",
    )
    finalize = sub.add_parser("finalize")
    finalize.add_argument("report")
    args = parser.parse_args()
    return {"init": cmd_init, "record": cmd_record, "finalize": cmd_finalize}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
