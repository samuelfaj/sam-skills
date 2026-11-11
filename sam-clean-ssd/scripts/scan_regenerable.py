#!/usr/bin/env python3
"""Read-only scan for regenerable build output and caches under a root.

Lists directories that a build tool or package manager recreates, with sizes.
Nothing is deleted. Output is TSV, largest first:

    size_kib <TAB> kind <TAB> status <TAB> path

status is `verified` when a marker proves the kind (a `target` directory next to
Cargo.toml), or `review:<git state>` for generic names such as build or dist that
can also hold source. A generic directory with files tracked by git is skipped.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _sibling(*names: str):
    return lambda p: any((p.parent / n).exists() for n in names)


def _inside(*names: str):
    return lambda p: any((p / n).exists() for n in names)


VERIFIED = {
    "node_modules": (
        "node-modules",
        lambda p: (p.parent / "package.json").is_file()
        or (p / ".package-lock.json").is_file()
        or (p / ".bin").is_dir(),
    ),
    "target": (
        "build-target",
        _sibling("Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts"),
    ),
    ".build": ("swiftpm-build", _sibling("Package.swift")),
    "Pods": ("cocoapods", _sibling("Podfile")),
    ".venv": ("python-venv", _inside("pyvenv.cfg")),
    "venv": ("python-venv", _inside("pyvenv.cfg")),
    ".turbo": ("turbo-cache", lambda p: True),
    "__pycache__": ("python-bytecode", lambda p: True),
    "DerivedData": (
        "xcode-derived-data",
        _inside("info.plist", "Build", "Index.noindex", "ModuleCache.noindex"),
    ),
}
REVIEW = {
    "build", "dist", "out", ".next", ".nuxt", ".svelte-kit", ".angular",
    ".parcel-cache", "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".gradle", ".cache", ".expo", ".dart_tool",
}


def _git(directory: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True, check=False
    )


def git_state(p: Path) -> str | None:
    """None when git tracks files inside p; otherwise ignored, untracked or no-repo."""
    try:
        if _git(p.parent, "rev-parse", "--is-inside-work-tree").returncode != 0:
            return "no-repo"
        if _git(p.parent, "ls-files", "--", p.name).stdout.strip():
            return None
        ignored = _git(p.parent, "check-ignore", "-q", "--", p.name).returncode == 0
        return "ignored" if ignored else "untracked"
    except OSError:
        return "no-repo"


def artifact_status(p: Path) -> tuple[str, str] | None:
    """(kind, status) when p is a recognised disposable directory, else None."""
    rule = VERIFIED.get(p.name)
    if rule and rule[1](p):
        return rule[0], "verified"
    if p.name in REVIEW:
        state = git_state(p)
        if state is not None:
            return p.name, f"review:{state}"
    return None


def size_kib(p: Path) -> int:
    result = subprocess.run(["du", "-sk", str(p)], capture_output=True, text=True, check=False)
    try:
        return int(result.stdout.split()[0])
    except (IndexError, ValueError):
        return 0


def scan(root: Path) -> list[tuple[str, str, Path]]:
    root_device = root.stat().st_dev
    found: list[tuple[str, str, Path]] = []
    for dirpath, dirnames, _ in os.walk(root, followlinks=False):
        keep = []
        for name in dirnames:
            p = Path(dirpath) / name
            if name == ".git" or p.is_symlink():
                continue
            try:
                if p.stat().st_dev != root_device:
                    continue
            except OSError:
                continue
            status = artifact_status(p)
            if status:
                found.append((status[0], status[1], p))
            else:
                keep.append(name)
        dirnames[:] = keep
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, help="write TSV here instead of stdout")
    parser.add_argument("--min-mib", type=int, default=50, help="hide entries smaller than this")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    found = scan(root)
    with ThreadPoolExecutor(max_workers=8) as pool:
        sizes = list(pool.map(size_kib, [p for _, _, p in found]))
    rows = [
        (size, kind, status, p)
        for (kind, status, p), size in zip(found, sizes)
        if size >= args.min_mib * 1024
    ]
    rows.sort(key=lambda row: -row[0])
    text = "".join(f"{size}\t{kind}\t{status}\t{p}\n" for size, kind, status, p in rows)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    totals: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for size, kind, status, _ in rows:
        totals[(kind, status)][0] += 1
        totals[(kind, status)][1] += size
    for (kind, status), (count, size) in sorted(totals.items(), key=lambda item: -item[1][1]):
        print(f"{size / 1048576:9.1f} GiB  {count:5d}  {kind}  {status}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
