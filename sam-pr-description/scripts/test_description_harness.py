#!/usr/bin/env python3
"""Exercise change-context construction and description validation."""

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
BUILDER = SCRIPT_DIR / "build_change_context.py"
VALIDATOR = SCRIPT_DIR / "validate_description.py"


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


def fixture(root: Path) -> tuple[Path, str, str]:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "trunk")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "Fixture")
    (repo / "src").mkdir()
    (repo / "docs").mkdir()
    (repo / "src" / "service.py").write_text(
        "def value():\n    return 0\n", encoding="utf-8"
    )
    (repo / "docs" / "old.md").write_text("stable note\n", encoding="utf-8")
    (repo / "docs" / "remove.md").write_text("obsolete note\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-c", "PROJ-9-correct-value")
    (repo / "tests").mkdir()
    (repo / "src" / "service.py").write_text(
        "def value():\n    return 1\n", encoding="utf-8"
    )
    (repo / "tests" / "test_service.py").write_text(
        "from src.service import value\n\ndef test_value():\n    assert value() == 1\n",
        encoding="utf-8",
    )
    git(repo, "mv", "docs/old.md", "docs/new.md")
    git(repo, "rm", "docs/remove.md")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "PROJ-9 correct service value")
    return repo, base, git(repo, "rev-parse", "HEAD")


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


def build_context(repo: Path, base: str, output: Path) -> dict[str, Any]:
    result = run(builder_command(repo, base, "HEAD"), repo)
    if result.returncode:
        raise AssertionError(f"context build failed: {result.stderr}")
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
        "--comparison",
        comparison,
    ]


