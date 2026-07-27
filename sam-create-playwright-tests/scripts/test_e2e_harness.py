#!/usr/bin/env python3
"""Self-test the E2E bundle, audit, and report validator with semantic fixtures."""

from __future__ import annotations

import copy
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
BUILDER = HERE / "build_e2e_bundle.py"
AUDITOR = HERE / "audit_test_diff.py"
RUN_CHECKED = HERE / "run_checked.py"
VALIDATOR = HERE / "validate_e2e_report.py"


def run(
    *command: str,
    cwd: pathlib.Path | None = None,
    expected: int = 0,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True, check=False
    )
    if result.returncode != expected:
        raise AssertionError(
            f"expected {expected}, got {result.returncode}: {' '.join(command)}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def write_probe(path: pathlib.Path, marker: pathlib.Path) -> None:
    path.write_text(
        f"#!/bin/sh\nprintf invoked >> {shlex.quote(str(marker))}\nexit 97\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def verify_git_isolation() -> None:
    with tempfile.TemporaryDirectory(prefix="sam-e2e-git-safety-") as temporary:
        root = pathlib.Path(temporary)
        run("git", "init", "-q", cwd=root)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
        run("git", "config", "user.name", "Fixture", cwd=root)
        (root / "src").mkdir()
        (root / ".gitattributes").write_text(
            "*.js diff=evil filter=evil\n", encoding="utf-8"
        )
        (root / "src" / "kept.js").write_text(
            "export const kept = 1;\n", encoding="utf-8"
        )
        (root / "src" / "rename-old.js").write_text(
            "export const renamed = 1;\n", encoding="utf-8"
        )
        (root / "src" / "deleted.js").write_text(
            "export const deleted = 1;\n", encoding="utf-8"
        )
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-qm", "base", cwd=root)
        (root / "src" / "kept.js").write_text(
            "export const kept = 2;\n", encoding="utf-8"
        )
        run("git", "mv", "src/rename-old.js", "src/rename-new.js", cwd=root)
        run("git", "rm", "-q", "src/deleted.js", cwd=root)
        (root / "notes.txt").write_text("untracked proof\n", encoding="utf-8")

        index_raw = run(
            "git", "rev-parse", "--git-path", "index", cwd=root
        ).stdout.strip()
        index_path = pathlib.Path(index_raw)
        if not index_path.is_absolute():
            index_path = root / index_path
        index_before = index_path.read_bytes()
        index_mtime = index_path.stat().st_mtime_ns

        marker = root / "git-probe-ran"
        probe = root / "git-probe"
        write_probe(probe, marker)
        fake_bin = root / "repo-bin"
        fake_bin.mkdir()
        fake_git_marker = root / "fake-git-ran"
        write_probe(fake_bin / "git", fake_git_marker)
        run("git", "config", "core.fsmonitor", str(probe), cwd=root)
        run("git", "config", "diff.external", str(probe), cwd=root)
        run("git", "config", "diff.evil.command", str(probe), cwd=root)
        run("git", "config", "diff.evil.textconv", str(probe), cwd=root)

        temp_indexes = root / "temporary-indexes"
        temp_indexes.mkdir()
        inherited = os.environ.copy()
        inherited.update(
            {
                "PATH": f"{fake_bin}{os.pathsep}{inherited.get('PATH', '')}",
                "TMPDIR": str(temp_indexes),
                "GIT_DIR": str(root / "redirected.git"),
                "GIT_WORK_TREE": str(root / "redirected-worktree"),
                "GIT_INDEX_FILE": str(root / "attacker-index"),
                "GIT_OBJECT_DIRECTORY": str(root / "attacker-objects"),
                "GIT_EXTERNAL_DIFF": str(probe),
                "GIT_CONFIG_COUNT": "3",
                "GIT_CONFIG_KEY_0": "core.fsmonitor",
                "GIT_CONFIG_VALUE_0": str(probe),
                "GIT_CONFIG_KEY_1": "diff.external",
                "GIT_CONFIG_VALUE_1": str(probe),
                "GIT_CONFIG_KEY_2": "filter.inherited.clean",
                "GIT_CONFIG_VALUE_2": str(probe),
            }
        )
        builder_command = (
            sys.executable,
            str(BUILDER),
            "--repo",
            str(root / "src"),
            "--path",
            "src",
            "--path",
            "notes.txt",
        )
        result = run(*builder_command, env=inherited)
        bundle = json.loads(result.stdout)
        records = {item["path"]: item for item in bundle["files"]}
        expected = {"src/kept.js", "src/rename-new.js", "src/deleted.js", "notes.txt"}
        if set(records) != expected:
            raise AssertionError(f"local Git states were not preserved: {records}")
        if not records["src/rename-new.js"]["status"].startswith("R"):
            raise AssertionError("staged rename was not preserved")
        if records["src/rename-new.js"]["previous_path"] != "src/rename-old.js":
            raise AssertionError("rename source was not preserved")
        if records["src/deleted.js"]["status"] != "D":
            raise AssertionError("staged deletion was not preserved")
        if records["notes.txt"]["status"] != "?":
            raise AssertionError("untracked file was not preserved")

        run("git", "config", "filter.evil.clean", str(probe), cwd=root)
        blocked = run(*builder_command, env=inherited, expected=2)
        if "configured clean/process filters" not in blocked.stderr:
            raise AssertionError("configured clean filter did not fail closed")
        run("git", "config", "--unset", "filter.evil.clean", cwd=root)

        secret_sentinel = "R3ALCRED_9f71c6aa83d24bc7e158cc31"
        secret_file = root / "src" / "credential.js"
        secret_file.write_text(
            f'export const api_key = "{secret_sentinel}";\n', encoding="utf-8"
        )
        secret_result = run(*builder_command, env=inherited, expected=2)
        if "secret-like content" not in secret_result.stderr:
            raise AssertionError("secret-like patch content was not rejected")
        if (
            secret_sentinel in secret_result.stdout
            or secret_sentinel in secret_result.stderr
        ):
            raise AssertionError("builder leaked rejected secret-like content")

        secret_file.write_text(
            'export const api_key = "changeme_placeholder_credential";\n',
            encoding="utf-8",
        )
        (root / "src" / ".env.example").write_text(
            "API_KEY=changeme_placeholder_credential\n", encoding="utf-8"
        )
        placeholder_bundle = json.loads(run(*builder_command, env=inherited).stdout)
        placeholder_paths = {item["path"] for item in placeholder_bundle["files"]}
        if not {"src/credential.js", "src/.env.example"}.issubset(placeholder_paths):
            raise AssertionError("safe placeholder/template files were rejected")

        private_sentinel = "PRIVATE_MATERIAL_MUST_NOT_LEAK_12d3"
        (root / "src" / "id_ed25519").write_text(private_sentinel, encoding="utf-8")
        sensitive_result = run(*builder_command, env=inherited, expected=2)
        if "refusing sensitive path" not in sensitive_result.stderr:
            raise AssertionError("private artifact path was not rejected")
        if (
            private_sentinel in sensitive_result.stdout
            or private_sentinel in sensitive_result.stderr
        ):
            raise AssertionError("builder leaked sensitive-file content")
        if marker.exists() or fake_git_marker.exists():
            raise AssertionError("repository-controlled Git integration executed")
        if (
            index_path.read_bytes() != index_before
            or index_path.stat().st_mtime_ns != index_mtime
        ):
            raise AssertionError("builder mutated the real Git index")
        if any(temp_indexes.iterdir()):
            raise AssertionError("temporary Git index was not cleaned")
        if (root / "attacker-index").exists():
            raise AssertionError("inherited GIT_INDEX_FILE was used")


def verify_base_resolution() -> None:
    with tempfile.TemporaryDirectory(prefix="sam-e2e-base-") as temporary:
        outer = pathlib.Path(temporary)
        root = outer / "work"
        remote = outer / "remote.git"
        root.mkdir()
        run("git", "init", "-q", cwd=root)
        run("git", "checkout", "-qb", "trunk", cwd=root)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
        run("git", "config", "user.name", "Fixture", cwd=root)
        (root / "app.txt").write_text("base\n", encoding="utf-8")
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-qm", "base", cwd=root)
        run("git", "checkout", "-qb", "feature", cwd=root)
        (root / "app.txt").write_text("feature\n", encoding="utf-8")
        run("git", "commit", "-qam", "feature", cwd=root)

        failed = run(sys.executable, str(BUILDER), "--repo", str(root), expected=2)
        if "cannot infer base" not in failed.stderr:
            raise AssertionError("missing base did not fail with actionable guidance")
        explicit = json.loads(
            run(
                sys.executable,
                str(BUILDER),
                "--repo",
                str(root),
                "--base",
                "trunk",
            ).stdout
        )
        if explicit["target"]["base_ref"] != "trunk":
            raise AssertionError("explicit base was not preserved")

        run("git", "init", "--bare", "-q", str(remote), cwd=outer)
        run("git", "remote", "add", "origin", str(remote), cwd=root)
        run("git", "push", "-q", "origin", "trunk:trunk", cwd=root)
        run("git", "push", "-q", "origin", "trunk:feature-base", cwd=root)
        run("git", "fetch", "-q", "origin", cwd=root)
        run(
            "git",
            "branch",
            "--set-upstream-to=origin/feature-base",
            "feature",
            cwd=root,
        )
        upstream = json.loads(
            run(sys.executable, str(BUILDER), "--repo", str(root)).stdout
        )
        if upstream["target"]["base_ref"] != "origin/feature-base":
            raise AssertionError("proven upstream was not used as base")

        run("git", "--git-dir", str(remote), "symbolic-ref", "HEAD", "refs/heads/trunk")
        run("git", "remote", "set-head", "origin", "-a", cwd=root)
        default = json.loads(
            run(sys.executable, str(BUILDER), "--repo", str(root)).stdout
        )
        if default["target"]["base_ref"] != "origin/trunk":
            raise AssertionError("non-main remote default branch was not used")


def write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def make_receipt(
    receipts: pathlib.Path,
    command_id: str,
    classification: str,
    shell: str,
    repeat: int = 2,
) -> dict[str, Any]:
    """Produce a real execution receipt so fixtures cannot fake a PASS."""
    receipts.mkdir(parents=True, exist_ok=True)
    run(
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
    )
    receipt = json.loads(
        (receipts / f"{command_id}.receipt.json").read_text(encoding="utf-8")
    )
    return {
        "path": str(receipts / f"{command_id}.receipt.json"),
        "command": " ".join(receipt["argv"]),
        "status": receipt["status"],
    }


def valid_report(bundle: dict[str, Any], receipts: pathlib.Path) -> dict[str, Any]:
    target = make_receipt(receipts, "CMD-001", "TARGET", "echo '1 passed'")
    before = make_receipt(
        receipts, "CMD-900", "ENVIRONMENT", "echo 'account.spec.js > loads'", repeat=1
    )
    after = make_receipt(
        receipts,
        "CMD-901",
        "ENVIRONMENT",
        "echo 'account.spec.js > loads > saved name remains visible'",
        repeat=1,
    )
    return {
        "baseline_fingerprint": bundle["fingerprint"],
        "bundle_fingerprint": bundle["fingerprint"],
        "target": {
            "base_sha": bundle["target"]["base_sha"],
            "head_sha": bundle["target"]["head_sha"],
        },
        "intent": {
            "summary": "Preserve the account name after save.",
            "invariants": ["Only the current account changes."],
            "no_go": ["Do not alter authentication."],
        },
        "environment": {
            "kind": "dev",
            "identity": "isolated-fixture",
            "real_data": False,
            "evidence": "temporary local repository and synthetic records",
        },
        "authorization": {"publish_requested": False},
        "command_definitions": {
            "changed": bool(bundle["command_definitions"]),
            "inspected": True,
            "evidence": "diff inspected before execution",
        },
        "criteria": [{"id": "AC-001", "text": "Saved name remains visible."}],
        "risks": [
            {
                "id": "R-001",
                "criterion_ids": ["AC-001"],
                "level": "HIGH",
                "evidence": "read-after-write may return stale data",
            }
        ],
        "scenarios": [
            {
                "id": "S-001",
                "criterion_ids": ["AC-001"],
                "risk_ids": ["R-001"],
                "status": "AUTOMATED",
                "test_ids": ["T-001"],
                "artifact_ids": ["ART-001"],
            }
        ],
        "tests": [
            {
                "id": "T-001",
                "scenario_ids": ["S-001"],
                "path": "tests/account.spec.js",
                "name": "saved name remains visible",
                "command_ids": ["CMD-001"],
                "regression_proof": {
                    "status": "CONTRACT",
                    "evidence": "asserts persisted value after a fresh read",
                },
            }
        ],
        "commands": [
            {
                "id": "CMD-001",
                "test_ids": ["T-001"],
                "command": target["command"],
                "status": target["status"],
                "classification": "TARGET",
                "evidence": "1 passed",
                "receipt": target["path"],
            }
        ],
        "artifacts": [
            {
                "id": "ART-001",
                "scenario_ids": ["S-001"],
                "status": "LOCAL",
                "path": "test-results/trace.zip",
                "safety_review": True,
            }
        ],
        "cleanup": [
            {
                "id": "CL-001",
                "resource": "synthetic account record",
                "status": "CLEANED",
            }
        ],
        "test_diff_audit": {"status": "PASS", "evidence": "audit script returned PASS"},
        "test_wiring": {
            "status": "PROVEN",
            "before_receipt": before["path"],
            "after_receipt": after["path"],
            "discovered_tests": ["saved name remains visible"],
            "evidence": ["runner test list before and after the new spec"],
        },
        "behavior_proof": {
            "status": "PROVEN",
            "evidence": "browser assertion and trace",
        },
        "decision": "COMPLETE",
    }


def expect_invalid(
    bundle_path: pathlib.Path,
    report_path: pathlib.Path,
    report: dict[str, Any],
    expect: str | None = None,
) -> None:
    write_json(report_path, report)
    result = run(
        sys.executable,
        str(VALIDATOR),
        "--baseline",
        str(bundle_path),
        "--bundle",
        str(bundle_path),
        str(report_path),
        expected=1,
    )
    if expect is not None and expect not in result.stderr:
        raise AssertionError(
            f"expected rejection reason {expect!r}, got:\n{result.stderr}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sam-e2e-harness-") as temporary:
        root = pathlib.Path(temporary)
        run("git", "init", "-q", cwd=root)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
        run("git", "config", "user.name", "Fixture", cwd=root)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "account.js").write_text(
            "export const name = 'old';\n", encoding="utf-8"
        )
        (root / "tests" / "account.spec.js").write_text(
            "test('old', async () => {});\n", encoding="utf-8"
        )
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-qm", "base", cwd=root)
        (root / "src" / "account.js").write_text(
            "export const name = 'saved';\n", encoding="utf-8"
        )
        (root / "tests" / "account.spec.js").write_text(
            "test('saved name remains visible', async () => { expect('saved').toBe('saved'); });\n",
            encoding="utf-8",
        )

        bundle_path = root / "bundle.json"
        result = run(
            sys.executable,
            str(BUILDER),
            "--repo",
            str(root),
            "--environment-kind",
            "dev",
            "--environment-id",
            "fixture",
        )
        bundle = json.loads(result.stdout)
        write_json(bundle_path, bundle)
        if len(bundle["files"]) != 2 or not bundle["fingerprint"]:
            raise AssertionError("builder did not preserve the complete local target")

        audit_path = root / "audit.json"
        audit = run(sys.executable, str(AUDITOR), str(bundle_path))
        audit_path.write_text(audit.stdout, encoding="utf-8")
        if json.loads(audit.stdout)["status"] != "PASS":
            raise AssertionError("safe test patch should pass audit")

        report_path = root / "report.json"
        receipts = root / "receipts"
        report = valid_report(bundle, receipts)
        write_json(report_path, report)
        run(
            sys.executable,
            str(VALIDATOR),
            "--baseline",
            str(bundle_path),
            "--bundle",
            str(bundle_path),
            str(report_path),
        )

        unsafe_bundle = copy.deepcopy(bundle)
        unsafe_bundle["files"].append(
            {
                "path": "tests/unsafe.spec.js",
                "is_test": True,
                "command_definition": False,
            }
        )
        unsafe_bundle["patch"] += (  # audit-fixture: allow
            "\n+++ b/tests/unsafe.spec.js\n+test.only('focused', async () => {});\n"
        )
        unsafe_path = root / "unsafe-bundle.json"
        write_json(unsafe_path, unsafe_bundle)
        run(sys.executable, str(AUDITOR), str(unsafe_path), expected=1)

        deleted_bundle = copy.deepcopy(bundle)
        deleted_bundle["files"].append(
            {
                "path": "tests/deleted.spec.js",
                "previous_path": None,
                "status": "D",
                "is_test": True,
                "command_definition": False,
            }
        )
        deleted_bundle["patch"] += (
            "\ndiff --git a/tests/deleted.spec.js b/tests/deleted.spec.js\n"
            "deleted file mode 100644\n"
            "--- a/tests/deleted.spec.js\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-expect(true).toBe(true);\n"
        )
        deleted_path = root / "deleted-test-bundle.json"
        write_json(deleted_path, deleted_bundle)
        deleted_audit = json.loads(
            run(sys.executable, str(AUDITOR), str(deleted_path), expected=1).stdout
        )
        deleted_kinds = {item["kind"] for item in deleted_audit["issues"]}
        if not {"TEST_FILE_DELETED", "ASSERTION_REMOVED"}.issubset(deleted_kinds):
            raise AssertionError("deleted test did not retain deletion/assertion audit")

        unsafe_environment = copy.deepcopy(report)
        unsafe_environment["environment"].update({"kind": "unknown", "real_data": True})
        expect_invalid(bundle_path, report_path, unsafe_environment)

        unauthorized_upload = copy.deepcopy(report)
        unauthorized_upload["artifacts"][0].update(
            {"status": "UPLOADED", "receipt": "remote-1", "readback_verified": True}
        )
        expect_invalid(bundle_path, report_path, unauthorized_upload)

        unproven = copy.deepcopy(report)
        unproven["tests"][0]["regression_proof"]["status"] = "NOT_PROVEN"
        expect_invalid(bundle_path, report_path, unproven)

        missing_trace = copy.deepcopy(report)
        missing_trace["scenarios"][0]["test_ids"] = ["T-999"]
        expect_invalid(bundle_path, report_path, missing_trace)

        non_string_reference = copy.deepcopy(report)
        non_string_reference["risks"][0]["criterion_ids"].append(7)
        expect_invalid(bundle_path, report_path, non_string_reference)

        missing_criterion_text = copy.deepcopy(report)
        missing_criterion_text["criteria"][0]["text"] = ""
        expect_invalid(bundle_path, report_path, missing_criterion_text)

        missing_risk_evidence = copy.deepcopy(report)
        missing_risk_evidence["risks"][0]["evidence"] = ""
        expect_invalid(bundle_path, report_path, missing_risk_evidence)

        missing_test_identity = copy.deepcopy(report)
        missing_test_identity["tests"][0]["path"] = ""
        expect_invalid(bundle_path, report_path, missing_test_identity)

        missing_scenario_test_backlink = copy.deepcopy(report)
        second_scenario = copy.deepcopy(missing_scenario_test_backlink["scenarios"][0])
        second_scenario.update({"id": "S-002", "artifact_ids": []})
        missing_scenario_test_backlink["scenarios"].append(second_scenario)
        expect_invalid(bundle_path, report_path, missing_scenario_test_backlink)

        missing_test_command_backlink = copy.deepcopy(report)
        second_command = copy.deepcopy(missing_test_command_backlink["commands"][0])
        second_command["id"] = "CMD-002"
        missing_test_command_backlink["commands"].append(second_command)
        expect_invalid(bundle_path, report_path, missing_test_command_backlink)

        missing_scenario_artifact_backlink = copy.deepcopy(report)
        missing_scenario_artifact_backlink["scenarios"][0]["artifact_ids"] = []
        expect_invalid(bundle_path, report_path, missing_scenario_artifact_backlink)

        # A status typed without an execution receipt is not a result.
        no_receipt = copy.deepcopy(report)
        no_receipt["commands"][0].pop("receipt")
        expect_invalid(bundle_path, report_path, no_receipt, "requires a receipt path")

        # The report cannot disagree with the receipt it cites.
        failing = make_receipt(
            receipts / "failing", "CMD-001", "TARGET", "echo '1 failed'; exit 1"
        )
        lying_status = copy.deepcopy(report)
        lying_status["commands"][0].update(
            {"receipt": failing["path"], "command": failing["command"]}
        )
        expect_invalid(
            bundle_path, report_path, lying_status, "its receipt records"
        )

        # Browser proof must be repeated; one green run does not show determinism.
        single_run = make_receipt(
            receipts / "single", "CMD-001", "TARGET", "echo '1 passed'", repeat=1
        )
        unrepeated = copy.deepcopy(report)
        unrepeated["commands"][0].update(
            {"receipt": single_run["path"], "command": single_run["command"]}
        )
        expect_invalid(bundle_path, report_path, unrepeated, "must run at least")

        # A flaky browser test is the classic false green; it cannot pass.
        flake_flag = receipts / "flake.flag"
        flaky = make_receipt(
            receipts / "flaky",
            "CMD-001",
            "TARGET",
            f"test -f {shlex.quote(str(flake_flag))} && exit 1; "
            f"touch {shlex.quote(str(flake_flag))}; exit 0",
            repeat=3,
        )
        flaky_report = copy.deepcopy(report)
        flaky_report["commands"][0].update(
            {
                "receipt": flaky["path"],
                "command": flaky["command"],
                "status": flaky["status"],
            }
        )
        expect_invalid(bundle_path, report_path, flaky_report, "flaky command(s)")

        # Editing a captured log breaks its recorded hash.
        log = receipts / "CMD-001.run1.log"
        original_log = log.read_bytes()
        log.write_bytes(original_log + b"fabricated success\n")
        expect_invalid(
            bundle_path, report_path, copy.deepcopy(report), "log hash does not match"
        )
        log.write_bytes(original_log)

        # A spec the runner never lists proves nothing.
        unwired = copy.deepcopy(report)
        unwired["test_wiring"]["discovered_tests"] = ["never listed by the runner"]
        expect_invalid(
            bundle_path, report_path, unwired, "not discovered by the runner"
        )

    verify_git_isolation()
    verify_base_resolution()
    print(
        "PASS: E2E bundle, Git isolation/base resolution, reciprocal graph, "
        "audit, safety, and decision fixtures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
