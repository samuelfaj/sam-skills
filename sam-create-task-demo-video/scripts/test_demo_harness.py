#!/usr/bin/env python3
"""Self-test demo manifest, plan audit, media capability probe, and report validator."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import runpy
import shlex
import subprocess
import sys
import tempfile
import time
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
BUILDER = HERE / "build_demo_manifest.py"
AUDITOR = HERE / "audit_demo_plan.py"
MEDIA = HERE / "media_tools.py"
VALIDATOR = HERE / "validate_demo_report.py"
SCAFFOLD = HERE / "scaffold_demo_report.py"
EMBEDS = HERE / "count_embeds.py"


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


def write_trusted_media_tools(
    directory: pathlib.Path, report_marker: pathlib.Path
) -> None:
    directory.mkdir()
    ffmpeg = directory / "ffmpeg"
    ffmpeg.write_text(
        "#!/bin/sh\n"
        f'if [ -n "${{FFREPORT:-}}" ]; then printf report > {shlex.quote(str(report_marker))}; fi\n'
        "mode=${FAKE_MEDIA_MODE:-success}\n"
        'if [ "$mode" = hang ]; then exec sleep 2; fi\n'
        'for arg in "$@"; do output=$arg; done\n'
        'case "$output" in\n'
        "  *.png) printf '\\211PNG\\r\\n\\032\\nsynthetic' > \"$output\" ;;\n"
        "  *.jpg|*.jpeg) printf '\\377\\330synthetic' > \"$output\" ;;\n"
        "  *) printf '\\000\\000\\000\\030ftypisomsynthetic' > \"$output\" ;;\n"
        "esac\n"
        'if [ "$mode" = fail ]; then printf MEDIA_TOOL_SECRET_MUST_NOT_LEAK >&2; exit 9; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    ffmpeg.chmod(0o755)
    ffprobe = directory / "ffprobe"
    ffprobe.write_text(
        "#!/bin/sh\n"
        'if [ "${FAKE_MEDIA_MODE:-success}" = hang-probe ]; then exec sleep 2; fi\n'
        'printf \'%s\' \'{"streams":[{"codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p","width":1280,"height":720,"avg_frame_rate":"30/1","duration":"1.0"}],"format":{"format_name":"mp4","duration":"1.0"}}\'\n',
        encoding="utf-8",
    )
    ffprobe.chmod(0o755)


def assert_no_media_temporary(output: pathlib.Path) -> None:
    leftovers = list(output.parent.glob(f".{output.stem}.*{output.suffix}"))
    if leftovers:
        raise AssertionError(f"temporary media output was not cleaned: {leftovers}")


def verify_git_isolation() -> None:
    with tempfile.TemporaryDirectory(prefix="sam-demo-git-safety-") as temporary:
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
        manifest = json.loads(result.stdout)
        records = {item["path"]: item for item in manifest["files"]}
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
        placeholder_manifest = json.loads(run(*builder_command, env=inherited).stdout)
        placeholder_paths = {item["path"] for item in placeholder_manifest["files"]}
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


def verify_racy_index() -> None:
    """A same-size edit made in the commit's second must still reach the manifest."""
    with tempfile.TemporaryDirectory(prefix="sam-demo-racy-") as temporary:
        root = pathlib.Path(temporary)
        run("git", "init", "-q", cwd=root)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
        run("git", "config", "user.name", "Fixture", cwd=root)
        time.sleep(1.05 - time.time() % 1)
        (root / "app.txt").write_text("value = 1\n", encoding="utf-8")
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-qm", "base", cwd=root)
        (root / "app.txt").write_text("value = 2\n", encoding="utf-8")
        time.sleep(1.2)
        manifest = json.loads(run(sys.executable, str(BUILDER), "--repo", str(root)).stdout)
        if [item["path"] for item in manifest["files"]] != ["app.txt"]:
            raise AssertionError("racily-clean edit was dropped from the manifest")


def verify_base_resolution() -> None:
    with tempfile.TemporaryDirectory(prefix="sam-demo-base-") as temporary:
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


