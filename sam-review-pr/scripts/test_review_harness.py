#!/usr/bin/env python3
"""Exercise immutable bundle construction and remote review validation."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BUILDER = SCRIPT_DIR / "build_review_bundle.py"
VALIDATOR = SCRIPT_DIR / "validate_review.py"


def refingerprint(value: dict[str, Any], key: str) -> None:
    value.pop(key, None)
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    value[key] = hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run(
    command: list[str], cwd: Path, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def git(repo: Path, *args: str) -> str:
    result = run(["git", *args], repo)
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def build_fixture(root: Path) -> tuple[Path, str, str]:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "trunk")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    (repo / "src").mkdir()
    (repo / "docs").mkdir()
    (repo / "src" / "service.py").write_text(
        "def enabled():\n    return False\n", encoding="utf-8"
    )
    (repo / "docs" / "old.md").write_text("stable note\n", encoding="utf-8")
    (repo / "docs" / "remove.md").write_text("obsolete note\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial")
    base = git(repo, "rev-parse", "HEAD")

    (repo / "tests").mkdir()
    (repo / "src" / "service.py").write_text(
        "def enabled():\n    return True\n", encoding="utf-8"
    )
    (repo / "tests" / "test_service.py").write_text(
        "from src.service import enabled\n\ndef test_enabled():\n    assert enabled() is True\n",
        encoding="utf-8",
    )
    git(repo, "mv", "docs/old.md", "docs/new.md")
    git(repo, "rm", "docs/remove.md")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "PROJ-7 enable service")
    head = git(repo, "rev-parse", "HEAD")
    return repo, base, head


def content_fixture(root: Path, path: str, content: str) -> tuple[Path, str, str]:
    repo = root / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "-b", "trunk")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "baseline")
    base = git(repo, "rev-parse", "HEAD")
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "content fixture")
    return repo, base, git(repo, "rev-parse", "HEAD")


def exercise_sensitive_content(root: Path) -> None:
    safe_repo, safe_base, safe_head = content_fixture(
        root / "safe-template",
        ".env.example",
        "API_KEY='example-placeholder-value'\n",
    )
    safe = run(builder_command(safe_repo, safe_base, safe_head), safe_repo)
    if safe.returncode != 0:
        raise AssertionError(f"safe credential template was rejected: {safe.stderr}")

    sentinel = "live_secret_value_47d8b2c1"
    secret_repo, secret_base, secret_head = content_fixture(
        root / "secret-content",
        "src/config.py",
        f"api_key = '{sentinel}'\n",
    )
    secret = run(builder_command(secret_repo, secret_base, secret_head), secret_repo)
    if secret.returncode == 0 or sentinel in secret.stdout or sentinel in secret.stderr:
        raise AssertionError("credential-like content was accepted or leaked")

    private_content = "private-material-should-not-be-read"
    private_repo, private_base, private_head = content_fixture(
        root / "private-path",
        "keys/signing.key",
        private_content,
    )
    private = run(
        builder_command(private_repo, private_base, private_head), private_repo
    )
    if (
        private.returncode == 0
        or private_content in private.stdout
        or private_content in private.stderr
    ):
        raise AssertionError("sensitive path was accepted or its content leaked")


def build_bundle(repo: Path, base: str, head: str, output: Path) -> dict[str, Any]:
    result = run(builder_command(repo, base, head), repo)
    if result.returncode:
        raise AssertionError(f"bundle build failed: {result.stderr}")
    output.write_text(result.stdout, encoding="utf-8")
    return json.loads(result.stdout)


def builder_command(
    repo: Path, base: str, head: str, comparison: str = "direct"
) -> list[str]:
    return [
        sys.executable,
        str(BUILDER),
        "--repo",
        str(repo),
        "--base",
        base,
        "--head",
        head,
        "--platform",
        "fixture",
        "--repository",
        "example/repo",
        "--change-id",
        "7",
        "--comparison",
        comparison,
    ]


def write_probe(path: Path) -> None:
    path.write_text(
        '#!/bin/sh\n: > "$SAM_REVIEW_PR_MARKER"\ncat "${1:-/dev/null}"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def exercise_git_isolation(root: Path, repo: Path, base: str, head: str) -> None:
    expected_paths = {
        "docs/new.md",
        "docs/remove.md",
        "src/service.py",
        "tests/test_service.py",
    }

    fake_bin = repo / "tools" / "bin"
    fake_bin.mkdir(parents=True)
    fake_git = fake_bin / "git"
    repository_git_marker = root / "repository-git.marker"
    write_probe(fake_git)
    repository_git_env = dict(os.environ)
    repository_git_env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{repository_git_env.get('PATH', '')}",
            "SAM_REVIEW_PR_MARKER": str(repository_git_marker),
        }
    )
    repository_git = run(
        builder_command(repo / "src", base, head),
        repo,
        env=repository_git_env,
    )
    if (
        repository_git.returncode != 1
        or repository_git_marker.exists()
        or "refusing repository-controlled git executable" not in repository_git.stderr
    ):
        raise AssertionError("nested repository-controlled git was not rejected")

    redirect_root = root / "redirect"
    redirect_root.mkdir()
    redirected_repo, _, _ = build_fixture(redirect_root)
    redirected_env = dict(os.environ)
    redirected_env.update(
        {
            "GIT_DIR": str(redirected_repo / ".git"),
            "GIT_WORK_TREE": str(redirected_repo),
            "GIT_INDEX_FILE": str(redirected_repo / ".git" / "index"),
            "GIT_OBJECT_DIRECTORY": str(redirected_repo / ".git" / "objects"),
        }
    )
    redirected = run(builder_command(repo, base, head), repo, env=redirected_env)
    if redirected.returncode != 0:
        raise AssertionError(f"isolated Git environment failed: {redirected.stderr}")
    redirected_paths = {item["path"] for item in json.loads(redirected.stdout)["files"]}
    if redirected_paths != expected_paths:
        raise AssertionError(
            f"inherited Git environment redirected target: {sorted(redirected_paths)}"
        )

    fsmonitor_marker = root / "fsmonitor.marker"
    fsmonitor_hook = root / "fsmonitor-hook"
    write_probe(fsmonitor_hook)
    git(repo, "config", "core.fsmonitor", str(fsmonitor_hook))
    fsmonitor_env = dict(os.environ)
    fsmonitor_env["SAM_REVIEW_PR_MARKER"] = str(fsmonitor_marker)
    fsmonitor = run(builder_command(repo, base, head), repo, env=fsmonitor_env)
    if fsmonitor.returncode != 0 or fsmonitor_marker.exists():
        raise AssertionError("repository-configured core.fsmonitor executed")

    driver_repo = root / "drivers"
    driver_repo.mkdir()
    git(driver_repo, "init", "-b", "trunk")
    git(driver_repo, "config", "user.email", "fixture@example.invalid")
    git(driver_repo, "config", "user.name", "Fixture")
    (driver_repo / ".gitattributes").write_text(
        "*.blob diff=review-probe\n", encoding="utf-8"
    )
    (driver_repo / "payload.blob").write_text("baseline\n", encoding="utf-8")
    git(driver_repo, "add", ".")
    git(driver_repo, "commit", "-m", "driver baseline")
    driver_base = git(driver_repo, "rev-parse", "HEAD")
    (driver_repo / "payload.blob").write_text("changed\n", encoding="utf-8")
    git(driver_repo, "add", ".")
    git(driver_repo, "commit", "-m", "driver change")
    driver_head = git(driver_repo, "rev-parse", "HEAD")
    driver_marker = root / "driver.marker"
    textconv = root / "textconv-driver"
    external = root / "external-diff"
    write_probe(textconv)
    write_probe(external)
    git(driver_repo, "config", "diff.review-probe.textconv", str(textconv))
    git(driver_repo, "config", "diff.external", str(external))
    driver_env = dict(os.environ)
    driver_env["SAM_REVIEW_PR_MARKER"] = str(driver_marker)
    driver_result = run(
        builder_command(driver_repo, driver_base, driver_head),
        driver_repo,
        env=driver_env,
    )
    if driver_result.returncode != 0 or driver_marker.exists():
        raise AssertionError("configured textconv or external diff executed")

    (repo / "staged-only.py").write_text("STAGED_ONLY = True\n", encoding="utf-8")
    git(repo, "add", "staged-only.py")
    tracked = repo / "src" / "service.py"
    tracked_stat = tracked.stat()
    os.utime(
        tracked,
        ns=(tracked_stat.st_atime_ns, tracked_stat.st_mtime_ns + 2_000_000_000),
    )
    index = repo / ".git" / "index"
    index_before = index.read_bytes()
    temporary_root = root / "temporary-indexes"
    temporary_root.mkdir()
    immutable_env = dict(os.environ)
    immutable_env["TMPDIR"] = str(temporary_root)
    immutable = run(builder_command(repo / "src", base, head), repo, env=immutable_env)
    if immutable.returncode != 0:
        raise AssertionError(f"immutable-index build failed: {immutable.stderr}")
    immutable_paths = {item["path"] for item in json.loads(immutable.stdout)["files"]}
    if immutable_paths != expected_paths or "staged-only.py" in immutable_paths:
        raise AssertionError("remote comparison included staged-only content")
    if index.read_bytes() != index_before:
        raise AssertionError("bundle construction mutated the real Git index")
    if any(temporary_root.iterdir()):
        raise AssertionError("temporary copied index was not cleaned up")


def valid_report(bundle: dict[str, Any]) -> dict[str, Any]:
    head = bundle["target"]["head_sha"]
    coverage = [
        {
            "path": item["path"],
            "classification": "TEST"
            if item["path"].startswith("tests/")
            else "REVIEWED",
            "reason": "Fixture path reviewed",
        }
        for item in bundle["files"]
    ]
    return {
        "schema_version": 1,
        "target": {
            "base_sha": bundle["target"]["base_sha"],
            "head_sha": head,
            "bundle_fingerprint": bundle["bundle_fingerprint"],
        },
        "intent": {
            "intended_behavior": ["Enable the service"],
            "must_not_change": ["Documentation content"],
            "invariants": ["The function returns a boolean"],
            "owner_boundary": "service module",
            "user_visible_change": False,
        },
        "file_coverage": coverage,
        "findings": [],
        "test_coverage": [
            {
                "behavior": "Enabled result",
                "level": "UNIT",
                "status": "COVERED",
                "paths": ["tests/test_service.py"],
                "reason": "The changed return value is asserted",
                "finding_id": None,
            }
        ],
        "validations": [
            {
                "command": "fixture unit test",
                "status": "PASS",
                "classification": "TARGET",
                "reason": "The focused assertion passed",
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
            "expected_head_sha": head,
            "observed_head_sha": head,
            "review_id": "fixture-review-0001",
            "action": "NONE",
            "status": "NOT_REQUESTED",
            "inline_comments": [],
            "receipts": [],
            "error": None,
        },
    }


def validate(
    bundle_path: Path, report: dict[str, Any], expected_success: bool, root: Path
) -> None:
    report_path = root / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = run(
        [
            sys.executable,
            str(VALIDATOR),
            "--bundle",
            str(bundle_path),
            str(report_path),
        ],
        root,
    )
    if (result.returncode == 0) != expected_success:
        raise AssertionError(
            f"validator expectation mismatch\nstdout={result.stdout}\nstderr={result.stderr}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sam-review-pr-test-") as temp_dir:
        root = Path(temp_dir)
        repo, base, head = build_fixture(root)
        bundle_path = root / "bundle.json"
        bundle = build_bundle(repo, base, head, bundle_path)
        merge_base_result = run(builder_command(repo, base, head, "merge-base"), repo)
        if merge_base_result.returncode != 0:
            raise AssertionError(
                f"merge-base comparison failed: {merge_base_result.stderr}"
            )
        merge_base_bundle = json.loads(merge_base_result.stdout)
        if (
            merge_base_bundle["target"]["comparison"] != "merge-base"
            or merge_base_bundle["target"]["base_sha"] != base
        ):
            raise AssertionError("merge-base comparison target was not preserved")
        paths = {item["path"] for item in bundle["files"]}
        if paths != {
            "docs/new.md",
            "docs/remove.md",
            "src/service.py",
            "tests/test_service.py",
        }:
            raise AssertionError(f"unexpected bundle paths: {sorted(paths)}")
        renamed = next(
            item for item in bundle["files"] if item["path"] == "docs/new.md"
        )
        deleted = next(
            item for item in bundle["files"] if item["path"] == "docs/remove.md"
        )
        if renamed["old_path"] != "docs/old.md" or renamed["new_path"] != "docs/new.md":
            raise AssertionError("rename paths were not preserved")
        if deleted["old_path"] != "docs/remove.md" or deleted["new_path"] is not None:
            raise AssertionError("deletion paths were not preserved")
        service = next(
            item for item in bundle["files"] if item["path"] == "src/service.py"
        )
        if not service["new_changed_ranges"]:
            raise AssertionError("runtime change must expose changed-line ranges")

        clean = valid_report(bundle)
        validate(bundle_path, clean, True, root)

        malformed_bundle = copy.deepcopy(bundle)
        del malformed_bundle["target"]["platform"]
        refingerprint(malformed_bundle, "bundle_fingerprint")
        malformed_bundle_path = root / "malformed-bundle.json"
        malformed_bundle_path.write_text(json.dumps(malformed_bundle), encoding="utf-8")
        malformed_report = valid_report(malformed_bundle)
        validate(malformed_bundle_path, malformed_report, False, root)

        visible_without_proof = copy.deepcopy(clean)
        visible_without_proof["intent"]["user_visible_change"] = True
        validate(bundle_path, visible_without_proof, False, root)

        substantive_stop = copy.deepcopy(clean)
        substantive_stop["findings"] = [
            {
                "id": "F1",
                "severity": "BLOCKER",
                "status": "STOP_AND_ESCALATE",
                "scope": "STOP_AND_ESCALATE",
                "path": None,
                "line": None,
                "side": None,
                "failure_mode": "Required remote evidence is unavailable",
                "impact": "Merge safety cannot be established",
                "evidence": ["Remote metadata request failed"],
                "required_change": "Restore remote access and rerun the review",
                "test_gap": False,
                "rejection_reason": None,
            }
        ]
        substantive_stop["decision"].update(
            {"result": "BLOCKED", "remaining_corrections": []}
        )
        validate(bundle_path, substantive_stop, True, root)

        empty_stop = copy.deepcopy(substantive_stop)
        empty_stop["findings"][0].update(
            {"failure_mode": "", "impact": "", "evidence": []}
        )
        validate(bundle_path, empty_stop, False, root)

        missing_coverage = copy.deepcopy(clean)
        missing_coverage["file_coverage"].pop()
        validate(bundle_path, missing_coverage, False, root)

        unauthorized = copy.deepcopy(clean)
        unauthorized["publication"]["action"] = "APPROVE"
        validate(bundle_path, unauthorized, False, root)

        unsafe_drift = copy.deepcopy(clean)
        unsafe_drift["publication"].update(
            {
                "requested": True,
                "observed_head_sha": "0" * len(head),
                "action": "APPROVE",
                "status": "PLANNED",
            }
        )
        validate(bundle_path, unsafe_drift, False, root)

        blocked_drift = copy.deepcopy(unsafe_drift)
        blocked_drift["publication"].update(
            {"action": "NONE", "status": "BLOCKED", "error": "Remote head changed"}
        )
        validate(bundle_path, blocked_drift, True, root)

        partial = copy.deepcopy(clean)
        partial["publication"].update(
            {
                "requested": True,
                "action": "APPROVE",
                "status": "PARTIAL",
                "receipts": [
                    {
                        "kind": "summary",
                        "id": "receipt-1",
                        "url": "https://example.invalid/review/1",
                        "status": "published",
                    }
                ],
                "error": "Review-state update failed",
            }
        )
        validate(bundle_path, partial, True, root)

        suggestion_inline = copy.deepcopy(clean)
        line = service["new_changed_ranges"][0][0]
        suggestion_inline["findings"] = [
            {
                "id": "F1",
                "severity": "SUGGESTION",
                "status": "ACCEPTED",
                "scope": "IN_SCOPE",
                "path": "src/service.py",
                "line": line,
                "side": "NEW",
                "failure_mode": "Optional naming improvement",
                "impact": "Readability only",
                "evidence": ["Changed function"],
                "required_change": "Consider a clearer name",
                "test_gap": False,
                "rejection_reason": None,
            }
        ]
        suggestion_inline["publication"].update(
            {
                "requested": True,
                "action": "COMMENT",
                "status": "PLANNED",
                "inline_comments": [
                    {
                        "finding_id": "F1",
                        "path": "src/service.py",
                        "line": line,
                        "side": "NEW",
                    }
                ],
            }
        )
        validate(bundle_path, suggestion_inline, False, root)

        exercise_git_isolation(root, repo, base, head)
        exercise_sensitive_content(root)

    print(
        "PASS: immutable bundle, Git isolation, secret safety, review validation, authorization, drift, and partial receipts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
