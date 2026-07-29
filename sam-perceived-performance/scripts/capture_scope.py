#!/usr/bin/env python3
"""Capture a read-only, secret-safe fingerprint of local Git scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any


JsonObject = dict[str, Any]
FILTER_COMMAND = re.compile(r"^filter\..*\.(clean|process)$", re.I)


class CaptureError(RuntimeError):
    """Raised when scope cannot be captured without executing repository code."""


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def worktree_hint(repo: Path) -> Path | None:
    current = repo.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate
    return None


def resolve_git(repo: Path) -> Path:
    search_dirs = [
        item
        for item in os.defpath.split(os.pathsep)
        if item and Path(item).is_absolute()
    ]
    search_dirs.extend(("/usr/local/bin", "/opt/homebrew/bin"))
    value = shutil.which("git", path=os.pathsep.join(dict.fromkeys(search_dirs)))
    if not value:
        raise CaptureError("git is not available in trusted system locations")
    selected = Path(value).absolute()
    try:
        resolved = selected.resolve(strict=True)
    except OSError as error:
        raise CaptureError(f"could not resolve git executable: {selected}") from error
    boundaries = [repo.resolve()]
    enclosing = worktree_hint(repo)
    if enclosing is not None:
        boundaries.append(enclosing)
    if any(
        is_within(candidate, boundary)
        for candidate in (selected, resolved)
        for boundary in boundaries
    ):
        raise CaptureError(f"refusing repository-controlled git executable: {selected}")
    return resolved


def git_environment(index_file: Path | None = None) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    if index_file is not None:
        environment["GIT_INDEX_FILE"] = str(index_file)
    return environment


def run_git(
    executable: Path,
    repo: Path,
    *args: str,
    check: bool = True,
    index_file: Path | None = None,
) -> bytes:
    command = [
        str(executable),
        "-C",
        str(repo),
        "-c",
        "core.fsmonitor=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "diff.external=",
        "-c",
        "pager.diff=false",
        "--no-pager",
        *args,
    ]
    result = subprocess.run(
        command,
        env=git_environment(index_file),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise CaptureError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout if result.returncode == 0 else b""


def repository_index(executable: Path, repo: Path) -> Path:
    value = run_git(executable, repo, "rev-parse", "--git-path", "index")
    source = Path(os.fsdecode(value).strip())
    if not source.is_absolute():
        source = repo / source
    return source.resolve()


def reject_worktree_filters(executable: Path, repo: Path, index_file: Path) -> None:
    names = run_git(
        executable,
        repo,
        "config",
        "--includes",
        "--name-only",
        "--list",
        index_file=index_file,
    ).decode("utf-8", "strict")
    dangerous = sorted(
        {
            name.strip()
            for name in names.splitlines()
            if FILTER_COMMAND.fullmatch(name.strip())
        }
    )
    if dangerous:
        raise CaptureError(
            "refusing worktree inspection with configured clean/process filters: "
            + ", ".join(dangerous)
        )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_paths(raw: bytes) -> list[str]:
    return [os.fsdecode(value) for value in raw.split(b"\0") if value]


def normalize_paths(root: Path, values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        raw = Path(value)
        if raw.is_absolute():
            raise ValueError(f"path scope must be repository-relative: {value}")
        resolved = (root / raw).resolve(strict=False)
        try:
            relative = resolved.relative_to(root)
        except ValueError as error:
            raise ValueError(f"path scope escapes repository: {value}") from error
        text = relative.as_posix()
        if text and text != "." and text not in normalized:
            normalized.append(text)
    return sorted(normalized)


def path_args(paths: list[str]) -> list[str]:
    return ["--", *paths] if paths else []


def is_test_path(path: str) -> bool:
    lowered = path.lower()
    name = Path(lowered).name
    return (
        "/test/" in f"/{lowered}/"
        or "/tests/" in f"/{lowered}/"
        or "/__tests__/" in f"/{lowered}/"
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    )


def text_line_count(root: Path, relative: str) -> int:
    path = root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return 0
    if not stat.S_ISREG(metadata.st_mode):
        return 0
    resolved = path.resolve(strict=True)
    if not is_within(resolved, root):
        return 0
    count = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            if b"\0" in chunk:
                return 0
            count += chunk.count(b"\n")
    return count


def numstat_lines(
    executable: Path, root: Path, paths: list[str], index_file: Path
) -> int:
    raw = run_git(
        executable,
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--numstat",
        "HEAD",
        *path_args(paths),
        check=False,
        index_file=index_file,
    )
    total = 0
    for line in raw.decode("utf-8", "replace").splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3 or is_test_path(parts[2]):
            continue
        if parts[0].isdigit() and parts[1].isdigit():
            total += int(parts[0]) + int(parts[1])
    return total


def file_record(
    executable: Path,
    root: Path,
    path: str,
    staged: set[str],
    unstaged: set[str],
    untracked: set[str],
    index_file: Path,
) -> JsonObject:
    absolute = root / path
    worktree_hash: str | None
    if absolute.is_symlink():
        state = "symlink"
        target = os.readlink(absolute)
        worktree_hash = sha256_bytes(os.fsencode(target))
        size = len(os.fsencode(target))
    elif absolute.exists() and absolute.is_file():
        state = "file"
        worktree_hash = sha256_file(absolute)
        size = absolute.stat().st_size
    elif absolute.exists():
        state = "other"
        worktree_hash = None
        size = 0
    else:
        state = "deleted"
        worktree_hash = None
        size = 0
    index_entry = run_git(
        executable,
        root,
        "ls-files",
        "--stage",
        "-z",
        "--",
        path,
        check=False,
        index_file=index_file,
    )
    return {
        "path": path,
        "state": state,
        "size": size,
        "worktree_sha256": worktree_hash,
        "index_entry_sha256": sha256_bytes(index_entry),
        "staged": path in staged,
        "unstaged": path in unstaged,
        "untracked": path in untracked,
        "test_file": is_test_path(path),
    }


def capture_with_index(
    executable: Path,
    root: Path,
    requested_paths: list[str],
    index_file: Path,
    source_index: Path,
    index_before: str | None,
) -> JsonObject:
    reject_worktree_filters(executable, root, index_file)
    paths = normalize_paths(root, requested_paths)
    status_before = run_git(
        executable,
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        index_file=index_file,
    )
    unstaged_raw = run_git(
        executable,
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--name-only",
        "-z",
        *path_args(paths),
        index_file=index_file,
    )
    staged_raw = run_git(
        executable,
        root,
        "diff",
        "--cached",
        "--no-ext-diff",
        "--no-textconv",
        "--name-only",
        "-z",
        *path_args(paths),
        index_file=index_file,
    )
    untracked_raw = run_git(
        executable,
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        *path_args(paths),
        index_file=index_file,
    )
    unstaged = set(decode_paths(unstaged_raw))
    staged = set(decode_paths(staged_raw))
    untracked = set(decode_paths(untracked_raw))
    changed = sorted(unstaged | staged | untracked)
    records = [
        file_record(executable, root, path, staged, unstaged, untracked, index_file)
        for path in changed
    ]
    unstaged_diff = run_git(
        executable,
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--binary",
        *path_args(paths),
        index_file=index_file,
    )
    staged_diff = run_git(
        executable,
        root,
        "diff",
        "--cached",
        "--no-ext-diff",
        "--no-textconv",
        "--binary",
        *path_args(paths),
        index_file=index_file,
    )
    untracked_lines = sum(
        text_line_count(root, path) for path in untracked if not is_test_path(path)
    )
    payload: JsonObject = {
        "schema_version": 1,
        "repo_root": str(root),
        "head_sha": os.fsdecode(
            run_git(
                executable,
                root,
                "rev-parse",
                "--verify",
                "HEAD",
                check=False,
                index_file=index_file,
            )
        ).strip()
        or None,
        "branch": os.fsdecode(
            run_git(
                executable,
                root,
                "branch",
                "--show-current",
                check=False,
                index_file=index_file,
            )
        ).strip()
        or None,
        "paths": paths,
        "files": records,
        "file_count": len(records),
        "non_test_changed_lines": numstat_lines(executable, root, paths, index_file)
        + untracked_lines,
        "status_sha256": sha256_bytes(status_before),
        "unstaged_diff_sha256": sha256_bytes(unstaged_diff),
        "staged_diff_sha256": sha256_bytes(staged_diff),
    }
    fingerprint_payload = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    payload["fingerprint"] = sha256_bytes(fingerprint_payload)
    status_after = run_git(
        executable,
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        index_file=index_file,
    )
    if status_before != status_after or index_before != sha256_file(source_index):
        raise CaptureError("scope capture changed Git status or the real index")
    payload["capture_read_only"] = True
    return payload


def capture(repo: Path, requested_paths: list[str]) -> JsonObject:
    repo_input = repo.resolve()
    if not repo_input.is_dir():
        raise CaptureError(f"repository does not exist: {repo_input}")
    executable = resolve_git(repo_input)
    root_text = run_git(executable, repo_input, "rev-parse", "--show-toplevel")
    root = Path(os.fsdecode(root_text).strip()).resolve()
    source_index = repository_index(executable, root)
    index_before = sha256_file(source_index)
    with tempfile.TemporaryDirectory(prefix="sam-delivery-git-index-") as temporary:
        index_file = Path(temporary) / "index"
        if source_index.is_file():
            shutil.copyfile(source_index, index_file)
        return capture_with_index(
            executable,
            root,
            requested_paths,
            index_file,
            source_index,
            index_before,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository or nested path.")
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Repository-relative path scope; repeat as needed.",
    )
    args = parser.parse_args()
    try:
        result = capture(Path(args.repo), args.path)
    except (CaptureError, OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
