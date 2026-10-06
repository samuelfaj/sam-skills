#!/usr/bin/env python3
"""Install the manifest design skills from their pinned upstream commits."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_design_skills import parse_manifest  # noqa: E402


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def clone_pinned(url: str, commit: str, target: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True, text=True)

    target.mkdir(parents=True, exist_ok=True)
    git("init", "--quiet")
    git("remote", "add", "origin", url)
    git("fetch", "--quiet", "--depth", "1", "origin", commit)
    git("checkout", "--quiet", "FETCH_HEAD")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, type=Path, help="host skill dir to install into")
    parser.add_argument("--source-dir", action="append", default=[], metavar="REPO=PATH",
                        help="use a local checkout for a manifest repo key instead of cloning")
    parser.add_argument("--dry-run", action="store_true", help="print actions without writing")
    parser.add_argument("--force", action="store_true", help="overwrite differing existing dirs")
    args = parser.parse_args(argv)

    overrides: dict[str, Path] = {}
    for item in args.source_dir:
        key, sep, path = item.partition("=")
        if not sep or not path:
            parser.error(f"--source-dir needs REPO=PATH, got {item!r}")
        overrides[key] = Path(path).expanduser()

    repos, skills = parse_manifest()
    dest = args.dest.expanduser()
    status = 0
    with tempfile.TemporaryDirectory(prefix="sam-design-") as tmp:
        roots: dict[str, Path | None] = {}
        for skill in skills:
            key = skill["repo"]
            if key not in roots:
                if key in overrides:
                    roots[key] = overrides[key]
                elif args.dry_run:
                    roots[key] = None
                else:
                    repo = repos[key]
                    print(f"clone {repo['url']} @ {repo['commit']}")
                    try:
                        clone_pinned(repo["url"], repo["commit"], Path(tmp) / key)
                    except (subprocess.CalledProcessError, OSError) as exc:
                        detail = getattr(exc, "stderr", "") or str(exc)
                        print(f"error: clone of {key} failed: {detail.strip()}", file=sys.stderr)
                        roots[key] = None
                        status = 2
                        continue
                    roots[key] = Path(tmp) / key
            root = roots[key]
            target = dest / skill["install"]
            if root is None:
                if args.dry_run:
                    verb = "exists, would compare" if target.exists() else "would install"
                    print(f"{verb} {skill['skill']} -> {target}")
                continue
            source = root / skill["source"]
            if not (source / "SKILL.md").is_file():
                print(f"error: {skill['skill']}: no SKILL.md at {source}", file=sys.stderr)
                status = 2
                continue
            if target.exists():
                if tree_digest(target) == tree_digest(source):
                    print(f"unchanged {skill['skill']} -> {target}")
                    continue
                if not args.force:
                    print(f"refused {skill['skill']}: {target} differs; use --force", file=sys.stderr)
                    status = status or 1
                    continue
                action = "overwrite"
            else:
                action = "install"
            print(f"{'would ' if args.dry_run else ''}{action} {skill['skill']} -> {target}")
            if not args.dry_run:
                if target.exists():
                    shutil.rmtree(target)
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, target)
    return status


if __name__ == "__main__":
    sys.exit(main())
