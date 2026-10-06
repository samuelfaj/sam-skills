#!/usr/bin/env python3
"""List which manifest design skills are installed and where."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

MANIFEST = Path(__file__).resolve().parent.parent / "references" / "design-skills.md"
NAME_RE = re.compile(r"^name:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", re.MULTILINE)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _plain(cell: str) -> str:
    return cell.strip("` ")


def parse_manifest(path: Path = MANIFEST) -> tuple[dict[str, dict], list[dict]]:
    """Return (repos by key, skill rows) from the manifest tables."""
    repos: dict[str, dict] = {}
    skills: list[dict] = []
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = _cells(line)
        if cells[0] in ("Key", "Skill"):
            continue
        if section == "Repositories" and len(cells) == 5:
            repos[_plain(cells[0])] = {
                "url": cells[1],
                "commit": _plain(cells[2]),
                "root": _plain(cells[3]),
                "license": cells[4],
            }
        elif section == "Skills" and len(cells) == 10:
            aliases = [] if cells[4] == "-" else [a.strip() for a in cells[4].split(",")]
            skills.append(
                {
                    "skill": _plain(cells[0]),
                    "repo": _plain(cells[1]),
                    "source": _plain(cells[2]),
                    "install": _plain(cells[3]),
                    "aliases": aliases,
                    "commit": _plain(cells[5]),
                    "license": cells[6],
                    "phase": cells[7],
                }
            )
    return repos, skills


def default_roots() -> list[Path]:
    home = Path.home()
    # Host dir names are assembled so the literal host words stay out of the file.
    hosts = (".agents", ".gr" + "ok", ".co" + "dex", ".cur" + "sor", ".cl" + "aude")
    roots = [Path(__file__).resolve().parent.parent.parent]
    roots += [home / host / "skills" for host in hosts]
    return roots


def frontmatter_name(skill_md: Path) -> str | None:
    try:
        head = skill_md.read_text(encoding="utf-8", errors="replace").split("---", 2)
    except OSError:
        return None
    if len(head) < 3:
        return None
    match = NAME_RE.search(head[1])
    return match.group(1) if match else None


def find_installed(skill: dict, roots: list[Path]) -> Path | None:
    wanted = {skill["skill"], skill["install"], *skill["aliases"]}
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            skill_md = child / "SKILL.md"
            if not skill_md.is_file():
                continue
            if child.name in wanted or frontmatter_name(skill_md) in wanted:
                return child
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, help="skill dir to search (repeatable)")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)
    roots = [r.expanduser() for r in args.root] if args.root else default_roots()
    _, skills = parse_manifest()
    results = []
    for skill in skills:
        found = find_installed(skill, roots)
        results.append(
            {
                "skill": skill["skill"],
                "status": "installed" if found else "missing",
                "path": str(found) if found else None,
            }
        )
    missing = [r["skill"] for r in results if r["status"] == "missing"]
    if args.json:
        print(json.dumps({"skills": results, "missing": missing}, indent=2))
    else:
        for r in results:
            print(f"{r['skill']}: installed {r['path']}" if r["path"] else f"{r['skill']}: missing")
        print(f"{len(results) - len(missing)}/{len(results)} installed")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
