#!/usr/bin/env python3
"""Build a complete, deterministic, read-only review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_VERSION = 1
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

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

SENSITIVE_FILE_NAMES = {
    ".env",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secrets.json",
}
SENSITIVE_SUFFIXES = {".jks", ".key", ".p12", ".pem", ".pfx"}
SAFE_TEMPLATE_SUFFIXES = {".example", ".sample", ".template", ".dist"}

TEST_PATTERNS = (
    re.compile(r"(^|/)(__tests__|tests?|specs?|e2e|integration)(/|$)", re.I),
    re.compile(r"\.(spec|test)\.[^.]+$", re.I),
    re.compile(r"(^|/)(test_[^/]+|[^/]+_test)\.py$", re.I),
)
GENERATED_PATTERNS = (
    re.compile(r"(^|/)(dist|build|generated|vendor|coverage)(/|$)", re.I),
    re.compile(r"\.(min\.(js|css)|snap|lock)$", re.I),
    re.compile(
        r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?)$", re.I
    ),
)
CONFIG_PATTERNS = (
    re.compile(r"(^|/)(\.github|\.gitlab|\.circleci|ci|config)(/|$)", re.I),
    re.compile(r"(^|/)(Dockerfile|Makefile|Procfile)$", re.I),
    re.compile(r"\.(ya?ml|toml|ini|cfg|conf|properties)$", re.I),
)
TYPE_ONLY_PATTERNS = (
    re.compile(r"\.d\.(ts|mts|cts)$", re.I),
    re.compile(r"(^|/)(types?|interfaces?)(/|$)", re.I),
)
COMMAND_DEFINITION_PATTERNS = (
    re.compile(
        r"(^|/)(package\.json|Makefile|Dockerfile|Justfile|Taskfile\.ya?ml)$", re.I
    ),
    re.compile(r"(^|/)(scripts?|hooks?|\.github/workflows|\.gitlab/ci)(/|$)", re.I),
    re.compile(r"(^|/)\.gitlab-ci\.ya?ml$", re.I),
)

RISK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "security": (
        re.compile(
            r"(^|/)(admin|auth|security|permissions?|roles?|sessions?|tokens?)(/|$)",
            re.I,
        ),
        re.compile(r"(credential|password|secret|oauth|jwt|csrf|cookie)", re.I),
    ),
    "data-migration": (
        re.compile(
            r"(^|/)(migrations?|schema|models?|entities?|repositories?)(/|$)", re.I
        ),
        re.compile(r"\.(sql|prisma)$", re.I),
    ),
    "concurrency-jobs": (
        re.compile(r"(^|/)(jobs?|workers?|queues?|tasks?|schedulers?)(/|$)", re.I),
        re.compile(r"(transaction|concurr|parallel|retry)", re.I),
    ),
    "public-contract": (
        re.compile(r"(^|/)(api|routes?|controllers?|openapi|graphql|proto)(/|$)", re.I),
        re.compile(r"(schema|contract)", re.I),
    ),
    "delivery": (
        re.compile(
            r"(^|/)(\.github|\.gitlab|ci|deploy|infra|terraform|k8s|helm)(/|$)", re.I
        ),
        re.compile(r"(Dockerfile|Makefile|appcast|release)", re.I),
    ),
    "integration": (
        re.compile(r"(^|/)(adapters?|clients?|integrations?|providers?)(/|$)", re.I),
        re.compile(r"(webhook|http|sdk|external)", re.I),
    ),
    "user-visible": (
        re.compile(
            r"(^|/)(components?|views?|screens?|pages?|templates?|cli)(/|$)", re.I
        ),
        re.compile(r"\.(tsx|jsx|vue|svelte|html|css|scss)$", re.I),
    ),
}
# Whole-word name hints, matched against the camelCase-split lowercase path so
# "lock" does not fire on Blocked/clock, "sign" on design/signal, "public" on
# publication, or "export" on exporter.
RISK_TOKEN_PATTERNS: dict[str, re.Pattern[str]] = {
    "concurrency-jobs": re.compile(
        r"(?<![a-z0-9])(?:(?:dead)?lock(?:s|ing|ed)?|mutex(?:es)?|semaphores?)(?![a-z0-9])"
    ),
    "public-contract": re.compile(r"(?<![a-z0-9])(?:public|exports?)(?![a-z0-9])"),
    "delivery": re.compile(
        r"(?<![a-z0-9])(?:(?:code_?)?sign(?:s|ing|ed)?|notari[sz][a-z]*)(?![a-z0-9])"
    ),
}
LOCKFILE_RE = re.compile(
    r"(^|/)([^/]+\.lock|[^/]*-lock\.(json|ya?ml)|bun\.lockb|npm-shrinkwrap\.json)$",
    re.I,
)
CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)
FILTER_COMMAND = re.compile(r"^filter\..*\.(clean|process)$", re.I)


class BundleError(RuntimeError):
    """Report an actionable bundle construction failure."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a complete JSON review bundle without modifying the repository."
    )
    parser.add_argument(
        "--repo", default=".", help="Repository or nested path to inspect."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "local", "branch", "commit", "range", "proposal"),
        default="auto",
    )
    parser.add_argument("--base", help="Base ref for branch mode.")
    parser.add_argument("--head", default="HEAD", help="Head ref for branch mode.")
    parser.add_argument(
        "--commit", dest="commit_ref", help="Commit ref for commit mode."
    )
    parser.add_argument(
        "--range", dest="range_ref", help="Git diff range for range mode."
    )
    parser.add_argument(
        "--comparison",
        choices=("merge-base", "direct"),
        default="merge-base",
        help="Proposal comparison semantics.",
    )
    parser.add_argument("--platform", help="Remote platform kind for proposal mode.")
    parser.add_argument(
        "--repository", help="Remote repository identity for proposal mode."
    )
    parser.add_argument("--change-id", help="Remote proposal identifier.")
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Repo-relative pathspec. Repeat to review multiple paths.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help="Fail rather than truncate when the serialized patch exceeds this size; 0 disables the cap.",
    )
    parser.add_argument(
        "--out",
        help=(
            "Directory outside the repository: write bundle.json (unchanged JSON) and "
            "patch.diff there and print a compact ledger instead of the JSON."
        ),
    )
    return parser.parse_args()


