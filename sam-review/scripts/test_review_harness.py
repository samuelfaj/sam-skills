#!/usr/bin/env python3
"""Exercise unified local and proposal review contracts with reproducible fixtures."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


FIXTURES: dict[str, dict[str, Any]] = {
    "clean-runtime-change": {
        "request": (
            "Normalize user-facing slugs so internal whitespace becomes one dash; "
            "preserve lowercase and empty-input behavior."
        ),
        "base": {
            "src/slug.py": (
                "def normalize_slug(value: str) -> str:\n"
                "    return value.strip().lower()\n"
            ),
            "tests/test_slug.py": (
                "from src.slug import normalize_slug\n\n"
                "def test_normalizes_case():\n"
                "    assert normalize_slug(' Hello ') == 'hello'\n"
            ),
        },
        "changed": {
            "src/slug.py": (
                "def normalize_slug(value: str) -> str:\n"
                "    return '-'.join(value.strip().lower().split())\n"
            ),
            "tests/test_slug.py": (
                "from src.slug import normalize_slug\n\n"
                "def test_normalizes_case_and_whitespace():\n"
                "    assert normalize_slug(' Hello   World ') == 'hello-world'\n\n"
                "def test_preserves_empty_input():\n"
                "    assert normalize_slug('   ') == ''\n"
            ),
        },
        "expected": {"decision": "APPROVE", "concept_groups": []},
    },
    "functional-regression": {
        "request": "Refactor discount calculation without changing its observable behavior.",
        "base": {
            "src/pricing.py": (
                "def total_after_discount(subtotal: int, discount: int) -> int:\n"
                "    return max(0, subtotal - discount)\n"
            ),
            "tests/test_pricing.py": (
                "from src.pricing import total_after_discount\n\n"
                "def test_discount_reduces_total():\n"
                "    assert total_after_discount(100, 20) == 80\n"
            ),
        },
        "changed": {
            "src/pricing.py": (
                "def total_after_discount(subtotal: int, discount: int) -> int:\n"
                "    adjusted = subtotal + discount\n"
                "    return max(0, adjusted)\n"
            ),
        },
        "expected": {
            "decision": "CHANGES_REQUIRED",
            "concept_groups": [["discount", "pricing calculation"]],
        },
    },
    "authorization-bypass": {
        "request": "Add an audit entry to admin report access without changing authorization.",
        "base": {
            "src/admin_report.py": (
                "def read_admin_report(actor: dict, audit: list[str]) -> str:\n"
                "    if not actor.get('is_admin'):\n"
                "        raise PermissionError('admin required')\n"
                "    return 'confidential-report'\n"
            ),
            "tests/test_admin_report.py": (
                "import pytest\n"
                "from src.admin_report import read_admin_report\n\n"
                "def test_denies_non_admin():\n"
                "    with pytest.raises(PermissionError):\n"
                "        read_admin_report({'is_admin': False}, [])\n"
            ),
        },
        "changed": {
            "src/admin_report.py": (
                "def read_admin_report(actor: dict, audit: list[str]) -> str:\n"
                "    audit.append(f\"report-read:{actor.get('id', 'unknown')}\")\n"
                "    return 'confidential-report'\n"
            ),
        },
        "expected": {
            "decision": "CHANGES_REQUIRED",
            "concept_groups": [
                ["authorization", "permission", "access control"],
                ["bypass", "removed", "missing", "not enforced", "no longer"],
            ],
        },
    },
    "unsafe-migration": {
        "request": "Add unique account handles while preserving existing production rows.",
        "base": {
            "schema.sql": (
                "CREATE TABLE accounts (\n"
                "  id INTEGER PRIMARY KEY,\n"
                "  email TEXT NOT NULL UNIQUE\n"
                ");\n"
            ),
        },
        "changed": {
            "migrations/002_add_handle.sql": (
                "ALTER TABLE accounts ADD COLUMN handle TEXT NOT NULL;\n"
                "CREATE UNIQUE INDEX accounts_handle_idx ON accounts(handle);\n"
            ),
        },
        "expected": {
            "decision": "CHANGES_REQUIRED",
            "concept_groups": [
                ["existing", "production rows"],
                ["backfill", "populate"],
                ["not null", "constraint"],
            ],
        },
    },
    "cosmetic-test": {
        "request": "Return a clear error when the payment provider returns no response.",
        "base": {
            "src/payment.py": (
                "class PaymentClient:\n"
                "    def __init__(self, provider):\n"
                "        self.provider = provider\n\n"
                "    def charge(self, amount: int) -> str:\n"
                "        response = self.provider.charge(amount)\n"
                "        return response['id']\n"
            ),
            "tests/test_payment.py": (
                "from src.payment import PaymentClient\n\n"
                "def test_constructs_client():\n"
                "    PaymentClient(object())\n"
            ),
        },
        "changed": {
            "src/payment.py": (
                "class PaymentClient:\n"
                "    def __init__(self, provider):\n"
                "        self.provider = provider\n\n"
                "    def charge(self, amount: int) -> str:\n"
                "        response = self.provider.charge(amount)\n"
                "        if response is None:\n"
                "            raise RuntimeError('payment provider returned no response')\n"
                "        return response['id']\n"
            ),
            "tests/test_payment.py": (
                "from src.payment import PaymentClient\n\n"
                "def test_constructs_client():\n"
                "    PaymentClient(object())\n\n"
                "def test_constructs_client_for_no_response_case():\n"
                "    PaymentClient(object())\n"
            ),
        },
        "expected": {
            "decision": "CHANGES_REQUIRED",
            "concept_groups": [
                ["test", "coverage"],
                ["no response", "none response", "provider returns none"],
            ],
        },
    },
    "ownership-regression": {
        "request": "Expose refund eligibility through the existing controller endpoint.",
        "base": {
            "src/refund_service.py": (
                "def can_refund(order: dict, actor: dict) -> bool:\n"
                "    return actor.get('is_admin', False) or order['age_days'] <= 30\n"
            ),
            "src/refund_controller.py": (
                "from src.refund_service import can_refund\n\n"
                "def refund_status(order: dict, actor: dict) -> dict:\n"
                "    return {'eligible': can_refund(order, actor)}\n"
            ),
        },
        "changed": {
            "src/refund_controller.py": (
                "def refund_status(order: dict, actor: dict) -> dict:\n"
                "    eligible = actor.get('is_admin', False) or order['age_days'] <= 30\n"
                "    return {'eligible': eligible}\n"
            ),
        },
        "expected": {
            "decision": "CHANGES_REQUIRED",
            "concept_groups": [
                ["business rule", "policy"],
                ["service"],
                ["controller"],
            ],
        },
    },
    "cross-file-contract": {
        "request": "Rename the public user identifier from user_id to id across the API contract.",
        "base": {
            "src/api.py": (
                "def serialize_user(user: dict) -> dict:\n"
                "    return {'user_id': user['id'], 'name': user['name']}\n"
            ),
            "src/client.py": (
                "def read_user_id(payload: dict) -> int:\n"
                "    return payload['user_id']\n"
            ),
            "schema/user.json": ('{\n  "required": ["user_id", "name"]\n}\n'),
            "tests/test_api.py": (
                "from src.api import serialize_user\n\n"
                "def test_serializes_user():\n"
                "    assert serialize_user({'id': 7, 'name': 'Ada'})['user_id'] == 7\n"
            ),
        },
        "changed": {
            "src/api.py": (
                "def serialize_user(user: dict) -> dict:\n"
                "    return {'id': user['id'], 'name': user['name']}\n"
            ),
            "schema/user.json": '{\n  "required": ["id", "name"]\n}\n',
            "tests/test_api.py": (
                "from src.api import serialize_user\n\n"
                "def test_serializes_user():\n"
                "    assert serialize_user({'id': 7, 'name': 'Ada'})['id'] == 7\n"
            ),
            "docs/api.md": (
                "# User response\n\n"
                "The response contains `id` and `name`.\n\n"
                "## Migration\n\n"
                "Consumers must read `id`; the prior `user_id` key is removed by this change.\n"
            ),
        },
        "expected": {
            "decision": "CHANGES_REQUIRED",
            "concept_groups": [
                ["client", "consumer"],
                ["user_id"],
                ["contract", "producer-consumer"],
            ],
        },
    },
    "test-only-clean": {
        "request": "Add regression coverage for the existing comma-separated tag parser.",
        "base": {
            "src/tags.py": (
                "def parse_tags(value: str) -> list[str]:\n"
                "    return [item.strip() for item in value.split(',') if item.strip()]\n"
            ),
        },
        "changed": {
            "tests/test_tags.py": (
                "from src.tags import parse_tags\n\n"
                "def test_ignores_empty_segments():\n"
                "    assert parse_tags('alpha, , beta,') == ['alpha', 'beta']\n"
            ),
        },
        "expected": {"decision": "APPROVE", "concept_groups": []},
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list", action="store_true", help="List fixture names and requests."
    )
    parser.add_argument(
        "--materialize", choices=sorted(FIXTURES), help="Create one dirty fixture repo."
    )
    parser.add_argument("--output", help="Required output directory for --materialize.")
    parser.add_argument(
        "--score",
        action="append",
        default=[],
        metavar="FIXTURE=REPORT.json",
        help="Score a structured review report against a fixture expectation.",
    )
    return parser.parse_args()


def run(
    command: list[str],
    cwd: Path,
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({' '.join(command)}): {result.stderr.strip()}"
        )
    return result


def write_files(root: Path, files: dict[str, str | None]) -> None:
    for relative, content in files.items():
        path = root / relative
        if content is None:
            if path.exists() or path.is_symlink():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def materialize(name: str, output: Path) -> Path:
    fixture = FIXTURES[name]
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"output directory must be absent or empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q"], output)
    run(["git", "config", "user.email", "review-fixture@example.invalid"], output)
    run(["git", "config", "user.name", "Review Fixture"], output)
    write_files(output, fixture["base"])
    run(["git", "add", "."], output)
    run(["git", "commit", "-q", "-m", "fixture baseline"], output)
    write_files(output, fixture["changed"])
    return output


RUN_CHECKED = Path(__file__).resolve().parent / "run_checked.py"
SCAFFOLD = Path(__file__).resolve().parent / "scaffold_review_report.py"


def make_receipt(
    receipts: Path,
    command_id: str,
    classification: str,
    shell: str,
    repeat: int = 2,
) -> dict[str, Any]:
    """Produce a real execution receipt so fixtures cannot fake a PASS."""
    receipts.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(RUN_CHECKED),
            "--id",
            command_id,
            "--receipts-dir",
            str(receipts),
            "--classification",
            classification,
            "--repeat",
            str(repeat),
            "--",
            "/bin/sh",
            "-c",
            shell,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    path = receipts / f"{command_id}.receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path),
        "command": " ".join(receipt["argv"]),
        "status": receipt["status"],
    }


def report_for_clean_bundle(
    bundle: dict[str, Any], request: str, receipts: Path
) -> dict[str, Any]:
    summary = bundle["summary"]
    coverage = []
    for item in bundle["files"]:
        if item["test"]:
            classification = "TEST"
        elif item["generated"]:
            classification = "GENERATED"
        elif item["config"]:
            classification = "CONFIG"
        elif item["probable_type_only"]:
            classification = "TYPE_ONLY"
        else:
            classification = "REVIEWED"
        coverage.append(
            {
                "path": item["path"],
                "classification": classification,
                "reason": "Fixture file accounted for",
            }
        )
    validation = make_receipt(
        receipts, "CMD-001", "TARGET", "echo 'harness contract validation passed'"
    )
    return {
        "schema_version": 1,
        "target": {
            "mode": bundle["target"]["mode"],
            "base_sha": bundle["target"]["base_sha"],
            "head_sha": bundle["target"]["head_sha"],
            "bundle_fingerprint": bundle["fingerprint"],
        },
        "intent": {
            "intended_behavior": [request],
            "must_not_change": [],
            "invariants": ["Review evidence remains tied to the frozen diff"],
            "owner_boundary": "fixture repository",
            "user_visible_change": False,
        },
        "scope": {
            "baseline_file_count": summary["file_count"],
            "baseline_non_test_lines": summary["non_test_added_lines"]
            + summary["non_test_deleted_lines"],
            "current_file_count": summary["file_count"],
            "current_non_test_lines": summary["non_test_added_lines"]
            + summary["non_test_deleted_lines"],
            "review_cycle": 1,
            "scope_expansion_approved": False,
            "remaining_findings_reclassified": False,
        },
        "file_coverage": coverage,
        "findings": [],
        "test_coverage": [
            {
                "behavior": "Fixture request",
                "level": "UNIT",
                "status": "COVERED",
                "paths": [item["path"] for item in bundle["files"] if item["test"]],
                "reason": "Harness contract check",
                "finding_id": None,
            }
        ],
        "validations": [
            {
                "command": validation["command"],
                "status": validation["status"],
                "classification": "TARGET",
                "reason": "Synthetic proof passed",
                "receipt": validation["path"],
            }
        ],
        "behavior_proof": {"status": "NOT_APPLICABLE", "evidence": []},
        "decision": {
            "result": "APPROVE",
            "confidence": "HIGH",
            "non_gating_requested": False,
            "remaining_corrections": [],
        },
        "publication": {
            "requested": False,
            "expected_head_sha": bundle["target"]["head_sha"],
            "observed_head_sha": bundle["target"]["head_sha"],
            "review_id": "fixture-review-0001",
            "action": "NONE",
            "status": "NOT_REQUESTED",
            "inline_comments": [],
            "receipts": [],
            "error": None,
        },
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def flatten_findings(report: dict[str, Any]) -> str:
    parts: list[str] = []
    for finding in report.get("findings", []):
        if not isinstance(finding, dict) or finding.get("status") != "ACCEPTED":
            continue
        for field in ("failure_mode", "impact", "required_change"):
            value = finding.get(field)
            if isinstance(value, str):
                parts.append(value)
        evidence = finding.get("evidence")
        if isinstance(evidence, list):
            parts.extend(value for value in evidence if isinstance(value, str))
    return " ".join(parts).lower()


def score_report(name: str, report_path: Path) -> tuple[bool, list[str]]:
    report = load_json(report_path)
    expectation = FIXTURES[name]["expected"]
    errors: list[str] = []
    result = report.get("decision", {}).get("result")
    if result != expectation["decision"]:
        errors.append(f"decision={result!r}, expected {expectation['decision']!r}")
    findings_text = flatten_findings(report)
    concept_groups = expectation["concept_groups"]
    for index, group in enumerate(concept_groups, start=1):
        if not any(concept in findings_text for concept in group):
            errors.append(
                f"accepted findings miss required risk concept group {index}: {group}"
            )
    if not concept_groups:
        blocking = [
            item
            for item in report.get("findings", [])
            if isinstance(item, dict)
            and item.get("status") == "ACCEPTED"
            and item.get("severity") in {"BLOCKER", "IMPORTANT"}
        ]
        if blocking:
            errors.append("clean fixture contains accepted blocking findings")
    return not errors, errors


def self_test() -> None:
    script_dir = Path(__file__).resolve().parent
    builder = script_dir / "build_review_bundle.py"
    validator = script_dir / "validate_review.py"
    with tempfile.TemporaryDirectory(prefix="sam-review-harness-") as temporary:
        temp = Path(temporary)
        bundles: dict[str, dict[str, Any]] = {}
        for name, fixture in FIXTURES.items():
            repo = materialize(name, temp / name)
            result = run(
                [sys.executable, str(builder), "--repo", str(repo), "--mode", "local"],
                repo,
            )
            bundle = json.loads(result.stdout)
            changed_paths = set(fixture["changed"])
            bundle_paths = {item["path"] for item in bundle["files"]}
            if changed_paths != bundle_paths:
                raise RuntimeError(
                    f"{name}: bundle paths {sorted(bundle_paths)} != changed paths {sorted(changed_paths)}"
                )
            if not bundle.get("fingerprint") or not bundle.get("patch"):
                raise RuntimeError(f"{name}: incomplete bundle")
            bundles[name] = bundle

        partial_reports = {
            "authorization-only": "Authorization changed",
            "bypass-only": "The admin check was removed, creating a bypass",
        }
        for label, finding_text in partial_reports.items():
            partial_path = temp / f"partial-{label}.json"
            partial_path.write_text(
                json.dumps(
                    {
                        "decision": {"result": "CHANGES_REQUIRED"},
                        "findings": [
                            {
                                "status": "ACCEPTED",
                                "failure_mode": finding_text,
                                "impact": finding_text,
                                "required_change": finding_text,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            partial_passed, partial_errors = score_report(
                "authorization-bypass", partial_path
            )
            if partial_passed or not any(
                "miss required risk concept group" in error for error in partial_errors
            ):
                raise RuntimeError(
                    f"semantic scorer accepted partial auth report {label}: "
                    f"{partial_errors}"
                )

        mode_repo = materialize("functional-regression", temp / "mode-targets")
        run(["git", "add", "."], mode_repo)
        run(["git", "commit", "-q", "-m", "fixture change"], mode_repo)
        mode_commands = {
            "commit": ["--mode", "commit", "--commit", "HEAD"],
            "branch": ["--mode", "branch", "--base", "HEAD^", "--head", "HEAD"],
            "range": ["--mode", "range", "--range", "HEAD^..HEAD"],
            "auto": ["--mode", "auto", "--base", "HEAD^"],
            "proposal": [
                "--mode",
                "proposal",
                "--base",
                "HEAD^",
                "--head",
                "HEAD",
                "--platform",
                "fixture",
                "--repository",
                "example/repository",
                "--change-id",
                "42",
                "--comparison",
                "direct",
            ],
        }
        for expected_mode, mode_args in mode_commands.items():
            mode_result = run(
                [sys.executable, str(builder), "--repo", str(mode_repo), *mode_args],
                mode_repo,
            )
            actual_mode = json.loads(mode_result.stdout)["target"]["mode"]
            normalized_expected = "branch" if expected_mode == "auto" else expected_mode
            if actual_mode != normalized_expected:
                raise RuntimeError(
                    f"target mode {expected_mode}: got {actual_mode}, expected {normalized_expected}"
                )

        proposal_result = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(mode_repo),
                *mode_commands["proposal"],
            ],
            mode_repo,
        )
        proposal_bundle = json.loads(proposal_result.stdout)
        proposal_target = proposal_bundle["target"]
        if (
            proposal_target.get("platform") != "fixture"
            or proposal_target.get("repository") != "example/repository"
            or proposal_target.get("change_id") != "42"
            or proposal_target.get("comparison") != "direct"
        ):
            raise RuntimeError("proposal identity was not preserved in the bundle")
        if not all(
            "old_changed_ranges" in item and "new_changed_ranges" in item
            for item in proposal_bundle["files"]
        ):
            raise RuntimeError("proposal bundle omitted changed-side ranges")

        proposal_bundle_path = temp / "proposal-bundle.json"
        proposal_report_path = temp / "proposal-report.json"
        proposal_bundle_path.write_text(
            json.dumps(proposal_bundle), encoding="utf-8"
        )
        proposal_report = report_for_clean_bundle(
            proposal_bundle, "Review the fixture proposal", temp / "receipts-proposal"
        )
        proposal_report_path.write_text(
            json.dumps(proposal_report), encoding="utf-8"
        )
        proposal_valid = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(proposal_bundle_path),
                str(proposal_report_path),
            ],
            temp,
            check=False,
        )
        if proposal_valid.returncode != 0:
            raise RuntimeError(
                f"valid unrequested proposal review rejected: {proposal_valid.stderr}"
            )

        planned_approval = copy.deepcopy(proposal_report)
        planned_approval["publication"].update(
            {"requested": True, "action": "APPROVE", "status": "PLANNED"}
        )
        proposal_report_path.write_text(
            json.dumps(planned_approval), encoding="utf-8"
        )
        planned_valid = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(proposal_bundle_path),
                str(proposal_report_path),
            ],
            temp,
            check=False,
        )
        if planned_valid.returncode != 0:
            raise RuntimeError(
                f"authorized planned approval rejected: {planned_valid.stderr}"
            )

        incompatible_action = copy.deepcopy(planned_approval)
        incompatible_action["publication"]["action"] = "REQUEST_CHANGES"
        proposal_report_path.write_text(
            json.dumps(incompatible_action), encoding="utf-8"
        )
        incompatible_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(proposal_bundle_path),
                str(proposal_report_path),
            ],
            temp,
            check=False,
        )
        if (
            incompatible_rejected.returncode != 1
            or "REQUEST_CHANGES action requires CHANGES_REQUIRED"
            not in incompatible_rejected.stderr
        ):
            raise RuntimeError("validator accepted an incompatible publication action")

        local_publication = report_for_clean_bundle(
            bundles["test-only-clean"],
            FIXTURES["test-only-clean"]["request"],
            temp / "receipts-local",
        )
        local_publication["publication"].update(
            {"requested": True, "action": "APPROVE", "status": "PLANNED"}
        )
        local_bundle_path = temp / "local-publication-bundle.json"
        local_report_path = temp / "local-publication-report.json"
        local_bundle_path.write_text(
            json.dumps(bundles["test-only-clean"]), encoding="utf-8"
        )
        local_report_path.write_text(json.dumps(local_publication), encoding="utf-8")
        local_publication_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(local_bundle_path),
                str(local_report_path),
            ],
            temp,
            check=False,
        )
        if (
            local_publication_rejected.returncode != 1
            or "publication is unavailable for non-proposal targets"
            not in local_publication_rejected.stderr
        ):
            raise RuntimeError("validator allowed publication for a local target")

        remote = temp / "remote.git"
        run(["git", "init", "--bare", "--initial-branch=trunk", str(remote)], temp)
        inferred_repo = temp / "inferred-base"
        run(["git", "clone", str(remote), str(inferred_repo)], temp)
        run(["git", "config", "user.email", "fixture@example.invalid"], inferred_repo)
        run(["git", "config", "user.name", "Fixture"], inferred_repo)
        write_files(inferred_repo, {"src/value.py": "VALUE = 1\n"})
        run(["git", "add", "."], inferred_repo)
        run(["git", "commit", "-q", "-m", "baseline"], inferred_repo)
        run(["git", "push", "-q", "-u", "origin", "trunk"], inferred_repo)
        run(["git", "remote", "set-head", "origin", "-a"], inferred_repo)
        run(["git", "switch", "-q", "-c", "feature"], inferred_repo)
        write_files(inferred_repo, {"src/value.py": "VALUE = 2\n"})
        run(["git", "add", "."], inferred_repo)
        run(["git", "commit", "-q", "-m", "feature change"], inferred_repo)
        inferred = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(inferred_repo),
                "--mode",
                "auto",
            ],
            inferred_repo,
        )
        inferred_target = json.loads(inferred.stdout)["target"]
        if (
            inferred_target["mode"] != "branch"
            or inferred_target["base_ref"] != "origin/trunk"
        ):
            raise RuntimeError(
                "auto mode did not resolve the advertised non-conventional remote HEAD"
            )

        path_filtered = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(temp / "cross-file-contract"),
                "--mode",
                "local",
                "--path",
                "src/api.py",
            ],
            temp / "cross-file-contract",
        )
        filtered_paths = {
            item["path"] for item in json.loads(path_filtered.stdout)["files"]
        }
        if filtered_paths != {"src/api.py"}:
            raise RuntimeError(f"path filter leaked files: {sorted(filtered_paths)}")

        rename_repo = temp / "rename-delete"
        rename_repo.mkdir()
        run(["git", "init", "-q"], rename_repo)
        run(
            ["git", "config", "user.email", "review-fixture@example.invalid"],
            rename_repo,
        )
        run(["git", "config", "user.name", "Review Fixture"], rename_repo)
        write_files(
            rename_repo,
            {
                "src/old_name.py": "VALUE = 1\n",
                "src/obsolete.py": "OBSOLETE = True\n",
            },
        )
        run(["git", "add", "."], rename_repo)
        run(["git", "commit", "-q", "-m", "rename baseline"], rename_repo)
        (rename_repo / "src/old_name.py").rename(rename_repo / "src/new_name.py")
        (rename_repo / "src/obsolete.py").unlink()
        run(["git", "add", "-A"], rename_repo)
        rename_result = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(rename_repo),
                "--mode",
                "local",
            ],
            rename_repo,
        )
        rename_statuses = {
            item["path"]: item["status"]
            for item in json.loads(rename_result.stdout)["files"]
        }
        if not rename_statuses.get("src/new_name.py", "").startswith("R"):
            raise RuntimeError("rename was not preserved in the bundle manifest")
        if rename_statuses.get("src/obsolete.py") != "D":
            raise RuntimeError("deletion was not preserved in the bundle manifest")

        large_repo = temp / "cross-file-contract"
        oversized = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(large_repo),
                "--mode",
                "local",
                "--max-bytes",
                "128",
            ],
            large_repo,
            check=False,
        )
        # An oversized patch is a final refusal: no truncation, BLOCKED, and no
        # advice to narrow --path or the range unless the user explicitly re-scopes
        # the review (SKILL.md section 2).
        final_refusal = (
            "rather than truncating" in oversized.stderr
            and "report BLOCKED" in oversized.stderr
            and "only on an explicit user re-scope" in oversized.stderr
            and "coherent --path targets" not in oversized.stderr
            and "separate target" not in oversized.stderr
        )
        if oversized.returncode != 2 or not final_refusal:
            raise RuntimeError(
                "oversized bundle did not fail closed as a final BLOCKED refusal"
            )

        sensitive_repo = temp / "sensitive"
        materialize("test-only-clean", sensitive_repo)
        (sensitive_repo / ".env").write_text(
            "PASSWORD='not-a-placeholder-secret-value'\n"
        )
        sensitive = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(sensitive_repo),
                "--mode",
                "local",
            ],
            sensitive_repo,
            check=False,
        )
        if sensitive.returncode != 2 or "review bundle refused" not in sensitive.stderr:
            raise RuntimeError("sensitive bundle did not fail closed")

        binary_repo = temp / "binary"
        materialize("test-only-clean", binary_repo)
        (binary_repo / "artifact.bin").write_bytes(b"\xff\xfe\x01\x02")
        binary_result = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(binary_repo),
                "--mode",
                "local",
            ],
            binary_repo,
        )
        binary_files = {
            item["path"]: item for item in json.loads(binary_result.stdout)["files"]
        }
        if not binary_files.get("artifact.bin", {}).get("binary"):
            raise RuntimeError(
                "invalid UTF-8 untracked content was not classified as binary"
            )

        repository_git_repo = temp / "repository-git"
        materialize("test-only-clean", repository_git_repo)
        fake_bin = repository_git_repo / "bin"
        fake_bin.mkdir()
        fake_git = fake_bin / "git"
        fake_git.write_text(
            '#!/bin/sh\n: > "$SAM_REVIEW_MARKER"\nexit 0\n', encoding="utf-8"
        )
        fake_git.chmod(0o755)
        repository_git_marker = temp / "repository-git.marker"
        repository_git_env = dict(os.environ)
        repository_git_env["PATH"] = (
            f"{fake_bin}{os.pathsep}{repository_git_env.get('PATH', '')}"
        )
        repository_git_env["SAM_REVIEW_MARKER"] = str(repository_git_marker)
        repository_git = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(repository_git_repo / "src"),
                "--mode",
                "local",
            ],
            repository_git_repo,
            check=False,
            env=repository_git_env,
        )
        # Git is resolved from trusted system locations only, so a PATH-injected
        # repository git is never executed and the build still succeeds.
        if repository_git_marker.exists():
            raise RuntimeError("repository-controlled git executable was executed")
        if repository_git.returncode != 0:
            raise RuntimeError(
                "PATH-injected git must not break the build: "
                f"exit {repository_git.returncode}: {repository_git.stderr[:200]}"
            )
        if not json.loads(repository_git.stdout).get("fingerprint"):
            raise RuntimeError("trusted git fallback did not produce a bundle")

        fsmonitor_repo = temp / "fsmonitor"
        materialize("test-only-clean", fsmonitor_repo)
        fsmonitor_marker = temp / "fsmonitor.marker"
        fsmonitor_hook = temp / "fsmonitor-hook"
        fsmonitor_hook.write_text(
            '#!/bin/sh\n: > "$SAM_REVIEW_MARKER"\nexit 0\n', encoding="utf-8"
        )
        fsmonitor_hook.chmod(0o755)
        run(
            ["git", "config", "core.fsmonitor", str(fsmonitor_hook)],
            fsmonitor_repo,
        )
        fsmonitor_env = dict(os.environ)
        fsmonitor_env["SAM_REVIEW_MARKER"] = str(fsmonitor_marker)
        fsmonitor = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(fsmonitor_repo),
                "--mode",
                "local",
            ],
            fsmonitor_repo,
            check=False,
            env=fsmonitor_env,
        )
        if fsmonitor.returncode != 0 or fsmonitor_marker.exists():
            raise RuntimeError("repository-configured core.fsmonitor executed")

        filter_repo = temp / "clean-filter"
        materialize("test-only-clean", filter_repo)
        filter_marker = temp / "clean-filter.marker"
        filter_driver = temp / "clean-filter-driver"
        filter_driver.write_text(
            '#!/bin/sh\n: > "$SAM_REVIEW_MARKER"\ncat\n', encoding="utf-8"
        )
        filter_driver.chmod(0o755)
        run(
            ["git", "config", "filter.review-probe.clean", str(filter_driver)],
            filter_repo,
        )
        filter_env = dict(os.environ)
        filter_env["SAM_REVIEW_MARKER"] = str(filter_marker)
        clean_filter = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(filter_repo),
                "--mode",
                "local",
            ],
            filter_repo,
            check=False,
            env=filter_env,
        )
        if (
            clean_filter.returncode != 2
            or filter_marker.exists()
            or "configured clean/process filters" not in clean_filter.stderr
        ):
            raise RuntimeError("configured clean filter did not fail closed")

        redirected_target = temp / "redirected-target"
        redirected_source = temp / "redirected-source"
        materialize("test-only-clean", redirected_target)
        materialize("functional-regression", redirected_source)
        redirected_env = dict(os.environ)
        redirected_env["GIT_DIR"] = str(redirected_source / ".git")
        redirected_env["GIT_WORK_TREE"] = str(redirected_source)
        redirected = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(redirected_target),
                "--mode",
                "local",
            ],
            redirected_target,
            check=False,
            env=redirected_env,
        )
        if redirected.returncode != 0:
            raise RuntimeError(
                f"isolated Git environment rejected valid target: {redirected.stderr}"
            )
        redirected_paths = {
            item["path"] for item in json.loads(redirected.stdout)["files"]
        }
        if redirected_paths != {"tests/test_tags.py"}:
            raise RuntimeError(
                f"inherited Git environment redirected target: {sorted(redirected_paths)}"
            )

        lock_control = temp / "optional-lock-control"
        materialize("test-only-clean", lock_control)
        control_tracked = lock_control / "src/tags.py"
        control_stat = control_tracked.stat()
        os.utime(
            control_tracked,
            ns=(control_stat.st_atime_ns, control_stat.st_mtime_ns + 2_000_000_000),
        )
        control_index = lock_control / ".git/index"
        control_before = control_index.read_bytes()
        run(["git", "status", "--short"], lock_control)
        if control_index.read_bytes() == control_before:
            raise RuntimeError("optional-lock control did not refresh the Git index")

        lock_repo = temp / "optional-locks"
        materialize("test-only-clean", lock_repo)
        lock_tracked = lock_repo / "src/tags.py"
        lock_stat = lock_tracked.stat()
        os.utime(
            lock_tracked,
            ns=(lock_stat.st_atime_ns, lock_stat.st_mtime_ns + 2_000_000_000),
        )
        lock_index = lock_repo / ".git/index"
        lock_before = lock_index.read_bytes()
        lock_result = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(lock_repo),
                "--mode",
                "local",
            ],
            lock_repo,
            check=False,
        )
        if lock_result.returncode != 0 or lock_index.read_bytes() != lock_before:
            raise RuntimeError("review bundle construction mutated the Git index")

        textconv_repo = temp / "textconv"
        textconv_repo.mkdir()
        run(["git", "init", "-q"], textconv_repo)
        run(
            ["git", "config", "user.email", "review-fixture@example.invalid"],
            textconv_repo,
        )
        run(["git", "config", "user.name", "Review Fixture"], textconv_repo)
        write_files(
            textconv_repo,
            {
                ".gitattributes": "*.blob diff=review-probe\n",
                "payload.blob": "baseline\n",
            },
        )
        run(["git", "add", "."], textconv_repo)
        run(["git", "commit", "-q", "-m", "textconv baseline"], textconv_repo)
        textconv_marker = temp / "textconv.marker"
        textconv_driver = temp / "textconv-driver"
        textconv_driver.write_text(
            '#!/bin/sh\n: > "$SAM_REVIEW_MARKER"\ncat "$1"\n',
            encoding="utf-8",
        )
        textconv_driver.chmod(0o755)
        run(
            ["git", "config", "diff.review-probe.textconv", str(textconv_driver)],
            textconv_repo,
        )
        (textconv_repo / "payload.blob").write_text("changed\n", encoding="utf-8")
        textconv_env = dict(os.environ)
        textconv_env["SAM_REVIEW_MARKER"] = str(textconv_marker)
        textconv = run(
            [
                sys.executable,
                str(builder),
                "--repo",
                str(textconv_repo),
                "--mode",
                "local",
            ],
            textconv_repo,
            check=False,
            env=textconv_env,
        )
        if textconv.returncode != 0 or textconv_marker.exists():
            raise RuntimeError("configured textconv driver executed")

        clean_bundle = bundles["test-only-clean"]
        bundle_path = temp / "bundle.json"
        report_path = temp / "report.json"
        bundle_path.write_text(json.dumps(clean_bundle), encoding="utf-8")
        report = report_for_clean_bundle(
            clean_bundle, FIXTURES["test-only-clean"]["request"], temp / "receipts-clean"
        )
        report_path.write_text(json.dumps(report), encoding="utf-8")
        valid = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if valid.returncode != 0:
            raise RuntimeError(f"valid report rejected: {valid.stderr}")
        scored, score_errors = score_report("test-only-clean", report_path)
        if not scored:
            raise RuntimeError(f"clean fixture score failed: {score_errors}")

        invalid = copy.deepcopy(report)
        changed_file = clean_bundle["files"][0]
        changed_line = changed_file["changed_lines"][0][0]
        invalid["findings"] = [
            {
                "id": "F1",
                "severity": "BLOCKER",
                "status": "ACCEPTED",
                "scope": "IN_SCOPE",
                "path": changed_file["path"],
                "line": changed_line,
                "side": "NEW",
                "failure_mode": "Synthetic failure",
                "impact": "Synthetic impact",
                "evidence": ["Synthetic evidence"],
                "required_change": "Synthetic correction",
                "test_gap": False,
                "rejection_reason": None,
            }
        ]
        report_path.write_text(json.dumps(invalid), encoding="utf-8")
        rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if rejected.returncode != 1 or "APPROVE cannot retain" not in rejected.stderr:
            raise RuntimeError("validator accepted an inconsistent approval")
        invalid_score, _ = score_report("test-only-clean", report_path)
        if invalid_score:
            raise RuntimeError(
                "fixture scorer accepted a blocking finding on a clean diff"
            )

        blocking = copy.deepcopy(invalid)
        blocking["decision"] = {
            "result": "CHANGES_REQUIRED",
            "confidence": "HIGH",
            "non_gating_requested": False,
            "remaining_corrections": ["F1"],
        }
        report_path.write_text(json.dumps(blocking), encoding="utf-8")
        blocking_valid = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if blocking_valid.returncode != 0:
            raise RuntimeError(
                f"valid blocking report rejected: {blocking_valid.stderr}"
            )

        unlinked_gap = copy.deepcopy(blocking)
        unlinked_gap["findings"][0]["test_gap"] = True
        report_path.write_text(json.dumps(unlinked_gap), encoding="utf-8")
        gap_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if (
            gap_rejected.returncode != 1
            or "missing from test_coverage" not in gap_rejected.stderr
        ):
            raise RuntimeError("validator accepted an unlinked required test gap")

        user_visible = copy.deepcopy(report)
        user_visible["intent"]["user_visible_change"] = True
        user_visible["behavior_proof"] = {
            "status": "NOT_PROVEN",
            "evidence": ["Behavior environment was unavailable"],
        }
        report_path.write_text(json.dumps(user_visible), encoding="utf-8")
        behavior_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if (
            behavior_rejected.returncode != 1
            or "requires proof for a user-visible change" not in behavior_rejected.stderr
        ):
            raise RuntimeError("validator approved an unproven user-visible change")

        incomplete_coverage = copy.deepcopy(report)
        incomplete_coverage["file_coverage"] = []
        report_path.write_text(json.dumps(incomplete_coverage), encoding="utf-8")
        coverage_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if (
            coverage_rejected.returncode != 1
            or "file_coverage missing paths" not in coverage_rejected.stderr
        ):
            raise RuntimeError("validator accepted incomplete changed-file coverage")

        missing_scenarios = copy.deepcopy(report)
        missing_scenarios["test_coverage"] = []
        report_path.write_text(json.dumps(missing_scenarios), encoding="utf-8")
        scenarios_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if (
            scenarios_rejected.returncode != 1
            or "at least one scenario" not in scenarios_rejected.stderr
        ):
            raise RuntimeError("validator accepted an empty scenario inventory")

        missing_validations = copy.deepcopy(report)
        missing_validations["validations"] = []
        report_path.write_text(json.dumps(missing_validations), encoding="utf-8")
        validations_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if (
            validations_rejected.returncode != 1
            or "at least one entry" not in validations_rejected.stderr
        ):
            raise RuntimeError("validator accepted an empty validation ledger")

        introduced_failure = copy.deepcopy(report)
        introduced_failure["validations"] = [
            {
                "command": "synthetic target validation",
                "status": "FAIL",
                "classification": "INTRODUCED",
                "reason": "Synthetic introduced failure",
            }
        ]
        report_path.write_text(json.dumps(introduced_failure), encoding="utf-8")
        introduced_rejected = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if (
            introduced_rejected.returncode != 1
            or "target validation failure" not in introduced_rejected.stderr
        ):
            raise RuntimeError("validator approved an introduced validation failure")

        # File-count growth alone does not change the authorized behavior.
        scope_growth = copy.deepcopy(report)
        scope_growth["scope"]["baseline_file_count"] = 0
        report_path.write_text(json.dumps(scope_growth), encoding="utf-8")
        scope_valid = run(
            [
                sys.executable,
                str(validator),
                "--bundle",
                str(bundle_path),
                str(report_path),
            ],
            temp,
            check=False,
        )
        if scope_valid.returncode != 0:
            raise RuntimeError(f"in-scope growth rejected: {scope_valid.stderr}")

        exercise_risk_tag_precision()
        exercise_out_mode(temp, builder, bundles["clean-runtime-change"])
        exercise_scaffold_and_delta(temp, builder, validator)


def exercise_risk_tag_precision() -> None:
    """Word-level matching keeps lens-routing tags from firing on every bundle; the
    DELTA gate adds fail-safe substring hints (see exercise_scaffold_and_delta)."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_review_bundle import risk_tags  # noqa: E402

    over_matches = {
        "yarn.lock": "concurrency-jobs",
        "package-lock.json": "concurrency-jobs",
        "src/ui/Blocked.py": "concurrency-jobs",
        "src/design/tokens.ts": "delivery",
        "docs/assign.md": "delivery",
        "src/signal.py": "delivery",
        "references/publication-policy.md": "public-contract",
        "src/exporter/csv.py": "public-contract",
    }
    for path, tag in over_matches.items():
        if tag in risk_tags(path):
            raise RuntimeError(f"risk tag {tag} over-matches {path}")
    true_positives = {
        "src/locks/mutex.py": "concurrency-jobs",
        "src/useLock.ts": "concurrency-jobs",
        "scripts/sign_release.sh": "delivery",
        "build/codesign.sh": "delivery",
        "src/public/api_client.ts": "public-contract",
        "src/exports.ts": "public-contract",
        "src/auth/session.py": "security",
    }
    for path, tag in true_positives.items():
        if tag not in risk_tags(path):
            raise RuntimeError(f"risk tag {tag} missed {path}")


