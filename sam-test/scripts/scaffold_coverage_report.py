#!/usr/bin/env python3
"""Scaffold report.json from real files so derived fields are never retyped.

Derived from files: fingerprints, base/head SHAs, command_definitions.changed,
commands[] from run_checked.py receipts (never the discovery or --wiring ids),
test_wiring receipt paths, and the test-diff audit recomputed from the final
bundle. Agent-owned fields start empty so the validator fails closed until they
are filled. With --previous, the prior report's ledger is carried forward and
derived fields and the decision are refreshed. When the head or bundle
fingerprint differs from --previous, only the ledger survives: proof, each
test's regression proof, environment evidence, artifacts, command-definition
inspection, wiring (without --wiring) and audit disproofs reset, and a receipts
dir holding the previous report's receipts is refused. The before-change
discovery receipt (CMD-900) missing from --receipts-dir is taken from
--previous or the lowest earlier receipts-<n> sibling, and is cited as
test_wiring.before_receipt even without --wiring. A receipts dir no cleanup
entry names gets a RETAINED entry.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_test_diff import audit as audit_patch  # noqa: E402

LEDGERS = ("criteria", "behaviors", "risks", "scenarios", "tests", "artifacts", "cleanup")
PROOF_FIELD = "real_system_proof"
PROOF_DEFAULT = {"status": "", "evidence": "", "reason": ""}
# Runner discovery listings are wiring evidence, never test commands.
DISCOVERY_IDS = ("CMD-900", "CMD-901")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def receipts_number(directory: Path) -> int | None:
    name = directory.name
    suffix = name[len("receipts-"):] if name.startswith("receipts-") else ""
    return int(suffix) if suffix.isdigit() else None


def earlier_receipt(command_id: str, prior: Any, receipts_dir: Path) -> str | None:
    """Return command_id's receipt from the previous report, else from the
    lowest-numbered receipts-<n> sibling older than receipts_dir."""
    candidates = [Path(str(prior))] if prior else []
    current = receipts_number(receipts_dir)
    if current is not None:
        siblings = []
        for path in receipts_dir.parent.glob(f"receipts-*/{command_id}.receipt.json"):
            number = receipts_number(path.parent)
            if number is not None and number < current:
                siblings.append((number, path))
        candidates += [path for _, path in sorted(siblings)]
    for path in candidates:
        if path.is_file() and load(path).get("id") == command_id:
            return str(path.resolve())
    return None


def receipt_commands(
    receipts_dir: Path, skip: set[str], previous: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    commands: list[dict[str, Any]] = []
    paths: dict[str, str] = {}
    for path in sorted(receipts_dir.glob("*.receipt.json")):
        receipt = load(path)
        command_id = str(receipt.get("id"))
        paths[command_id] = str(path.resolve())
        if command_id in skip:
            continue
        runs = [run for run in receipt.get("runs", []) if isinstance(run, dict)]
        codes = [run.get("exit_code") for run in runs]
        commands.append(
            {
                "id": command_id,
                "test_ids": list(previous.get(command_id, {}).get("test_ids", [])),
                "command": " ".join(str(item) for item in receipt.get("argv", [])),
                "status": receipt.get("status"),
                "classification": receipt.get("classification"),
                "receipt": str(path.resolve()),
                "evidence": f"run_checked {receipt.get('status')}; "
                f"determinism={receipt.get('determinism')}; exit_codes={codes}",
            }
        )
    covered = {item["id"] for item in commands} | skip
    for command_id, command in previous.items():
        if command_id not in covered and command.get("status") == "NOT_RUN":
            commands.append(command)
    return commands, paths


def scaffold(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    baseline = load(Path(args.baseline))
    bundle = load(Path(args.bundle))
    report = load(Path(args.previous)) if args.previous else {}
    moved = bool(report) and (
        (report.get("target") or {}).get("head_sha")
        != bundle.get("target", {}).get("head_sha")
        or report.get("bundle_fingerprint") != bundle.get("fingerprint")
    )
    previous_commands = {
        str(item.get("id")): item
        for item in report.get("commands") or []
        if isinstance(item, dict)
    }
    prior_wiring = report.get("test_wiring") or {}
    receipts_dir = Path(args.receipts_dir).resolve()
    if moved:
        # Receipts carry no head, so the previous run's directory proves nothing
        # about the new inputs.
        cited = [item.get("receipt") for item in previous_commands.values()]
        cited.append(prior_wiring.get("after_receipt"))
        if receipts_dir in {Path(str(item)).resolve().parent for item in cited if item}:
            raise ValueError(
                f"head or fingerprint changed since --previous and {receipts_dir} holds "
                "its receipts; use a fresh --receipts-dir and re-run every PASS/FAIL command"
            )
    before, after = args.wiring or DISCOVERY_IDS
    commands, receipt_paths = receipt_commands(receipts_dir, {before, after}, previous_commands)

    report["baseline_fingerprint"] = baseline.get("fingerprint")
    report["bundle_fingerprint"] = bundle.get("fingerprint")
    report["target"] = {
        "base_sha": bundle.get("target", {}).get("base_sha"),
        "head_sha": bundle.get("target", {}).get("head_sha"),
    }
    report.setdefault("intent", {"summary": "", "invariants": [], "no_go": []})
    environment = bundle.get("environment", {})
    report.setdefault(
        "environment",
        {
            "kind": environment.get("kind", "unknown"),
            "identity": environment.get("identity", ""),
            "real_data": False,
            "evidence": "",
        },
    )
    if moved:
        report["environment"] = {**report["environment"], "evidence": ""}
    report.setdefault("authorization", {"publish_requested": False})

    definitions = list(bundle.get("command_definitions") or [])
    prior = report.get("command_definitions") or {}
    if not definitions:
        report["command_definitions"] = {
            "changed": False,
            "paths": [],
            "inspected": False,
            "evidence": "the final bundle changes no command definitions",
        }
    elif not moved and prior.get("paths") == definitions:
        report["command_definitions"] = {**prior, "changed": True}
    else:
        report["command_definitions"] = {
            "changed": True,
            "paths": definitions,
            "inspected": False,
            "evidence": "",
        }

    for name in LEDGERS:
        report.setdefault(name, [])
    if moved:
        report["artifacts"] = [
            {
                "id": item.get("id"),
                "scenario_ids": list(item.get("scenario_ids") or []),
                "status": "",
                "safety_review": False,
            }
            for item in report["artifacts"]
            if isinstance(item, dict)
        ]
    if moved:
        # Counterfactual proof ran against the old inputs; it proves nothing now.
        for item in report["tests"]:
            if isinstance(item, dict):
                item["regression_proof"] = {"status": "", "evidence": ""}
    # The cleanup ledger must name the receipts dir the report now cites; a
    # sibling such as receipts-10 does not name receipts-1.
    names_dir = re.compile(re.escape(str(receipts_dir)) + r"(?![\w-]|\.[\w-])")
    if not any(
        isinstance(item, dict) and names_dir.search(str(item.get("resource")))
        for item in report["cleanup"]
    ):
        taken = {str(item.get("id")) for item in report["cleanup"] if isinstance(item, dict)}
        number = 1
        while f"CL-{number:03d}" in taken:
            number += 1
        report["cleanup"].append(
            {
                "id": f"CL-{number:03d}",
                "resource": "retained evidence: report, "
                f"{args.baseline}, {args.bundle}, receipts and logs in "
                f"{receipts_dir}",
                "status": "RETAINED",
                "reason": "kept for caller re-validation",
            }
        )
    report["commands"] = commands

    # CMD-900 is captured once, before any test changed; a later receipts dir
    # reuses that receipt instead of a re-capture that lists the new tests.
    if before not in receipt_paths:
        prior_before = prior_wiring.get("before_receipt") or (
            previous_commands.get(before) or {}
        ).get("receipt")
        found = earlier_receipt(before, prior_before, receipts_dir)
        if found:
            receipt_paths[before] = found
    if args.wiring:
        missing = [item for item in (before, after) if item not in receipt_paths]
        if missing:
            raise ValueError(
                f"no receipt for wiring command(s): {', '.join(missing)}; "
                "omit --wiring when no test was added"
            )
        report["test_wiring"] = {
            "status": "PROVEN",
            "before_receipt": receipt_paths[before],
            "after_receipt": receipt_paths[after],
            "discovered_tests": list(prior_wiring.get("discovered_tests") or []),
            "evidence": ["runner discovery before and after the change"],
        }
    else:
        wiring = report.get("test_wiring")
        if moved or not isinstance(wiring, dict):
            wiring = {"status": "NOT_PROVEN", "reason": ""}
        if before in receipt_paths:
            # Cite the before-listing so a later --wiring run can reuse it.
            wiring["before_receipt"] = receipt_paths[before]
        report["test_wiring"] = wiring

    # Audit ids are positional, so disproofs survive only an identical patch.
    recomputed = audit_patch(bundle)
    issues = {(item["id"], item["kind"], item["path"]) for item in recomputed["issues"]}
    prior_audit = report.get("test_diff_audit") or {}
    kept = [
        item
        for item in prior_audit.get("disproven") or []
        if not moved
        and isinstance(item, dict)
        and (item.get("id"), item.get("kind"), item.get("path")) in issues
    ]
    report["test_diff_audit"] = {
        "status": recomputed["status"],
        "evidence": f"audit_test_diff.py on the final bundle: {recomputed['status']}, "
        f"{len(recomputed['issues'])} issue(s)",
        "issues": [f"{item['id']} {item['kind']} {item['path']}" for item in recomputed["issues"]],
        "disproven": kept,
    }
    if moved or PROOF_FIELD not in report:
        report[PROOF_FIELD] = dict(PROOF_DEFAULT)
    report["decision"] = ""
    return report, moved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--receipts-dir", required=True)
    parser.add_argument(
        "--wiring",
        nargs=2,
        metavar=("BEFORE_ID", "AFTER_ID"),
        help="receipt ids of the discovery runs captured before and after the tests",
    )
    parser.add_argument("--previous", help="prior report whose ledger is carried forward")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out.exists() and (not args.previous or Path(args.previous).resolve() != out):
        print(f"ERROR: refusing to overwrite {out}; pass it as --previous", file=sys.stderr)
        return 2
    try:
        report, moved = scaffold(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    carried = "no" if not args.previous else "ledger-only (inputs changed)" if moved else "yes"
    print(
        f"SCAFFOLD {out}: commands={len(report['commands'])} "
        f"audit={report['test_diff_audit']['status']} "
        f"carried={carried}; fill empty fields and the decision, then run the validator"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
