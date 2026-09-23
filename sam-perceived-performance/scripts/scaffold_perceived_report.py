#!/usr/bin/env python3
"""Scaffold a perceived-performance report from scope bundles and receipts.

Copies what the validator compares against real files: target fingerprints and
paths, each receipt's id/classification/status/command/receipt path, the scope
delta as file_coverage paths, and the four mandatory gate names. Everything else
is a placeholder that fails closed ("", null, [], "TODO:<enum>"). Owned paths
are never derived from the delta: they come from the step-1 freeze.

Each --measured-scope is the capture_scope bundle taken right after a
measurement the report cites as `after`. If any fingerprint differs from
--current, the code changed since that measurement: nothing is written and the
exit status is 1 (after_reuse=REMEASURE). --no-after declares that no
measurement is cited as `after` (every interaction BLOCKED). This is a
scaffold-time guard, not proof: it trusts that each bundle really was captured
right after its measurement. --check reruns only this guard and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

GATES = (
    "honest-feedback",
    "real-latency-non-regression",
    "failure-path-proof",
    "accessibility-announcement",
)
METRICS = ("feedback_ms", "meaningful_ms", "settled_ms", "dead_time_ms", "samples")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def fingerprint(bundle: dict[str, Any], path: Path) -> str:
    value = bundle.get("fingerprint")
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} is not a capture_scope bundle (no fingerprint)")
    return value


def scope_delta(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Same rule as the validator: a path whose file record differs."""

    def records(bundle: dict[str, Any]) -> dict[str, Any]:
        files = bundle.get("files")
        return {
            item["path"]: item
            for item in (files if isinstance(files, list) else [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }

    before, after = records(baseline), records(current)
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def evidence(receipts_dir: Path) -> list[dict[str, Any]]:
    items = []
    for path in sorted(receipts_dir.glob("*.receipt.json")):
        receipt = load(path)
        argv = receipt.get("argv")
        if not isinstance(argv, list) or not receipt.get("id"):
            raise ValueError(f"{path} is not a run_checked.py receipt")
        items.append(
            {
                "id": receipt["id"],
                "kind": "TODO:MEASUREMENT|TEST",
                "classification": receipt.get("classification"),
                "status": receipt.get("status"),
                "command": " ".join(str(item) for item in argv),
                "receipt": str(path.resolve()),
                "detail": "",
            }
        )
    return sorted(items, key=lambda item: str(item["id"]))


def metric_block() -> dict[str, Any]:
    block: dict[str, Any] = {field: None for field in METRICS}
    block["evidence_ids"] = []
    return block


def skeleton(
    baseline: dict[str, Any], current: dict[str, Any], receipts: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "workflow": "perceived-performance",
        "target": {
            "baseline_fingerprint": baseline["fingerprint"],
            "current_fingerprint": current["fingerprint"],
            "paths": current.get("paths"),
        },
        "intent": {"goal": "", "owner_boundary": "", "must_not_change": [], "invariants": []},
        "environment": {
            "kind": "TODO:local|test|dev|staging|production|unknown",
            "identity": "",
            "device_profile": "",
            "network_profile": "",
        },
        "evidence": receipts,
        "interactions": [
            {
                "id": "I-001",
                "name": "",
                "entry_point": "",
                "trigger": "",
                "blocking_work": "",
                "technique_ids": ["T-001"],
                "status": "TODO:IMPROVED|UNCHANGED|BLOCKED",
                "baseline": metric_block(),
                "after": metric_block(),
            }
        ],
        "techniques": [
            {
                "id": "T-001",
                "name": "",
                "status": "TODO:APPLIED|REJECTED|BLOCKED",
                "interaction_ids": ["I-001"],
                "paths": [],
                "optimistic": None,
                "reversible": None,
                "irreversible_effect": None,
                "failure_mode": "",
                "rollback": "",
                "on_failure_ui": "",
                "accessibility": "",
                "progress_signal": "TODO:REAL|SYNTHETIC|NONE",
                "progress_presentation": "TODO:DETERMINATE|INDETERMINATE|NONE",
                "added_delay_ms": None,
                "evidence_ids": [],
                "failure_path_evidence_ids": [],
            }
        ],
        "file_coverage": [
            {"path": path, "reason": ""} for path in scope_delta(baseline, current)
        ],
        "scope": {
            "initial_owned_paths": [],
            "current_owned_paths": [],
            "scope_expansion_approved": None,
            "cycle": None,
        },
        "gates": [
            {
                "name": name,
                "mandatory": True,
                "status": "TODO:PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
                "evidence_ids": [],
            }
            for name in GATES
        ],
        "decision": {
            "result": "TODO:PERCEIVED_INSTANT|IMPROVED|NO_CHANGE|BLOCKED",
            "remaining": [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--receipts-dir", required=True, type=Path)
    after = parser.add_mutually_exclusive_group(required=True)
    after.add_argument(
        "--measured-scope",
        action="append",
        type=Path,
        help="bundle captured right after a measurement cited as `after`; repeatable",
    )
    after.add_argument(
        "--no-after", action="store_true", help="no measurement is cited as `after`"
    )
    parser.add_argument("--out", type=Path, help="report to create; required unless --check")
    parser.add_argument("--check", action="store_true", help="rerun only the stale check")
    args = parser.parse_args()
    try:
        baseline = load(args.baseline)
        current = load(args.current)
        fingerprint(baseline, args.baseline)
        expected = fingerprint(current, args.current)
        stale = [
            str(path)
            for path in args.measured_scope or []
            if fingerprint(load(path), path) != expected
        ]
        if stale:
            print(
                "after_reuse=REMEASURE: scope changed since the measurement captured in "
                + ", ".join(stale)
                + "; re-measure as TARGET --repeat 2, capture scope again, and rerun",
                file=sys.stderr,
            )
            return 1
        reuse = "NONE" if args.no_after else "ALLOWED"
        if args.check:
            print(f"scaffold: check after_reuse={reuse}")
            return 0
        if args.out is None:
            raise ValueError("--out is required unless --check")
        if args.out.exists():
            raise ValueError(f"{args.out} exists; patch it in place instead")
        report = skeleton(baseline, current, evidence(args.receipts_dir))
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        f"scaffold: wrote {args.out} evidence={len(report['evidence'])} "
        f"file_coverage={len(report['file_coverage'])} after_reuse={reuse}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
