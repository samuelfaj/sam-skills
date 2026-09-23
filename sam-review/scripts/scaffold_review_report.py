#!/usr/bin/env python3
"""Prefill a review report's mechanical fields from real files.

Derived from the bundle, receipts, and (for a follow-up cycle) the base review:
target, scope counts, file_coverage paths with classification hints (to verify),
validations from run_checked receipts written after the bundle, a clean
NOT_REQUESTED publication block, and review_basis. Judgment fields stay empty or
null so the validator fails until the reviewer fills them: intent (first cycle),
coverage reasons, findings, test_coverage, validation reasons, behavior_proof,
and decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_review_bundle import file_patch_digests  # noqa: E402
from validate_review import (  # noqa: E402
    delta_blockers,
    delta_identity_errors,
    load_json,
    open_required_ids,
    target_mismatches,
    validate,
    validate_bundle,
)


class ScaffoldError(RuntimeError):
    """Report an actionable scaffold failure."""


def classification_hint(item: dict[str, Any]) -> str:
    for key, value in (
        ("test", "TEST"),
        ("generated", "GENERATED"),
        ("config", "CONFIG"),
        ("probable_type_only", "TYPE_ONLY"),
    ):
        if item.get(key):
            return value
    return "REVIEWED"


def load_valid_bundle(path: Path, label: str) -> dict[str, Any]:
    bundle = load_json(path, label)
    errors: list[str] = []
    validate_bundle(bundle, errors)
    if errors:
        raise ScaffoldError(f"{label} is invalid: {'; '.join(errors[:3])}")
    return bundle


def receipt_validations(receipts_dir: Path, bundle_path: Path) -> list[dict[str, Any]]:
    """Prefill validations; a receipt older than the bundle is stale proof."""
    rows: list[dict[str, Any]] = []
    bundle_mtime = bundle_path.stat().st_mtime_ns
    for path in sorted(receipts_dir.glob("*.receipt.json")):
        if path.stat().st_mtime_ns < bundle_mtime:
            raise ScaffoldError(
                f"receipt {path} predates the bundle; rerun validations into a fresh "
                "receipts directory for this bundle"
            )
        receipt = load_json(path, f"receipt {path.name}")
        argv = receipt.get("argv")
        if not isinstance(argv, list):
            raise ScaffoldError(f"receipt {path} has no argv")
        rows.append(
            {
                "command": " ".join(str(item) for item in argv),
                "status": receipt.get("status"),
                "classification": receipt.get("classification"),
                "reason": "",
                "receipt": str(path.resolve()),
            }
        )
    return rows


def scaffold(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    bundle_path = Path(args.bundle).resolve()
    bundle = load_valid_bundle(bundle_path, "bundle")
    summary, target = bundle["summary"], bundle["target"]
    current_lines = summary["non_test_added_lines"] + summary["non_test_deleted_lines"]
    coverage = [
        {"path": item["path"], "classification": classification_hint(item), "reason": ""}
        for item in bundle["files"]
    ]
    report: dict[str, Any] = {
        "schema_version": 1,
        "target": {
            "mode": target["mode"],
            "base_sha": target["base_sha"],
            "head_sha": target["head_sha"],
            "bundle_fingerprint": bundle["fingerprint"],
        },
        "intent": {
            "intended_behavior": [],
            "must_not_change": [],
            "invariants": [],
            "owner_boundary": "",
            "user_visible_change": None,
        },
        "scope": {
            "baseline_file_count": summary["file_count"],
            "baseline_non_test_lines": current_lines,
            "current_file_count": summary["file_count"],
            "current_non_test_lines": current_lines,
            "review_cycle": 1,
            "scope_expansion_approved": False,
            "remaining_findings_reclassified": False,
        },
        "file_coverage": coverage,
        "findings": [],
        "test_coverage": [],
        "validations": (
            receipt_validations(Path(args.receipts_dir), bundle_path)
            if args.receipts_dir
            else []
        ),
        "behavior_proof": {"status": None, "evidence": []},
        "decision": {
            "result": None,
            "confidence": None,
            "non_gating_requested": False,
            "remaining_corrections": [],
        },
        "publication": {
            "requested": False,
            "expected_head_sha": target["head_sha"],
            "observed_head_sha": target["head_sha"],
            "review_id": f"review-{bundle['fingerprint'][:24]}",
            "action": "NONE",
            "status": "NOT_REQUESTED",
            "inline_comments": [],
            "receipts": [],
            "error": None,
        },
        "review_basis": {
            "mode": "DELTA" if args.delta_bundle else "FULL",
            "base_review": None,
            "base_bundle": None,
            "delta_bundle": None,
            "carried_forward": [],
            "resolved_findings": [],
        },
    }
    if not args.base_review:
        return report, "FULL"

    base_review_path = Path(args.base_review).resolve()
    base_bundle_path = Path(args.base_bundle).resolve()
    base_bundle = load_valid_bundle(base_bundle_path, "base bundle")
    base_report = load_json(base_review_path, "base review")
    base_errors = validate(base_bundle, base_report)
    if base_errors:
        raise ScaffoldError(
            "base review is not VALID (never reuse its receipts directory); restore it, "
            "or scaffold without --base-review and keep each of its open findings in "
            "findings: " + "; ".join(base_errors[:3])
        )
    mismatches = target_mismatches(base_bundle, bundle)
    if mismatches:
        raise ScaffoldError(
            "base review targets another review; scaffold without --base-review: "
            + "; ".join(mismatches)
        )
    open_ids = set(open_required_ids(base_report))
    base_scope = base_report["scope"]
    report["intent"] = base_report["intent"]
    report["scope"].update(
        {
            "baseline_file_count": base_scope["baseline_file_count"],
            "baseline_non_test_lines": base_scope["baseline_non_test_lines"],
            "review_cycle": base_scope["review_cycle"] + 1,
            "scope_expansion_approved": base_scope["scope_expansion_approved"],
        }
    )
    report["findings"] = [
        finding for finding in base_report["findings"] if finding["id"] in open_ids
    ]
    linked = {
        finding["id"] for finding in report["findings"] if finding.get("test_gap")
    }
    # Keep test-gap rows linked to carried findings. DELTA also keeps the rest,
    # but a coverage judgment never crosses heads on its own: its reason is
    # cleared so validation fails until the reviewer re-affirms the row.
    report["test_coverage"] = [
        row if row.get("finding_id") in linked else {**row, "reason": ""}
        for row in base_report["test_coverage"]
        if row.get("finding_id") in linked
        or (args.delta_bundle and row.get("status") != "MISSING_REQUIRED")
    ]
    report["decision"]["remaining_corrections"] = sorted(
        finding["id"]
        for finding in report["findings"]
        if finding["status"] == "ACCEPTED"
    )
    basis = report["review_basis"]
    basis.update(
        {"base_review": str(base_review_path), "base_bundle": str(base_bundle_path)}
    )
    if not args.delta_bundle:
        return report, "FULL"

    delta_path = Path(args.delta_bundle).resolve()
    delta = load_valid_bundle(delta_path, "delta bundle")
    mismatched = delta_identity_errors(delta, bundle, base_report)
    if mismatched:
        raise ScaffoldError(
            "rebuild the delta as range <base review head>..<reviewed head> with the "
            "bundle's --path filters: " + "; ".join(mismatched)
        )
    blockers = delta_blockers(base_bundle, bundle, delta)
    if blockers:
        raise ScaffoldError(
            "FULL review required (rerun without --delta-bundle): " + "; ".join(blockers)
        )
    current = file_patch_digests(bundle["patch"], bundle["files"])
    previous = file_patch_digests(base_bundle["patch"], base_bundle["files"])
    base_rows = {row["path"]: row for row in base_report["file_coverage"]}
    carried = sorted(
        path
        for path, digest in current.items()
        if digest is not None and digest == previous.get(path) and path in base_rows
    )
    report["file_coverage"] = [
        dict(base_rows[row["path"]]) if row["path"] in carried else row
        for row in coverage
    ]
    basis.update({"delta_bundle": str(delta_path), "carried_forward": carried})
    return report, "DELTA"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="Current bundle.json.")
    parser.add_argument("--receipts-dir", help="run_checked receipts to prefill.")
    parser.add_argument("--base-review", help="Prior VALID report.json (next cycle).")
    parser.add_argument("--base-bundle", help="Bundle the base review validated.")
    parser.add_argument(
        "--delta-bundle", help="Range bundle BASE_HEAD..HEAD for a DELTA review."
    )
    parser.add_argument("--out", required=True, help="New report.json path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out).resolve()
    try:
        if bool(args.base_review) != bool(args.base_bundle):
            raise ScaffoldError("--base-review and --base-bundle go together")
        if args.delta_bundle and not args.base_review:
            raise ScaffoldError("--delta-bundle requires --base-review and --base-bundle")
        if out.exists():
            raise ScaffoldError(f"refusing to overwrite existing report: {out}")
        report, mode = scaffold(args)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (ScaffoldError, ValueError, OSError, KeyError, TypeError) as error:
        print(f"scaffold_review_report: {error}", file=sys.stderr)
        return 2
    basis = report["review_basis"]
    print(
        f"scaffold: {out} mode={mode} files={len(report['file_coverage'])} "
        f"validations={len(report['validations'])} "
        f"carried={len(basis['carried_forward'])} open_prior={len(report['findings'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