def verify_media_resolution() -> None:
    with tempfile.TemporaryDirectory(prefix="sam-demo-media-safety-") as temporary:
        outer = pathlib.Path(temporary)
        root = outer / "repo"
        nested = root / "nested" / "work"
        fake_bin = root / "repo-bin"
        nested.mkdir(parents=True)
        fake_bin.mkdir()
        run("git", "init", "-q", cwd=root)
        marker = root / "media-probe-ran"
        write_probe(fake_bin / "ffmpeg", marker)
        write_probe(fake_bin / "ffprobe", marker)
        sample = root / "sample.mp4"
        sample.write_bytes(b"\x00\x00\x00\x18ftypisomsynthetic-demo-fixture")

        inherited = os.environ.copy()
        inherited["PATH"] = f"{fake_bin}{os.pathsep}{inherited.get('PATH', '')}"
        capabilities = json.loads(
            run(
                sys.executable,
                str(MEDIA),
                "capabilities",
                cwd=nested,
                env=inherited,
            ).stdout
        )
        if capabilities != {"ffmpeg": False, "ffprobe": False}:
            raise AssertionError("repo-local media tools were reported as safe")
        run(
            sys.executable,
            str(MEDIA),
            "inspect",
            "--input",
            str(sample),
            cwd=nested,
            env=inherited,
            expected=2,
        )

        symlink_bin = outer / "symlink-bin"
        symlink_bin.mkdir()
        (symlink_bin / "ffmpeg").symlink_to(fake_bin / "ffmpeg")
        (symlink_bin / "ffprobe").symlink_to(fake_bin / "ffprobe")
        inherited["PATH"] = f"{symlink_bin}{os.pathsep}{os.environ.get('PATH', '')}"
        linked = json.loads(
            run(
                sys.executable,
                str(MEDIA),
                "capabilities",
                cwd=nested,
                env=inherited,
            ).stdout
        )
        if linked != {"ffmpeg": False, "ffprobe": False}:
            raise AssertionError(
                "symlinked repo-local media tools were reported as safe"
            )
        if marker.exists():
            raise AssertionError("repository-controlled media executable ran")

        foreign_root = outer / "foreign-repo"
        foreign_bin = foreign_root / "bin"
        foreign_bin.mkdir(parents=True)
        run("git", "init", "-q", cwd=foreign_root)
        foreign_marker = outer / "foreign-media-probe-ran"
        write_probe(foreign_bin / "ffmpeg", foreign_marker)
        write_probe(foreign_bin / "ffprobe", foreign_marker)
        foreign = os.environ.copy()
        foreign["PATH"] = f"{foreign_bin}{os.pathsep}{foreign.get('PATH', '')}"
        foreign_capabilities = json.loads(
            run(
                sys.executable,
                str(MEDIA),
                "capabilities",
                cwd=nested,
                env=foreign,
            ).stdout
        )
        if foreign_capabilities != {"ffmpeg": False, "ffprobe": False}:
            raise AssertionError("foreign worktree media tools were reported as safe")
        if foreign_marker.exists():
            raise AssertionError("foreign worktree media executable ran")

        package_manager_root = outer / "opt" / "homebrew"
        (package_manager_root / ".git").mkdir(parents=True)
        package_manager_bin = package_manager_root / "bin"
        package_manager_marker = outer / "package-manager-report-created"
        write_trusted_media_tools(package_manager_bin, package_manager_marker)
        namespace = runpy.run_path(str(MEDIA), run_name="sam_demo_media_tools_harness")
        resolver = namespace["executable"]
        configured_roots = resolver.__globals__["TRUSTED_PACKAGE_MANAGER_ROOTS"]
        if pathlib.Path("/opt/homebrew") not in configured_roots:
            raise AssertionError("Homebrew prefix is not configured as trusted")
        resolver.__globals__["TRUSTED_PACKAGE_MANAGER_ROOTS"] = (
            package_manager_root.absolute(),
            package_manager_root.resolve(),
        )
        original_path = os.environ.get("PATH")
        os.environ["PATH"] = f"{package_manager_bin}{os.pathsep}{original_path or ''}"
        try:
            package_manager_tools = {
                name: resolver(name) for name in ("ffmpeg", "ffprobe")
            }
        finally:
            if original_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original_path
        expected_package_manager_tools = {
            name: str((package_manager_bin / name).resolve())
            for name in ("ffmpeg", "ffprobe")
        }
        if package_manager_tools != expected_package_manager_tools:
            raise AssertionError("trusted package-manager media tools were rejected")

        nested_worktree = package_manager_root / "nested-repo"
        nested_bin = nested_worktree / "bin"
        nested_bin.mkdir(parents=True)
        run("git", "init", "-q", cwd=nested_worktree)
        nested_marker = outer / "nested-media-probe-ran"
        write_probe(nested_bin / "ffmpeg", nested_marker)
        write_probe(nested_bin / "ffprobe", nested_marker)
        os.environ["PATH"] = f"{nested_bin}{os.pathsep}{original_path or ''}"
        try:
            try:
                resolver("ffmpeg")
            except namespace["MediaError"]:
                pass
            else:
                raise AssertionError(
                    "nested package-manager worktree tool was reported as safe"
                )
        finally:
            if original_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original_path
        if nested_marker.exists():
            raise AssertionError("nested package-manager worktree executable ran")

        report_marker = outer / "ffreport-created"
        trusted_bin = outer / "trusted-bin"
        write_trusted_media_tools(trusted_bin, report_marker)
        trusted = os.environ.copy()
        trusted.update(
            {
                "PATH": f"{trusted_bin}{os.pathsep}{trusted.get('PATH', '')}",
                "FFREPORT": f"file={report_marker}",
                "FAKE_MEDIA_MODE": "success",
            }
        )
        trusted_capabilities = json.loads(
            run(
                sys.executable,
                str(MEDIA),
                "capabilities",
                cwd=nested,
                env=trusted,
            ).stdout
        )
        if trusted_capabilities != {"ffmpeg": True, "ffprobe": True}:
            raise AssertionError("trusted external media tools were rejected")

        preserved = outer / "preserved.mp4"
        preserved_bytes = b"existing-output-must-survive"
        preserved.write_bytes(preserved_bytes)
        run(
            sys.executable,
            str(MEDIA),
            "convert",
            "--input",
            str(sample),
            "--output",
            str(preserved),
            cwd=nested,
            env=trusted,
            expected=2,
        )
        if preserved.read_bytes() != preserved_bytes:
            raise AssertionError("existing MP4 output was overwritten")
        assert_no_media_temporary(preserved)

        symlink_target = outer / "symlink-target.mp4"
        symlink_target.write_bytes(preserved_bytes)
        symlink_output = outer / "symlink-output.mp4"
        symlink_output.symlink_to(symlink_target)
        run(
            sys.executable,
            str(MEDIA),
            "convert",
            "--input",
            str(sample),
            "--output",
            str(symlink_output),
            cwd=nested,
            env=trusted,
            expected=2,
        )
        if symlink_target.read_bytes() != preserved_bytes:
            raise AssertionError("symlink target was overwritten")

        failed_output = outer / "partial.mp4"
        failed = trusted.copy()
        failed["FAKE_MEDIA_MODE"] = "fail"
        failed_result = run(
            sys.executable,
            str(MEDIA),
            "convert",
            "--input",
            str(sample),
            "--output",
            str(failed_output),
            cwd=nested,
            env=failed,
            expected=2,
        )
        if failed_output.exists():
            raise AssertionError("failed conversion installed a partial output")
        if "MEDIA_TOOL_SECRET_MUST_NOT_LEAK" in (
            failed_result.stdout + failed_result.stderr
        ):
            raise AssertionError("media tool stderr leaked through the wrapper")
        assert_no_media_temporary(failed_output)

        timeout_output = outer / "timeout.mp4"
        hanging = trusted.copy()
        hanging["FAKE_MEDIA_MODE"] = "hang"
        timeout_result = run(
            sys.executable,
            str(MEDIA),
            "convert",
            "--input",
            str(sample),
            "--output",
            str(timeout_output),
            "--timeout-seconds",
            "0.1",
            cwd=nested,
            env=hanging,
            expected=2,
        )
        if "timed out" not in timeout_result.stderr or timeout_output.exists():
            raise AssertionError("hanging media command did not fail cleanly")
        assert_no_media_temporary(timeout_output)

        converted = outer / "converted.mp4"
        run(
            sys.executable,
            str(MEDIA),
            "convert",
            "--input",
            str(sample),
            "--output",
            str(converted),
            cwd=nested,
            env=trusted,
        )
        if not converted.read_bytes().startswith(b"\x00\x00\x00\x18ftyp"):
            raise AssertionError("validated conversion was not atomically installed")
        assert_no_media_temporary(converted)

        existing_sheet = outer / "existing.png"
        existing_sheet.write_bytes(preserved_bytes)
        run(
            sys.executable,
            str(MEDIA),
            "contact-sheet",
            "--input",
            str(sample),
            "--output",
            str(existing_sheet),
            cwd=nested,
            env=trusted,
            expected=2,
        )
        if existing_sheet.read_bytes() != preserved_bytes:
            raise AssertionError("existing contact sheet was overwritten")

        sheet = outer / "sheet.png"
        run(
            sys.executable,
            str(MEDIA),
            "contact-sheet",
            "--input",
            str(sample),
            "--output",
            str(sheet),
            cwd=nested,
            env=trusted,
        )
        if not sheet.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise AssertionError("validated contact sheet was not installed")
        assert_no_media_temporary(sheet)
        if report_marker.exists():
            raise AssertionError("FFREPORT side effect was not stripped")


