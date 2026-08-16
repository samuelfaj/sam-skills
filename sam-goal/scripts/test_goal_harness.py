#!/usr/bin/env python3
"""Adversarial fixtures for sam-goal checkers, scaffold, and report validation."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
REPO_ROOT = SKILL_DIR.parent


def load(name: str) -> ModuleType:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gates_mod = load("check_gates.py")
ledger_mod = load("check_ledger.py")
validate_mod = load("validate_goal_report.py")
detect_mod = load("detect_host.py")

HOST_ENV_KEYS = (
    "CLAUDECODE",
    "CLAUDE_CODE",
    "CLAUDE_PLUGIN_ROOT",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION",
    "CODEX_HOME",
    "CODEX_THREAD_ID",
    "CODEX_SANDBOX",
    "CODEX_CI",
    "CODEX_TASK",
    "GROK_AGENT",
    "GROK_HOME",
    "GROK_SESSION",
    "GROK_SESSION_ID",
    "SAM_GOAL_HOST",
    "SAM_ACTIVE_HOST",
)


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in HOST_ENV_KEYS:
        env.pop(key, None)
    return env


def run_script(
    script: str,
    args: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / script), *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def solo_report(goal_dir: Path, **overrides: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "workflow": "goal",
        "goal": "Add a native date field",
        "action": "execute",
        "intensity": "full",
        "mode": "solo",
        "tree_depth": 2,
        "goal_dir": str(goal_dir),
        "host": {
            "key": "grok",
            "status": "DETECTED",
            "detected_from": "env:GROK_AGENT",
        },
        "units": {
            "counted": 1,
            "gate": "closed",
            "reason": "single-agent: 1 unit, below threshold",
        },
        "ladder": {
            "rung": 4,
            "rationale": "native date input covers the request",
            "skipped": ["picker package"],
            "new_dependencies": [],
            "authorized_dependencies": [],
        },
        "gates": {
            "path": str(goal_dir / "GATES.md"),
            "total": 1,
            "met": 1,
            "abandoned": 0,
            "unmet": [],
            "abandoned_ids": [],
        },
        "delegation": None,
        "overbuild_review": {"lean_already": True, "net_lines": 0, "findings": []},
        "checks": {
            "gates": {"exit_code": 0, "summary": "ALL MET (1 met)"},
            "ledger": None,
        },
        "evidence": [
            {
                "id": "E1",
                "status": "PASS",
                "detail": "check_gates.py --status: ALL MET (1 met)",
            }
        ],
        "decision": {"result": "COMPLETE", "remaining": []},
    }
    report.update(overrides)
    return report


def delegated_report(goal_dir: Path, **overrides: Any) -> dict[str, Any]:
    report = solo_report(goal_dir)
    report.update(
        {
            "mode": "delegated",
            "tree_depth": 4,
            "units": {
                "counted": 3,
                "gate": "open",
                "reason": "gate open: 3 units",
            },
            "delegation": {
                "path": str(goal_dir / "DELEGATION.md"),
                "units": 3,
                "verified": 3,
                "pending": 0,
                "complete": True,
            },
            "checks": {
                "gates": {"exit_code": 0, "summary": "ALL MET (1 met)"},
                "ledger": {
                    "exit_code": 0,
                    "summary": "ledger complete: every unit verified.",
                },
            },
        }
    )
    report.update(overrides)
    return report


def expect(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        raise AssertionError(f"{name}: {detail or 'failed'}")


def test_no_third_party_imports() -> None:
    allowed = {
        "argparse",
        "ast",
        "dataclasses",
        "json",
        "os",
        "pathlib",
        "re",
        "subprocess",
        "sys",
        "tempfile",
        "typing",
        "importlib",
        "importlib.util",
        "types",
    }
    for path in SCRIPTS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            extra = [name for name in names if name not in allowed and name not in sys.stdlib_module_names]
            expect(f"stdlib-only {path.name}", not extra, str(extra))


def test_scaffold(root: Path) -> None:
    solo = root / "solo"
    result = run_script(
        "scaffold_goal_dir.py",
        ["--out", str(solo), "--json"],
        root,
    )
    expect("scaffold solo", result.returncode == 0, result.stderr)
    payload = json.loads(result.stdout)
    expect("scaffold path", payload["goal_dir"] == str(solo.resolve()))
    expect("scaffold gates", (solo / "GATES.md").is_file())
    expect("scaffold no ledger", not (solo / "DELEGATION.md").exists())
    again = run_script("scaffold_goal_dir.py", ["--out", str(solo), "--json"], root)
    expect("scaffold keep", "GATES.md" in json.loads(again.stdout)["existing"])

    delegated = root / "delegated"
    result = run_script(
        "scaffold_goal_dir.py",
        ["--out", str(delegated), "--mode", "delegated", "--tree", "5", "--json"],
        root,
    )
    expect("scaffold delegated", result.returncode == 0, result.stderr)
    expect("scaffold ledger", (delegated / "DELEGATION.md").is_file())
    expect("scaffold brief", (delegated / "briefs" / "worker-1.md").is_file())
    expect("scaffold plan", (delegated / "PLAN.md").is_file())
    expect("scaffold leaf", (delegated / "gates" / "leaf-1.1.md").is_file())


def test_gates(root: Path) -> None:
    empty = run_script("check_gates.py", [], root)
    expect("gates missing", empty.returncode == 2, empty.stderr)

    target = root / "gates-work"
    target.mkdir()
    path = write(
        target / "GATES.md",
        "# Gates: demo\n\n"
        "- [ ] G1: hello\n"
        "  CHECK: printf 'hello-ok\\n'\n"
        "  EXPECT: hello-ok\n"
        "  EVIDENCE: pending\n",
    )
    status = run_script("check_gates.py", ["--status", str(path)], target)
    expect("gates unmet status", status.returncode == 1, status.stdout)
    expect("gates unchecked noted", "UNMET G1 (unchecked)" in status.stdout, status.stdout)

    passing = run_script("check_gates.py", [str(path)], target)
    expect("gates pass", passing.returncode == 0, passing.stdout + passing.stderr)
    expect("gates flipped", "- [x] G1:" in path.read_text(encoding="utf-8"))
    expect("gates evidence filled", "hello-ok" in path.read_text(encoding="utf-8"))

    abandoned = write(
        target / "abandoned.md",
        "# Gates: gone\n\n- [ ] G1: impossible\n  EVIDENCE: pending\n\nABANDON: G1 no surface\n",
    )
    result = run_script("check_gates.py", ["--status", str(abandoned)], target)
    expect("gates abandon", result.returncode == 0, result.stdout)
    expect("gates abandon summary", "ALL MET" in result.stdout, result.stdout)

    regex = write(
        target / "regex.md",
        "# Gates: re\n\n- [ ] G1: count\n  CHECK: printf '8/8 passed\\n'\n"
        "  EXPECT: /8\\/8 passed/\n  EVIDENCE: pending\n",
    )
    result = run_script("check_gates.py", [str(regex)], target)
    expect("gates regex", result.returncode == 0, result.stdout)

    checked_pending = write(
        target / "lying.md",
        "# Gates: lie\n\n- [x] G1: claimed\n  EVIDENCE: pending\n",
    )
    result = run_script("check_gates.py", ["--status", str(checked_pending)], target)
    expect("gates lie", result.returncode == 1, result.stdout)
    expect("gates lie why", "EVIDENCE pending" in result.stdout, result.stdout)

    nested = target / "gates"
    write(
        nested / "leaf.md",
        "# Gates: leaf\n\n- [x] G1: ready\n  EVIDENCE: `python3 -c 'print(1)'` printed 1\n",
    )
    result = run_script("check_gates.py", ["--status", str(nested)], target)
    expect("gates dir", result.returncode == 0, result.stdout)

    goal_root = target / "goal-root"
    write(
        goal_root / "GATES.md",
        "# Gates: root\n\n- [x] G1: root\n  EVIDENCE: ran python3 -c pass\n",
    )
    write(
        goal_root / "gates" / "leaf.md",
        "# Gates: leaf\n\n- [x] G1: leaf\n  EVIDENCE: ran python3 -c pass\n",
    )
    result = run_script("check_gates.py", ["--status", str(goal_root)], target)
    expect("gates goal dir", result.returncode == 0, result.stdout)
    expect("gates both files", "GATES.md" in result.stdout and "leaf.md" in result.stdout, result.stdout)


def test_ledger(root: Path) -> None:
    complete = write(
        root / "complete.md",
        "# Delegation plan\nUnits: 2\n\n"
        "| # | Unit | Files (mine) | Worker | Acceptance | Status |\n"
        "|---|------|--------------|--------|------------|--------|\n"
        "| 1 | stats | app/stats.py | worker-1 | python3 tests/run.py | verified |\n"
        "| 2 | finance | app/finance.py | worker-2 | python3 tests/run.py | verified |\n\n"
        "Verified both: ran python3 tests/run.py -> 93 passed.\n",
    )
    result = run_script("check_ledger.py", [str(complete)], root)
    expect("ledger complete", result.returncode == 0, result.stdout)

    partial = write(
        root / "partial.md",
        "# Delegation plan\nUnits: 2\n\n"
        "| # | Unit | Files (mine) | Worker | Acceptance | Status |\n"
        "|---|------|--------------|--------|------------|--------|\n"
        "| 1 | stats | app/stats.py | worker-1 | tests pass | verified |\n"
        "| 2 | finance | app/finance.py | worker-2 | tests pass | pending |\n\n"
        "Ran `python3 tests/run.py`: 1 passed\n",
    )
    result = run_script("check_ledger.py", [str(partial)], root)
    expect("ledger partial", result.returncode == 1, result.stdout)

    junk = write(
        root / "junk.md",
        "# Delegation plan\nUnits: 1\n\n"
        "| # | Unit | Files (mine) | Worker | Acceptance | Status |\n"
        "|---|------|--------------|--------|------------|--------|\n"
        "| 1 | stats | app/stats.py | worker-1 | tests pass | verified |\n\n"
        "done\n",
    )
    result = run_script("check_ledger.py", [str(junk)], root)
    expect("ledger junk", result.returncode == 1, result.stdout)
    expect("ledger junk missing", "MISSING" in result.stdout, result.stdout)

    word = write(
        root / "word.md",
        "# Delegation plan\nUnits: 1\n\n"
        "| # | Unit | Files (mine) | Worker | Acceptance | Status |\n"
        "|---|------|--------------|--------|------------|--------|\n"
        "| 1 | stats | app/stats.py | worker-1 | tests pass | verified |\n\n"
        "verified\n",
    )
    result = run_script("check_ledger.py", [str(word)], root)
    expect("ledger word", result.returncode == 1, result.stdout)

    tick = write(
        root / "tick.md",
        "# Delegation plan\nUnits: 1\n\n"
        "| # | Unit | Files (mine) | Worker | Acceptance | Status |\n"
        "|---|------|--------------|--------|------------|--------|\n"
        "| 1 | stats | app/stats.py | worker-1 | tests pass | verified |\n\n"
        "`done`\n",
    )
    result = run_script("check_ledger.py", [str(tick)], root)
    expect("ledger tick", result.returncode == 1, result.stdout)

    truncated = write(
        root / "truncated.md",
        "# Delegation plan\nUnits: 2\n\n"
        "| # | Unit | Files (mine) | Worker | Acceptance | Status |\n"
        "|---|------|--------------|--------|------------|--------|\n"
        "| 1 | stats | app/stats.py | worker-1 | tests pass | verified |\n"
        "| 2 | finance | app/finance.py |\n\n"
        "- Ran `python3 tests/run.py`: all pass\n",
    )
    result = run_script("check_ledger.py", [str(truncated)], root)
    expect("ledger truncated", result.returncode == 1, result.stdout)

    piped = write(
        root / "piped.md",
        "# Delegation plan\nUnits: 1\n\n"
        "| # | Unit | Files (mine) | Worker | Acceptance | Status |\n"
        "|:--|:------|:--------------|:--------|:------------|:--------|\n"
        "| 1 | stats | app/stats.py | worker-1 | `pytest \\| tail -1` matches PASS | verified |\n\n"
        "- Ran `python3 tests/run.py`: all pass\n",
    )
    result = run_script("check_ledger.py", [str(piped)], root)
    expect("ledger piped", result.returncode == 0, result.stdout)

    other = write(root / "notes.md", "# hello\n\nno table here\n")
    missing = run_script("check_ledger.py", [str(other)], root)
    expect("ledger not ledger", missing.returncode == 2, missing.stderr)

    code, _ = ledger_mod.inspect(complete)
    expect("ledger inspect", code == 0)


def test_report(root: Path) -> None:
    goal_dir = root / "goal"
    goal_dir.mkdir()
    good = solo_report(goal_dir)
    expect("report solo", validate_mod.validate(good) == [], str(validate_mod.validate(good)))

    dep = solo_report(
        goal_dir,
        ladder={
            "rung": 7,
            "rationale": "added a package",
            "skipped": [],
            "new_dependencies": ["fancy-picker"],
            "authorized_dependencies": [],
        },
    )
    errors = validate_mod.validate(dep)
    expect("report unauthorized dep", any("unauthorized" in item for item in errors), str(errors))

    allowed = solo_report(
        goal_dir,
        ladder={
            "rung": 7,
            "rationale": "user named the package",
            "skipped": [],
            "new_dependencies": ["fancy-picker"],
            "authorized_dependencies": ["fancy-picker"],
        },
    )
    expect("report authorized dep", validate_mod.validate(allowed) == [], str(validate_mod.validate(allowed)))

    delegated = delegated_report(goal_dir)
    expect(
        "report delegated",
        validate_mod.validate(delegated) == [],
        str(validate_mod.validate(delegated)),
    )
    broken = delegated_report(
        goal_dir,
        checks={
            "gates": {"exit_code": 0, "summary": "ALL MET (1 met)"},
            "ledger": {"exit_code": 1, "summary": "INCOMPLETE"},
        },
    )
    errors = validate_mod.validate(broken)
    expect("report ledger exit", any("ledger.exit_code" in item for item in errors), str(errors))

    mismatch = solo_report(
        goal_dir,
        mode="solo",
        units={"counted": 1, "gate": "open", "reason": "wrong"},
    )
    errors = validate_mod.validate(mismatch)
    expect("report mode gate", any("solo mode" in item for item in errors), str(errors))

    leftover = solo_report(
        goal_dir,
        decision={"result": "IN_PROGRESS", "remaining": []},
    )
    errors = validate_mod.validate(leftover)
    expect("report remaining", any("remaining" in item for item in errors), str(errors))

    review = solo_report(
        goal_dir,
        action="review",
        gates={
            "path": str(goal_dir / "GATES.md"),
            "total": 0,
            "met": 0,
            "abandoned": 0,
            "unmet": [],
            "abandoned_ids": [],
        },
        checks={"gates": None, "ledger": None},
    )
    expect("report review", validate_mod.validate(review) == [], str(validate_mod.validate(review)))

    path = write(root / "goal-report.json", json.dumps(good))
    result = run_script("validate_goal_report.py", [str(path)], root)
    expect("report cli", result.returncode == 0 and "VALID" in result.stdout, result.stdout + result.stderr)

    parsed = gates_mod.parse_gates(
        ["- [ ] G1: demo", "  CHECK: true", "  EXPECT: ok", "  EVIDENCE: pending"]
    )
    expect("parse one gate", len(parsed.gates) == 1 and parsed.gates[0].id == "G1")

    missing_host = dict(good)
    missing_host.pop("host")
    errors = validate_mod.validate(missing_host)
    expect("report missing host", any(item.startswith("host ") for item in errors), str(errors))

    unknown = solo_report(
        goal_dir,
        host={"key": None, "status": "UNKNOWN", "detected_from": "none"},
    )
    expect("report unknown host", validate_mod.validate(unknown) == [], str(validate_mod.validate(unknown)))

    bad_key = solo_report(
        goal_dir,
        host={"key": None, "status": "DETECTED", "detected_from": "env:GROK_AGENT"},
    )
    errors = validate_mod.validate(bad_key)
    expect("report detected needs key", any("host.key" in item for item in errors), str(errors))


def test_host(root: Path) -> None:
    empty = {}
    unknown = detect_mod.detect_host(empty)
    expect("detect unknown", unknown["status"] == "UNKNOWN" and unknown["host"] is None)

    grok = detect_mod.detect_host({"GROK_AGENT": "1"})
    expect("detect grok", grok["host"] == "grok" and grok["status"] == "DETECTED")

    claude = detect_mod.detect_host({"CLAUDECODE": "1"})
    expect(
        "detect claude-code",
        claude["host"] == "claude-code" and claude["status"] == "DETECTED",
    )

    codex = detect_mod.detect_host({"CODEX_THREAD_ID": "t1"})
    expect("detect codex", codex["host"] == "codex" and codex["status"] == "DETECTED")

    conflict = detect_mod.detect_host({"GROK_AGENT": "1", "CLAUDECODE": "1"})
    expect("detect conflict", conflict["status"] == "CONFLICT" and conflict["host"] is None)

    override = detect_mod.detect_host(
        {"GROK_AGENT": "1", "SAM_GOAL_HOST": "codex"}
    )
    expect(
        "detect override",
        override["host"] == "codex" and override["status"] == "OVERRIDE",
    )

    invalid = detect_mod.detect_host({"SAM_GOAL_HOST": "nope"})
    expect("detect invalid", invalid["status"] == "INVALID")

    env = clean_env()
    env["CODEX_SANDBOX"] = "workspace"
    result = run_script("detect_host.py", [], root, env=env)
    expect("detect cli", result.returncode == 0, result.stderr)
    payload = json.loads(result.stdout)
    expect("detect cli host", payload["host"] == "codex")

    none = run_script("detect_host.py", [], root, env=clean_env())
    expect("detect cli unknown", none.returncode == 2, none.stderr)


def main() -> int:
    try:
        test_no_third_party_imports()
        with tempfile.TemporaryDirectory(prefix="sam-goal-") as temporary:
            root = Path(temporary)
            test_scaffold(root)
            test_gates(root)
            test_ledger(root)
            test_report(root)
            test_host(root)
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: sam-goal harness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