def is_within(path: Path, parent: Path) -> bool:
    """Compare identity, not spelling: a case-insensitive filesystem must not let a
    differently cased path escape the check."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        pass
    for candidate in (path, *path.parents):
        try:
            if candidate.exists() and os.path.samefile(candidate, parent):
                return True
        except OSError:
            continue
    return False


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


def verify_genuine_git(git_path: Path) -> None:
    """Reject a PATH wrapper that is not a real git implementation."""
    try:
        probe = subprocess.run(
            [str(git_path), "--version"],
            env=isolated_git_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise BundleError(f"could not execute git executable {git_path}: {exc}") from exc
    if probe.returncode != 0:
        message = probe.stderr.decode("utf-8", errors="replace").strip()
        raise BundleError(f"git executable {git_path} failed --version: {message}")
    banner = probe.stdout.decode("utf-8", errors="replace").strip()
    if not banner.startswith("git version "):
        raise BundleError(
            f"refusing non-git executable {git_path}: unexpected --version banner "
            f"{banner[:120]!r}"
        )


def resolve_git(repo_hint: Path) -> Path:
    resolved = shutil.which("git", path=trusted_git_search_path())
    if not resolved:
        raise BundleError("git is not available in trusted system locations")
    git_path = Path(resolved).resolve()
    boundaries = [repo_hint.resolve()]
    worktree_hint = enclosing_worktree_hint(repo_hint)
    if worktree_hint is not None:
        boundaries.append(worktree_hint)
    if any(is_within(git_path, boundary) for boundary in boundaries):
        raise BundleError(f"refusing repository-controlled git executable: {git_path}")
    verify_genuine_git(git_path)
    return git_path


def isolated_git_environment(index_file: Path | None = None) -> dict[str, str]:
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
        }
    )
    if index_file is not None:
        environment["GIT_INDEX_FILE"] = str(index_file)
    return environment


def run_git(
    git: Path,
    repo: Path,
    args: Iterable[str],
    *,
    check: bool = True,
    index_file: Path | None = None,
) -> subprocess.CompletedProcess[bytes]:
    command = [
        str(git),
        "-C",
        str(repo),
        "-c",
        "core.quotePath=false",
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
        env=isolated_git_environment(index_file),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise BundleError(f"git command failed ({' '.join(args)}): {message}")
    return result


def repository_root(git: Path, repo_hint: Path) -> Path:
    result = run_git(git, repo_hint, ("rev-parse", "--show-toplevel"))
    return Path(result.stdout.decode().strip()).resolve()


def repository_index(git: Path, repo: Path) -> Path:
    result = run_git(git, repo, ("rev-parse", "--git-path", "index"))
    index = Path(result.stdout.decode().strip())
    if not index.is_absolute():
        index = repo / index
    index = index.resolve()
    if not index.is_file():
        raise BundleError(f"repository index is unavailable: {index}")
    return index


def reject_worktree_filters(git: Path, repo: Path, index_file: Path) -> None:
    result = run_git(
        git,
        repo,
        ("config", "--includes", "--name-only", "--list"),
        index_file=index_file,
    )
    names = result.stdout.decode("utf-8", errors="strict")
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


def rev_parse(git: Path, repo: Path, ref: str, index_file: Path) -> str:
    return (
        run_git(
            git,
            repo,
            ("rev-parse", "--verify", ref),
            index_file=index_file,
        )
        .stdout.decode()
        .strip()
    )


def ref_exists(git: Path, repo: Path, ref: str, index_file: Path) -> bool:
    result = run_git(
        git,
        repo,
        ("rev-parse", "--verify", "--quiet", ref),
        check=False,
        index_file=index_file,
    )
    return result.returncode == 0


def normalize_paths(raw_paths: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for raw in raw_paths:
        value = raw.replace(os.sep, "/")
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts:
            raise BundleError(f"path must be non-empty and repo-relative: {raw!r}")
        normalized.append(path.as_posix())
    return normalized


def has_local_changes(
    git: Path, repo: Path, paths: list[str], index_file: Path
) -> bool:
    args = ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    if paths:
        args.extend(("--", *paths))
    return bool(run_git(git, repo, args, index_file=index_file).stdout)


def diff_has_changes(
    git: Path,
    repo: Path,
    diff_spec: str,
    paths: list[str],
    index_file: Path,
) -> bool:
    args = [
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--quiet",
        diff_spec,
    ]
    if paths:
        args.extend(("--", *paths))
    result = run_git(git, repo, args, check=False, index_file=index_file)
    if result.returncode not in (0, 1):
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise BundleError(f"could not compare {diff_spec}: {message}")
    return result.returncode == 1


def plausible_base(
    git: Path,
    repo: Path,
    head: str,
    paths: list[str],
    index_file: Path,
) -> str | None:
    candidates: list[str] = []
    remote_heads = run_git(
        git,
        repo,
        ("for-each-ref", "--format=%(symref)", "refs/remotes/*/HEAD"),
        check=False,
        index_file=index_file,
    )
    if remote_heads.returncode == 0:
        prefix = "refs/remotes/"
        candidates.extend(
            line[len(prefix) :] if line.startswith(prefix) else line
            for line in remote_heads.stdout.decode().splitlines()
            if line
        )
    upstream = run_git(
        git,
        repo,
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"),
        check=False,
        index_file=index_file,
    )
    if upstream.returncode == 0:
        candidates.append(upstream.stdout.decode().strip())

    seen: set[str] = set()
    viable: list[tuple[str, str]] = []
    for candidate in candidates:
        if (
            not candidate
            or candidate in seen
            or not ref_exists(git, repo, candidate, index_file)
        ):
            continue
        seen.add(candidate)
        merge_base = run_git(
            git,
            repo,
            ("merge-base", candidate, head),
            check=False,
            index_file=index_file,
        )
        if merge_base.returncode != 0:
            continue
        merge_base_sha = merge_base.stdout.decode().strip()
        spec = f"{merge_base_sha}..{head}"
        if diff_has_changes(git, repo, spec, paths, index_file):
            viable.append((candidate, merge_base_sha))

    distinct_bases = {merge_base_sha for _, merge_base_sha in viable}
    if len(distinct_bases) != 1:
        return None
    return viable[0][0]


def target_spec(
    git: Path,
    repo: Path,
    args: argparse.Namespace,
    paths: list[str],
    index_file: Path,
) -> tuple[dict[str, Any], str, bool]:
    mode = args.mode
    if mode == "auto":
        if has_local_changes(git, repo, paths, index_file):
            mode = "local"
        else:
            base = args.base or plausible_base(git, repo, args.head, paths, index_file)
            if not base:
                raise BundleError(
                    "no reviewable local or branch diff found; provide an explicit target"
                )
            args.base = base
            mode = "branch"

    if mode == "local":
        if not ref_exists(git, repo, "HEAD", index_file):
            raise BundleError("local mode requires at least one commit")
        base_sha = rev_parse(git, repo, "HEAD", index_file)
        return (
            {
                "mode": mode,
                "base_ref": "HEAD",
                "base_sha": base_sha,
                "head_ref": "WORKTREE",
                "head_sha": base_sha,
                "merge_base_sha": base_sha,
            },
            "HEAD",
            True,
        )

    if mode == "branch":
        base = args.base or plausible_base(git, repo, args.head, paths, index_file)
        if not base:
            raise BundleError(
                "branch mode requires --base or a locally resolvable plausible base"
            )
        base_sha = rev_parse(git, repo, base, index_file)
        head_sha = rev_parse(git, repo, args.head, index_file)
        merge_base = (
            run_git(
                git,
                repo,
                ("merge-base", base, args.head),
                index_file=index_file,
            )
            .stdout.decode()
            .strip()
        )
        return (
            {
                "mode": mode,
                "base_ref": base,
                "base_sha": base_sha,
                "head_ref": args.head,
                "head_sha": head_sha,
                "merge_base_sha": merge_base,
            },
            f"{merge_base}..{head_sha}",
            False,
        )

    if mode == "commit":
        if not args.commit_ref:
            raise BundleError("commit mode requires --commit")
        commit_sha = rev_parse(git, repo, args.commit_ref, index_file)
        parent = run_git(
            git,
            repo,
            ("rev-parse", "--verify", f"{commit_sha}^"),
            check=False,
            index_file=index_file,
        )
        base_sha = (
            parent.stdout.decode().strip() if parent.returncode == 0 else EMPTY_TREE_SHA
        )
        return (
            {
                "mode": mode,
                "base_ref": f"{args.commit_ref}^" if parent.returncode == 0 else None,
                "base_sha": base_sha,
                "head_ref": args.commit_ref,
                "head_sha": commit_sha,
                "merge_base_sha": base_sha,
            },
            f"{base_sha}..{commit_sha}",
            False,
        )

    if mode == "range":
        if not args.range_ref or ".." not in args.range_ref:
            raise BundleError("range mode requires --range BASE..HEAD or BASE...HEAD")
        separator = "..." if "..." in args.range_ref else ".."
        base_ref, head_ref = args.range_ref.split(separator, 1)
        if not base_ref or not head_ref:
            raise BundleError("range must contain both base and head refs")
        base_sha = rev_parse(git, repo, base_ref, index_file)
        head_sha = rev_parse(git, repo, head_ref, index_file)
        merge_base = (
            run_git(
                git,
                repo,
                ("merge-base", base_ref, head_ref),
                index_file=index_file,
            )
            .stdout.decode()
            .strip()
            if separator == "..."
            else base_sha
        )
        return (
            {
                "mode": mode,
                "base_ref": base_ref,
                "base_sha": base_sha,
                "head_ref": head_ref,
                "head_sha": head_sha,
                "merge_base_sha": merge_base,
            },
            args.range_ref,
            False,
        )

    if mode == "proposal":
        missing = [
            flag
            for flag, value in (
                ("--base", args.base),
                ("--head", args.head),
                ("--platform", args.platform),
                ("--repository", args.repository),
                ("--change-id", args.change_id),
            )
            if not value
        ]
        if missing:
            raise BundleError(
                "proposal mode requires " + ", ".join(missing)
            )
        requested_base_sha = rev_parse(git, repo, args.base, index_file)
        head_sha = rev_parse(git, repo, args.head, index_file)
        if args.comparison == "merge-base":
            base_sha = (
                run_git(
                    git,
                    repo,
                    ("merge-base", requested_base_sha, head_sha),
                    index_file=index_file,
                )
                .stdout.decode()
                .strip()
            )
        else:
            base_sha = requested_base_sha
        if base_sha == head_sha:
            raise BundleError("proposal contains no reviewable changes")
        return (
            {
                "mode": mode,
                "platform": args.platform,
                "repository": args.repository,
                "change_id": args.change_id,
                "base_ref": args.base,
                "requested_base_sha": requested_base_sha,
                "base_sha": base_sha,
                "head_ref": args.head,
                "head_sha": head_sha,
                "merge_base_sha": base_sha,
                "comparison": args.comparison,
            },
            f"{base_sha}..{head_sha}",
            False,
        )

    raise BundleError(f"unsupported mode: {mode}")


def diff_output(
    git: Path,
    repo: Path,
    diff_spec: str,
    paths: list[str],
    flags: Iterable[str],
    index_file: Path,
) -> bytes:
    args = [
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--find-renames",
        *flags,
        diff_spec,
    ]
    if paths:
        args.extend(("--", *paths))
    return run_git(git, repo, args, index_file=index_file).stdout


def parse_name_status(data: bytes) -> list[dict[str, Any]]:
    tokens = data.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()
    files: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index].decode("utf-8")
        index += 1
        if not status:
            continue
        code = status[0]
        if code in {"R", "C"}:
            if index + 1 >= len(tokens):
                raise BundleError("malformed rename/copy status from git")
            old_path = tokens[index].decode("utf-8")
            path = tokens[index + 1].decode("utf-8")
            index += 2
        else:
            if index >= len(tokens):
                raise BundleError("malformed name status from git")
            old_path = None
            path = tokens[index].decode("utf-8")
            index += 1
        files.append({"path": path, "old_path": old_path, "status": status})
    return files


def parse_numstat(data: bytes) -> dict[str, tuple[int | None, int | None]]:
    tokens = data.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()
    stats: dict[str, tuple[int | None, int | None]] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        fields = token.split(b"\t", 2)
        if len(fields) != 3:
            continue
        added_raw, deleted_raw, path_raw = fields
        added = None if added_raw == b"-" else int(added_raw)
        deleted = None if deleted_raw == b"-" else int(deleted_raw)
        if path_raw:
            path = path_raw.decode("utf-8")
        else:
            if index + 1 >= len(tokens):
                raise BundleError("malformed rename/copy numstat from git")
            index += 1  # old path is not the reporting key
            path = tokens[index].decode("utf-8")
            index += 1
        stats[path] = (added, deleted)
    return stats


def parse_changed_ranges(
    patch: str,
) -> dict[str, dict[str, list[list[int]]]]:
    changed: dict[str, dict[str, list[list[int]]]] = {}
    old_path: str | None = None
    new_path: str | None = None
    for line in patch.splitlines():
        if line.startswith("--- "):
            value = line[4:]
            old_path = None if value == "/dev/null" else (
                value[2:] if value.startswith("a/") else value
            )
            if old_path is not None:
                changed.setdefault(old_path, {"OLD": [], "NEW": []})
            continue
        if line.startswith("+++ "):
            value = line[4:]
            new_path = None if value == "/dev/null" else (
                value[2:] if value.startswith("b/") else value
            )
            if new_path is not None:
                changed.setdefault(new_path, {"OLD": [], "NEW": []})
            continue
        match = HUNK_RE.match(line)
        if not match:
            continue
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        new_start = int(match.group(3))
        new_count = int(match.group(4) or "1")
        if old_path is not None and old_count > 0:
            changed[old_path]["OLD"].append(
                [old_start, old_start + old_count - 1]
            )
        if new_path is not None and new_count > 0:
            changed[new_path]["NEW"].append(
                [new_start, new_start + new_count - 1]
            )
    return changed


def matches_any(path: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(path) for pattern in patterns)


def risk_tags(path: str) -> list[str]:
    tags = {
        tag for tag, patterns in RISK_PATTERNS.items() if matches_any(path, patterns)
    }
    words = CAMEL_BOUNDARY.sub("_", path).lower()
    for tag, pattern in RISK_TOKEN_PATTERNS.items():
        if tag == "concurrency-jobs" and LOCKFILE_RE.search(path):
            continue
        if pattern.search(words):
            tags.add(tag)
    return sorted(tags)


def file_patch_digests(patch: str, files: list[dict[str, Any]]) -> dict[str, str | None]:
    """Map each bundle path to the SHA-256 of its own patch section.

    None means the section could not be matched unambiguously; callers must then
    treat the file as changed (it can never be carried forward).
    """
    sections: list[tuple[str, list[str]]] = []
    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git "):
            sections.append((line.rstrip("\r\n"), [line]))
        elif sections:
            sections[-1][1].append(line)
    by_header: dict[str, str | None] = {}
    for header, lines in sections:
        digest = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
        by_header[header] = None if header in by_header else digest
    digests: dict[str, str | None] = {}
    for record in files:
        path = record.get("path")
        if not isinstance(path, str):
            continue
        old_path = record.get("old_path") or path
        digests[path] = by_header.get(f"diff --git a/{old_path} b/{path}")
    return digests


def is_sensitive_path(path: str) -> bool:
    pure = PurePosixPath(path)
    name = pure.name.lower()
    if any(name.endswith(suffix) for suffix in SAFE_TEMPLATE_SUFFIXES):
        return False
    if name in SENSITIVE_FILE_NAMES or pure.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    return any(
        part.lower() in {".secrets", "private-credentials"} for part in pure.parts
    )


def secret_like(text: str) -> bool:
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(0).lower()
            if not any(marker in candidate for marker in PLACEHOLDER_MARKERS):
                return True
    return False


def untracked_snapshot(
    repo: Path, relative: str, max_bytes: int
) -> tuple[str, dict[str, Any], str]:
    path = repo / relative
    lstat = path.lstat()
    if stat.S_ISLNK(lstat.st_mode):
        target = os.readlink(path)
        patch = (
            f"diff --git a/{relative} b/{relative}\n"
            "new file mode 120000\n"
            "--- /dev/null\n"
            f"+++ b/{relative}\n"
            "@@ -0,0 +1 @@\n"
            f"+{target}\n"
        )
        record = {
            "path": relative,
            "old_path": None,
            "status": "??",
            "added_lines": 1,
            "deleted_lines": 0,
            "binary": False,
            "symlink": True,
            "old_changed_ranges": [],
            "new_changed_ranges": [[1, 1]],
            "changed_lines": [[1, 1]],
        }
        return patch, record, target

    if not stat.S_ISREG(lstat.st_mode):
        raise BundleError(f"unsupported untracked file type: {relative}")

    if max_bytes and lstat.st_size > max_bytes:
        raise BundleError(
            f"untracked file {relative} is {lstat.st_size} bytes, above "
            f"--max-bytes={max_bytes}; refusing rather than truncating (final: report "
            "BLOCKED; narrow --path or the range only on an explicit user re-scope)"
        )

    raw_content = path.read_bytes()
    try:
        content = raw_content.decode("utf-8")
    except UnicodeDecodeError:
        content = ""

    if b"\0" in raw_content[:8192] or (raw_content and not content):
        patch = (
            f"diff --git a/{relative} b/{relative}\n"
            f"Binary untracked file {relative} ({lstat.st_size} bytes)\n"
        )
        record = {
            "path": relative,
            "old_path": None,
            "status": "??",
            "added_lines": None,
            "deleted_lines": None,
            "binary": True,
            "symlink": False,
            "old_changed_ranges": [],
            "new_changed_ranges": [],
            "changed_lines": [],
        }
        return patch, record, ""

    lines = content.splitlines()
    count = len(lines)
    body = "\n".join(f"+{line}" for line in lines)
    if body:
        body += "\n"
    hunk = f"@@ -0,0 +1,{count} @@\n{body}" if count else ""
    patch = (
        f"diff --git a/{relative} b/{relative}\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        f"+++ b/{relative}\n"
        f"{hunk}"
    )
    record = {
        "path": relative,
        "old_path": None,
        "status": "??",
        "added_lines": count,
        "deleted_lines": 0,
        "binary": False,
        "symlink": False,
        "old_changed_ranges": [],
        "new_changed_ranges": [[1, count]] if count else [],
        "changed_lines": [[1, count]] if count else [],
    }
    return patch, record, content


def list_untracked(
    git: Path, repo: Path, paths: list[str], index_file: Path
) -> list[str]:
    args = ["ls-files", "--others", "--exclude-standard", "-z"]
    if paths:
        args.extend(("--", *paths))
    data = run_git(git, repo, args, index_file=index_file).stdout
    return sorted(token.decode("utf-8") for token in data.split(b"\0") if token)


def enrich_file(record: dict[str, Any]) -> dict[str, Any]:
    path = record["path"]
    record.update(
        {
            "test": matches_any(path, TEST_PATTERNS),
            "generated": matches_any(path, GENERATED_PATTERNS),
            "config": matches_any(path, CONFIG_PATTERNS),
            "probable_type_only": matches_any(path, TYPE_ONLY_PATTERNS),
            "command_definition": matches_any(path, COMMAND_DEFINITION_PATTERNS),
            "risk_tags": risk_tags(path),
        }
    )
    return record


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    repo_hint = Path(args.repo).resolve()
    git = resolve_git(repo_hint)
    root = repository_root(git, repo_hint)
    paths = normalize_paths(args.path)
    source_index = repository_index(git, root)
    with tempfile.TemporaryDirectory(prefix="sam-review-index-") as temporary:
        index_file = Path(temporary) / "index"
        shutil.copyfile(source_index, index_file)
        return build_bundle_with_index(args, git, root, paths, index_file)


def build_bundle_with_index(
    args: argparse.Namespace,
    git: Path,
    root: Path,
    paths: list[str],
    index_file: Path,
) -> dict[str, Any]:
    if args.mode in {"auto", "local"}:
        reject_worktree_filters(git, root, index_file)
    target, diff_spec, include_untracked = target_spec(
        git, root, args, paths, index_file
    )

    patch_bytes = diff_output(
        git,
        root,
        diff_spec,
        paths,
        ("--no-color", "--unified=3"),
        index_file,
    )
    try:
        patch = patch_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BundleError(
            "tracked patch contains non-UTF-8 text; review the affected path as binary"
        ) from error
    files = parse_name_status(
        diff_output(
            git,
            root,
            diff_spec,
            paths,
            ("--name-status", "-z"),
            index_file,
        )
    )
    numstat = parse_numstat(
        diff_output(git, root, diff_spec, paths, ("--numstat", "-z"), index_file)
    )
    changed_patch = diff_output(
        git,
        root,
        diff_spec,
        paths,
        ("--no-color", "--unified=0"),
        index_file,
    )
    try:
        changed_ranges = parse_changed_ranges(changed_patch.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise BundleError(
            "tracked patch contains non-UTF-8 text; review the affected path as binary"
        ) from error

    sensitive_paths = [
        record["path"] for record in files if is_sensitive_path(record["path"])
    ]
    secret_sources: list[str] = []
    if secret_like(patch):
        secret_sources.append("tracked patch")

    for record in files:
        added, deleted = numstat.get(record["path"], (None, None))
        record.update(
            {
                "added_lines": added,
                "deleted_lines": deleted,
                "binary": added is None and deleted is None,
                "symlink": False,
                "old_changed_ranges": changed_ranges.get(
                    record.get("old_path") or record["path"], {}
                ).get("OLD", []),
                "new_changed_ranges": changed_ranges.get(record["path"], {}).get(
                    "NEW", []
                ),
                "changed_lines": changed_ranges.get(record["path"], {}).get(
                    "NEW", []
                ),
            }
        )

    if include_untracked:
        for relative in list_untracked(git, root, paths, index_file):
            if is_sensitive_path(relative):
                sensitive_paths.append(relative)
                continue
            snapshot, record, content = untracked_snapshot(
                root, relative, args.max_bytes
            )
            if content and secret_like(content):
                secret_sources.append(relative)
                continue
            if patch and not patch.endswith("\n"):
                patch += "\n"
            patch += snapshot
            files.append(record)

    if sensitive_paths or secret_sources:
        details: list[str] = []
        if sensitive_paths:
            details.append(
                "sensitive paths: " + ", ".join(sorted(set(sensitive_paths)))
            )
        if secret_sources:
            details.append(
                "secret-like content: " + ", ".join(sorted(set(secret_sources)))
            )
        raise BundleError("review bundle refused; " + "; ".join(details))

    files = [enrich_file(record) for record in files]
    files.sort(key=lambda item: item["path"])
    if not files and not patch.strip():
        raise BundleError("selected target contains no reviewable changes")

    patch_size = len(patch.encode("utf-8"))
    if args.max_bytes and patch_size > args.max_bytes:
        raise BundleError(
            f"patch is {patch_size} bytes, above --max-bytes={args.max_bytes}; "
            "refusing rather than truncating (final: report BLOCKED; narrow --path or "
            "the range only on an explicit user re-scope)"
        )

    aggregate_risks = sorted({tag for record in files for tag in record["risk_tags"]})
    command_definitions = [
        record["path"] for record in files if record["command_definition"]
    ]
    non_test_added = sum(
        record["added_lines"] or 0 for record in files if not record["test"]
    )
    non_test_deleted = sum(
        record["deleted_lines"] or 0 for record in files if not record["test"]
    )
    binary_count = sum(1 for record in files if record["binary"])

    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "repository_root": str(root),
        "target": target,
        "path_filters": paths,
        "summary": {
            "file_count": len(files),
            "test_file_count": sum(1 for record in files if record["test"]),
            "binary_file_count": binary_count,
            "non_test_added_lines": non_test_added,
            "non_test_deleted_lines": non_test_deleted,
            "patch_bytes": patch_size,
        },
        "risk_tags": aggregate_risks,
        "command_definitions_requiring_inspection": command_definitions,
        "files": files,
        "patch": patch,
        "warnings": [
            "Classification and risk tags are deterministic hints; verify them against repository context."
        ],
    }
    canonical = json.dumps(
        bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    bundle["fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return bundle


def format_ranges(ranges: list[list[int]]) -> str:
    return ",".join(
        str(start) if start == end else f"{start}-{end}" for start, end in ranges
    )


def ledger_line(record: dict[str, Any]) -> str:
    """One compact line per changed file: status, path, counts, ranges, hints."""
    parts = [record["status"], record["path"]]
    if record.get("old_path"):
        parts.append(f"<- {record['old_path']}")
    added, deleted = record.get("added_lines"), record.get("deleted_lines")
    parts.append(
        f"+{'-' if added is None else added}/-{'-' if deleted is None else deleted}"
    )
    if record.get("new_changed_ranges"):
        parts.append(f"new={format_ranges(record['new_changed_ranges'])}")
    if record.get("old_changed_ranges"):
        parts.append(f"old={format_ranges(record['old_changed_ranges'])}")
    for key, flag in (
        ("test", "test"),
        ("generated", "generated"),
        ("config", "config"),
        ("probable_type_only", "type-only"),
        ("command_definition", "command"),
        ("binary", "binary"),
        ("symlink", "symlink"),
    ):
        if record.get(key):
            parts.append(flag)
    if record.get("risk_tags"):
        parts.append("risk=" + ",".join(record["risk_tags"]))
    return " ".join(parts)


def one_line_summary(bundle: dict[str, Any]) -> str:
    """Hashes, counts, and tags only: never paths or patch content."""
    target, summary = bundle["target"], bundle["summary"]
    return (
        f"build_review_bundle: fingerprint={bundle['fingerprint']} "
        f"mode={target['mode']} base={target['base_sha']} head={target['head_sha']} "
        f"files={summary['file_count']} "
        f"non_test_lines={summary['non_test_added_lines'] + summary['non_test_deleted_lines']} "
        f"patch_bytes={summary['patch_bytes']} "
        f"risk_tags={','.join(bundle['risk_tags']) or 'none'}"
    )


def write_out(bundle: dict[str, Any], raw_out: str) -> str:
    """Write bundle.json and patch.diff outside the repository; return the ledger."""
    out = Path(raw_out).resolve()
    root = Path(bundle["repository_root"]).resolve()
    if is_within(out, root):
        raise BundleError(f"--out must be outside the repository: {out}")
    bundle_path = out / "bundle.json"
    patch_path = out / "patch.diff"
    previous: Any = None
    if bundle_path.exists():
        try:
            previous = json.loads(bundle_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            previous = {}
        if not isinstance(previous, dict) or previous.get("fingerprint") != bundle["fingerprint"]:
            raise BundleError(
                f"refusing to overwrite a different bundle in {out}; use a new --out directory"
            )
    # An identical rebuild leaves the files (and the bundle mtime the scaffold uses
    # to reject receipts that predate the bundle) untouched.
    if previous != bundle:
        out.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    patch = bundle["patch"].encode("utf-8")
    if not patch_path.is_file() or patch_path.read_bytes() != patch:
        patch_path.write_bytes(patch)
    target, summary = bundle["target"], bundle["summary"]
    identity = " ".join(
        f"{key}={target[key]}"
        for key in ("platform", "repository", "change_id", "comparison")
        if target.get(key)
    )
    lines = [
        f"bundle: {bundle_path}",
        f"patch: {patch_path}",
        f"fingerprint: {bundle['fingerprint']}",
        (
            f"target: mode={target['mode']} base={target['base_sha']} "
            f"head={target['head_sha']} merge_base={target['merge_base_sha']}"
            + (f" {identity}" if identity else "")
        ),
        (
            f"summary: files={summary['file_count']} tests={summary['test_file_count']} "
            f"binary={summary['binary_file_count']} "
            f"non_test=+{summary['non_test_added_lines']}/-{summary['non_test_deleted_lines']} "
            f"patch_bytes={summary['patch_bytes']}"
        ),
        f"risk_tags: {', '.join(bundle['risk_tags']) or 'none'}",
        "inspect_before_running: "
        + (", ".join(bundle["command_definitions_requiring_inspection"]) or "none"),
        "files:",
        *(ledger_line(record) for record in bundle["files"]),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        bundle = build_bundle(args)
        ledger = write_out(bundle, args.out) if args.out else None
    except (BundleError, OSError, ValueError) as error:
        print(f"build_review_bundle: {error}", file=sys.stderr)
        return 2
    if ledger is None:
        json.dump(bundle, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(ledger)
    print(one_line_summary(bundle), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