def dump(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def valid_report(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_fingerprint": manifest["fingerprint"],
        "target": {
            "base_sha": manifest["target"]["base_sha"],
            "head_sha": manifest["target"]["head_sha"],
        },
        "intent": {
            "summary": "Show the saved profile name after reload.",
            "invariants": ["Only the demo profile changes."],
            "no_go": ["Do not show private account data."],
        },
        "environment": {
            "kind": "dev",
            "identity": "temporary-demo-fixture",
            "real_data": False,
            "evidence": "isolated local app with synthetic account",
        },
        "authorization": {"publish_requested": False},
        "command_definitions": {
            "changed": bool(manifest["command_definitions"]),
            "inspected": True,
            "evidence": "changed command definitions inspected before startup",
        },
        "criteria": [
            {"id": "AC-001", "text": "Saved name remains visible after reload."}
        ],
        "risks": [
            {
                "id": "R-001",
                "criterion_ids": ["AC-001"],
                "level": "HIGH",
                "evidence": "stale state could hide persistence failure",
            }
        ],
        "scenarios": [
            {
                "id": "S-001",
                "criterion_ids": ["AC-001"],
                "risk_ids": ["R-001"],
                "check_ids": ["T-001"],
                "artifact_ids": ["ART-001"],
                "initial_state": "profile page shows the original name",
                "actions": ["edit name", "save", "reload page"],
                "proof_moment": "saved name remains visible after reload",
                "final_state": "profile page remains stable with saved name",
            }
        ],
        "checks": [
            {
                "id": "T-001",
                "scenario_ids": ["S-001"],
                "command_ids": ["CMD-001"],
                "assertion": "video visibly shows the persisted value after reload",
            }
        ],
        "commands": [
            {
                "id": "CMD-001",
                "check_ids": ["T-001"],
                "command": "record, convert, inspect, and validate local demo",
                "status": "PASS",
                "evidence": "recording and media validation completed",
            }
        ],
        "artifacts": [
            {
                "id": "ART-001",
                "scenario_ids": ["S-001"],
                "status": "LOCAL",
                "path": "/tmp/profile-demo.mp4",
                "media": {
                    "mime_type": "video/mp4",
                    "conversion_status": "PASS",
                    "sha256": "a" * 64,
                    "metadata": {
                        "has_video": True,
                        "codec": "h264",
                        "duration_seconds": 12.5,
                        "width": 1280,
                        "height": 720,
                    },
                },
                "playback_verified": True,
                "privacy_review": {
                    "status": "PASS",
                    "evidence": "full playback reviewed",
                },
                "contact_sheet_review": {
                    "status": "PASS",
                    "evidence": "twelve timeline frames reviewed",
                },
            }
        ],
        "cleanup": [
            {
                "id": "CL-001",
                "resource": "raw WebM and synthetic record",
                "status": "CLEANED",
            }
        ],
        "plan_audit": {"status": "PASS", "evidence": "audit script returned PASS"},
        "recording": {
            "real_ui": True,
            "requires_linked_backend": True,
            "linked_backend": True,
            "fallback_reason": "",
        },
        "publication": {"status": "NOT_REQUESTED"},
        "decision": "READY_LOCAL",
    }


def invalid(
    manifest_path: pathlib.Path,
    report_path: pathlib.Path,
    report: dict[str, Any],
    needle: str | None = None,
) -> None:
    dump(report_path, report)
    result = run(
        sys.executable,
        str(VALIDATOR),
        "--manifest",
        str(manifest_path),
        str(report_path),
        expected=1,
    )
    if needle is not None and needle not in result.stderr:
        raise AssertionError(f"expected {needle!r} in:\n{result.stderr}")


def verify_scaffold(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
    manifest: dict[str, Any],
    video_path: pathlib.Path,
    filled: dict[str, Any],
) -> None:
    """The scaffold copies manifest and media facts exactly and fails closed elsewhere."""
    report_path = root / "scaffold-report.json"
    base = (sys.executable, str(SCAFFOLD), "--manifest", str(manifest_path))
    # Creating a report forces an explicit publication decision.
    run(*base, "--report", str(report_path), expected=2)
    if report_path.exists():
        raise AssertionError("scaffold created a report without a publication decision")
    run(*base, "--report", str(report_path), "--publish-requested", "false")
    created = json.loads(report_path.read_text(encoding="utf-8"))
    if created["manifest_fingerprint"] != manifest["fingerprint"] or created[
        "target"
    ] != {
        "base_sha": manifest["target"]["base_sha"],
        "head_sha": manifest["target"]["head_sha"],
    }:
        raise AssertionError("scaffold did not copy the manifest fingerprint and SHAs")
    if created["command_definitions"]["changed"] is not bool(
        manifest["command_definitions"]
    ):
        raise AssertionError("scaffold did not derive the command-definition flag")
    if created["publication"] != {"status": "NOT_REQUESTED"}:
        raise AssertionError("local-only scaffold must start NOT_REQUESTED")
    # Unfilled placeholders must never validate.
    run(
        sys.executable,
        str(VALIDATOR),
        "--manifest",
        str(manifest_path),
        str(report_path),
        expected=1,
    )
    # The pre-recording audit refuses an environment that never declared real_data.
    raw_audit = run(
        sys.executable, str(AUDITOR), "--manifest", str(manifest_path), str(report_path),
        expected=1,
    )
    if "UNDECLARED_REAL_DATA" not in raw_audit.stdout:
        raise AssertionError("audit passed the scaffold's undeclared real_data")
    # Authorization cannot be flipped by a refresh.
    run(*base, "--report", str(report_path), "--publish-requested", "true", expected=2)
    if json.loads(report_path.read_text(encoding="utf-8"))["authorization"] != {
        "publish_requested": False
    }:
        raise AssertionError("refresh changed the publication authorization")

    media = {
        "path": str(video_path),
        "mime_type": "video/mp4",
        "container": "mov,mp4,m4a,3gp,3g2,mj2",
        "size_bytes": video_path.stat().st_size,
        "sha256": hashlib.sha256(video_path.read_bytes()).hexdigest(),
        "has_video": True,
        "codec": "h264",
        "pixel_format": "yuv420p",
        "width": 1280,
        "height": 720,
        "frame_rate": "30/1",
        "duration_seconds": 12.5,
    }
    media_path = root / "media.json"
    dump(media_path, media)
    run(*base, "--report", str(report_path), "--media", str(media_path))
    refreshed = json.loads(report_path.read_text(encoding="utf-8"))
    artifact = refreshed["artifacts"][0]
    if (
        artifact["path"] != media["path"]
        or artifact["media"]["sha256"] != media["sha256"]
        or artifact["media"]["metadata"]["width"] != 1280
        or artifact["media"]["metadata"]["duration_seconds"] != 12.5
    ):
        raise AssertionError("scaffold did not copy the inspected media facts")
    if artifact["media"]["conversion_status"] != "TODO:PASS|FAIL":
        raise AssertionError("scaffold must not assert the conversion result")

    # Filling only the semantic fields must validate: the derived ones are exact.
    completed = copy.deepcopy(refreshed)
    for key in (
        "intent",
        "environment",
        "criteria",
        "risks",
        "scenarios",
        "checks",
        "commands",
        "cleanup",
        "plan_audit",
        "recording",
        "publication",
        "decision",
    ):
        completed[key] = copy.deepcopy(filled[key])
    for key in ("inspected", "evidence"):
        completed["command_definitions"][key] = filled["command_definitions"][key]
    for key in ("status", "playback_verified", "privacy_review", "contact_sheet_review"):
        completed["artifacts"][0][key] = copy.deepcopy(filled["artifacts"][0][key])
    completed["artifacts"][0]["media"]["conversion_status"] = "PASS"
    dump(report_path, completed)
    run(
        sys.executable,
        str(VALIDATOR),
        "--manifest",
        str(manifest_path),
        str(report_path),
    )

    # A rebuilt manifest is re-derived on refresh without touching filled fields.
    rebuilt = copy.deepcopy(manifest)
    rebuilt["fingerprint"] = "f" * 64
    rebuilt_path = root / "rebuilt-manifest.json"
    dump(rebuilt_path, rebuilt)
    run(sys.executable, str(SCAFFOLD), "--manifest", str(rebuilt_path), "--report", str(report_path))
    again = json.loads(report_path.read_text(encoding="utf-8"))
    if again["manifest_fingerprint"] != "f" * 64 or again["intent"] != filled["intent"]:
        raise AssertionError("refresh must re-derive the fingerprint and keep filled fields")


def verify_embed_counts(root: pathlib.Path) -> None:
    """Readback passes only when each uploaded URL renders as its kind's embed."""
    gh_video = "https://github.com/user-attachments/assets/1a2b-3c4d"
    gh_image = "https://github.com/user-attachments/assets/5e6f-7a8b"
    gl_video = "/uploads/abc123/demo.mp4"
    gl_image = "/uploads/abc123/after.png"
    gh = ("--video-url", gh_video, "--image-url", gh_image)
    cases = (
        # Host player/image markup, beside a legitimate link to source code.
        (
            f"### Demo\n\n{gh_video}\n\n### After\n\n![after]({gh_image})\n\n"
            "See [the handler](https://github.com/o/r/blob/main/src/app.ts).\n",
            gh,
            True,
        ),
        (
            f"### Demo\n\n![demo]({gl_video}){{width=100%}}\n\n### After\n\n![after]({gl_image})\n",
            ("--video-url", gl_video, "--image-url", gl_image),
            True,
        ),
        (f"[Download MP4]({gh_video})\n", ("--video-url", gh_video), False),
        (
            f"{gh_video}\n\n[video](https://github.com/org/repo/blob/main/demo.mp4)\n",
            ("--video-url", gh_video),
            False,
        ),
        (f'<video src="{gl_video}"></video>\n', ("--video-url", gl_video), False),
        (f"[![thumb]({gl_image})]({gl_video})\n", ("--video-url", gl_video), False),
        # A download link beside a real player still fails.
        (f"{gh_video}\n\n[Download]({gh_video})\n", ("--video-url", gh_video), False),
        # Code renders as text, never as a player.
        (f"```\n{gh_video}\n```\n", ("--video-url", gh_video), False),
        (f"~~~md\n![demo]({gl_video})\n~~~\n", ("--video-url", gl_video), False),
        (f"`![after]({gl_image})`\n", ("--image-url", gl_image), False),
        (f"<!--\n{gh_video}\n-->\n", ("--video-url", gh_video), False),
        (f"    {gh_video}\n", ("--video-url", gh_video), False),
        (f"Intro\n\n    ![demo]({gl_video})\n", ("--video-url", gl_video), False),
        (f"Intro\n\n\t![after]({gh_image})\n", ("--image-url", gh_image), False),
        # Indentation inside a list item or a paragraph continuation is not code.
        (f"- Demo\n\n    ![demo]({gl_video})\n", ("--video-url", gl_video), True),
        (f"Intro\n    ![after]({gh_image})\n", ("--image-url", gh_image), True),
        # A committed media file is forbidden even as a bare line or autolink.
        (
            f"{gh_video}\n\nhttps://github.com/o/r/blob/main/demo.mp4\n",
            ("--video-url", gh_video),
            False,
        ),
        (f"{gh_video}\n\nSee https://github.com/o/r/blob/main/demo.mp4.\n", ("--video-url", gh_video), False),
        (
            f"![after]({gh_image})\n\n<https://raw.githubusercontent.com/o/r/main/demo.mp4>\n",
            ("--image-url", gh_image),
            False,
        ),
        (
            f"{gh_video}\n\n[demo](https://media.githubusercontent.com/media/o/r/main/demo.mp4)\n",
            ("--video-url", gh_video),
            False,
        ),
        # GitHub attachment URLs carry no extension: the kind comes from the receipt.
        (f"![demo]({gh_video})\n\n{gh_image}\n", gh, False),
        (f"![demo]({gh_video})\n", ("--video-url", gh_video), False),
        (f"![after]({gh_image})\n\n{gh_image}\n", ("--image-url", gh_image), False),
        # GLFM plays only video extensions inside image syntax.
        (f"![demo]({gl_image})\n", ("--video-url", gl_image), False),
        # Only host uploads count; media hosted elsewhere is not an attachment.
        (
            "![demo](https://cdn.example.com/demo.mp4)\n",
            ("--video-url", "https://cdn.example.com/demo.mp4"),
            False,
        ),
        # An uploaded URL that never made it into the body is a failed publication.
        ("### Demo\n\nno media here\n", ("--video-url", gh_video), False),
        (f"{gh_video}\n", ("--video-url", "https://github.com/o/r/blob/main/demo.mp4"), False),
        # Download forms hidden in reference links, anchors, or legacy asset URLs.
        (
            f"![demo]({gl_video})\n\n[Download][1]\n\n[1]: /uploads/zzz/other.mp4\n",
            ("--video-url", gl_video),
            False,
        ),
        (
            f"{gh_video}\n\n[Download][d]\n\n[d]: https://cdn.example.com/demo.mp4\n",
            ("--video-url", gh_video),
            False,
        ),
        (
            f"{gh_video}\n\n[x](https://github.com/o/r/assets/1/demo.mp4)\n",
            ("--video-url", gh_video),
            False,
        ),
        (
            f'![demo]({gl_video})\n\n<a data-href="x" href="/uploads/zzz/other.mp4">demo</a>\n',
            ("--video-url", gl_video),
            False,
        ),
        (f"[ ![thumb]({gl_image}) ](https://example.com/v)\n", ("--image-url", gl_image), False),
        # HTML code renders as text; unmatched backticks open no code span.
        (f"<pre>\n{gh_video}\n</pre>\n", ("--video-url", gh_video), False),
        (f"<code>![demo]({gl_video})</code>\n", ("--video-url", gl_video), False),
        (f"{gh_video}\n\nRun ``a [Download]({gh_video}) b`\n", ("--video-url", gh_video), False),
        (f"Run ``a ![after]({gh_image}) b`\n", ("--image-url", gh_image), True),
        # Every copy of a GitHub video must be bare, and any <video> tag fails.
        (f"{gh_video}\n\n![x]({gh_video})\n", ("--video-url", gh_video), False),
        (f'{gh_video}\n\n<video src="https://cdn.example.com/x.mp4"></video>\n', ("--video-url", gh_video), False),
        # A definition whose destination sits on the next line is still a link.
        (f"### Demo\n\n[Watch the demo][1]\n\n[1]:\n{gh_video}\n", ("--video-url", gh_video), False),
        # A backtick inside a comment never pairs with a later one to hide a link.
        (f"{gh_video}\n\n<!-- use ` for code -->\n[Download]({gh_video}) and `x`\n", ("--video-url", gh_video), False),
        # Media files and attachment assets are links wherever they are wrapped.
        (f"{gh_video}\n\n[Download](https://cdn.example.com/demo.mp4)\n", ("--video-url", gh_video), False),
        (f"{gh_video}\n\n[Download [mp4]](https://github.com/user-attachments/assets/other)\n", ("--video-url", gh_video), False),
        (f'![demo]({gl_video})\n\n<a title=">" href="/uploads/z/o.mp4">demo</a>\n', ("--video-url", gl_video), False),
        # Links to uploaded non-media files are not media links.
        (f"{gh_video}\n\n[build log](https://github.com/user-attachments/files/123/log.txt)\n", ("--video-url", gh_video), True),
        (f"![demo]({gl_video})\n\n[trace](/uploads/zzz/trace.zip)\n", ("--video-url", gl_video), True),
        # Inline code that merely names an HTML tag hides nothing after it.
        (f"Replaced `<code>` and `<!--` markers.\n\n{gh_video}\n\n[Download]({gh_video})\n", ("--video-url", gh_video), False),
        (f"Replaced `<code>` and `<!--` markers.\n\n{gh_video}\n", ("--video-url", gh_video), True),
    )
    body = root / "readback.md"
    for text, urls, passes in cases:
        body.write_text(text, encoding="utf-8")
        result = run(sys.executable, str(EMBEDS), str(body), *urls, expected=0 if passes else 1)
        verdict = json.loads(result.stdout)
        if (verdict["status"] == "PASS") != passes or (
            not passes and not (verdict["problems"] or verdict["media_links"])
        ):
            raise AssertionError(f"embed readback misjudged {text!r}: {verdict}")
    # Without the uploaded URLs nothing can be checked.
    run(sys.executable, str(EMBEDS), str(body), expected=2)
    # Long whitespace-free runs stay linear (backtracking scans took minutes).
    body.write_text(
        f"{gh_video}\n\n" + "/raw/" * 13000 + " " + "a" * 65000 + " " + "![" * 20000
        + " [a](" + "/x/" * 5000 + " " + " ".join("`" * n for n in range(1, 300)) + "\n",
        encoding="utf-8",
    )
    started = time.monotonic()
    try:
        result = subprocess.run(
            [sys.executable, str(EMBEDS), str(body), "--video-url", gh_video],
            text=True, capture_output=True, check=False, timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError("embed readback hangs on long lines") from exc
    if result.returncode != 0 or time.monotonic() - started > 10:
        raise AssertionError(f"long-line readback slow or misjudged: {result.stdout}")


def main() -> int:
    capabilities = json.loads(run(sys.executable, str(MEDIA), "capabilities").stdout)
    if set(capabilities) != {"ffmpeg", "ffprobe"}:
        raise AssertionError("capability probe must work without requiring media tools")

    with tempfile.TemporaryDirectory(prefix="sam-demo-harness-") as temp:
        root = pathlib.Path(temp)
        run("git", "init", "-q", cwd=root)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
        run("git", "config", "user.name", "Fixture", cwd=root)
        (root / "app.txt").write_text("old profile\n", encoding="utf-8")
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-qm", "base", cwd=root)
        (root / "app.txt").write_text("saved profile\n", encoding="utf-8")

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
        manifest = json.loads(result.stdout)
        manifest_path = root / "manifest.json"
        dump(manifest_path, manifest)
        if len(manifest["files"]) != 1 or not manifest["fingerprint"]:
            raise AssertionError("manifest lost the changed target")
        # Callers read SHAs from one stderr line instead of the patch-bearing file.
        summary = result.stderr.strip().splitlines()
        if not summary or not summary[-1].startswith(
            f"manifest fingerprint={manifest['fingerprint']} "
            f"base={manifest['target']['base_sha']} "
            f"head={manifest['target']['head_sha']} "
        ):
            raise AssertionError(f"missing compact manifest summary: {result.stderr!r}")
        # Changed paths come from stderr too, so storyboarding never opens the manifest.
        if 'changed_paths=["app.txt"]' not in summary:
            raise AssertionError(f"missing changed-path line: {result.stderr!r}")
        if "saved profile" in result.stderr:
            raise AssertionError("manifest summary leaked patch content")

        video_path = root / "profile-demo.mp4"
        video_path.write_bytes(b"\x00\x00\x00\x18ftypisomsynthetic-demo-fixture")
        report = valid_report(manifest)
        report["artifacts"][0]["path"] = str(video_path)
        report["artifacts"][0]["media"]["sha256"] = hashlib.sha256(
            video_path.read_bytes()
        ).hexdigest()
        report_path = root / "report.json"
        dump(report_path, report)
        run(
            sys.executable,
            str(AUDITOR),
            "--manifest",
            str(manifest_path),
            str(report_path),
        )
        run(
            sys.executable,
            str(VALIDATOR),
            "--manifest",
            str(manifest_path),
            str(report_path),
        )
        verify_scaffold(root, manifest_path, manifest, video_path, report)
        verify_embed_counts(root)

        unsafe_data = copy.deepcopy(report)
        unsafe_data["environment"].update({"kind": "unknown", "real_data": True})
        invalid(manifest_path, report_path, unsafe_data)

        # The scaffold's null real_data must never pass as "no real data".
        undeclared = copy.deepcopy(report)
        undeclared["environment"]["real_data"] = None
        invalid(manifest_path, report_path, undeclared, "environment.real_data must be boolean")
        audit = run(
            sys.executable, str(AUDITOR), "--manifest", str(manifest_path), str(report_path),
            expected=1,
        )
        if "UNDECLARED_REAL_DATA" not in audit.stdout:
            raise AssertionError("pre-recording audit accepted an undeclared real_data")

        bad_media = copy.deepcopy(report)
        bad_media["artifacts"][0]["path"] = "/tmp/profile-demo.webm"
        invalid(manifest_path, report_path, bad_media)

        missing_privacy = copy.deepcopy(report)
        missing_privacy["artifacts"][0]["privacy_review"] = {
            "status": "NOT_RUN",
            "evidence": "",
        }
        # Each failed media condition is named so the report is patched from the line.
        invalid(
            manifest_path,
            report_path,
            missing_privacy,
            "privacy_review must be PASS with evidence",
        )

        unauthorized = copy.deepcopy(report)
        unauthorized["artifacts"][0].update(
            {"status": "UPLOADED", "receipt": "remote-1", "readback_verified": True}
        )
        unauthorized["publication"] = {
            "status": "PUBLISHED",
            "receipt": "remote-1",
            "readback_verified": True,
        }
        unauthorized["decision"] = "PUBLISHED"
        invalid(manifest_path, report_path, unauthorized)

        dishonest_fallback = copy.deepcopy(report)
        dishonest_fallback["recording"]["real_ui"] = False
        dishonest_fallback["recording"]["fallback_reason"] = ""
        invalid(manifest_path, report_path, dishonest_fallback)

        secret_plan = copy.deepcopy(report)
        secret_sentinel = "DEMO_SECRET_MUST_NOT_LEAK_9f71c6"
        secret_plan["intent"]["summary"] = f"token={secret_sentinel}"
        dump(report_path, secret_plan)
        secret_result = run(
            sys.executable,
            str(AUDITOR),
            "--manifest",
            str(manifest_path),
            str(report_path),
            expected=1,
        )
        if (
            secret_sentinel in secret_result.stdout
            or secret_sentinel in secret_result.stderr
        ):
            raise AssertionError("demo audit leaked secret-like report text")

        non_string_reference = copy.deepcopy(report)
        non_string_reference["risks"][0]["criterion_ids"].append(7)
        invalid(manifest_path, report_path, non_string_reference)

        missing_criterion_text = copy.deepcopy(report)
        missing_criterion_text["criteria"][0]["text"] = ""
        invalid(manifest_path, report_path, missing_criterion_text)

        missing_risk_evidence = copy.deepcopy(report)
        missing_risk_evidence["risks"][0]["evidence"] = ""
        invalid(manifest_path, report_path, missing_risk_evidence)

        missing_scenario_check_backlink = copy.deepcopy(report)
        second_check = copy.deepcopy(missing_scenario_check_backlink["checks"][0])
        second_check["id"] = "T-002"
        missing_scenario_check_backlink["checks"].append(second_check)
        missing_scenario_check_backlink["commands"][0]["check_ids"].append("T-002")
        invalid(manifest_path, report_path, missing_scenario_check_backlink)

        missing_check_command_backlink = copy.deepcopy(report)
        second_command = copy.deepcopy(missing_check_command_backlink["commands"][0])
        second_command["id"] = "CMD-002"
        missing_check_command_backlink["commands"].append(second_command)
        invalid(manifest_path, report_path, missing_check_command_backlink)

        missing_scenario_artifact_backlink = copy.deepcopy(report)
        second_artifact = copy.deepcopy(
            missing_scenario_artifact_backlink["artifacts"][0]
        )
        second_artifact["id"] = "ART-002"
        missing_scenario_artifact_backlink["artifacts"].append(second_artifact)
        invalid(manifest_path, report_path, missing_scenario_artifact_backlink)

        publication_contradiction = copy.deepcopy(report)
        publication_contradiction["authorization"]["publish_requested"] = True
        invalid(manifest_path, report_path, publication_contradiction)

        blocked_without_reason = copy.deepcopy(report)
        blocked_without_reason["authorization"]["publish_requested"] = True
        blocked_without_reason["publication"] = {"status": "BLOCKED"}
        blocked_without_reason["decision"] = "BLOCKED"
        invalid(manifest_path, report_path, blocked_without_reason)

    verify_git_isolation()
    verify_racy_index()
    verify_base_resolution()
    verify_media_resolution()
    print(
        "PASS: demo manifest, Git/media isolation, base resolution, reciprocal "
        "graph, audit, authorization, privacy, and decision fixtures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
