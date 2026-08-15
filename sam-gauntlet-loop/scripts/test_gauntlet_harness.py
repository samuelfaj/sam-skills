#!/usr/bin/env python3
"""Exercise host detection, prompt compile, and report validation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent
DETECT = SCRIPT_DIR / "detect_host.py"
COMPILE = SCRIPT_DIR / "compile_prompt.py"
VALIDATE = SCRIPT_DIR / "validate_gauntlet.py"
SUITE = REPO_ROOT / "scripts" / "validate_skill_suite.py"

from gauntlet_core import compile_prompt, detect_host, validate_report

CLEAR_KEYS = (
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
    "SAM_GAUNTLET_HOST",
    "SAM_ACTIVE_HOST",
)


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in CLEAR_KEYS:
        env.pop(key, None)
    return env


def run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=SKILL_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def compiled_prompt(host: str) -> dict[str, Any]:
    return compile_prompt(
        host=host,
        goal="a landing page for a running brand, athletic, green and dark",
        bar_name="Nike current running campaign page",
        bar_locator="https://www.nike.com/running",
        fetch_method="screenshot",
        kind="visual",
    )


def prompt_only_report(host: str, *, status: str = "DETECTED") -> dict[str, Any]:
    compiled = compiled_prompt(host)
    return {
        "schema_version": 1,
        "goal": compiled["goal"],
        "bar": compiled["bar"],
        "host": {
            "key": host,
            "status": status,
            "detected_from": f"env:probe-{host}",
        },
        "mode": "PROMPT_ONLY",
        "prompt": compiled["prompt"],
        "pieces": [],
        "rounds": [],
        "decision": {
            "result": "PROMPT_READY",
            "critic_pick": None,
            "remaining": [],
        },
    }


def run_report(host: str) -> dict[str, Any]:
    report = prompt_only_report(host)
    report["mode"] = "RUN"
    report["pieces"] = [
        {"id": "hero", "name": "hero", "critic_pick": "ours"},
    ]
    report["rounds"] = [
        {
            "index": 1,
            "piece_id": "hero",
            "critic_pick": "bar",
            "gap": "motion is dead",
            "gap_fingerprint": "motion-dead",
        },
        {
            "index": 2,
            "piece_id": "hero",
            "critic_pick": "ours",
            "gap": "",
            "gap_fingerprint": "won",
        },
    ]
    report["decision"] = {
        "result": "WON",
        "critic_pick": "ours",
        "remaining": [],
    }
    return report


def expect_detect(env: dict[str, str], host: str, status: str) -> None:
    result = run([sys.executable, "-B", str(DETECT)], env)
    if result.returncode != 0:
        raise AssertionError(f"detect failed: {result.stderr}")
    payload = json.loads(result.stdout)
    if payload["host"] != host or payload["status"] != status:
        raise AssertionError(f"expected {status}/{host}, got {payload}")


def test_detects_each_host_from_process_env() -> None:
    mapping = {
        "GROK_AGENT": ("grok", "1"),
        "CLAUDECODE": ("claude-code", "1"),
        "CODEX_THREAD_ID": ("codex", "thread-1"),
    }
    for key, (host, value) in mapping.items():
        env = clean_env()
        env[key] = value
        expect_detect(env, host, "DETECTED")


def test_override_wins_and_conflict_is_loud() -> None:
    env = clean_env()
    env["GROK_AGENT"] = "1"
    env["SAM_GAUNTLET_HOST"] = "codex"
    expect_detect(env, "codex", "OVERRIDE")

    conflict = clean_env()
    conflict["GROK_AGENT"] = "1"
    conflict["CLAUDECODE"] = "1"
    result = run([sys.executable, "-B", str(DETECT)], conflict)
    if result.returncode == 0:
        raise AssertionError("conflicting hosts must fail closed")
    payload = json.loads(result.stdout)
    if payload["status"] != "CONFLICT" or payload["host"] is not None:
        raise AssertionError(f"conflict not reported: {payload}")

    unknown = run([sys.executable, "-B", str(DETECT)], clean_env())
    if unknown.returncode == 0:
        raise AssertionError("missing host signals must fail closed")
    if json.loads(unknown.stdout)["status"] != "UNKNOWN":
        raise AssertionError("missing signals must be UNKNOWN")


def test_home_directory_presence_is_ignored() -> None:
    """Why: all three clients can exist on disk; files are not a host signal."""
    env = clean_env()
    env["HOME"] = str(Path.home())
    result = detect_host(env)
    if result["status"] != "UNKNOWN":
        raise AssertionError(f"home-directory clients leaked into detect: {result}")


def test_compile_binds_host_safe_tokens() -> None:
    grok = compiled_prompt("grok")
    if "/loop" in grok["prompt"] or "ultracode" in grok["prompt"].lower():
        raise AssertionError("grok prompt must not carry foreign orchestration tokens")
    if "/workflows" not in grok["prompt"] or "workflow" not in grok["prompt"]:
        raise AssertionError("grok prompt must name the host workflow path")

    claude = compiled_prompt("claude-code")
    if "/loop" not in claude["prompt"] or "ultracode" not in claude["prompt"]:
        raise AssertionError("claude-code prompt must opt into native loop + workflow")

    codex = compiled_prompt("codex")
    if "/loop" in codex["prompt"] or "ultracode" in codex["prompt"].lower():
        raise AssertionError("codex prompt must not carry foreign orchestration tokens")
    if "lead owns the loop" not in codex["prompt"]:
        raise AssertionError("codex prompt must keep the loop on the lead")


def test_compile_cli_rejects_vague_bar() -> None:
    env = clean_env()
    result = run(
        [
            sys.executable,
            "-B",
            str(COMPILE),
            "--host",
            "grok",
            "--goal",
            "a pricing page",
            "--bar-name",
            "award-winning SaaS sites",
            "--bar-locator",
            "saas sites",
            "--fetch-method",
            "screenshot",
            "--kind",
            "visual",
        ],
        env,
    )
    if result.returncode == 0:
        raise AssertionError("vague bar must not compile")
    if "vague" not in result.stderr.lower() and "category" not in result.stderr.lower():
        raise AssertionError(f"vague-bar failure was unclear: {result.stderr}")


def test_report_validator_accepts_prompt_only_and_rejects_run() -> None:
    """Why: this skill returns a paste-ready prompt; a RUN report means it started."""
    for host in ("grok", "codex", "claude-code"):
        errors = validate_report(prompt_only_report(host))
        if errors:
            raise AssertionError(f"{host} prompt report invalid: {errors}")
        errors = validate_report(run_report(host))
        if not any("mode must be" in item for item in errors):
            raise AssertionError(f"{host} RUN report was accepted: {errors}")

    grok_with_loop = prompt_only_report("grok")
    grok_with_loop["prompt"] = grok_with_loop["prompt"] + " /loop until perfect ultracode"
    errors = validate_report(grok_with_loop)
    if not any("forbidden token" in item for item in errors):
        raise AssertionError(f"foreign /loop on grok was accepted: {errors}")


def test_unfetched_bar_cannot_be_ready() -> None:
    report = prompt_only_report("claude-code")
    report["decision"]["critic_pick"] = "unfetched"
    errors = validate_report(report)
    if not any("unfetched" in item for item in errors):
        raise AssertionError(f"unfetched bar treated as ready: {errors}")


def test_skill_returns_prompt_and_does_not_start() -> None:
    """Why: the user copies, edits, and pastes; starting here skips that."""
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    if "I can run this here" in text or "Run only when asked" in text:
        raise AssertionError("skill must not offer or start a run")
    if "never start the loop" not in text.lower():
        raise AssertionError("skill must forbid starting the loop")
    if "copy, edit, and paste" not in text.lower():
        raise AssertionError("skill must return a paste-ready prompt")


def test_cli_validate_and_suite_accept_package() -> None:
    report = prompt_only_report("grok")
    path = SCRIPT_DIR / "_tmp_report.json"
    try:
        path.write_text(json.dumps(report), encoding="utf-8")
        result = run([sys.executable, "-B", str(VALIDATE), str(path)], clean_env())
        if result.returncode != 0:
            raise AssertionError(f"validator cli failed: {result.stderr}")
    finally:
        if path.exists():
            path.unlink()
    suite = run([sys.executable, "-B", str(SUITE), str(REPO_ROOT)], clean_env())
    if suite.returncode != 0:
        raise AssertionError(f"skill suite rejected package: {suite.stderr}")


def main() -> int:
    tests = [
        test_detects_each_host_from_process_env,
        test_override_wins_and_conflict_is_loud,
        test_home_directory_presence_is_ignored,
        test_compile_binds_host_safe_tokens,
        test_compile_cli_rejects_vague_bar,
        test_report_validator_accepts_prompt_only_and_rejects_run,
        test_unfetched_bar_cannot_be_ready,
        test_skill_returns_prompt_and_does_not_start,
        test_cli_validate_and_suite_accept_package,
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} gauntlet harness checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
