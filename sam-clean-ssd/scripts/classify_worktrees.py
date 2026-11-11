#!/usr/bin/env python3
"""Read-only safety classification of git worktrees and clones before removal.

Prints TSV, path last:

    decision, kind, tracked_changes, untracked, unpushed, orphan, size_kib, nested, path

Removing a linked worktree keeps every commit that is on a branch, because refs
live in the main repository. What is lost is uncommitted work, untracked files,
and commits reachable only from a detached HEAD (orphan). A standalone clone
keeps its history in its own .git, so any unpushed work there is the only copy.
Nothing is modified.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def git(directory: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout


def count_lines(directory: Path, *args: str) -> int:
    code, out = git(directory, *args)
    return len(out.splitlines()) if code == 0 else 0


def process_cwds() -> set[str] | None:
    """Working directories of running processes, or None when lsof is unavailable."""
    try:
        result = subprocess.run(
            ["lsof", "-a", "-d", "cwd", "-Fn"], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return {line[1:] for line in result.stdout.splitlines() if line.startswith("n")}


def in_use(directory: Path, cwds: set[str] | None) -> bool:
    prefix = str(directory)
    return cwds is not None and any(c == prefix or c.startswith(prefix + "/") for c in cwds)


def repo_kind(directory: Path) -> str:
    marker = directory / ".git"
    if marker.is_dir():
        return "clone"
    if marker.is_file():
        text = marker.read_text(encoding="utf-8", errors="replace")
        return "linked" if "/worktrees/" in text else "gitfile-other"
    return "nogit"


def nested_repos(directory: Path, max_depth: int = 6) -> list[str]:
    found: list[str] = []
    base = len(directory.parts)
    for dirpath, dirnames, filenames in os.walk(directory):
        here = Path(dirpath)
        if here != directory and (".git" in dirnames or ".git" in filenames):
            found.append(str(here.relative_to(directory)))
        dirnames[:] = [] if len(here.parts) - base >= max_depth else [n for n in dirnames if n != ".git"]
    return found


def size_kib(directory: Path) -> int:
    result = subprocess.run(["du", "-sk", str(directory)], capture_output=True, text=True, check=False)
    try:
        return int(result.stdout.split()[0])
    except (IndexError, ValueError):
        return 0


def classify(directory: Path, cwds: set[str] | None) -> list[str]:
    kind = repo_kind(directory)
    tracked = untracked = unpushed = orphan = 0
    nested: list[str] = []
    if kind in {"linked", "clone"}:
        _, status = git(directory, "status", "--porcelain")
        lines = status.splitlines()
        untracked = sum(1 for line in lines if line.startswith("??"))
        tracked = len(lines) - untracked
        unpushed = count_lines(directory, "rev-list", "HEAD", "--not", "--remotes")
        orphan = count_lines(directory, "rev-list", "HEAD", "--not", "--branches", "--remotes", "--tags")
        nested = nested_repos(directory)
    if kind == "nogit":
        decision = "SKIP_NOT_GIT"
    elif kind == "gitfile-other":
        decision = "SKIP_UNSUPPORTED_GITFILE"
    elif in_use(directory, cwds):
        decision = "SKIP_IN_USE"
    elif nested:
        decision = "REVIEW_NESTED"
    elif kind == "clone" and (tracked or untracked or unpushed):
        decision = "SKIP_CLONE_HAS_WORK"
    elif orphan:
        decision = "SKIP_ORPHAN_COMMITS"
    elif tracked or untracked:
        decision = "REMOVE_LOSES_CHANGES"
    else:
        decision = "REMOVE"
    return [
        decision, kind, str(tracked), str(untracked), str(unpushed), str(orphan),
        str(size_kib(directory)), str(len(nested)), str(directory),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--from-file", type=Path, help="file with one path per line")
    args = parser.parse_args()
    paths = list(args.paths)
    if args.from_file:
        paths += [
            Path(line.strip().split("\t")[-1])
            for line in args.from_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    if not paths:
        parser.error("give at least one path or --from-file")
    cwds = process_cwds()
    if cwds is None:
        print("warning: lsof unavailable, running-process check skipped", file=sys.stderr)
    resolved = [p.resolve() for p in paths if p.is_dir()]
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(lambda d: classify(d, cwds), resolved))
    for row in sorted(rows, key=lambda r: r[-1]):
        print("\t".join(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