def exercise_out_mode(temp: Path, builder: Path, default_bundle: dict[str, Any]) -> None:
    """--out writes the unchanged bundle plus raw patch and prints a compact ledger."""
    repo = temp / "clean-runtime-change"
    out = temp / "out-bundle"
    result = run(
        [sys.executable, str(builder), "--repo", str(repo), "--mode", "local", "--out", str(out)],
        repo,
    )
    written = json.loads((out / "bundle.json").read_text(encoding="utf-8"))
    if written != default_bundle:
        raise RuntimeError("--out bundle.json differs from the default stdout bundle")
    if (out / "patch.diff").read_bytes() != default_bundle["patch"].encode("utf-8"):
        raise RuntimeError("--out patch.diff is not the raw bundle patch")
    stdout = result.stdout
    if f"fingerprint: {default_bundle['fingerprint']}" not in stdout or '"patch"' in stdout:
        raise RuntimeError("--out must print the compact summary, not the bundle JSON")
    ledger = stdout.split("files:\n", 1)[1].splitlines()
    if len(ledger) != len(default_bundle["files"]) or not all(
        line.split(" ")[1] == item["path"]
        for line, item in zip(ledger, default_bundle["files"])
    ):
        raise RuntimeError(f"--out ledger must list one line per file: {ledger}")
    summary_line = f"fingerprint={default_bundle['fingerprint']}"
    if summary_line not in result.stderr or len(result.stderr.strip().splitlines()) != 1:
        raise RuntimeError("builder must print exactly one stderr summary line")
    default = run(
        [sys.executable, str(builder), "--repo", str(repo), "--mode", "local"], repo
    )
    if summary_line not in default.stderr or json.loads(default.stdout) != default_bundle:
        raise RuntimeError("default mode must keep stdout JSON and add the stderr summary")

    inside = run(
        [
            sys.executable,
            str(builder),
            "--repo",
            str(repo),
            "--mode",
            "local",
            "--out",
            str(repo / "review-out"),
        ],
        repo,
        check=False,
    )
    if (
        inside.returncode != 2
        or "outside the repository" not in inside.stderr
        or (repo / "review-out").exists()
    ):
        raise RuntimeError("--out inside the repository must fail closed without writing")
    # On a case-insensitive filesystem a differently cased spelling of the checkout
    # is still the checkout: writing there would break the read-only contract.
    recased = repo.parent / repo.name.swapcase()
    if recased.exists() and os.path.samefile(recased, repo):
        cased = run(
            [sys.executable, str(builder), "--repo", str(repo), "--mode", "local", "--out", str(recased / "review-case")],
            repo,
            check=False,
        )
        if cased.returncode != 2 or "outside the repository" not in cased.stderr or (repo / "review-case").exists():
            raise RuntimeError("--out inside the repository under another case must fail closed")
    else:
        print("test_review_harness: case-sensitive filesystem; recased --out case skipped", file=sys.stderr)

    # An identical rebuild must not refresh the bundle: the scaffold dates receipts
    # against it, so a rewrite would turn valid post-bundle receipts into stale ones.
    kept_mtime = (out / "bundle.json").stat().st_mtime_ns
    run(
        [sys.executable, str(builder), "--repo", str(repo), "--mode", "local", "--out", str(out)],
        repo,
    )
    if (out / "bundle.json").stat().st_mtime_ns != kept_mtime:
        raise RuntimeError("an identical --out rebuild must leave bundle.json untouched")

    other_repo = temp / "functional-regression"
    clobber = run(
        [
            sys.executable,
            str(builder),
            "--repo",
            str(other_repo),
            "--mode",
            "local",
            "--out",
            str(out),
        ],
        other_repo,
        check=False,
    )
    retained = json.loads((out / "bundle.json").read_text(encoding="utf-8"))
    if (
        clobber.returncode != 2
        or "refusing to overwrite" not in clobber.stderr
        or retained != default_bundle
    ):
        raise RuntimeError("--out must never overwrite a different retained bundle")


