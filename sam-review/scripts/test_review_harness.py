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
        explicit_split = any(
            marker in oversized.stderr
            for marker in ("rather than truncating", "review it as a separate target")
        )
        if oversized.returncode != 2 or not explicit_split:
            raise RuntimeError(
                "oversized bundle did not fail closed without truncation"
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

        scope_blocked = copy.deepcopy(report)
        scope_blocked["scope"]["baseline_file_count"] = 0
        scope_blocked["decision"] = {
            "result": "BLOCKED",
            "confidence": "HIGH",
            "non_gating_requested": False,
            "remaining_corrections": [],
        }
        report_path.write_text(json.dumps(scope_blocked), encoding="utf-8")
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
            raise RuntimeError(f"valid scope block rejected: {scope_valid.stderr}")


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
            "proposal publication states, and report validation"
        )
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"test_review_harness: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
