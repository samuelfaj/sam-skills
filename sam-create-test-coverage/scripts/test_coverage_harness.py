#!/usr/bin/env python3
"""Self-test coverage bundle, anti-gaming audit, and report validation."""

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
BUILDER = HERE / "build_test_impact.py"
AUDITOR = HERE / "audit_test_diff.py"
VALIDATOR = HERE / "validate_coverage_report.py"


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
    with tempfile.TemporaryDirectory(prefix="sam-coverage-git-safety-") as temporary:
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
    with tempfile.TemporaryDirectory(prefix="sam-coverage-base-") as temporary:
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


def dump(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def report_for(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "baseline_fingerprint": bundle["fingerprint"],
        "bundle_fingerprint": bundle["fingerprint"],
        "target": {
            "base_sha": bundle["target"]["base_sha"],
            "head_sha": bundle["target"]["head_sha"],
        },
        "intent": {
            "summary": "Reject invalid transfer amounts.",
            "invariants": ["Valid transfers remain accepted."],
            "no_go": ["Do not alter authentication."],
        },
        "environment": {
            "kind": "test",
            "identity": "temporary-fixture",
            "real_data": False,
            "evidence": "isolated synthetic repository",
        },
        "authorization": {"publish_requested": False},
        "command_definitions": {
            "changed": bool(bundle["command_definitions"]),
            "inspected": True,
            "evidence": "all changed command definitions inspected",
        },
        "criteria": [{"id": "AC-001", "text": "Negative amount is rejected."}],
        "behaviors": [
            {
                "id": "B-001",
                "criterion_ids": ["AC-001"],
                "description": "validator rejects negative values",
                "paths": ["src/transfer.js"],
            }
        ],
        "risks": [
            {
                "id": "R-001",
                "criterion_ids": ["AC-001"],
                "behavior_ids": ["B-001"],
                "level": "HIGH",
                "evidence": "invalid amount could corrupt balances",
            }
        ],
        "scenarios": [
            {
                "id": "S-001",
                "criterion_ids": ["AC-001"],
                "behavior_ids": ["B-001"],
                "risk_ids": ["R-001"],
                "status": "AUTOMATED",
                "layer": "UNIT",
                "sufficiency": "pure deterministic validator branch",
                "test_ids": ["T-001"],
                "artifact_ids": ["ART-001"],
            }
        ],
        "tests": [
            {
                "id": "T-001",
                "scenario_ids": ["S-001"],
                "path": "tests/transfer.test.js",
                "name": "rejects a negative amount",
                "command_ids": ["CMD-001"],
                "regression_proof": {
                    "status": "CONTRACT",
                    "evidence": "asserts the documented non-negative invariant",
                },
            }
        ],
        "commands": [
            {
                "id": "CMD-001",
                "test_ids": ["T-001"],
                "command": "test-runner tests/transfer.test.js",
                "status": "PASS",
                "classification": "TARGET",
                "evidence": "1 passed",
            }
        ],
        "artifacts": [
            {
                "id": "ART-001",
                "scenario_ids": ["S-001"],
                "status": "LOCAL",
                "path": "test-output.txt",
                "safety_review": True,
            }
        ],
        "cleanup": [
            {"id": "CL-001", "resource": "temporary test database", "status": "CLEANED"}
        ],
        "test_diff_audit": {"status": "PASS", "evidence": "audit script returned PASS"},
        "real_system_proof": {
            "status": "NOT_APPLICABLE",
            "evidence": "scenario is a pure validator contract",
        },
        "decision": "FULL",
    }


def invalid(
    bundle_path: pathlib.Path, report_path: pathlib.Path, report: dict[str, Any]
) -> None:
    dump(report_path, report)
    run(
        sys.executable,
        str(VALIDATOR),
        "--baseline",
        str(bundle_path),
        "--bundle",
        str(bundle_path),
        str(report_path),
        expected=1,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sam-coverage-harness-") as temp:
        root = pathlib.Path(temp)
        run("git", "init", "-q", cwd=root)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
        run("git", "config", "user.name", "Fixture", cwd=root)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "transfer.js").write_text(
            "export const valid = () => true;\n", encoding="utf-8"
        )
        (root / "tests" / "transfer.test.js").write_text(
            "test('base', () => {});\n", encoding="utf-8"
        )
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-qm", "base", cwd=root)
        (root / "src" / "transfer.js").write_text(
            "export const valid = n => n >= 0;\n", encoding="utf-8"
        )
        (root / "tests" / "transfer.test.js").write_text(
            "test('negative', () => { expect(-1 >= 0).toBe(false); });\n",
            encoding="utf-8",
        )

        bundle_result = run(
            sys.executable,
            str(BUILDER),
            "--repo",
            str(root),
            "--environment-kind",
            "test",
            "--environment-id",
            "fixture",
        )
        bundle = json.loads(bundle_result.stdout)
        bundle_path = root / "bundle.json"
        dump(bundle_path, bundle)
        if len(bundle["files"]) != 2 or not bundle["fingerprint"]:
            raise AssertionError("bundle lost changed files or fingerprint")
        run(sys.executable, str(AUDITOR), str(bundle_path))

        report_path = root / "report.json"
        valid = report_for(bundle)
        dump(report_path, valid)
        run(
            sys.executable,
            str(VALIDATOR),
            "--baseline",
            str(bundle_path),
            "--bundle",
            str(bundle_path),
            str(report_path),
        )

        weakened_bundle = copy.deepcopy(bundle)
        weakened_bundle["files"].append(
            {
                "path": "tests/weakened.test.js",
                "is_test": True,
                "command_definition": False,
            }
        )
        weakened_bundle["patch"] += (  # audit-fixture: allow
            "\n+++ b/tests/weakened.test.js\n+test.skip('regression', () => {});\n"
        )
        weakened_path = root / "weakened.json"
        dump(weakened_path, weakened_bundle)
        run(sys.executable, str(AUDITOR), str(weakened_path), expected=1)

        deleted_bundle = copy.deepcopy(bundle)
        deleted_bundle["files"].append(
            {
                "path": "tests/deleted.test.js",
                "previous_path": None,
                "status": "D",
                "is_test": True,
                "command_definition": False,
            }
        )
        deleted_bundle["patch"] += (
            "\ndiff --git a/tests/deleted.test.js b/tests/deleted.test.js\n"
            "deleted file mode 100644\n"
            "--- a/tests/deleted.test.js\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-expect(true).toBe(true);\n"
        )
        deleted_path = root / "deleted-test-bundle.json"
        dump(deleted_path, deleted_bundle)
        deleted_audit = json.loads(
            run(sys.executable, str(AUDITOR), str(deleted_path), expected=1).stdout
        )
        deleted_kinds = {item["kind"] for item in deleted_audit["issues"]}
        if not {"TEST_FILE_DELETED", "ASSERTION_REMOVED"}.issubset(deleted_kinds):
            raise AssertionError("deleted test did not retain deletion/assertion audit")

        unproven = copy.deepcopy(valid)
        unproven["tests"][0]["regression_proof"]["status"] = "NOT_PROVEN"
        invalid(bundle_path, report_path, unproven)

        unsafe_data = copy.deepcopy(valid)
        unsafe_data["environment"].update({"kind": "production", "real_data": True})
        invalid(bundle_path, report_path, unsafe_data)

        missing_layer = copy.deepcopy(valid)
        missing_layer["scenarios"][0]["layer"] = "UNKNOWN"
        invalid(bundle_path, report_path, missing_layer)

        fake_e2e = copy.deepcopy(valid)
        fake_e2e["scenarios"][0]["layer"] = "E2E"
        fake_e2e["real_system_proof"] = {
            "status": "FALLBACK",
            "evidence": "mocked page only",
        }
        invalid(bundle_path, report_path, fake_e2e)

        non_string_reference = copy.deepcopy(valid)
        non_string_reference["risks"][0]["criterion_ids"].append(7)
        invalid(bundle_path, report_path, non_string_reference)

        missing_criterion_text = copy.deepcopy(valid)
        missing_criterion_text["criteria"][0]["text"] = ""
        invalid(bundle_path, report_path, missing_criterion_text)

        missing_risk_evidence = copy.deepcopy(valid)
        missing_risk_evidence["risks"][0]["evidence"] = ""
        invalid(bundle_path, report_path, missing_risk_evidence)

        missing_scenario_test_backlink = copy.deepcopy(valid)
        second_scenario = copy.deepcopy(missing_scenario_test_backlink["scenarios"][0])
        second_scenario.update({"id": "S-002", "artifact_ids": []})
        missing_scenario_test_backlink["scenarios"].append(second_scenario)
        invalid(bundle_path, report_path, missing_scenario_test_backlink)

        missing_test_command_backlink = copy.deepcopy(valid)
        second_command = copy.deepcopy(missing_test_command_backlink["commands"][0])
        second_command["id"] = "CMD-002"
        missing_test_command_backlink["commands"].append(second_command)
        invalid(bundle_path, report_path, missing_test_command_backlink)

        missing_scenario_artifact_backlink = copy.deepcopy(valid)
        missing_scenario_artifact_backlink["scenarios"][0]["artifact_ids"] = []
        invalid(bundle_path, report_path, missing_scenario_artifact_backlink)

    verify_git_isolation()
    verify_base_resolution()
    print(
        "PASS: coverage bundle, Git isolation/base resolution, reciprocal graph, "
        "layer, audit, proof, environment, and decision fixtures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
