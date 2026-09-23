#!/usr/bin/env python3
"""Scaffold and finalize a sam-council report.

init      after the packet is frozen: report reuse of an identical VALID packet,
          or write the report skeleton (constants, runtime, seats, placeholders).
          The head comes from the --repo work tree (default: cwd; required with
          --reuse-dir or --base-report). Reuse needs a clean work tree; a dirty
          one, or a run outside any repository, records no fingerprint, so its
          report is never reused. Runtime flags describe the first provider;
          other providers' runtimes stay placeholders until filled.
finalize  derive reviewer/verifier IDs, the minimum batch plan, the final thesis
          ID (thesis.id when a BLOCKED report has no rounds), and the decision
          ledgers from the authored rounds; then validate inside --repo (default:
          cwd), where the DELTA ancestry check runs. A DELTA report requires a
          --repo that holds its and its base's packet_head.

Placeholders (`TODO`, empty values, zero capacity, a seat prefix with no
reason) fail validation until replaced.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_council_report.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT_DIR))
from validate_council_report import (  # noqa: E402
    COMMIT_SHA,
    PASSING_STATUSES,
    THESIS_ID,
    packet_fingerprint,
)
PROVIDER_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FAST_REVIEWERS = ["frame-evidence", "delivery-failure", "simplification"]
FULL_REVIEWERS = [
    "logic",
    "assumptions",
    "execution",
    "adversarial",
    "alternatives",
    "problem-frame",
]
CONDITIONAL = [
    "security-privacy",
    "data-migration",
    "reliability-performance",
    "api-compatibility",
    "testability-release",
    "operations-observability",
    "cost-dependency",
    "product-ux",
    "compliance-governance",
]
THESIS_LISTS = (
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
)
TODO = "TODO"


def validate(path: Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    # The validator checks DELTA ancestry in its working directory's repository.
    return subprocess.run(
        [sys.executable, "-B", str(VALIDATOR), str(path)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def git(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def find_reuse(directory: Path, value: str, repo: Path) -> tuple[Path, str] | None:
    """Return (report, validator line) for a VALID non-BLOCKED match.

    The validator recomputes each candidate's fingerprint from its packet file,
    so a typed fingerprint without the identical packet never matches.
    """
    for candidate in sorted(directory.rglob("*.json")):
        try:
            report = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            not isinstance(report, dict)
            or report.get("packet_fingerprint") != value
            or report.get("status") == "BLOCKED"
        ):
            continue
        result = validate(candidate, repo)
        if result.returncode == 0:
            return candidate, result.stdout.strip().splitlines()[-1]
    return None


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 2


def cmd_init(args: argparse.Namespace) -> int:
    providers: list[str] = args.provider
    invalid = [item for item in providers if not PROVIDER_ID.fullmatch(item)]
    if invalid:
        return fail(f"invalid provider slug(s) {invalid}")
    if len(set(providers)) != len(providers):
        return fail("duplicate --provider")
    mode = "multi-provider" if len(providers) > 1 else "single-host"
    if mode == "multi-provider" and args.profile != "full":
        return fail("multi-provider requires --profile full")
    selected = list(dict.fromkeys(args.select or []))
    if selected and args.profile != "full":
        return fail("--select is full-only; a fast seat records ESCALATE instead")
    if args.max_parallel < 1:
        return fail("--max-parallel must be positive")
    out = Path(args.out).resolve()
    packet_path = Path(args.packet).resolve()
    try:
        packet = packet_path.read_bytes()
    except OSError as error:
        return fail(f"cannot read --packet: {error}")
    if args.repo is None and (args.reuse_dir or args.base_report):
        return fail("--repo is required with --reuse-dir or --base-report")
    repo = Path(args.repo or ".").resolve()
    repo_head = git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    if repo_head is None:
        head = args.head or "none"
        if head != "none" and not COMMIT_SHA.fullmatch(head):
            return fail("--head outside a repository must be a full commit SHA")
    elif args.head is None:
        head = repo_head
    elif git(repo, "rev-parse", "--verify", f"{args.head}^{{commit}}") != repo_head:
        return fail(f"--head must be the checked-out HEAD of {repo} ({repo_head})")
    else:
        head = repo_head
    dirty = repo_head is not None and git(repo, "status", "--porcelain") != ""
    value = (
        None
        if dirty or repo_head is None
        else packet_fingerprint(args.profile, providers, head, packet)
    )
    base: dict[str, Any] = {}
    if args.base_report:
        base_path = Path(args.base_report).resolve()
        try:
            base = json.loads(base_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            return fail(f"cannot read --base-report: {error}")
        if dirty or repo_head is None:
            return fail("a DELTA packet needs a clean git work tree")
        checked = validate(base_path, repo)
        if checked.returncode != 0:
            return fail(f"--base-report is not VALID: {checked.stderr.strip()[-300:]}")
        if (
            base.get("status") not in PASSING_STATUSES
            or base.get("profile") != args.profile
        ):
            return fail("--base-report must pass and share --profile; else use FULL")
        base_head = base.get("packet_head")
        if not isinstance(base_head, str) or not COMMIT_SHA.fullmatch(base_head):
            return fail("--base-report has no commit packet_head; use a FULL packet")
        if base_head == head:
            return fail("--base-report is on this head; reuse it instead of a DELTA")
    if args.reuse_dir and value is not None and repo_head is not None:
        prior = find_reuse(Path(args.reuse_dir), value, repo)
        if prior is not None:
            print(f"REUSE {prior[0].resolve()} fingerprint={value} validator: {prior[1]}")
            return 0
    if out.exists() and not args.force:
        return fail(f"{out} exists; finalize it or pass --force")

    seats = (FAST_REVIEWERS if args.profile == "fast" else FULL_REVIEWERS) + selected
    multi = mode == "multi-provider"
    reviewer_ids = (
        [f"{provider}/{seat}" for provider in providers for seat in seats]
        if multi
        else seats
    )
    if args.profile == "fast":
        verifiers = ["triage-arbiter"]
    else:
        verifiers = [
            "closure-verifier",
            "system-verifier",
            "meta-arbiter" if multi else "arbiter",
        ]
    runtime = {
        "adapter": args.adapter,
        "model": args.model,
        "reviewer_effort": args.reviewer_effort,
        "arbiter_effort": args.arbiter_effort,
        "max_parallel_workers": args.max_parallel,
    }
    prefixes = "ESCALATE|NOT_APPLICABLE" if args.profile == "fast" else "NOT_APPLICABLE"
    report: dict[str, Any] = {
        "schema_version": 2,
        "profile": args.profile,
        "status": TODO,
        "packet_path": str(packet_path),
        "packet_head": head,
        **({"packet_fingerprint": value} if value is not None else {}),
        "packet_scope": "DELTA" if args.base_report else "FULL",
        **({"base_report": str(Path(args.base_report).resolve())} if args.base_report else {}),
        "execution_policy": {
            "default_round_limit": 1,
            "hard_round_limit": 1 if args.profile == "fast" else 3,
            "continuation_authorized": False,
            "max_objections_per_reviewer": 3,
            "max_response_words": 1000,
            "packet_strategy": "RELEVANT_ONLY",
            "parallelism": "MAX_AVAILABLE",
            "initial_effort": "medium",
            "arbiter_effort": "high",
        },
        "thesis": {
            "id": TODO,
            "objective": base["thesis"]["objective"] if base else "",
            "problem_frame": "",
            **{field: [] for field in THESIS_LISTS},
            "assumptions": [],
        },
        "evidence": [],
        "independence": {
            "mode": mode,
            "providers": providers,
            "provider_runtimes": {
                provider: dict(runtime)
                if index == 0
                # Empty adapter/model and zero capacity fail the validator; a
                # literal TODO or the controller's capacity would validate as a
                # recorded runtime.
                else {
                    **{key: TODO for key in runtime},
                    "adapter": "",
                    "model": "",
                    "max_parallel_workers": 0,
                }
                for index, provider in enumerate(providers)
            },
            "blind_first_pass": True,
            "reviewers_saw_peer_reviews_before_submission": False,
            "reviewer_ids": [],
            "verifier_ids": [],
            # Prefix only: the empty reason fails validation until a
            # system-specific reason is written.
            "conditional_seat_selection": {
                seat: f"{'SELECTED' if seat in selected else prefixes}: "
                for seat in CONDITIONAL
            },
            "batch_plan": [],
            "conflicts": [],
        },
        "confrontation": (
            {
                "provider_positions": [
                    {
                        "provider": provider,
                        "stance": TODO,
                        "material_objection_ids": [],
                        "preferred_correction": "",
                    }
                    for provider in providers
                ],
                "disagreements": [],
                "resolution": "EVIDENCE_WEIGHTED",
                "surviving_claim_ids": [],
                "rejected_claim_summaries": [],
                "rationale": "",
            }
            if multi
            else None
        ),
        "rounds": [
            {
                "number": 1,
                "input_thesis_id": (
                    base["decision"]["final_thesis_id"] if base else "T-001"
                ),
                "output_thesis_id": TODO,
                "reviewer_ids": reviewer_ids,
                "reviewer_results": [
                    {
                        "reviewer_id": reviewer_id,
                        **({"provider": reviewer_id.split("/", 1)[0]} if multi else {}),
                        "verdict": TODO,
                        "search_summary": "",
                        "disconfirming_evidence": "",
                        "residual_uncertainty": "",
                    }
                    for reviewer_id in reviewer_ids
                ],
                "objections": [],
                "verification": [
                    {
                        "verifier_id": verifier_id,
                        "verdict": TODO,
                        "objection_ids": [],
                        "rationale": "",
                    }
                    for verifier_id in verifiers
                ],
                "new_material_objections": 0,
            }
        ],
        "decision": {
            "final_thesis_id": "",
            "confidence": None,
            "basis": "EVIDENCE_AND_RISK",
            "rationale": "",
            "open_blocker_ids": [],
            "open_high_ids": [],
            "conditions": [],
            "accepted_risk_ids": [],
            "required_experiment_ids": [],
            "change_summary": [],
            "decision_owner_actions": [],
        },
        "historical_record_limitations": [],
        "blockers": [],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"INIT {out} profile={args.profile} mode={mode} head={head} "
        f"reviewers={len(reviewer_ids)} verifiers={len(verifiers)} "
        f"fingerprint={value or 'n/a (dirty or non-git work tree: never reused)'}"
    )
    return 0


def strings(values: Any) -> list[str]:
    return [item for item in values if isinstance(item, str)] if isinstance(values, list) else []


def derive(report: dict[str, Any]) -> None:
    independence = report.setdefault("independence", {})
    providers = strings(independence.get("providers"))
    runtimes = independence.get("provider_runtimes") or {}
    multi = independence.get("mode") == "multi-provider"
    rounds = [item for item in report.get("rounds") or [] if isinstance(item, dict)]
    reviewer_ids: list[str] = []
    verifier_ids: list[str] = []
    plan: list[dict[str, Any]] = []

    def schedule(number: int, phase: str, provider: str, seats: list[str]) -> None:
        runtime = runtimes.get(provider) if isinstance(runtimes, dict) else None
        size = runtime.get("max_parallel_workers") if isinstance(runtime, dict) else None
        size = size if isinstance(size, int) and size > 0 else 1
        for start in range(0, len(seats), size):
            plan.append(
                {
                    "round": number,
                    "phase": phase,
                    "provider": provider,
                    "seat_ids": seats[start : start + size],
                }
            )

    for number, round_item in enumerate(rounds, 1):
        seats = list(dict.fromkeys(strings(round_item.get("reviewer_ids"))))
        verifiers = list(
            dict.fromkeys(
                item.get("verifier_id")
                for item in round_item.get("verification") or []
                if isinstance(item, dict) and isinstance(item.get("verifier_id"), str)
            )
        )
        reviewer_ids.extend(seat for seat in seats if seat not in reviewer_ids)
        verifier_ids.extend(item for item in verifiers if item not in verifier_ids)
        if not providers:
            continue
        for provider in providers:
            group = [
                seat
                for seat in seats
                if (seat.split("/", 1)[0] if multi and "/" in seat else providers[0])
                == provider
            ]
            if group:
                schedule(number, "blind", provider, group)
        if verifiers:
            schedule(number, "verification", providers[0], verifiers)
    independence["reviewer_ids"] = reviewer_ids
    independence["verifier_ids"] = verifier_ids
    independence["batch_plan"] = plan

    records = [
        (item.get("id"), item.get("severity"), item.get("status"))
        for round_item in rounds
        for item in round_item.get("objections") or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    assumptions = (report.get("thesis") or {}).get("assumptions") or []
    decision = report.setdefault("decision", {})
    decision["open_blocker_ids"] = sorted(
        oid for oid, severity, status in records if severity == "BLOCKER" and status == "OPEN"
    )
    decision["open_high_ids"] = sorted(
        oid for oid, severity, status in records if severity == "HIGH" and status == "OPEN"
    )
    decision["accepted_risk_ids"] = sorted(
        oid for oid, _, status in records if status == "ACCEPTED_RISK"
    )
    decision["required_experiment_ids"] = sorted(
        item["id"]
        for item in assumptions
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("state") == "EXPERIMENT_PLANNED"
    )
    if rounds:
        decision["final_thesis_id"] = rounds[-1].get("output_thesis_id", "")
    else:
        # A report BLOCKED before dispatch has no rounds; its thesis is final.
        thesis_id = (report.get("thesis") or {}).get("id")
        if isinstance(thesis_id, str) and THESIS_ID.fullmatch(thesis_id):
            decision["final_thesis_id"] = thesis_id


def cmd_finalize(args: argparse.Namespace) -> int:
    path = Path(args.report).resolve()
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return fail(f"cannot read report: {error}")
    if not isinstance(report, dict):
        return fail("report must be a JSON object")
    repo = Path(args.repo).resolve() if args.repo else None
    if repo is not None and not repo.is_dir():
        return fail(f"--repo is not a directory: {repo}")
    if report.get("packet_scope") == "DELTA":
        # Outside a repository that knows both heads the ancestry check passes
        # silently, so a DELTA needs the target repository explicitly.
        heads = [report.get("packet_head")]
        base_text = report.get("base_report")
        try:
            base = json.loads((path.parent / str(base_text)).read_text(encoding="utf-8"))
            heads.append(base.get("packet_head") if isinstance(base, dict) else None)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass  # the validator reports an unreadable base_report
        if repo is None or any(
            not isinstance(head, str) or git(repo, "cat-file", "-e", f"{head}^{{commit}}") is None
            for head in heads
        ):
            return fail("a DELTA report needs --repo <target repo> holding both packet_heads")
    derive(report)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    result = validate(path, repo)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="write the skeleton or report reuse")
    init.add_argument("--out", required=True, help="report path to write")
    init.add_argument("--packet", required=True, help="frozen packet file")
    init.add_argument("--profile", required=True, choices=("fast", "full"))
    init.add_argument(
        "--provider",
        required=True,
        action="append",
        help="provider slug; repeat for multi-provider, controller's provider first",
    )
    init.add_argument("--max-parallel", required=True, type=int)
    init.add_argument(
        "--repo", help="target git work tree (default: cwd; required with --reuse-dir/--base-report)"
    )
    init.add_argument(
        "--head", help="checked-out HEAD of --repo (derived if omitted), else a full SHA"
    )
    init.add_argument("--adapter", default="host-native-workers")
    init.add_argument("--model", required=True, help="host-reported model label, or host-default")
    init.add_argument("--reviewer-effort", required=True, choices=("medium", "host-default"))
    init.add_argument("--arbiter-effort", required=True, choices=("high", "host-default"))
    init.add_argument("--select", action="append", choices=CONDITIONAL, help="full-only specialist")
    init.add_argument("--base-report", help="prior passing report; marks a DELTA packet")
    init.add_argument("--reuse-dir", help="scan for a VALID report with this fingerprint")
    init.add_argument("--force", action="store_true", help="overwrite an existing --out")
    init.set_defaults(handler=cmd_init)
    finalize = commands.add_parser("finalize", help="derive mechanical fields, then validate")
    finalize.add_argument("report")
    finalize.add_argument(
        "--repo", help="target git work tree for the DELTA ancestry check (required for DELTA)"
    )
    finalize.set_defaults(handler=cmd_finalize)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
