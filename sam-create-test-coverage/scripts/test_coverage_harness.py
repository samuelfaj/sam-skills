#!/usr/bin/env python3
"""Self-test coverage bundle, anti-gaming audit, and report validation."""

from __future__ import annotations

import copy
import importlib.util
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
RUN_CHECKED = HERE / "run_checked.py"
VALIDATOR = HERE / "validate_coverage_report.py"
SCAFFOLD = HERE / "scaffold_report.py"


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


def load_builder() -> Any:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("coverage_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_risk_tags() -> None:
    """Risk tags feed the elevated-risk floor, so both directions matter: an
    audited false-positive word or a dependency lockfile must not force HIGH
    proof, and every other substring match (flatcase compounds included) must
    still force it."""
    builder = load_builder()
    false_positives = {
        "yarn.lock": "concurrency",
        "package-lock.json": "concurrency",
        "src/Clock.tsx": "concurrency",
        "src/block/Blocker.tsx": "concurrency",
        "src/rapid/capital.py": "contract",
    }
    for path, tag in false_positives.items():
        if tag in builder.risk_tags(path):
            raise AssertionError(f"substring over-match tagged {path} as {tag}")
    true_positives = {
        "src/auth/session.py": {"security"},
        "src/oauth2/callback.py": {"security"},
        "src/AuthController.ts": {"security", "contract"},
        "src/api/routes.py": {"contract"},
        "src/APIClient.ts": {"contract"},
        "db/migrations/001_init.sql": {"data"},
        "workers/queue_consumer.py": {"concurrency"},
        "src/locks/mutex.py": {"concurrency"},
        "src/async-helpers.ts": {"concurrency"},
        "src/jobs/enqueue.py": {"concurrency"},
        "Dockerfile": {"delivery"},
        ".github/workflows/ci.yml": {"delivery"},
        "middleware/basicauth.go": {"security"},
        "src/reauthorize.py": {"security"},
        "src/csrftoken.py": {"security"},
        "src/accesstoken.ts": {"security"},
        "src/filelock.py": {"concurrency"},
        "src/taskqueue.py": {"concurrency"},
        "config/redis_lock.json": {"concurrency"},
        "src/httpclient.go": {"contract"},
        "src/approutes.py": {"contract"},
    }
    for path, tags in true_positives.items():
        found = set(builder.risk_tags(path))
        if not tags <= found:
            raise AssertionError(f"elevated risk lost for {path}: {sorted(found)}")


def risk_floor_bundle(paths: list[str]) -> dict[str, Any]:
    """Build a real bundle whose only changes are the given paths."""
    with tempfile.TemporaryDirectory(prefix="sam-coverage-risk-") as temporary:
        root = pathlib.Path(temporary)
        run("git", "init", "-q", cwd=root)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
        run("git", "config", "user.name", "Fixture", cwd=root)
        (root / "README.md").write_text("base\n", encoding="utf-8")
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-qm", "base", cwd=root)
        for name in paths:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("changed = 1\n", encoding="utf-8")
        return json.loads(run(sys.executable, str(BUILDER), "--repo", str(root)).stdout)


def check(
    bundle_path: pathlib.Path,
    report_path: pathlib.Path,
    report: dict[str, Any],
    expected: int,
    expect: str | None = None,
    baseline_path: pathlib.Path | None = None,
) -> None:
    dump(report_path, report)
    result = run(
        sys.executable,
        str(VALIDATOR),
        "--baseline",
        str(baseline_path or bundle_path),
        "--bundle",
        str(bundle_path),
        str(report_path),
        expected=expected,
    )
    if expect is not None and expect not in result.stderr:
        raise AssertionError(f"expected {expect!r}, got:\n{result.stderr}")


def rebind(report: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(report)
    value["baseline_fingerprint"] = value["bundle_fingerprint"] = bundle["fingerprint"]
    value["target"] = {
        "base_sha": bundle["target"]["base_sha"],
        "head_sha": bundle["target"]["head_sha"],
    }
    value["command_definitions"]["changed"] = bool(bundle["command_definitions"])
    return value


def dump(path: pathlib.Path, value: dict[str, Any]) -> None:
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
    path = receipts / f"{command_id}.receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path),
        "command": " ".join(receipt["argv"]),
        "status": receipt["status"],
    }


def report_for(bundle: dict[str, Any], receipts: pathlib.Path) -> dict[str, Any]:
    target = make_receipt(receipts, "CMD-001", "TARGET", "echo '1 passed'")
    before = make_receipt(
        receipts, "CMD-900", "ENVIRONMENT", "echo 'collected: rejects_zero'", repeat=1
    )
    after = make_receipt(
        receipts,
        "CMD-901",
        "ENVIRONMENT",
        "echo 'collected: rejects_zero rejects_a_negative_amount'",
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
                    "status": "MUTATION",
                    "evidence": "inverted the guard in an isolated copy; test failed",
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
                "path": "test-output.txt",
                "safety_review": True,
            }
        ],
        "cleanup": [
            {"id": "CL-001", "resource": "temporary test database", "status": "CLEANED"}
        ],
        "test_diff_audit": {"status": "PASS", "evidence": "audit script returned PASS"},
        "test_wiring": {
            "status": "PROVEN",
            "before_receipt": before["path"],
            "after_receipt": after["path"],
            "discovered_tests": ["rejects_a_negative_amount"],
            "evidence": ["runner discovery before and after the new test"],
        },
        "real_system_proof": {
            "status": "NOT_APPLICABLE",
            "evidence": "scenario is a pure validator contract",
        },
        "decision": "FULL",
    }