def commit_all(repo: Path, message: str) -> str:
    run(["git", "add", "-A"], repo)
    run(["git", "commit", "-q", "-m", message], repo)
    return run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


def build_out(builder: Path, repo: Path, out: Path, *mode_args: str) -> Path:
    run(
        [sys.executable, str(builder), "--repo", str(repo), *mode_args, "--out", str(out)],
        repo,
    )
    return out / "bundle.json"


def scaffold_report(out: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(
        [sys.executable, str(SCAFFOLD), *args, "--out", str(out)], out.parent, check=False
    )


def validate_with(
    validator: Path, bundle_path: Path, report: dict[str, Any], report_path: Path
) -> subprocess.CompletedProcess[str]:
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return run(
        [sys.executable, str(validator), "--bundle", str(bundle_path), str(report_path)],
        report_path.parent,
        check=False,
    )


def fill_judgment(report: dict[str, Any], result: str) -> dict[str, Any]:
    """Stand in for the reviewer: only fields the scaffold must leave empty."""
    if not report["intent"]["intended_behavior"]:
        report["intent"].update(
            {
                "intended_behavior": ["Fixture behavior changes as requested"],
                "invariants": ["Review evidence remains tied to the frozen diff"],
                "owner_boundary": "fixture repository",
                "user_visible_change": False,
            }
        )
    for row in report["file_coverage"]:
        row["reason"] = row["reason"] or "Fixture file reviewed"
    if not report["test_coverage"]:
        report["test_coverage"] = [
            {
                "behavior": "Fixture behavior",
                "level": "UNIT",
                "status": "COVERED",
                "paths": [],
                "reason": "Harness contract check",
                "finding_id": None,
            }
        ]
    for row in report["validations"]:
        row["reason"] = row["reason"] or "Receipt-backed fixture check"
    report["behavior_proof"] = {"status": "NOT_APPLICABLE", "evidence": []}
    report["decision"].update({"result": result, "confidence": "HIGH"})
    return report


def expect_rejected(
    completed: subprocess.CompletedProcess[str], marker: str, label: str
) -> None:
    if completed.returncode == 0 or marker not in completed.stderr:
        raise RuntimeError(f"{label}: expected rejection containing {marker!r}: {completed.stderr}")


def exercise_scaffold_and_delta(temp: Path, builder: Path, validator: Path) -> None:
    """Scaffolds prefill only derivable fields; DELTA reviews carry forward only what
    the validator can prove unchanged and must re-adjudicate every open finding."""
    repo = temp / "delta-review"
    repo.mkdir()
    run(["git", "init", "-q", "-b", "trunk"], repo)
    run(["git", "config", "user.email", "review-fixture@example.invalid"], repo)
    run(["git", "config", "user.name", "Review Fixture"], repo)
    write_files(
        repo,
        {
            "src/rates.py": "def rate(amount):\n    return amount\n",
            "src/label.py": "def label(value):\n    return str(value)\n",
        },
    )
    commit_all(repo, "baseline")
    run(["git", "switch", "-q", "-c", "feature"], repo)
    write_files(
        repo,
        {
            "src/rates.py": "def rate(amount):\n    return amount * 2\n",
            "src/label.py": "def label(value):\n    return f'{value}!'\n",
        },
    )
    head0 = commit_all(repo, "feature change")
    bundle0 = build_out(builder, repo, temp / "delta-b0", "--mode", "branch", "--base", "trunk", "--head", head0)
    make_receipt(temp / "receipts-r0", "CMD-001", "TARGET", "echo cycle-one")

    report0_path = temp / "delta-r0.json"
    scaffolded = scaffold_report(
        report0_path, "--bundle", str(bundle0), "--receipts-dir", str(temp / "receipts-r0")
    )
    if scaffolded.returncode != 0:
        raise RuntimeError(f"FULL scaffold failed: {scaffolded.stderr}")
    raw = json.loads(report0_path.read_text(encoding="utf-8"))
    bundle0_data = json.loads(bundle0.read_text(encoding="utf-8"))
    receipt0 = json.loads((temp / "receipts-r0/CMD-001.receipt.json").read_text(encoding="utf-8"))
    if (
        raw["target"]["bundle_fingerprint"] != bundle0_data["fingerprint"]
        or raw["scope"]["current_file_count"] != bundle0_data["summary"]["file_count"]
        or raw["validations"][0]["command"] != " ".join(receipt0["argv"])
        or raw["publication"]["status"] != "NOT_REQUESTED"
        or [row["path"] for row in raw["file_coverage"]] != ["src/label.py", "src/rates.py"]
    ):
        raise RuntimeError("scaffold did not derive mechanical fields from real files")
    # Fail closed: an unfilled scaffold must never validate.
    unfilled = validate_with(validator, bundle0, raw, temp / "delta-unfilled.json")
    for marker in ("intent.intended_behavior", "reason must be a non-empty string", "decision.result is invalid"):
        expect_rejected(unfilled, marker, "unfilled scaffold")
    if scaffold_report(report0_path, "--bundle", str(bundle0)).returncode != 2:
        raise RuntimeError("scaffold must refuse to overwrite an existing report")

    report0 = fill_judgment(raw, "CHANGES_REQUIRED")
    report0["findings"] = [
        {
            "id": "F1",
            "severity": "BLOCKER",
            "status": "ACCEPTED",
            "scope": "IN_SCOPE",
            "path": "src/rates.py",
            "line": 2,
            "side": "NEW",
            "failure_mode": "Rate doubles instead of applying the agreed factor",
            "impact": "Totals are wrong",
            "evidence": ["src/rates.py:2"],
            "required_change": "Apply the agreed factor",
            "test_gap": False,
            "rejection_reason": None,
        }
    ]
    report0["decision"]["remaining_corrections"] = ["F1"]
    if validate_with(validator, bundle0, report0, report0_path).returncode != 0:
        raise RuntimeError("cycle-one CHANGES_REQUIRED report was rejected")

    write_files(repo, {"src/rates.py": "def rate(amount):\n    return amount * 3\n"})
    head1 = commit_all(repo, "correct rate")
    bundle1 = build_out(builder, repo, temp / "delta-b1", "--mode", "branch", "--base", "trunk", "--head", head1)
    delta = build_out(builder, repo, temp / "delta-d", "--mode", "range", "--range", f"{head0}..{head1}")
    make_receipt(temp / "receipts-r1", "CMD-001", "TARGET", "echo cycle-two")
    report1_path = temp / "delta-r1.json"
    scaffolded = scaffold_report(
        report1_path,
        "--bundle", str(bundle1),
        "--receipts-dir", str(temp / "receipts-r1"),
        "--base-review", str(report0_path),
        "--base-bundle", str(bundle0),
        "--delta-bundle", str(delta),
    )
    if scaffolded.returncode != 0:
        raise RuntimeError(f"DELTA scaffold failed: {scaffolded.stderr}")
    report1 = json.loads(report1_path.read_text(encoding="utf-8"))
    basis = report1["review_basis"]
    if (
        basis["mode"] != "DELTA"
        or basis["carried_forward"] != ["src/label.py"]
        or [finding["id"] for finding in report1["findings"]] != ["F1"]
        or report1["scope"]["review_cycle"] != 2
    ):
        raise RuntimeError(f"DELTA scaffold carried the wrong state: {basis}")
    # A carried coverage judgment is never re-used untouched on the new head.
    carried_rows = [row for row in report1["test_coverage"] if row["finding_id"] is None]
    if not carried_rows or any(row["reason"] for row in carried_rows):
        raise RuntimeError(f"DELTA scaffold must clear carried test_coverage reasons: {carried_rows}")
    untouched = fill_judgment(copy.deepcopy(report1), "APPROVE")
    untouched["findings"] = []
    untouched["decision"]["remaining_corrections"] = []
    untouched["review_basis"]["resolved_findings"] = [
        {"id": "F1", "evidence": "rates.py now applies the agreed factor"}
    ]
    expect_rejected(
        validate_with(validator, bundle1, untouched, temp / "delta-untouched.json"),
        "test_coverage[0].reason",
        "untouched carried test_coverage",
    )
    for row in carried_rows:
        row["reason"] = "Re-affirmed against the delta: rates.py test still covers it"
    report1 = fill_judgment(report1, "APPROVE")
    report1["findings"] = []
    report1["decision"]["remaining_corrections"] = []
    basis = report1["review_basis"]
    basis["resolved_findings"] = [{"id": "F1", "evidence": "rates.py now applies the agreed factor"}]
    check_path = temp / "delta-check.json"
    accepted = validate_with(validator, bundle1, report1, check_path)
    if accepted.returncode != 0:
        raise RuntimeError(f"valid DELTA review rejected: {accepted.stderr}")

    def variant(mutate: Any) -> dict[str, Any]:
        value = copy.deepcopy(report1)
        mutate(value)
        return value

    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"]["carried_forward"].append("src/rates.py")), check_path),
        "patch changed since the base review",
        "carried changed file",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(resolved_findings=[])), check_path),
        "prior open finding F1 must be re-adjudicated",
        "dropped prior finding",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"]["resolved_findings"].append({"id": "F9", "evidence": "never open"})), check_path),
        "resolved finding F9 is not an open base review finding",
        "resolving an unknown finding",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["findings"].append(copy.deepcopy(report0["findings"][0]))), check_path),
        "resolved finding F1 must not remain in findings",
        "resolved finding still listed",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["scope"].update(review_cycle=1)), check_path),
        "must exceed the base review cycle",
        "cycle reset",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["file_coverage"][0].update(reason="Re-worded")), check_path),
        "must equal the base review row",
        "edited carried row",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(mode="FULL", delta_bundle=None)), check_path),
        "FULL review must not carry coverage forward",
        "FULL with carry-forward",
    )
    tampered_base = copy.deepcopy(report0)
    tampered_base["decision"]["result"] = "APPROVE"
    tampered_path = temp / "delta-r0-tampered.json"
    tampered_path.write_text(json.dumps(tampered_base), encoding="utf-8")
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(base_review=str(tampered_path))), check_path),
        "review_basis.base_review is not VALID",
        "invalid base review",
    )
    wrong_delta = build_out(builder, repo, temp / "delta-wrong", "--mode", "range", "--range", f"trunk..{head1}")
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(delta_bundle=str(wrong_delta))), check_path),
        "delta_bundle base must equal the base review head",
        "delta from the wrong base",
    )
    branch_delta = build_out(builder, repo, temp / "delta-branch-d", "--mode", "branch", "--base", head0, "--head", head1)
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(delta_bundle=str(branch_delta))), check_path),
        "must be a range bundle",
        "branch-mode delta bundle",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(base_review=None, base_bundle=None, delta_bundle=None, carried_forward=[])), check_path),
        "DELTA review requires review_basis.base_review",
        "DELTA without a base review",
    )
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(mode="FULL", carried_forward=[])), check_path),
        "FULL review must not cite review_basis.delta_bundle",
        "FULL citing a delta bundle",
    )
    forged_delta = temp / "delta-forged.json"
    forged = json.loads(delta.read_text(encoding="utf-8"))
    forged["patch"] += "\n"
    forged_delta.write_text(json.dumps(forged), encoding="utf-8")
    expect_rejected(
        validate_with(validator, bundle1, variant(lambda r: r["review_basis"].update(delta_bundle=str(forged_delta))), check_path),
        "review_basis.delta_bundle is invalid",
        "tampered delta bundle",
    )
    # A delta that stops at an older head would let later changes (here a
    # risk-tagged auth change) escape the FULL-review triggers.
    run(["git", "switch", "-q", "-c", "after-delta", head1], repo)
    write_files(repo, {"src/auth/guard.py": "ALLOW = True\n"})
    head2 = commit_all(repo, "auth change after the delta head")
    bundle2 = build_out(builder, repo, temp / "delta-b2", "--mode", "branch", "--base", "trunk", "--head", head2)
    make_receipt(temp / "receipts-r2", "CMD-001", "TARGET", "echo cycle-three")
    older_path = temp / "delta-older-head.json"
    if scaffold_report(older_path, "--bundle", str(bundle2), "--receipts-dir", str(temp / "receipts-r2"), "--base-review", str(report0_path), "--base-bundle", str(bundle0)).returncode != 0:
        raise RuntimeError("FULL scaffold with a base review on a later head failed")
    older = fill_judgment(json.loads(older_path.read_text(encoding="utf-8")), "APPROVE")
    older["findings"] = []
    older["decision"]["remaining_corrections"] = []
    base_label = next(row for row in report0["file_coverage"] if row["path"] == "src/label.py")
    for row in older["file_coverage"]:
        if row["path"] == "src/label.py":
            row.update(base_label)
    older["review_basis"].update(
        mode="DELTA",
        delta_bundle=str(delta),
        carried_forward=["src/label.py"],
        resolved_findings=[{"id": "F1", "evidence": "rates.py now applies the agreed factor"}],
    )
    expect_rejected(
        validate_with(validator, bundle2, older, temp / "delta-older-head-check.json"),
        "head must equal the reviewed head",
        "delta ending at an older head",
    )
    # A delta whose --path filter hides that auth change: DELTA reads only the
    # delta patch, so the validator and the scaffold both refuse it.
    hidden = build_out(builder, repo, temp / "delta-hidden-d", "--mode", "range", "--range", f"{head0}..{head2}", "--path", "src/rates.py")
    expect_rejected(
        validate_with(validator, bundle2, {**older, "review_basis": {**older["review_basis"], "delta_bundle": str(hidden)}}, temp / "delta-hidden-check.json"),
        "path filters must match the bundle",
        "path-filtered delta",
    )
    base_args2 = ("--bundle", str(bundle2), "--base-review", str(report0_path), "--base-bundle", str(bundle0))
    for name, delta_arg, marker in (
        ("older", delta, "head must equal the reviewed head"),
        ("hidden", hidden, "path filters must match the bundle"),
    ):
        refused = scaffold_report(temp / f"delta-{name}-refused.json", *base_args2, "--delta-bundle", str(delta_arg))
        if refused.returncode != 2 or "rebuild the delta" not in refused.stderr or marker not in refused.stderr:
            raise RuntimeError(f"scaffold accepted a {name} delta: {refused.stderr}")
    # A commit target is always reviewed FULL, even for a small untagged delta.
    commit_b0 = build_out(builder, repo, temp / "delta-commit-b0", "--mode", "commit", "--commit", head0)
    make_receipt(temp / "receipts-c0", "CMD-001", "TARGET", "echo commit-one")
    commit_r0_path = temp / "delta-commit-r0.json"
    if scaffold_report(commit_r0_path, "--bundle", str(commit_b0), "--receipts-dir", str(temp / "receipts-c0")).returncode != 0:
        raise RuntimeError("commit-target scaffold failed")
    commit_r0 = fill_judgment(json.loads(commit_r0_path.read_text(encoding="utf-8")), "CHANGES_REQUIRED")
    commit_r0["findings"] = copy.deepcopy(report0["findings"])
    commit_r0["decision"]["remaining_corrections"] = ["F1"]
    if validate_with(validator, commit_b0, commit_r0, commit_r0_path).returncode != 0:
        raise RuntimeError("commit-target base review was rejected")
    run(["git", "switch", "-q", "-c", "amended", head0], repo)
    write_files(repo, {"src/rates.py": "def rate(amount):\n    return amount * 3\n"})
    run(["git", "add", "-A"], repo)
    run(["git", "commit", "-q", "--amend", "--no-edit"], repo)
    amended = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    commit_b1 = build_out(builder, repo, temp / "delta-commit-b1", "--mode", "commit", "--commit", amended)
    commit_delta = build_out(builder, repo, temp / "delta-commit-d", "--mode", "range", "--range", f"{head0}..{amended}")
    base_args = ("--base-review", str(commit_r0_path), "--base-bundle", str(commit_b0))
    refused = scaffold_report(temp / "delta-commit.json", "--bundle", str(commit_b1), *base_args, "--delta-bundle", str(commit_delta))
    if refused.returncode != 2 or "cannot be delta-reviewed" not in refused.stderr:
        raise RuntimeError(f"scaffold allowed a DELTA review of a commit target: {refused.stderr}")
    commit_full_path = temp / "delta-commit-full.json"
    if scaffold_report(commit_full_path, "--bundle", str(commit_b1), *base_args).returncode != 0:
        raise RuntimeError("commit-target FULL scaffold with a base review failed")
    claimed = json.loads(commit_full_path.read_text(encoding="utf-8"))
    claimed["review_basis"].update(mode="DELTA", delta_bundle=str(commit_delta))
    expect_rejected(
        validate_with(validator, commit_b1, claimed, temp / "delta-commit-check.json"),
        "cannot be delta-reviewed",
        "commit-target DELTA",
    )

    # Full-review triggers: a risk-tagged delta (including the fail-safe substring
    # hints the precise tags skip, e.g. rwlock), or a delta larger than the change.
    for label, files, marker in (
        ("risk", {"src/auth/guard.py": "ALLOW = False\n"}, "risk-tagged paths"),
        ("hint", {"src/sync/rwlock.rs": "// shared lock\n"}, "risk-tagged paths: src/sync/rwlock.rs"),
        ("size", {"src/rates.py": "".join(f"# note {n}\n" for n in range(12)) + "def rate(amount):\n    return amount * 3\n"}, "larger than the original change"),
    ):
        run(["git", "switch", "-q", "-c", f"fix-{label}", head0], repo)
        write_files(repo, files)
        head_x = commit_all(repo, f"{label} correction")
        bundle_x = build_out(builder, repo, temp / f"delta-{label}-b", "--mode", "branch", "--base", "trunk", "--head", head_x)
        delta_x = build_out(builder, repo, temp / f"delta-{label}-d", "--mode", "range", "--range", f"{head0}..{head_x}")
        refused = scaffold_report(
            temp / f"delta-{label}.json",
            "--bundle", str(bundle_x),
            "--base-review", str(report0_path),
            "--base-bundle", str(bundle0),
            "--delta-bundle", str(delta_x),
        )
        if refused.returncode != 2 or "FULL review required" not in refused.stderr or marker not in refused.stderr:
            raise RuntimeError(f"{label}: scaffold allowed a DELTA review: {refused.stderr}")
        full_path = temp / f"delta-{label}-full.json"
        if scaffold_report(full_path, "--bundle", str(bundle_x), "--base-review", str(report0_path), "--base-bundle", str(bundle0)).returncode != 0:
            raise RuntimeError(f"{label}: FULL scaffold with a base review failed")
        claimed = json.loads(full_path.read_text(encoding="utf-8"))
        claimed["review_basis"].update(mode="DELTA", delta_bundle=str(delta_x))
        expect_rejected(
            validate_with(validator, bundle_x, claimed, temp / f"delta-{label}-check.json"),
            f"DELTA review not allowed (delta {'is ' if label == 'size' else 'touches '}",
            f"{label} trigger",
        )

    # A base review must target the same mode, base, and path filters, even for FULL.
    filtered = build_out(builder, repo, temp / "delta-filtered-b", "--mode", "branch", "--base", "trunk", "--head", head1, "--path", "src/rates.py")
    refused = scaffold_report(temp / "delta-filtered-refused.json", "--bundle", str(filtered), "--base-review", str(report0_path), "--base-bundle", str(bundle0))
    if refused.returncode != 2 or "targets another review" not in refused.stderr:
        raise RuntimeError(f"scaffold accepted a base review for another target: {refused.stderr}")
    make_receipt(temp / "receipts-filtered", "CMD-001", "TARGET", "echo filtered")
    filtered_path = temp / "delta-filtered.json"
    if scaffold_report(filtered_path, "--bundle", str(filtered), "--receipts-dir", str(temp / "receipts-filtered")).returncode != 0:
        raise RuntimeError("filtered FULL scaffold failed")
    mismatched = fill_judgment(json.loads(filtered_path.read_text(encoding="utf-8")), "CHANGES_REQUIRED")
    mismatched["findings"] = copy.deepcopy(report0["findings"])
    mismatched["decision"]["remaining_corrections"] = ["F1"]
    mismatched["scope"]["review_cycle"] = 2
    mismatched["review_basis"].update(base_review=str(report0_path), base_bundle=str(bundle0))
    expect_rejected(
        validate_with(validator, filtered, mismatched, temp / "delta-filtered-check.json"),
        "base_review targets another review (path filters changed",
        "FULL with a base review of another target",
    )
    # FULL without a usable base still records a prior finding the correction fixed
    # as resolved (never REJECTED); it cannot also stay open, and nothing carries.
    fallback = copy.deepcopy(mismatched)
    fallback["findings"] = []
    fallback["decision"].update(result="APPROVE", remaining_corrections=[])
    fallback["review_basis"].update(
        base_review=None,
        base_bundle=None,
        resolved_findings=[{"id": "F1", "evidence": "rates.py now applies the agreed factor"}],
    )
    fallback_path = temp / "delta-fallback.json"
    accepted = validate_with(validator, filtered, fallback, fallback_path)
    if accepted.returncode != 0:
        raise RuntimeError(f"FULL review without a base rejected a resolved prior finding: {accepted.stderr}")
    still_open = copy.deepcopy(fallback)
    still_open["findings"] = copy.deepcopy(report0["findings"])
    still_open["decision"].update(result="CHANGES_REQUIRED", remaining_corrections=["F1"])
    expect_rejected(
        validate_with(validator, filtered, still_open, fallback_path),
        "resolved finding F1 must not remain in findings",
        "resolved and still open without a base",
    )
    fallback["review_basis"]["carried_forward"] = ["src/rates.py"]
    expect_rejected(
        validate_with(validator, filtered, fallback, fallback_path),
        "review_basis.carried_forward requires base_review",
        "carry-forward without a base",
    )

    # The shared-receipts-directory flow must fail closed: cycle-one receipts are
    # stale proof for the new head, and overwriting them breaks the base review.
    make_receipt(temp / "receipts-r0", "CMD-002", "TARGET", "echo shared-dir")
    stale = scaffold_report(temp / "delta-shared.json", "--bundle", str(bundle1), "--receipts-dir", str(temp / "receipts-r0"), "--base-review", str(report0_path), "--base-bundle", str(bundle0))
    if stale.returncode != 2 or "predates the bundle" not in stale.stderr:
        raise RuntimeError(f"scaffold prefilled receipts that predate the bundle: {stale.stderr}")
    for receipt_id in ("CMD-001", "CMD-002"):
        shared_path = temp / "receipts-r0" / f"{receipt_id}.receipt.json"
        shared_argv = json.loads(shared_path.read_text(encoding="utf-8"))["argv"]
        shared_row = {
            "command": " ".join(shared_argv),
            "status": "PASS",
            "classification": "TARGET",
            "reason": "Reused directory",
            "receipt": str(shared_path),
        }
        expect_rejected(
            validate_with(validator, bundle1, variant(lambda r: r["validations"].append(shared_row)), check_path),
            "in a base review's receipts directory",
            f"receipt {receipt_id} from the base review's directory",
        )
    make_receipt(temp / "receipts-r0", "CMD-001", "TARGET", "echo overwritten")
    expect_rejected(
        validate_with(validator, bundle1, report1, check_path),
        "review_basis.base_review is not VALID",
        "base review whose receipt was overwritten",
    )


