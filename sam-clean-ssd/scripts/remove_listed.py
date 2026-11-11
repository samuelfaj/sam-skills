#!/usr/bin/env python3
"""Guarded removal of an approved list of directories. Dry run unless --execute.

LIST holds one path per line; the last tab-separated field is the path, so the
output of scan_regenerable.py or classify_worktrees.py can be filtered and passed
as is. Every path is re-validated here, whatever produced the list:

  --kind artifacts  only recognised regenerable directories (see scan_regenerable.py)
  --kind worktrees  only linked git worktrees with no commits that exist nowhere else

A path is refused when it is relative, a symlink, outside --root, inside .git,
used as the working directory of a running process, or fails the kind check.
Worktrees with uncommitted or untracked work are refused unless
--allow-uncommitted-loss is given; --save-patches then keeps a patch of the
tracked changes first (untracked files are not saved). Exit code 1 means
something was refused or failed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from classify_worktrees import git, in_use, process_cwds
from scan_regenerable import artifact_status, size_kib


def read_list(path: Path) -> list[str]:
    return [
        line.strip().split("\t")[-1]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def uncommitted(p: Path) -> int:
    _, status = git(p, "status", "--porcelain")
    return len(status.splitlines())


def refusal(p: Path, root: Path, args: argparse.Namespace) -> str | None:
    if not p.is_absolute():
        return "path is not absolute"
    if p.is_symlink():
        return "path is a symlink"
    if not p.is_dir():
        return "not a directory"
    if p.resolve() != p:
        return "path contains a symlink or dot segment"
    if p == root or root not in p.parents:
        return "outside --root"
    if ".git" in p.parts:
        return "inside a .git directory"
    if args.kind == "artifacts":
        status = artifact_status(p)
        if status is None:
            return "not a recognised regenerable directory (marker missing or tracked by git)"
        if status[1].startswith("review") and not args.include_review:
            return "generic name; needs --include-review after the user approved it"
        return None
    marker = p / ".git"
    if not (marker.is_file() and "/worktrees/" in marker.read_text(encoding="utf-8", errors="replace")):
        return "not a linked git worktree"
    _, orphans = git(p, "rev-list", "HEAD", "--not", "--branches", "--remotes", "--tags")
    if orphans.split():
        return "has commits reachable from no branch, remote or tag"
    if uncommitted(p) and not args.allow_uncommitted_loss:
        return "has uncommitted or untracked work; needs --allow-uncommitted-loss"
    return None


def save_patch(p: Path, root: Path, outdir: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(p), "diff", "HEAD", "--binary"], capture_output=True, check=False
    )
    if result.returncode == 0 and result.stdout:
        outdir.mkdir(parents=True, exist_ok=True)
        name = str(p.relative_to(root)).replace(os.sep, "__") + ".patch"
        (outdir / name).write_bytes(result.stdout)


def remove(p: Path, root: Path, args: argparse.Namespace) -> tuple[str, str | None]:
    if not os.path.lexists(p):
        return "already-gone", None
    common = None
    if args.kind == "worktrees":
        code, out = git(p, "rev-parse", "--path-format=absolute", "--git-common-dir")
        common = out.strip() if code == 0 else None
        if args.save_patches:
            save_patch(p, root, args.save_patches)
    result = subprocess.run(["rm", "-rf", "--", str(p)], capture_output=True, text=True, check=False)
    if os.path.lexists(p):
        reason = (result.stderr.strip().splitlines() or ["still exists"])[0]
        return f"FAILED ({reason})", common
    return "removed", common


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("list_file", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--kind", choices=("artifacts", "worktrees"), required=True)
    parser.add_argument("--execute", action="store_true", help="delete; default is a dry run")
    parser.add_argument("--include-review", action="store_true")
    parser.add_argument("--allow-uncommitted-loss", action="store_true")
    parser.add_argument("--save-patches", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    root = args.root.resolve()
    cwds = process_cwds()
    if cwds is None:
        print("warning: lsof unavailable, running-process check skipped", file=sys.stderr)

    refused: list[tuple[Path, str]] = []
    plan: list[Path] = []
    for p in sorted({Path(x) for x in read_list(args.list_file)}, key=lambda q: -len(q.parts)):
        if not os.path.lexists(p):
            print(f"ALREADY-GONE  {p}")
            continue
        why = refusal(p, root, args) or ("used by a running process" if in_use(p, cwds) else None)
        if why:
            refused.append((p, why))
            print(f"REFUSED       {p}  ({why})")
        else:
            plan.append(p)

    free_before = shutil.disk_usage(root).free
    failed = 0
    commons: set[str] = set()
    if not args.execute:
        for p in plan:
            print(f"WOULD-REMOVE  {size_kib(p) // 1024:7d} MiB  {p}")
    else:
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            results = list(pool.map(lambda p: remove(p, root, args), plan))
        for p, (status, common) in zip(plan, results):
            print(f"{status.upper() if status == 'removed' else status}  {p}")
            failed += status.startswith("FAILED")
            if common:
                commons.add(common)
        for common in sorted(commons):
            subprocess.run(["git", "--git-dir", common, "worktree", "prune"], capture_output=True, check=False)
    freed = (shutil.disk_usage(root).free - free_before) / 1073741824
    mode = "executed" if args.execute else "dry run (nothing deleted)"
    print(f"{mode}: {len(plan)} planned, {len(refused)} refused, {failed} failed, free space change {freed:+.1f} GiB")
    return 1 if refused or failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