def write_probe(path: Path) -> None:
    path.write_text(
        '#!/bin/sh\n: > "$SAM_PR_DESCRIPTION_MARKER"\ncat "${1:-/dev/null}"\n',
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
            "SAM_PR_DESCRIPTION_MARKER": str(repository_git_marker),
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
    redirected_repo, _, _ = fixture(redirect_root)
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
    fsmonitor_env["SAM_PR_DESCRIPTION_MARKER"] = str(fsmonitor_marker)
    fsmonitor = run(builder_command(repo, base, head), repo, env=fsmonitor_env)
    if fsmonitor.returncode != 0 or fsmonitor_marker.exists():
        raise AssertionError("repository-configured core.fsmonitor executed")

    driver_repo = root / "drivers"
    driver_repo.mkdir()
    git(driver_repo, "init", "-b", "trunk")
    git(driver_repo, "config", "user.email", "fixture@example.invalid")
    git(driver_repo, "config", "user.name", "Fixture")
    (driver_repo / ".gitattributes").write_text(
        "*.blob diff=description-probe\n", encoding="utf-8"
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
    git(driver_repo, "config", "diff.description-probe.textconv", str(textconv))
    git(driver_repo, "config", "diff.external", str(external))
    driver_env = dict(os.environ)
    driver_env["SAM_PR_DESCRIPTION_MARKER"] = str(driver_marker)
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
        raise AssertionError("context construction mutated the real Git index")
    if any(temporary_root.iterdir()):
        raise AssertionError("temporary copied index was not cleaned up")


def body() -> str:
    return """## Description

Service returns the corrected value.

## Type of Change

- [x] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Other: Not applicable

## What Changed

- User-visible change: The service returns the corrected value.
- Internal change: The return value and its regression test were updated.

## Behavior

- Before: The service returned zero.
- After: The service returns one.
- Unchanged: The service interface is unchanged.

## Business Rules

- Added: None.
- Changed: When the service value is requested, the system must return one.
- Preserved: The service call remains parameterless.

## Scope and Impact

- `docs/new.md` — Preserves the renamed documentation note.
- `docs/remove.md` — Removes the obsolete documentation note.
- `src/service.py` — Corrects the service result.
- `tests/test_service.py` — Adds regression coverage.
- Out of scope: Other service behavior.
- User impact: Consumers receive the corrected value.
- Technical impact: No API, data, configuration, or compatibility change.

## Risks and Mitigations

- Risk: Consumers may rely on the previous incorrect value.
- Mitigation: The focused regression test proves the corrected contract.
- Remaining risk: Broader compatibility was not verified.

## Rollout and Recovery

- Rollout: Standard deployment.
- Monitoring: Observe service-result errors.
- Recovery: Revert the change if consumers regress.

## Validation

- `fixture test` — PASS: Focused fixture test passed.

## Tests

- Scenarios: The service returns one.
- Added: `tests/test_service.py` covers the corrected value.
- Executed: `fixture test` passed.

## Author Checklist

- [x] Description explains the problem, outcome, and reason.
- [x] Before/after behavior and business rules are explicit.
- [x] Every changed file is represented in scope.
- [x] Risks, mitigations, and recovery are documented.
- [x] Tests and validation reflect commands actually run.
- [x] No unrelated changes are included.

## Notes for Reviewer

- Review first: Verify the value contract.
- Open questions: None.
"""


def valid_report(context: dict[str, Any]) -> dict[str, Any]:
    head = context["target"]["head_sha"]
    return {
        "schema_version": 1,
        "target": {
            "base_sha": context["target"]["base_sha"],
            "head_sha": head,
            "context_fingerprint": context["context_fingerprint"],
        },
        "language": "EN-US",
        "change_types": ["BUG_FIX"],
        "file_coverage": [
            {
                "path": "docs/new.md",
                "section": "Scope and Impact",
                "summary": "Preserves the renamed documentation note.",
            },
            {
                "path": "docs/remove.md",
                "section": "Scope and Impact",
                "summary": "Removes the obsolete documentation note.",
            },
            {
                "path": "src/service.py",
                "section": "Scope and Impact",
                "summary": "Corrects the service result.",
            },
            {
                "path": "tests/test_service.py",
                "section": "Scope and Impact",
                "summary": "Adds regression coverage.",
            },
        ],
        "evidence": [
            {
                "id": "E1",
                "type": "DIFF",
                "reference": "src/service.py",
                "status": "INFO",
                "detail": "The return value changed from zero to one",
            },
            {
                "id": "E2",
                "type": "VALIDATION",
                "reference": "fixture test",
                "status": "PASS",
                "detail": "Focused fixture test passed",
            },
        ],
        "claims": [
            {
                "id": "C1",
                "category": "IMPLEMENTATION",
                "text": "Service returns the corrected value.",
                "evidence_ids": ["E1"],
            },
            {
                "id": "C2",
                "category": "TEST",
                "text": "Focused fixture test passed.",
                "evidence_ids": ["E2"],
            },
        ],
        "body": body(),
        "remote_update": {
            "requested": False,
            "expected_head_sha": head,
            "observed_head_sha": head,
            "status": "NOT_REQUESTED",
            "receipts": [],
            "error": None,
        },
    }


def validate(
    context_path: Path, report: dict[str, Any], expected_success: bool, root: Path
) -> None:
    report_path = root / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = run(
        [
            sys.executable,
            str(VALIDATOR),
            "--context",
            str(context_path),
            str(report_path),
        ],
        root,
    )
    if (result.returncode == 0) != expected_success:
        raise AssertionError(
            f"validator expectation mismatch\nstdout={result.stdout}\nstderr={result.stderr}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sam-pr-description-test-") as temp_dir:
        root = Path(temp_dir)
        repo, base, head = fixture(root)
        context_path = root / "context.json"
        context = build_context(repo, base, context_path)
        merge_base_result = run(builder_command(repo, base, head, "merge-base"), repo)
        if merge_base_result.returncode != 0:
            raise AssertionError(
                f"merge-base comparison failed: {merge_base_result.stderr}"
            )
        merge_base_context = json.loads(merge_base_result.stdout)
        if (
            merge_base_context["target"]["comparison"] != "merge-base"
            or merge_base_context["target"]["base_sha"] != base
        ):
            raise AssertionError("merge-base comparison target was not preserved")
        if "PROJ-9" not in context["reference_candidates"]:
            raise AssertionError(
                "reference candidate should come from branch or commit evidence"
            )
        renamed = next(
            item for item in context["files"] if item["path"] == "docs/new.md"
        )
        deleted = next(
            item for item in context["files"] if item["path"] == "docs/remove.md"
        )
        if renamed["old_path"] != "docs/old.md" or renamed["new_path"] != "docs/new.md":
            raise AssertionError("rename paths were not preserved")
        if deleted["old_path"] != "docs/remove.md" or deleted["new_path"] is not None:
            raise AssertionError("deletion paths were not preserved")

        clean = valid_report(context)
        validate(context_path, clean, True, root)

        malformed_context = copy.deepcopy(context)
        malformed_context["commits"][0]["sha"] = "not-a-full-object-id"
        refingerprint(malformed_context, "context_fingerprint")
        malformed_context_path = root / "malformed-context.json"
        malformed_context_path.write_text(
            json.dumps(malformed_context), encoding="utf-8"
        )
        malformed_report = valid_report(malformed_context)
        validate(malformed_context_path, malformed_report, False, root)

        missing_file = copy.deepcopy(clean)
        missing_file["file_coverage"].pop()
        validate(context_path, missing_file, False, root)

        placeholder = copy.deepcopy(clean)
        placeholder["body"] = placeholder["body"].replace(
            "Verify the value contract.", "TODO"
        )
        validate(context_path, placeholder, False, root)

        unsupported_claim = copy.deepcopy(clean)
        unsupported_claim["claims"][0]["evidence_ids"] = ["missing"]
        validate(context_path, unsupported_claim, False, root)

        wrong_type = copy.deepcopy(clean)
        wrong_type["change_types"] = ["NEW_FEATURE"]
        validate(context_path, wrong_type, False, root)

        unsafe_drift = copy.deepcopy(clean)
        unsafe_drift["remote_update"].update(
            {
                "requested": True,
                "observed_head_sha": "0" * len(head),
                "status": "PLANNED",
            }
        )
        validate(context_path, unsafe_drift, False, root)

        blocked_drift = copy.deepcopy(unsafe_drift)
        blocked_drift["remote_update"].update(
            {"status": "BLOCKED", "error": "Remote head changed"}
        )
        validate(context_path, blocked_drift, True, root)

        updated = copy.deepcopy(clean)
        updated["remote_update"].update(
            {
                "requested": True,
                "status": "UPDATED",
                "receipts": [
                    {
                        "kind": "description",
                        "id": "receipt-9",
                        "url": "https://example.invalid/change/9",
                        "status": "updated",
                    }
                ],
            }
        )
        validate(context_path, updated, True, root)

        exercise_git_isolation(root, repo, base, head)
        exercise_sensitive_content(root)

    print(
        "PASS: base-aware context, Git isolation, secret safety, claims, coverage, placeholders, drift, and receipts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
