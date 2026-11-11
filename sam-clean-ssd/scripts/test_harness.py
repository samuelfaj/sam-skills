#!/usr/bin/env python3
"""Prove the safety rules of the scan, classify and remove scripts on fixtures.

Each check states the reason the rule exists, so a regression names the harm.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE / "scan_regenerable.py"
CLASSIFY = HERE / "classify_worktrees.py"
REMOVE = HERE / "remove_listed.py"
CHECKS = 0

os.environ.update(
    GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
    GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
)


def check(condition: bool, reason: str) -> None:
    global CHECKS
    CHECKS += 1
    assert condition, reason


def run(script: Path, *args: object, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *map(str, args)],
        capture_output=True, text=True, check=False, cwd=cwd,
    )


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)
    return done.stdout


def touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    touch(path / "README.md", "one\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "init")


def listing(root: Path, *paths: Path) -> Path:
    file = root / "list.txt"
    file.write_text("".join(f"1\tkind\t{p}\n" for p in paths), encoding="utf-8")
    return file


def test_scan(root: Path) -> None:
    touch(root / "rust/Cargo.toml")
    touch(root / "rust/target/a.bin")
    touch(root / "notrust/target/source.txt")
    touch(root / "web/package.json")
    touch(root / "web/node_modules/m/index.js")
    touch(root / "swift/Package.swift")
    touch(root / "swift/.build/b")
    touch(root / "py/.venv/pyvenv.cfg")
    init_repo(root / "repo")
    touch(root / "repo/.gitignore", "dist/\n")
    touch(root / "repo/dist/out.js")
    touch(root / "repo/build/kept.txt")
    git(root / "repo", "add", "-A")
    git(root / "repo", "commit", "-q", "-m", "tracked build dir")
    (root / "linked").mkdir()
    os.symlink(root / "web/node_modules", root / "linked/node_modules")
    out = run(SCAN, root, "--min-mib", "0")
    rows = {line.split("\t")[3]: line.split("\t")[1:3] for line in out.stdout.splitlines()}
    check(out.returncode == 0, "scan must succeed")
    check(rows.get(str(root / "rust/target")) == ["build-target", "verified"], "target next to Cargo.toml is build output")
    check(str(root / "notrust/target") not in rows, "a target directory with no manifest may be source")
    check(rows.get(str(root / "web/node_modules")) == ["node-modules", "verified"], "node_modules with package.json")
    check(str(root / "swift/.build") in rows and str(root / "py/.venv") in rows, "markers for .build and .venv")
    check(rows.get(str(root / "repo/dist"), [""])[-1] == "review:ignored", "generic name is review, never verified")
    check(str(root / "repo/build") not in rows, "a build directory tracked by git is source, not output")
    check(str(root / "linked/node_modules") not in rows, "symlinks must not be followed or listed")


def test_remove_artifacts(root: Path) -> None:
    outside = Path(tempfile.mkdtemp()).resolve()
    touch(outside / "web/package.json")
    touch(outside / "web/node_modules/m.js")
    wanted = [root / "rust/target", root / "web/node_modules"]
    bad = [
        root / "notrust/target", root, outside / "web/node_modules",
        root / "linked/node_modules", Path("web/node_modules"), root / "repo/dist",
    ]
    lst = listing(root, *wanted, *bad, root / "gone/node_modules")
    dry = run(REMOVE, lst, "--root", root, "--kind", "artifacts", cwd=root)
    check(all(p.exists() for p in wanted), "a dry run must delete nothing")
    check(dry.returncode == 1 and dry.stdout.count("REFUSED") == len(bad), f"every unsafe path is refused: {dry.stdout}")
    check("ALREADY-GONE" in dry.stdout, "a missing path is reported, not an error")
    check("not absolute" in dry.stdout, "a relative path must not be resolved against the caller's directory")
    for p in bad[:4]:
        check(p.exists(), f"refused path must survive: {p}")
    shutil.rmtree(outside)
    done = run(REMOVE, listing(root, *wanted), "--root", root, "--kind", "artifacts", "--execute")
    check(done.returncode == 0, f"valid list must succeed: {done.stdout}")
    check(not any(p.exists() for p in wanted), "approved regenerable directories are removed")
    check((root / "notrust/target/source.txt").exists(), "source-like target stays")
    gen = run(REMOVE, listing(root, root / "repo/dist"), "--root", root, "--kind", "artifacts", "--execute", "--include-review")
    check(gen.returncode == 0 and not (root / "repo/dist").exists(), "review names go only with the explicit flag")


def classify(root: Path, *paths: Path) -> dict[str, list[str]]:
    out = run(CLASSIFY, *paths)
    check(out.returncode == 0, f"classify must succeed: {out.stderr}")
    return {Path(line.split("\t")[-1]).name: line.split("\t") for line in out.stdout.splitlines()}


def test_worktrees(root: Path) -> None:
    main = root / "main_repo"
    init_repo(main)
    names = ["clean", "branch_commit", "dirty", "detached", "nested", "busy"]
    for name in names:
        git(main, "worktree", "add", "-q", "-b", f"b_{name}", str(root / f"wt_{name}"))
    touch(root / "wt_branch_commit/feature.txt")
    git(root / "wt_branch_commit", "add", "-A")
    git(root / "wt_branch_commit", "commit", "-q", "-m", "work on a branch")
    touch(root / "wt_dirty/README.md", "edited\n")
    touch(root / "wt_dirty/new.txt")
    git(root / "wt_detached", "checkout", "-q", "--detach")
    touch(root / "wt_detached/lost.txt")
    git(root / "wt_detached", "add", "-A")
    git(root / "wt_detached", "commit", "-q", "-m", "only here")
    init_repo(root / "wt_nested/dependency")
    clone = root / "clone_ok"
    git(root, "clone", "-q", str(main), str(clone))
    work = root / "clone_work"
    git(root, "clone", "-q", str(main), str(work))
    touch(work / "mine.txt")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "unpushed")
    plain = root / "not_git"
    plain.mkdir()
    holder = None
    if shutil.which("lsof"):
        holder = subprocess.Popen(["sleep", "60"], cwd=root / "wt_busy")
        time.sleep(0.3)
    try:
        rows = classify(root, *[root / f"wt_{n}" for n in names], clone, work, plain)
    finally:
        if holder:
            holder.kill()
    want = {
        "wt_clean": "REMOVE", "wt_branch_commit": "REMOVE", "wt_dirty": "REMOVE_LOSES_CHANGES",
        "wt_detached": "SKIP_ORPHAN_COMMITS", "wt_nested": "REVIEW_NESTED",
        "clone_ok": "REMOVE", "clone_work": "SKIP_CLONE_HAS_WORK", "not_git": "SKIP_NOT_GIT",
    }
    if holder:
        want["wt_busy"] = "SKIP_IN_USE"
    for name, decision in want.items():
        check(rows[name][0] == decision, f"{name}: expected {decision}, got {rows[name][0]}")
    check(int(rows["wt_branch_commit"][4]) > 0, "an unpushed commit on a branch is still safe: the branch survives")
    check(rows["wt_dirty"][2] == "1" and rows["wt_dirty"][3] == "1", "tracked and untracked changes are counted apart")

    patches = root / "patches"
    targets = [root / "wt_clean", root / "wt_branch_commit", root / "wt_dirty", root / "wt_detached"]
    refused = run(REMOVE, listing(root, *targets), "--root", root, "--kind", "worktrees", "--execute")
    check((root / "wt_dirty").exists() and (root / "wt_detached").exists(), "uncommitted work and orphan commits block removal")
    check(not (root / "wt_clean").exists() and refused.returncode == 1, "safe worktrees go, refusals set exit code 1")
    forced = run(REMOVE, listing(root, root / "wt_dirty", root / "wt_detached"), "--root", root, "--kind", "worktrees",
                 "--execute", "--allow-uncommitted-loss", "--save-patches", patches)
    check((root / "wt_detached").exists(), "orphan commits stay protected even with the loss flag")
    check(not (root / "wt_dirty").exists(), "the loss flag removes a dirty worktree")
    saved = list(patches.glob("*wt_dirty.patch"))
    check(len(saved) == 1 and "edited" in saved[0].read_text(encoding="utf-8"), "tracked changes are saved before removal")
    check(forced.returncode == 1, "the refused orphan worktree keeps exit code 1")
    check("b_branch_commit" in git(main, "branch", "--list"), "commits on a branch survive worktree removal")
    check(str(root / "wt_clean") not in git(main, "worktree", "list"), "worktree metadata is pruned")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        test_scan(root)
        test_remove_artifacts(root)
    with tempfile.TemporaryDirectory() as tmp:
        test_worktrees(Path(tmp).resolve())
    print(f"PASS: {CHECKS} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
