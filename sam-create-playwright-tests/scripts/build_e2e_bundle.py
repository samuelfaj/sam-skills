#!/usr/bin/env python3
"""Build an immutable, local Playwright work bundle from a Git repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

MAX_PATCH_BYTES = 4 * 1024 * 1024
MAX_UNTRACKED_BYTES = 512 * 1024
SENSITIVE_NAMES = {
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
SENSITIVE_SUFFIXES = {".jks", ".key", ".p12", ".pem", ".pfx"}
SAFE_TEMPLATE_SUFFIXES = (".dist", ".example", ".sample", ".template")
TEST_PATH = re.compile(
    r"(^|/)(tests?|e2e|specs?|__tests__)(/|$)|"
    r"(^|/)(test_.*|.*_test)\.[^/]+$|\.(test|spec)\.|Test\.(java|kt)$",
    re.I,
)
COMMAND_PATH = re.compile(
    r"(^|/)(package\.json|Makefile|Dockerfile|compose[^/]*\.ya?ml|"
    r"playwright[^/]*\.(ts|js|mjs|cjs)|\.github/workflows/.*|\.gitlab-ci\.yml)$",
    re.I,
)
FILTER_COMMAND = re.compile(r"^filter\..*\.(clean|process)$", re.I)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)(?:api[_-]?key|secret|token|password|passwd|private[_-]?key)"
        r"\s*[:=]\s*(['\"])([^'\"\r\n]{16,})\1"
    ),
    re.compile(
        r"(?i)(?:api[_-]?key|secret|token|password|passwd|private[_-]?key)"
        r"\s*=\s*([A-Za-z0-9/+_=.-]{24,})\b"
    ),
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/-]{20,}"),
    re.compile(r"https?://[^/\s:@]+:[^@\s/]+@"),
)
PLACEHOLDER_MARKERS = (
    "example",
    "sample",
    "placeholder",
    "changeme",
    "redacted",
    "dummy",
    "fake",
    "test-only",
    "xxxxxxxx",
    "<secret>",
    "${",
)


class BundleError(RuntimeError):
    """Raised when a safe complete bundle cannot be built."""


def is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def worktree_hint(repo: pathlib.Path) -> pathlib.Path | None:
    current = repo.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate
    return None


def resolve_git(repo: pathlib.Path) -> pathlib.Path:
    search_dirs = [
        item
        for item in os.defpath.split(os.pathsep)
        if item and pathlib.Path(item).is_absolute()
    ]
    search_dirs.extend(("/usr/local/bin", "/opt/homebrew/bin"))
    search_path = os.pathsep.join(dict.fromkeys(search_dirs))
    value = shutil.which("git", path=search_path)
    if not value:
        raise BundleError("git is not available in trusted system locations")
    selected = pathlib.Path(value).absolute()
    try:
        resolved = selected.resolve(strict=True)
    except OSError as exc:
        raise BundleError(f"could not resolve git executable: {selected}") from exc
    boundaries = [repo.resolve()]
    enclosing = worktree_hint(repo)
    if enclosing is not None:
        boundaries.append(enclosing)
    if any(
        is_within(candidate, boundary)
        for candidate in (selected, resolved)
        for boundary in boundaries
    ):
        raise BundleError(f"refusing repository-controlled git executable: {selected}")
    return resolved


def git_environment(index_file: pathlib.Path | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    env.update(
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
        env["GIT_INDEX_FILE"] = str(index_file)
    return env


def run_git(
    executable: pathlib.Path,
    repo: pathlib.Path,
    *args: str,
    check: bool = True,
    index_file: pathlib.Path | None = None,
) -> bytes:
    command = [
        str(executable),
        "-C",
        str(repo),
        "-c",
        "core.fsmonitor=false",
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
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise BundleError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def resolve_sha(
    executable: pathlib.Path, repo: pathlib.Path, ref: str, index_file: pathlib.Path
) -> str:
    value = (
        run_git(
            executable,
            repo,
            "rev-parse",
            "--verify",
            f"{ref}^{{commit}}",
            index_file=index_file,
        )
        .decode()
        .strip()
    )
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise BundleError(f"could not resolve commit: {ref}")
    return value


def optional_ref(
    executable: pathlib.Path,
    repo: pathlib.Path,
    index_file: pathlib.Path,
    *args: str,
) -> str:
    return (
        run_git(executable, repo, *args, check=False, index_file=index_file)
        .decode()
        .strip()
    )


def inferred_base(
    executable: pathlib.Path,
    repo: pathlib.Path,
    head_sha: str,
    index_file: pathlib.Path,
) -> tuple[str, str]:
    upstream = optional_ref(
        executable,
        repo,
        index_file,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )
    remotes = optional_ref(executable, repo, index_file, "remote").splitlines()
    default_refs: list[tuple[str, str]] = []
    for remote in remotes:
        ref = optional_ref(
            executable,
            repo,
            index_file,
            "symbolic-ref",
            "--quiet",
            "--short",
            f"refs/remotes/{remote}/HEAD",
        )
        if not ref:
            continue
        try:
            candidate_sha = resolve_sha(executable, repo, ref, index_file)
        except BundleError:
            continue
        default_refs.append((ref, candidate_sha))

    if default_refs:
        unique_shas = {candidate_sha for _, candidate_sha in default_refs}
        if len(unique_shas) > 1:
            refs = ", ".join(sorted(ref for ref, _ in default_refs))
            raise BundleError(
                f"multiple remote default branches disagree ({refs}); pass --base"
            )
        return sorted(default_refs)[0]

    if upstream:
        upstream_sha = resolve_sha(executable, repo, upstream, index_file)
        if upstream_sha != head_sha:
            return upstream, upstream_sha

    raise BundleError(
        "cannot infer base: pass --base or configure a branch upstream or remote default branch"
    )


def repository_index(executable: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    value = run_git(executable, repo, "rev-parse", "--git-path", "index").decode()
    source = pathlib.Path(value.strip())
    if not source.is_absolute():
        source = repo / source
    source = source.resolve()
    if not source.is_file():
        raise BundleError(f"repository index is unavailable: {source}")
    return source


def reject_worktree_filters(
    executable: pathlib.Path, repo: pathlib.Path, index_file: pathlib.Path
) -> None:
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
        raise BundleError(
            "refusing worktree inspection with configured clean/process filters: "
            + ", ".join(dangerous)
        )


def matches_path(path: str, filters: list[str]) -> bool:
    if not filters:
        return True
    normalized = path.rstrip("/")
    return any(
        normalized == item.rstrip("/") or normalized.startswith(f"{item.rstrip('/')}/")
        for item in filters
    )


def parse_name_status(raw: bytes) -> list[tuple[str, str, str | None]]:
    parts = raw.decode("utf-8", "strict").split("\0")
    rows: list[tuple[str, str, str | None]] = []
    index = 0
    while index < len(parts) and parts[index]:
        status = parts[index]
        index += 1
        if index >= len(parts):
            raise BundleError("incomplete git name-status output")
        old_path = parts[index]
        index += 1
        new_path: str | None = None
        if status.startswith(("R", "C")):
            if index >= len(parts):
                raise BundleError("incomplete rename/copy record")
            new_path = parts[index]
            index += 1
        rows.append((status, old_path, new_path))
    return rows


def risk_tags(path: str) -> list[str]:
    lower = path.lower()
    tags: set[str] = set()
    mapping = {
        "auth": ("auth", "permission", "role", "session"),
        "data": ("migration", "schema", "database", "repository"),
        "contract": ("api", "route", "controller", "client", "openapi"),
        "delivery": ("docker", "compose", "workflow", "gitlab-ci", "package.json"),
        "ui": ("component", "page", "screen", "view", "playwright"),
    }
    for tag, markers in mapping.items():
        if any(marker in lower for marker in markers):
            tags.add(tag)
    return sorted(tags)


def contains_secret_like_content(text: str) -> bool:
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(0).lower()
            if not any(marker in candidate for marker in PLACEHOLDER_MARKERS):
                return True
    return False


def sensitive_path(path: str) -> bool:
    name = pathlib.PurePosixPath(path).name.lower()
    if name.endswith(SAFE_TEMPLATE_SUFFIXES):
        return False
    return (
        name in SENSITIVE_NAMES
        or name.startswith(".env.")
        or name.startswith("credentials.")
        or pathlib.PurePosixPath(name).suffix in SENSITIVE_SUFFIXES
    )


def make_file(status: str, path: str, previous: str | None = None) -> dict[str, Any]:
    if sensitive_path(path) or (previous and sensitive_path(previous)):
        raise BundleError(f"refusing sensitive path: {path}")
    return {
        "path": path,
        "previous_path": previous,
        "status": status,
        "is_test": bool(TEST_PATH.search(path)),
        "command_definition": bool(COMMAND_PATH.search(path)),
        "risk_tags": risk_tags(path),
    }


def untracked_patch(
    executable: pathlib.Path,
    repo: pathlib.Path,
    paths: list[str],
    index_file: pathlib.Path,
) -> tuple[list[dict[str, Any]], str]:
    raw = run_git(
        executable,
        repo,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        index_file=index_file,
    )
    files: list[dict[str, Any]] = []
    chunks: list[str] = []
    for name in raw.decode("utf-8", "strict").split("\0"):
        if not name or not matches_path(name, paths):
            continue
        item = make_file("?", name)
        source = repo / name
        if source.is_symlink():
            item["symlink"] = True
            data = os.readlink(source).encode()
        else:
            item["symlink"] = False
            data = source.read_bytes()
        if len(data) > MAX_UNTRACKED_BYTES:
            raise BundleError(f"untracked file exceeds safety limit: {name}")
        try:
            text = data.decode("utf-8", "strict")
        except UnicodeDecodeError:
            item["binary"] = True
        else:
            item["binary"] = False
            prefixed = "\n".join(f"+{line}" for line in text.splitlines())
            chunks.append(
                f"diff --git a/{name} b/{name}\nnew file mode 100644\n--- /dev/null\n+++ b/{name}\n{prefixed}\n"
            )
        files.append(item)
    return files, "".join(chunks)


def build_with_index(
    args: argparse.Namespace,
    executable: pathlib.Path,
    root: pathlib.Path,
    index_file: pathlib.Path,
) -> dict[str, Any]:
    reject_worktree_filters(executable, root, index_file)
    head_ref = args.head or "HEAD"
    head_sha = resolve_sha(executable, root, head_ref, index_file)
    dirty = bool(
        run_git(
            executable,
            root,
            "status",
            "--porcelain",
            "-z",
            index_file=index_file,
        )
    )
    if args.base:
        base_ref = args.base
        base_sha = resolve_sha(executable, root, args.base, index_file)
        mode = "range"
    elif dirty:
        base_ref, base_sha, mode = "HEAD", head_sha, "local"
    else:
        base_ref, base_sha = inferred_base(executable, root, head_sha, index_file)
        mode = "range"

    path_args = ["--", *args.path] if args.path else ["--"]
    endpoints: tuple[str, ...]
    if mode == "local":
        endpoints = ("HEAD",)
    else:
        endpoints = (base_sha, head_sha)
    diff_args = (
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--find-renames",
        "--full-index",
        *endpoints,
        *path_args,
    )
    name_args = (
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--find-renames",
        "--name-status",
        "-z",
        *endpoints,
        *path_args,
    )

    patch_bytes = run_git(executable, root, *diff_args, index_file=index_file)
    try:
        patch = patch_bytes.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise BundleError("tracked patch is not valid UTF-8") from exc
    files = [
        make_file(status, new_path or old_path, old_path if new_path else None)
        for status, old_path, new_path in parse_name_status(
            run_git(executable, root, *name_args, index_file=index_file)
        )
    ]
    if mode == "local":
        new_files, new_patch = untracked_patch(executable, root, args.path, index_file)
        files.extend(new_files)
        patch += new_patch
    if contains_secret_like_content(patch):
        raise BundleError(
            "refusing bundle because the patch contains secret-like content"
        )
    if not files:
        raise BundleError("target contains no changed files")
    if len(patch.encode()) > MAX_PATCH_BYTES:
        raise BundleError(
            "complete patch exceeds safety limit; split the target by path"
        )

    files.sort(key=lambda item: item["path"])
    core: dict[str, Any] = {
        "schema_version": 1,
        "repository": str(root),
        "target": {
            "mode": mode,
            "base_ref": base_ref,
            "base_sha": base_sha,
            "head_ref": head_ref,
            "head_sha": head_sha,
            "dirty": dirty,
            "paths": args.path,
        },
        "environment": {
            "kind": args.environment_kind,
            "identity": args.environment_id,
        },
        "files": files,
        "command_definitions": [
            item["path"] for item in files if item["command_definition"]
        ],
        "risk_tags": sorted({tag for item in files for tag in item["risk_tags"]}),
        "patch": patch,
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
    }
    canonical = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    core["fingerprint"] = hashlib.sha256(canonical).hexdigest()
    return core


def build(args: argparse.Namespace) -> dict[str, Any]:
    repo_input = pathlib.Path(args.repo).resolve()
    executable = resolve_git(repo_input)
    root = pathlib.Path(
        run_git(executable, repo_input, "rev-parse", "--show-toplevel").decode().strip()
    ).resolve()
    source_index = repository_index(executable, root)
    with tempfile.TemporaryDirectory(prefix="sam-e2e-git-index-") as temporary:
        index_file = pathlib.Path(temporary) / "index"
        shutil.copyfile(source_index, index_file)
        return build_with_index(args, executable, root, index_file)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", default=".")
    value.add_argument("--base")
    value.add_argument("--head")
    value.add_argument("--path", action="append", default=[])
    value.add_argument(
        "--environment-kind",
        choices=("unknown", "local", "test", "dev", "staging", "production"),
        default="unknown",
    )
    value.add_argument("--environment-id", default="unverified")
    return value


def main() -> int:
    try:
        result = build(parser().parse_args())
    except (BundleError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
