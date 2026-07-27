#!/usr/bin/env python3
"""Build a complete immutable context for a change-proposal description."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

REFERENCE_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b|(?<!\w)#\d+\b")
SECRET_RE = re.compile(
    rb"(?i)(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*['\"][A-Za-z0-9_./+\-=]{16,}['\"]"
    rb"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    rb"|AKIA[0-9A-Z]{16}"
)
PLACEHOLDER_MARKERS = (
    b"example",
    b"sample",
    b"placeholder",
    b"changeme",
    b"redacted",
    b"dummy",
    b"fake",
    b"test-only",
    b"xxxxxxxx",
    b"<secret>",
    b"${",
)
SAFE_TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist")
SENSITIVE_NAMES = {
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
}
SENSITIVE_SUFFIXES = {".pem", ".p12", ".pfx", ".jks", ".key"}


def is_within(path: Path, boundary: Path) -> bool:
    try:
        path.relative_to(boundary)
    except ValueError:
        return False
    return True


def enclosing_worktree_hint(repo_hint: Path) -> Path | None:
    current = repo_hint.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        marker = candidate / ".git"
        if marker.exists() or marker.is_symlink():
            return candidate
    return None


def trusted_git_search_path() -> str:
    search_dirs = [
        item
        for item in os.defpath.split(os.pathsep)
        if item and Path(item).is_absolute()
    ]
    search_dirs.extend(("/usr/local/bin", "/opt/homebrew/bin"))
    return os.pathsep.join(dict.fromkeys(search_dirs))


def verify_genuine_git(git: Path) -> None:
    """Reject a PATH wrapper that is not a real git implementation."""
    try:
        probe = subprocess.run(
            [str(git), "--version"],
            env=git_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ValueError(f"could not execute git executable {git}: {exc}") from exc
    if probe.returncode != 0:
        stderr = probe.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git executable {git} failed --version: {stderr}")
    banner = probe.stdout.decode("utf-8", errors="replace").strip()
    if not banner.startswith("git version "):
        raise ValueError(
            f"refusing non-git executable {git}: unexpected --version banner "
            f"{banner[:120]!r}"
        )


def resolve_git(repo_hint: Path) -> Path:
    resolved = shutil.which("git", path=trusted_git_search_path())
    if not resolved:
        raise ValueError("git is not available in trusted system locations")
    git = Path(resolved).resolve()
    boundaries = [repo_hint.resolve()]
    worktree_hint = enclosing_worktree_hint(repo_hint)
    if worktree_hint is not None:
        boundaries.append(worktree_hint)
    if any(is_within(git, boundary) for boundary in boundaries):
        raise ValueError(f"refusing repository-controlled git executable: {git}")
    verify_genuine_git(git)
    return git


def git_env(index_file: Path | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    env.update(
        {
            "GIT_EXTERNAL_DIFF": "",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    if index_file is not None:
        env["GIT_INDEX_FILE"] = str(index_file)
    return env


def run_git(git: Path, repo: Path, *args: str, index_file: Path | None = None) -> bytes:
    result = subprocess.run(
        [
            str(git),
            "--no-pager",
            "-C",
            str(repo),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "diff.external=",
            "-c",
            "pager.diff=false",
            *args,
        ],
        env=git_env(index_file),
        check=False,
        capture_output=True,
    )
    if result.returncode:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git command failed ({' '.join(args)}): {stderr}")
    return result.stdout


def repository_root(git: Path, repo_hint: Path) -> Path:
    value = decode_text(
        run_git(git, repo_hint, "rev-parse", "--show-toplevel"), "repository root"
    ).strip()
    root = Path(value).resolve()
    if not root.is_dir():
        raise ValueError(f"repository root does not exist: {root}")
    return root


def repository_index(git: Path, repo: Path) -> Path:
    value = decode_text(
        run_git(git, repo, "rev-parse", "--git-path", "index"), "repository index"
    ).strip()
    index = Path(value)
    if not index.is_absolute():
        index = repo / index
    index = index.resolve()
    if not index.is_file():
        raise ValueError(f"repository index is unavailable: {index}")
    return index


def decode_text(value: bytes, label: str) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"{label} is not valid UTF-8; treat it as a binary artifact"
        ) from exc


def resolve_sha(git: Path, repo: Path, ref: str, index_file: Path) -> str:
    sha = decode_text(
        run_git(
            git,
            repo,
            "rev-parse",
            "--verify",
            f"{ref}^{{commit}}",
            index_file=index_file,
        ),
        ref,
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
        raise ValueError(f"could not resolve immutable commit for {ref}")
    return sha


def safe_path(value: bytes) -> str:
    path = decode_text(value, "changed path")
    pure = PurePosixPath(path)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        raise ValueError(f"unsafe changed path: {path}")
    return path


def parse_name_status(raw: bytes) -> list[dict[str, Any]]:
    tokens = raw.split(b"\0")
    if tokens and not tokens[-1]:
        tokens.pop()
    files: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        status_raw = tokens[index]
        index += 1
        first_path: bytes | None = None
        if b"\t" in status_raw:
            status_raw, first_path = status_raw.split(b"\t", 1)
        status = decode_text(status_raw, "change status")
        if not status:
            raise ValueError("empty change status")
        code = status[0]
        old_path: str | None
        new_path: str | None
        if code in {"R", "C"}:
            if first_path is not None:
                old_raw = first_path
            elif index < len(tokens):
                old_raw = tokens[index]
                index += 1
            else:
                raise ValueError("truncated rename/copy status")
            if index >= len(tokens):
                raise ValueError("truncated rename/copy destination")
            new_raw = tokens[index]
            index += 1
            old_path = safe_path(old_raw)
            new_path = safe_path(new_raw)
        else:
            if first_path is not None:
                path_raw = first_path
            elif index < len(tokens):
                path_raw = tokens[index]
                index += 1
            else:
                raise ValueError("truncated changed path")
            path = safe_path(path_raw)
            old_path = None if code == "A" else path
            new_path = None if code == "D" else path
        canonical = new_path or old_path
        if canonical is None:
            raise ValueError("change has neither old nor new path")
        files.append(
            {
                "path": canonical,
                "status": status,
                "old_path": old_path,
                "new_path": new_path,
            }
        )
    return files


def sensitive_path(path: str) -> bool:
    pure = PurePosixPath(path.lower())
    if pure.name.endswith(SAFE_TEMPLATE_SUFFIXES):
        return False
    return (
        pure.name in SENSITIVE_NAMES
        or pure.name.startswith(".env.")
        or pure.suffix in SENSITIVE_SUFFIXES
        or tuple(pure.parts[-2:]) == (".aws", "credentials")
    )


def resembles_secret(content: bytes) -> bool:
    for match in SECRET_RE.finditer(content):
        candidate = match.group(0).lower()
        if not any(marker in candidate for marker in PLACEHOLDER_MARKERS):
            return True
    return False


def parse_commits(raw: bytes) -> list[dict[str, str]]:
    tokens = raw.split(b"\0")
    if tokens and not tokens[-1]:
        tokens.pop()
    if len(tokens) % 2:
        raise ValueError("unexpected commit log format")
    commits: list[dict[str, str]] = []
    for index in range(0, len(tokens), 2):
        commits.append(
            {
                "sha": decode_text(tokens[index], "commit sha"),
                "subject": decode_text(tokens[index + 1], "commit subject"),
            }
        )
    return commits


def fingerprint(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    repo_hint = Path(args.repo).resolve()
    if not repo_hint.is_dir():
        raise ValueError(f"repository does not exist: {repo_hint}")
    git = resolve_git(repo_hint)
    if (
        decode_text(
            run_git(git, repo_hint, "rev-parse", "--is-inside-work-tree"),
            "repository",
        ).strip()
        != "true"
    ):
        raise ValueError(f"not a Git worktree: {repo_hint}")
    repo = repository_root(git, repo_hint)
    source_index = repository_index(git, repo)
    with tempfile.TemporaryDirectory(prefix="sam-pr-description-index-") as temporary:
        index_file = Path(temporary) / "index"
        shutil.copyfile(source_index, index_file)
        return build_context_with_index(args, git, repo, index_file)


def build_context_with_index(
    args: argparse.Namespace, git: Path, repo: Path, index_file: Path
) -> dict[str, Any]:

    requested_base_sha = resolve_sha(git, repo, args.base, index_file)
    head_sha = resolve_sha(git, repo, args.head, index_file)
    if args.comparison == "merge-base":
        base_sha = decode_text(
            run_git(
                git,
                repo,
                "merge-base",
                requested_base_sha,
                head_sha,
                index_file=index_file,
            ),
            "merge base",
        ).strip()
    else:
        base_sha = requested_base_sha
    if base_sha == head_sha:
        raise ValueError("branch has no describable diff")

    files = parse_name_status(
        run_git(
            git,
            repo,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--find-renames",
            "--name-status",
            "-z",
            base_sha,
            head_sha,
            index_file=index_file,
        )
    )
    if not files:
        raise ValueError("branch has no changed files")
    for item in files:
        for path in {item.get("old_path"), item.get("new_path")} - {None}:
            if isinstance(path, str) and sensitive_path(path):
                raise ValueError(f"refusing to read sensitive path: {path}")

    patch_bytes = run_git(
        git,
        repo,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--find-renames",
        "--full-index",
        "--unified=3",
        base_sha,
        head_sha,
        index_file=index_file,
    )
    if len(patch_bytes) > args.max_patch_bytes:
        raise ValueError(
            f"patch is {len(patch_bytes)} bytes, above limit {args.max_patch_bytes}; split by coherent scope"
        )
    if resembles_secret(patch_bytes):
        raise ValueError(
            "refusing to read content that resembles a credential or private key"
        )
    patch = decode_text(patch_bytes, "change patch")

    for item in files:
        selected = [
            path
            for path in (item.get("old_path"), item.get("new_path"))
            if isinstance(path, str)
        ]
        file_patch = run_git(
            git,
            repo,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--find-renames",
            "--unified=0",
            base_sha,
            head_sha,
            "--",
            *dict.fromkeys(selected),
            index_file=index_file,
        )
        item["binary"] = (
            b"Binary files " in file_patch or b"GIT binary patch" in file_patch
        )

    commits = parse_commits(
        run_git(
            git,
            repo,
            "log",
            "-z",
            "--format=%H%x00%s",
            f"{base_sha}..{head_sha}",
            index_file=index_file,
        )
    )
    candidate_source = "\n".join([args.head, *(item["subject"] for item in commits)])
    reference_candidates = sorted(set(REFERENCE_RE.findall(candidate_source)))
    context: dict[str, Any] = {
        "schema_version": 1,
        "target": {
            "base_ref": args.base,
            "head_ref": args.head,
            "requested_base_sha": requested_base_sha,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "comparison": args.comparison,
        },
        "commits": commits,
        "reference_candidates": reference_candidates,
        "files": files,
        "patch": patch,
        "patch_sha256": hashlib.sha256(patch_bytes).hexdigest(),
    }
    context["context_fingerprint"] = fingerprint(context)
    return context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument(
        "--comparison", choices=("merge-base", "direct"), default="merge-base"
    )
    parser.add_argument("--max-patch-bytes", type=int, default=5_000_000)
    return parser.parse_args()


def main() -> int:
    try:
        context = build_context(parse_args())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(context, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