def main() -> int:
    args = parse_args()
    try:
        if args.list:
            for name in sorted(FIXTURES):
                print(f"{name}: {FIXTURES[name]['request']}")
            return 0
        if args.materialize:
            if not args.output:
                raise RuntimeError("--materialize requires --output")
            output = materialize(args.materialize, Path(args.output).resolve())
            print(
                json.dumps(
                    {
                        "fixture": args.materialize,
                        "repo": str(output),
                        "request": FIXTURES[args.materialize]["request"],
                    }
                )
            )
            return 0
        if args.score:
            failed = False
            for value in args.score:
                if "=" not in value:
                    raise RuntimeError("--score requires FIXTURE=REPORT.json")
                name, raw_path = value.split("=", 1)
                if name not in FIXTURES:
                    raise RuntimeError(f"unknown fixture: {name}")
                passed, errors = score_report(name, Path(raw_path))
                print(f"{name}: {'PASS' if passed else 'FAIL'}")
                for error in errors:
                    print(f"  - {error}")
                failed = failed or not passed
            return 1 if failed else 0

        self_test()
        print(
            f"PASS: {len(FIXTURES)} semantic fixtures; target modes, path filters, "
            "rename/delete, Git isolation, bundle safety, strict semantic scoring, "
            "proposal publication states, report validation, --out ledger, risk-tag "
            "precision, fail-closed scaffold, and DELTA re-review gates"
        )
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"test_review_harness: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
