#!/usr/bin/env python3
"""Offline tests for the sam-design manifest, check script, and installer."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import check_design_skills as check  # noqa: E402

CHECK = SCRIPTS / "check_design_skills.py"
INSTALL = SCRIPTS / "install_design_skills.py"


def write_skill(path: Path, name: str, body: str = "x") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d\n---\n{body}\n")


def build_fake_repos(base: Path) -> dict[str, Path]:
    repos, skills = check.parse_manifest()
    roots = {key: base / key for key in repos}
    for skill in skills:
        write_skill(roots[skill["repo"]] / skill["source"], skill["skill"])
    return roots


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})


class ManifestTests(unittest.TestCase):
    def test_21_rows_with_pinned_commits(self):
        repos, skills = check.parse_manifest()
        self.assertEqual(len(skills), 21)
        self.assertEqual(len({s["skill"] for s in skills}), 21)
        for skill in skills:
            self.assertRegex(skill["commit"], r"^[0-9a-f]{40}$", skill["skill"])
            self.assertEqual(skill["commit"], repos[skill["repo"]]["commit"])
            self.assertIn(skill["repo"], repos)


class CheckTests(unittest.TestCase):
    def test_installed_missing_and_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root / "animate", "animate")
            write_skill(root / "ckm-design", "ckm:design")
            write_skill(root / "renamed-dir", "break-ui")
            result = run(CHECK, "--root", tmp, "--json")
            self.assertEqual(result.returncode, 1)
            data = {r["skill"]: r for r in json.loads(result.stdout)["skills"]}
            self.assertEqual(data["animate"]["status"], "installed")
            self.assertEqual(data["design"]["status"], "installed")  # alias via dir and name
            self.assertEqual(data["break-ui"]["status"], "installed")  # frontmatter name
            self.assertEqual(data["slides"]["status"], "missing")
            self.assertEqual(len(data), 21)

    def test_all_installed_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            repos = build_fake_repos(Path(tmp) / "src")
            _, skills = check.parse_manifest()
            for s in skills:
                write_skill(Path(tmp) / "host" / s["install"], s["skill"])
            result = run(CHECK, "--root", str(Path(tmp) / "host"))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("21/21 installed", result.stdout)
            self.assertEqual(set(repos), {"emil", "uupm"})


class InstallTests(unittest.TestCase):
    def test_install_idempotent_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repos = build_fake_repos(base / "src")
            dest = base / "dest"
            src_args = [a for k, p in repos.items() for a in ("--source-dir", f"{k}={p}")]

            dry = run(INSTALL, "--dest", str(dest), *src_args, "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertFalse(dest.exists())

            first = run(INSTALL, "--dest", str(dest), *src_args)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(run(CHECK, "--root", str(dest)).returncode, 0)

            again = run(INSTALL, "--dest", str(dest), *src_args)
            self.assertEqual(again.returncode, 0)
            self.assertEqual(again.stdout.count("unchanged"), 21)

            (dest / "animate" / "SKILL.md").write_text("local edit")
            refused = run(INSTALL, "--dest", str(dest), *src_args)
            self.assertEqual(refused.returncode, 1)
            self.assertIn("refused animate", refused.stderr)
            self.assertEqual((dest / "animate" / "SKILL.md").read_text(), "local edit")

            forced = run(INSTALL, "--dest", str(dest), *src_args, "--force")
            self.assertEqual(forced.returncode, 0)
            self.assertIn("name: animate", (dest / "animate" / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()