def invalid(
    bundle_path: pathlib.Path,
    report_path: pathlib.Path,
    report: dict[str, Any],
    expect: str | None = None,
) -> None:
    dump(report_path, report)
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
        # The stderr summary carries the freeze fields and no patch content.
        for field in (
            f"fingerprint={bundle['fingerprint']}",
            f"base={bundle['target']['base_sha']}",
            f"head={bundle['target']['head_sha']}",
            "risk_tags=",
            "command_definitions=",
        ):
            if field not in bundle_result.stderr:
                raise AssertionError(f"builder summary lacks {field}: {bundle_result.stderr}")
        if "expect(-1 >= 0)" in bundle_result.stderr:
            raise AssertionError("builder summary leaked patch content")
        with tempfile.TemporaryDirectory(prefix="sam-coverage-out-") as out_temp:
            out_dir = pathlib.Path(out_temp) / "final"
            builder_args = (
                sys.executable, str(BUILDER), "--repo", str(root),
                "--environment-kind", "test", "--environment-id", "fixture",
            )
            out_result = run(*builder_args, "--out", str(out_dir))
            if out_result.stdout:
                raise AssertionError("--out must keep stdout empty")
            if json.loads((out_dir / "bundle.json").read_text(encoding="utf-8")) != bundle:
                raise AssertionError("--out bundle differs from the stdout bundle")
            if (out_dir / "bundle.patch").read_text(encoding="utf-8") != bundle["patch"]:
                raise AssertionError("--out patch sidecar differs from the bundle patch")
            if f"json={out_dir.resolve() / 'bundle.json'}" not in out_result.stderr:
                raise AssertionError("summary does not name the written bundle")
            inside = run(*builder_args, "--out", str(root / "out"), expected=2)
            if "outside the repository" not in inside.stderr:
                raise AssertionError("--out inside the repository was not refused")
        bundle_path = root / "bundle.json"
        dump(bundle_path, bundle)
        if len(bundle["files"]) != 2 or not bundle["fingerprint"]:
            raise AssertionError("bundle lost changed files or fingerprint")
        run(sys.executable, str(AUDITOR), str(bundle_path))

        report_path = root / "report.json"
        receipts = root / "receipts"
        valid = report_for(bundle, receipts)
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

        # A status typed without an execution receipt is not a result.
        no_receipt = copy.deepcopy(valid)
        no_receipt["commands"][0].pop("receipt")
        invalid(bundle_path, report_path, no_receipt, "requires a receipt path")

        # The report cannot disagree with the receipt it cites.
        failing = make_receipt(
            receipts / "failing", "CMD-001", "TARGET", "echo '1 failed'; exit 1"
        )
        lying_status = copy.deepcopy(valid)
        lying_status["commands"][0].update(
            {"receipt": failing["path"], "command": failing["command"]}
        )
        invalid(bundle_path, report_path, lying_status, "its receipt records")

        # The command text must match the argv that actually ran.
        wrong_command = copy.deepcopy(valid)
        wrong_command["commands"][0]["command"] = "npm test -- --some-other-suite"
        invalid(bundle_path, report_path, wrong_command, "does not match the executed argv")

        # TARGET proof must be repeated; a single run cannot show determinism.
        single_run = make_receipt(
            receipts / "single", "CMD-001", "TARGET", "echo '1 passed'", repeat=1
        )
        unrepeated = copy.deepcopy(valid)
        unrepeated["commands"][0].update(
            {"receipt": single_run["path"], "command": single_run["command"]}
        )
        invalid(bundle_path, report_path, unrepeated, "must run at least")

        # A flaky green is not proof.
        flake_flag = receipts / "flake.flag"
        flaky = make_receipt(
            receipts / "flaky",
            "CMD-001",
            "TARGET",
            f"test -f {shlex.quote(str(flake_flag))} && exit 1; "
            f"touch {shlex.quote(str(flake_flag))}; exit 0",
            repeat=3,
        )
        flaky_report = copy.deepcopy(valid)
        flaky_report["commands"][0].update(
            {
                "receipt": flaky["path"],
                "command": flaky["command"],
                "status": flaky["status"],
            }
        )
        invalid(bundle_path, report_path, flaky_report, "flaky command(s)")

        # Editing a captured log breaks its recorded hash.
        tampered = copy.deepcopy(valid)
        log = receipts / "CMD-001.run1.log"
        original_log = log.read_bytes()
        log.write_bytes(original_log + b"fabricated success\n")
        invalid(bundle_path, report_path, tampered, "log hash does not match")
        log.write_bytes(original_log)

        # A test that the runner never discovers proves nothing.
        unwired = copy.deepcopy(valid)
        unwired["test_wiring"]["discovered_tests"] = ["never_collected_anywhere"]
        invalid(bundle_path, report_path, unwired, "not discovered by the runner")

        # A test already present before the change is not proof of new wiring.
        preexisting = copy.deepcopy(valid)
        preexisting["test_wiring"]["discovered_tests"] = ["rejects_zero"]
        invalid(bundle_path, report_path, preexisting, "already discovered before the change")

        # HIGH risk needs discriminating proof; CONTRACT is assertable.
        weak_high_risk = copy.deepcopy(valid)
        weak_high_risk["tests"][0]["regression_proof"] = {
            "status": "CONTRACT",
            "evidence": "asserts the documented invariant",
        }
        invalid(bundle_path, report_path, weak_high_risk, "RED_GREEN or MUTATION proof for HIGH/CRITICAL")

        # An elevated machine risk tag cannot be downgraded away.
        if {"security", "data", "contract", "concurrency"} & set(
            bundle.get("risk_tags") or []
        ):
            downgraded = copy.deepcopy(valid)
            downgraded["risks"][0]["level"] = "LOW"
            downgraded["tests"][0]["regression_proof"] = {
                "status": "MUTATION",
                "evidence": "mutation still recorded",
            }
            invalid(bundle_path, report_path, downgraded, "no HIGH or CRITICAL risk is declared")

        # The language-aware audit must not pass a weakened non-JavaScript suite.
        python_bundle = copy.deepcopy(bundle)
        python_bundle["files"].append(
            {
                "path": "tests/test_transfer.py",
                "previous_path": None,
                "status": "M",
                "is_test": True,
                "command_definition": False,
            }
        )
        python_bundle["patch"] += (
            "\ndiff --git a/tests/test_transfer.py b/tests/test_transfer.py\n"
            "--- a/tests/test_transfer.py\n"
            "+++ b/tests/test_transfer.py\n"
            "@@ -1,2 +1,3 @@\n"
            "-    assert transfer(-1) is None\n"
            "+@pytest.mark.skip(reason='flaky')\n"
            "+def test_transfer():\n"
            "+    assert True\n"
        )
        python_path = root / "python-weakened.json"
        dump(python_path, python_bundle)
        python_audit = json.loads(
            run(sys.executable, str(AUDITOR), str(python_path), expected=1).stdout
        )
        python_kinds = {item["kind"] for item in python_audit["issues"]}
        if not {"SKIPPED_TEST", "WEAK_ASSERTION", "ASSERTION_REMOVED"}.issubset(
            python_kinds
        ):
            raise AssertionError(
                f"Python test weakening was not detected: {sorted(python_kinds)}"
            )

        # An unknown test language must be reported, never assumed clean.
        unknown_bundle = copy.deepcopy(bundle)
        unknown_bundle["files"].append(
            {
                "path": "test/billing_SUITE.erl",
                "previous_path": None,
                "status": "M",
                "is_test": True,
                "command_definition": False,
            }
        )
        unknown_path = root / "unknown-language.json"
        dump(unknown_path, unknown_bundle)
        unknown_audit = json.loads(
            run(sys.executable, str(AUDITOR), str(unknown_path), expected=1).stdout
        )
        if not any(
            item["kind"] == "AUDIT_LANGUAGE_UNSUPPORTED"
            for item in unknown_audit["issues"]
        ):
            raise AssertionError("unsupported test language passed the audit silently")

        # Suppressing the runner's exit code in CI is not a green suite.
        neutered_bundle = copy.deepcopy(bundle)
        neutered_bundle["files"].append(
            {
                "path": "Makefile",
                "previous_path": None,
                "status": "M",
                "is_test": False,
                "command_definition": True,
            }
        )
        neutered_bundle["patch"] += (
            "\ndiff --git a/Makefile b/Makefile\n"
            "--- a/Makefile\n"
            "+++ b/Makefile\n"
            "@@ -1,2 +1,3 @@\n"
            "+\tnpm test --passWithNoTests || true\n"
        )
        neutered_path = root / "neutered-ci.json"
        dump(neutered_path, neutered_bundle)
        neutered_audit = json.loads(
            run(sys.executable, str(AUDITOR), str(neutered_path), expected=1).stdout
        )
        neutered_kinds = {item["kind"] for item in neutered_audit["issues"]}
        if not {"CI_FAILURE_SUPPRESSED", "EMPTY_SUITE_TOLERATED"}.issubset(
            neutered_kinds
        ):
            raise AssertionError(
                f"CI failure suppression was not detected: {sorted(neutered_kinds)}"
            )

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

        # The audit is recomputed from the bundle: a typed PASS cannot hide a
        # finding, and each real finding needs its own disproof.
        suspicious_bundle = copy.deepcopy(bundle)
        suspicious_bundle["files"].append(
            {"path": "tests/config.test.js", "is_test": True, "command_definition": False}
        )
        suspicious_bundle["patch"] += (  # audit-fixture: allow
            "\n--- a/tests/config.test.js\n+++ b/tests/config.test.js\n"
            "+  expect(config.timeout(5000)).toBe(5000);\n"
        )
        suspicious_path = root / "suspicious-bundle.json"
        dump(suspicious_path, suspicious_bundle)
        check(suspicious_path, report_path, valid, 1, "undisproven finding(s): AUD-001 TIMEOUT_INCREASE")
        wrong_disproof = copy.deepcopy(valid)
        wrong_disproof["test_diff_audit"]["disproven"] = [
            {"id": "AUD-001", "kind": "SKIPPED_TEST", "reason": "not a skip"}
        ]
        check(suspicious_path, report_path, wrong_disproof, 1, "undisproven finding(s)")
        disproved = copy.deepcopy(valid)
        disproved["test_diff_audit"]["disproven"] = [
            {
                "id": "AUD-001",
                "kind": "TIMEOUT_INCREASE",
                "path": "tests/config.test.js",
                "reason": "asserts the product timeout value; no runner timeout changed",
            }
        ]
        check(suspicious_path, report_path, disproved, 0)

        # Under a parent that runs the Playwright phase, browser journeys may be
        # handed off only with the exact delegation reason.
        journey = {
            "id": "S-002",
            "criterion_ids": ["AC-001"],
            "behavior_ids": ["B-001"],
            "risk_ids": ["R-001"],
            "status": "PLANNED",
            "layer": "E2E",
            "sufficiency": "browser journey proved by the parent Playwright phase",
            "test_ids": [],
            "artifact_ids": [],
        }
        delegated = copy.deepcopy(valid)
        delegated["scenarios"].append(journey)
        delegated["real_system_proof"] = {
            "status": "NOT_APPLICABLE",
            "reason": "delegated to playwright phase",
            "evidence": "parent runs sam-create-playwright-tests on the final head",
        }
        check(bundle_path, report_path, delegated, 0)
        not_delegated = copy.deepcopy(delegated)
        not_delegated["real_system_proof"]["reason"] = "browser proof not needed"
        check(bundle_path, report_path, not_delegated, 1, "FULL with E2E but no proven real system")
        automated_journey = copy.deepcopy(fake_e2e)
        automated_journey["real_system_proof"] = copy.deepcopy(delegated["real_system_proof"])
        check(bundle_path, report_path, automated_journey, 1, "FULL with E2E but no proven real system")

        # Risk floor end to end: audited false positives no longer force HIGH
        # proof; flatcase compound names still do.
        low_risk = copy.deepcopy(valid)
        low_risk["risks"][0]["level"] = "LOW"
        noisy = risk_floor_bundle(["yarn.lock", "src/Clock.tsx", "src/rapid/capital.py"])
        if {"security", "data", "contract", "concurrency"} & set(noisy["risk_tags"]):
            raise AssertionError(f"false-positive paths raised the floor: {noisy['risk_tags']}")
        noisy_path = root / "noisy-bundle.json"
        dump(noisy_path, noisy)
        check(noisy_path, report_path, rebind(low_risk, noisy), 0)
        real = risk_floor_bundle(["src/taskqueue.py", "middleware/basicauth.go"])
        real_path = root / "real-risk-bundle.json"
        dump(real_path, real)
        check(real_path, report_path, rebind(low_risk, real), 1, "no HIGH or CRITICAL risk is declared")

        # The scaffold derives mechanical fields from real files and fails closed
        # until the agent fills the ledger and decision.
        scaffold_path = root / "scaffold-report.json"
        scaffolded = run(
            sys.executable, str(SCAFFOLD),
            "--baseline", str(bundle_path), "--bundle", str(bundle_path),
            "--receipts-dir", str(receipts), "--wiring", "CMD-900", "CMD-901",
            "--out", str(scaffold_path),
        )
        if "SCAFFOLD" not in scaffolded.stdout:
            raise AssertionError(f"scaffold did not report: {scaffolded.stdout}")
        draft = json.loads(scaffold_path.read_text(encoding="utf-8"))
        for field in ("baseline_fingerprint", "bundle_fingerprint", "target"):
            if draft[field] != valid[field]:
                raise AssertionError(f"scaffold derived the wrong {field}")
        derived = {key: draft["commands"][0][key] for key in ("id", "command", "status", "classification", "receipt")}
        expected_command = {key: valid["commands"][0][key] for key in derived}
        expected_command["receipt"] = str(pathlib.Path(expected_command["receipt"]).resolve())
        if derived != expected_command or len(draft["commands"]) != 1:
            raise AssertionError(f"scaffold commands differ from receipts: {draft['commands']}")
        if [draft["test_wiring"][key] for key in ("before_receipt", "after_receipt")] != [
            str(pathlib.Path(valid["test_wiring"][key]).resolve())
            for key in ("before_receipt", "after_receipt")
        ]:
            raise AssertionError("scaffold wiring receipts differ")
        if draft["test_diff_audit"]["status"] != "PASS":
            raise AssertionError("scaffold did not recompute the audit")
        run(
            sys.executable, str(VALIDATOR), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), str(scaffold_path), expected=1,
        )
        for field in ("intent", "environment", "criteria", "behaviors", "risks", "scenarios",
                      "tests", "artifacts", "cleanup", "real_system_proof", "decision"):
            draft[field] = copy.deepcopy(valid[field])
        draft["commands"][0]["test_ids"] = ["T-001"]
        draft["test_wiring"]["discovered_tests"] = ["rejects_a_negative_amount"]
        check(bundle_path, report_path, draft, 0)
        refused = run(
            sys.executable, str(SCAFFOLD), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), "--receipts-dir", str(receipts),
            "--out", str(report_path), expected=2,
        )
        if "refusing to overwrite" not in refused.stderr:
            raise AssertionError("scaffold overwrote an existing report")
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), "--receipts-dir", str(receipts),
            "--wiring", "CMD-900", "CMD-901", "--previous", str(report_path),
            "--out", str(report_path),
        )
        carried = json.loads(report_path.read_text(encoding="utf-8"))
        if carried["decision"] != "" or carried["scenarios"] != valid["scenarios"]:
            raise AssertionError("carry-forward must keep the ledger and reset the decision")
        carried["decision"] = "FULL"
        check(bundle_path, report_path, carried, 0)

        # A run that adds no test omits --wiring, but its discovery listings are
        # still wiring evidence: harvesting them as commands would leave entries
        # that reference no test, which the validator rejects.
        unwired_path = root / "scaffold-unwired.json"
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), "--receipts-dir", str(receipts),
            "--out", str(unwired_path),
        )
        unwired = json.loads(unwired_path.read_text(encoding="utf-8"))
        if [item["id"] for item in unwired["commands"]] != ["CMD-001"]:
            raise AssertionError(f"scaffold harvested discovery receipts: {unwired['commands']}")
        for field in ("intent", "environment", "criteria", "behaviors", "risks", "scenarios",
                      "tests", "artifacts", "cleanup", "real_system_proof", "decision"):
            unwired[field] = copy.deepcopy(valid[field])
        unwired["commands"][0]["test_ids"] = ["T-001"]
        unwired["test_wiring"] = {"status": "NOT_APPLICABLE", "reason": "only existing tests changed"}
        check(bundle_path, unwired_path, unwired, 0)

        # Audit ids are positional: a new earlier file shifts AUD-001, so a
        # disproof binds to its path and cannot migrate to another finding.
        def timeout_bundle(paths: list[str], fingerprint: str) -> dict[str, Any]:
            value = copy.deepcopy(bundle)
            for name in paths:
                value["files"].append({"path": name, "is_test": True, "command_definition": False})
                value["patch"] += f"\n--- a/{name}\n+++ b/{name}\n"
                value["patch"] += "+  expect(config.timeout(5000)).toBe(5000);\n"  # audit-fixture: allow
            value["fingerprint"] = fingerprint
            return value

        only_b = timeout_bundle(["tests/b.test.js"], "b" * 64)
        a_and_b = timeout_bundle(["tests/a.test.js", "tests/b.test.js"], "c" * 64)
        only_b_path, a_and_b_path = root / "only-b.json", root / "a-and-b.json"
        dump(only_b_path, only_b)
        dump(a_and_b_path, a_and_b)
        b_disproof = {
            "id": "AUD-001", "kind": "TIMEOUT_INCREASE", "path": "tests/b.test.js",
            "reason": "asserts the product timeout value",
        }
        previous = rebind(carried, only_b)
        previous["test_diff_audit"]["disproven"] = [b_disproof]
        check(only_b_path, report_path, previous, 0)
        shifted = rebind(previous, a_and_b)
        shifted["test_diff_audit"]["disproven"] = [b_disproof, {**b_disproof, "id": "AUD-002"}]
        check(a_and_b_path, report_path, shifted, 1,
              "undisproven finding(s): AUD-001 TIMEOUT_INCREASE tests/a.test.js")

        # A new head or fingerprint keeps only the ledger: the previous receipts
        # dir is refused, proof/evidence/artifacts/disproofs reset, and the
        # original CMD-900 before-receipt is reused.
        dump(report_path, previous)
        moved_head = copy.deepcopy(only_b)
        moved_head["target"]["head_sha"] = "f" * 40
        moved_head_path = root / "moved-head.json"
        dump(moved_head_path, moved_head)
        for changed_path in (moved_head_path, a_and_b_path):
            stale = run(
                sys.executable, str(SCAFFOLD), "--baseline", str(changed_path),
                "--bundle", str(changed_path), "--receipts-dir", str(receipts),
                "--wiring", "CMD-900", "CMD-901", "--previous", str(report_path),
                "--out", str(report_path), expected=2,
            )
            if "use a fresh --receipts-dir" not in stale.stderr:
                raise AssertionError(f"stale receipts accepted for {changed_path.name}")
        fresh = root / "receipts-2"
        make_receipt(fresh, "CMD-001", "TARGET", "echo '1 passed'")
        make_receipt(
            fresh, "CMD-901", "ENVIRONMENT",
            "echo 'collected: rejects_zero rejects_a_negative_amount'", repeat=1,
        )
        moved_run = run(
            sys.executable, str(SCAFFOLD), "--baseline", str(a_and_b_path),
            "--bundle", str(a_and_b_path), "--receipts-dir", str(fresh),
            "--wiring", "CMD-900", "CMD-901", "--previous", str(report_path),
            "--out", str(report_path),
        )
        moved = json.loads(report_path.read_text(encoding="utf-8"))
        wiring = moved["test_wiring"]
        if (
            "carried=ledger-only" not in moved_run.stdout
            or moved["scenarios"] != valid["scenarios"]
            or moved["real_system_proof"]["status"] != ""
            or moved["environment"]["evidence"] != ""
            or moved["test_diff_audit"]["disproven"] != []
            or any(item["status"] or item["safety_review"] for item in moved["artifacts"])
            or wiring["before_receipt"]
            != str(pathlib.Path(valid["test_wiring"]["before_receipt"]).resolve())
            or wiring["after_receipt"] != str((fresh / "CMD-901.receipt.json").resolve())
            or [(item["receipt"], item["test_ids"]) for item in moved["commands"]]
            != [(str((fresh / "CMD-001.receipt.json").resolve()), ["T-001"])]
            # Counterfactual proof from the old head is re-established, never carried.
            or any(item["regression_proof"] != {"status": "", "evidence": ""} for item in moved["tests"])
            or not any(str(fresh.resolve()) in item["resource"] for item in moved["cleanup"])
        ):
            raise AssertionError(f"changed inputs must keep only the ledger: {moved}")
        check(a_and_b_path, report_path, moved, 1)
        for field in ("environment", "artifacts", "real_system_proof"):
            moved[field] = copy.deepcopy(valid[field])
        for item, source in zip(moved["tests"], valid["tests"]):
            item["regression_proof"] = copy.deepcopy(source["regression_proof"])
        moved["test_diff_audit"]["status"] = "PASS"
        moved["test_diff_audit"]["disproven"] = [
            {**b_disproof, "path": "tests/a.test.js"}, {**b_disproof, "id": "AUD-002"},
        ]
        moved["decision"] = "FULL"
        check(a_and_b_path, report_path, moved, 0)

        # The same patch on a new head resets disproofs too: the path key cannot
        # show that the flagged line is unchanged.
        dump(report_path, previous)
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(moved_head_path),
            "--bundle", str(moved_head_path), "--receipts-dir", str(fresh),
            "--wiring", "CMD-900", "CMD-901", "--previous", str(report_path),
            "--out", str(report_path),
        )
        if json.loads(report_path.read_text(encoding="utf-8"))["test_diff_audit"]["disproven"]:
            raise AssertionError("a disproof survived a head change")

        # A previous report without wiring still cites the once-per-work CMD-900
        # receipt as a command; a later --wiring must reuse it, not demand a
        # re-capture that would list the new tests as already present.
        unwired = copy.deepcopy(previous)
        unwired["test_wiring"] = {"status": "NOT_APPLICABLE", "reason": "no test added"}
        unwired["commands"].append(
            {"id": "CMD-900", "status": "PASS", "receipt": valid["test_wiring"]["before_receipt"]}
        )
        dump(report_path, unwired)
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(a_and_b_path),
            "--bundle", str(a_and_b_path), "--receipts-dir", str(fresh),
            "--wiring", "CMD-900", "CMD-901", "--previous", str(report_path),
            "--out", str(report_path),
        )
        reused = json.loads(report_path.read_text(encoding="utf-8"))["test_wiring"]
        if reused["before_receipt"] != str(
            pathlib.Path(valid["test_wiring"]["before_receipt"]).resolve()
        ):
            raise AssertionError(f"previous CMD-900 command not reused: {reused}")

        # A FAIL is never re-run under its id: after a fix the next receipts dir
        # re-runs every command except CMD-900, captured once before any test
        # changed. An early unwired scaffold still cites CMD-900, and later
        # scaffolds find it in --previous or an earlier receipts-<n> instead of
        # demanding a re-capture that would list the new tests as present.
        phase = root / "phase"
        first, second = phase / "receipts-1", phase / "receipts-2"
        make_receipt(first, "CMD-900", "ENVIRONMENT", "echo 'collected: rejects_zero'", repeat=1)
        make_receipt(first, "CMD-001", "TARGET", "echo 'failed'; exit 1")
        early_path = phase / "early.json"
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), "--receipts-dir", str(first),
            "--out", str(early_path),
        )
        early = json.loads(early_path.read_text(encoding="utf-8"))
        first_before = str((first / "CMD-900.receipt.json").resolve())
        if early["test_wiring"].get("before_receipt") != first_before:
            raise AssertionError(f"unwired scaffold did not cite CMD-900: {early['test_wiring']}")
        make_receipt(second, "CMD-001", "TARGET", "echo '1 passed'")
        make_receipt(
            second, "CMD-901", "ENVIRONMENT",
            "echo 'collected: rejects_zero rejects_a_negative_amount'", repeat=1,
        )
        fixed_path = phase / "fixed.json"
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), "--receipts-dir", str(second),
            "--wiring", "CMD-900", "CMD-901", "--out", str(fixed_path),
        )
        fixed = json.loads(fixed_path.read_text(encoding="utf-8"))
        if fixed["test_wiring"]["before_receipt"] != first_before or [
            (item["id"], item["status"]) for item in fixed["commands"]
        ] != [("CMD-001", "PASS")]:
            raise AssertionError(f"rerun after a fix lost CMD-900 or kept the FAIL: {fixed}")
        for field in ("intent", "environment", "criteria", "behaviors", "risks", "scenarios",
                      "tests", "artifacts", "cleanup", "real_system_proof", "decision"):
            fixed[field] = copy.deepcopy(valid[field])
        fixed["commands"][0]["test_ids"] = ["T-001"]
        fixed["test_wiring"]["discovered_tests"] = ["rejects_a_negative_amount"]
        check(bundle_path, fixed_path, fixed, 0)
        # Re-invoked in a parent's fresh phase dir, only the early report's
        # citation can supply CMD-900.
        other = root / "phase-2" / "receipts-1"
        make_receipt(other, "CMD-001", "TARGET", "echo '1 passed'")
        make_receipt(
            other, "CMD-901", "ENVIRONMENT",
            "echo 'collected: rejects_zero rejects_a_negative_amount'", repeat=1,
        )
        again_path = root / "phase-2" / "report.json"
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), "--receipts-dir", str(other),
            "--wiring", "CMD-900", "CMD-901", "--previous", str(early_path),
            "--out", str(again_path),
        )
        again = json.loads(again_path.read_text(encoding="utf-8"))["test_wiring"]
        if again["before_receipt"] != first_before:
            raise AssertionError(f"re-invocation did not reuse the cited CMD-900: {again}")
        # A cleanup entry for receipts-10 does not name receipts-1.
        early["cleanup"] = [
            {"id": "CL-001", "resource": str(first.resolve()) + "0", "status": "CLEANED"}
        ]
        dump(early_path, early)
        run(
            sys.executable, str(SCAFFOLD), "--baseline", str(bundle_path),
            "--bundle", str(bundle_path), "--receipts-dir", str(first),
            "--previous", str(early_path), "--out", str(early_path),
        )
        cleanup = json.loads(early_path.read_text(encoding="utf-8"))["cleanup"]
        if [item["resource"].endswith(str(first.resolve())) for item in cleanup] != [False, True]:
            raise AssertionError(f"receipts-10 entry hid the receipts-1 RETAINED entry: {cleanup}")

    verify_risk_tags()
    verify_git_isolation()
    verify_base_resolution()
    print(
        "PASS: coverage bundle, summary/--out, risk tags, Git isolation/base "
        "resolution, reciprocal graph, layer, recomputed audit, delegation, scaffold "
        "carry-forward, proof, environment, and decision fixtures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
