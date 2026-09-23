#!/usr/bin/env python3
"""Exercise host detection, prompt compile, and report validation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent
DETECT = SCRIPT_DIR / "detect_host.py"
COMPILE = SCRIPT_DIR / "compile_prompt.py"
VALIDATE = SCRIPT_DIR / "validate_gauntlet.py"
SUITE = REPO_ROOT / "scripts" / "validate_skill_suite.py"

from gauntlet_core import (
    build_report,
    compile_prompt,
    detect_host,
    is_compound_bar,
    validate_report,
)

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
    if "owns the loop" not in grok["prompt"]:
        raise AssertionError("grok prompt must make a workflow the lead")
    if "Children do not spawn children" not in grok["prompt"]:
        raise AssertionError("grok prompt must keep children as leaves")
    if "top-level subagents" in grok["prompt"]:
        raise AssertionError("grok prompt must not offer subagents as an equal path")

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


def test_compile_rejects_compound_bar() -> None:
    """Why: a critic cannot A/B two products as one pick."""
    if not is_compound_bar(
        "live desktop app plus a second product",
        "https://example.com/app",
    ):
        raise AssertionError("name joined with plus must be compound")
    if not is_compound_bar(
        "live desktop app",
        "window com.example.app and https://github.com/example/mode",
    ):
        raise AssertionError("locator joining a window and a URL must be compound")
    if not is_compound_bar(
        "two sites",
        "https://example.com/a and https://example.com/b",
    ):
        raise AssertionError("two URLs must be compound")
    if is_compound_bar(
        "Nike current running campaign page",
        "https://www.nike.com/running",
    ):
        raise AssertionError("single named page must not be compound")
    env = clean_env()
    result = run(
        [
            sys.executable,
            "-B",
            str(COMPILE),
            "--host",
            "grok",
            "--goal",
            "bots with a configurable settings surface",
            "--bar-name",
            "live desktop app plus a second product",
            "--bar-locator",
            "app window com.example.app and https://github.com/example/mode",
            "--fetch-method",
            "screenshot",
            "--kind",
            "visual",
        ],
        env,
    )
    if result.returncode == 0:
        raise AssertionError("compound bar must not compile")
    if "union" not in result.stderr.lower() and "compound" not in result.stderr.lower():
        raise AssertionError(f"compound-bar failure was unclear: {result.stderr}")


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
    if "does not launch a run or save a workflow" not in text.lower():
        raise AssertionError("skill must say paste does not launch or save a workflow")
    if "compound" not in text.lower():
        raise AssertionError("skill must reject a compound bar")


def compile_cli(env: dict[str, str], *extra: str, bar: str = "Nike current running campaign page") -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-B",
            str(COMPILE),
            "--host",
            "grok",
            "--goal",
            "a landing page for a running brand, athletic, green and dark",
            "--bar-name",
            bar,
            "--bar-locator",
            "https://www.nike.com/running",
            "--fetch-method",
            "screenshot",
            "--kind",
            "visual",
            *extra,
        ],
        env,
    )


def test_blocked_reports_validate() -> None:
    """Why: a BLOCKED return must validate honestly, or agents fabricate a host, bar, or prompt."""
    unknown = build_report(
        host="grok",
        goal="a pricing page",
        bar_name="Stripe pricing page",
        bar_locator="https://stripe.com/pricing",
        fetch_method="screenshot",
        kind="visual",
        environ={},
    )
    if unknown["decision"]["result"] != "BLOCKED" or unknown["prompt"] != "":
        raise AssertionError(f"UNKNOWN host must block with no prompt: {unknown}")
    if not unknown["decision"]["remaining"][0].startswith("host_unknown"):
        raise AssertionError(f"host_unknown gap missing: {unknown['decision']}")
    # Why: under a parent the gap lands in the parent's open items, and a child must not ask.
    if "ask" in unknown["decision"]["remaining"][0].lower():
        raise AssertionError(f"host gap tells a child to ask: {unknown['decision']}")
    errors = validate_report(unknown)
    if errors:
        raise AssertionError(f"host_unknown BLOCKED report rejected: {errors}")

    vague = build_report(
        host="grok",
        goal="a pricing page",
        bar_name="award-winning SaaS sites",
        bar_locator="saas sites",
        fetch_method="screenshot",
        kind="visual",
        environ={"GROK_AGENT": "1"},
    )
    codes = [item.split(":", 1)[0] for item in vague["decision"]["remaining"]]
    if vague["decision"]["result"] != "BLOCKED" or "vague_bar" not in codes:
        raise AssertionError(f"vague bar must block with vague_bar: {vague['decision']}")
    errors = validate_report(vague)
    if errors:
        raise AssertionError(f"vague_bar BLOCKED report rejected: {errors}")


def test_blocked_and_ready_stay_fail_closed() -> None:
    """Why: relaxing BLOCKED must not let a gapless block, a blocked prompt, or a guessed host through."""
    empty_gap = build_report(
        host="grok",
        goal="a pricing page",
        bar_name="Stripe pricing page",
        bar_locator="https://stripe.com/pricing",
        fetch_method="screenshot",
        kind="visual",
        environ={},
    )
    empty_gap["decision"]["remaining"] = []
    if not any("concrete remaining" in item for item in validate_report(empty_gap)):
        raise AssertionError("BLOCKED without a gap was accepted")

    leaked = prompt_only_report("grok")
    leaked["decision"]["result"] = "BLOCKED"
    leaked["decision"]["remaining"] = ["vague_bar: example"]
    if not any("empty prompt" in item for item in validate_report(leaked)):
        raise AssertionError("BLOCKED report carrying a paste-ready prompt was accepted")

    guessed = prompt_only_report("grok")
    guessed["host"] = {"key": None, "status": "UNKNOWN", "detected_from": "none"}
    if not any("DETECTED or OVERRIDE" in item for item in validate_report(guessed)):
        raise AssertionError("PROMPT_READY with an UNKNOWN host was accepted")

    vague = prompt_only_report("grok")
    vague["bar"]["name"] = "award-winning SaaS sites"
    if not any("vague" in item for item in validate_report(vague)):
        raise AssertionError("PROMPT_READY with a vague bar was accepted")


def test_compile_cli_self_validates_report() -> None:
    """Why: the compiler owns the report, so no hand-copied prompt can drift from what was checked."""
    env = clean_env()
    env["GROK_AGENT"] = "1"
    with tempfile.TemporaryDirectory(prefix="sam-gauntlet-") as temporary:
        saved = Path(temporary) / "report.json"
        result = compile_cli(env, "--report", str(saved))
        if result.returncode != 0:
            raise AssertionError(f"compile failed: {result.stderr}")
        lines = result.stdout.strip().splitlines()
        if lines[-1] != "VALID PROMPT_READY host=grok (DETECTED)":
            raise AssertionError(f"compile status line wrong: {lines[-1]}")
        if "/workflows" not in result.stdout:
            raise AssertionError("compile did not print the grok prompt")
        check = run([sys.executable, "-B", str(VALIDATE), str(saved)], clean_env())
        if check.returncode != 0 or check.stdout.strip() != "VALID PROMPT_READY":
            raise AssertionError(f"saved report invalid: {check.stdout}{check.stderr}")


def test_compile_cli_binds_host_from_env() -> None:
    """Why: --host is a claim; env detection decides, and only a user answer binds an UNKNOWN host."""
    mismatch = clean_env()
    mismatch["CLAUDECODE"] = "1"
    result = compile_cli(mismatch)
    if result.returncode == 0 or "host_mismatch" not in result.stderr:
        raise AssertionError(f"--host disagreeing with env compiled: {result.stdout}{result.stderr}")
    if "/workflows" in result.stdout:
        raise AssertionError("blocked compile printed a prompt")

    with tempfile.TemporaryDirectory(prefix="sam-gauntlet-") as temporary:
        blocked = Path(temporary) / "blocked.json"
        result = compile_cli(clean_env(), "--report", str(blocked))
        if result.returncode == 0 or "host_unknown" not in result.stdout:
            raise AssertionError(f"UNKNOWN host compiled: {result.stdout}{result.stderr}")
        check = run([sys.executable, "-B", str(VALIDATE), str(blocked)], clean_env())
        if check.returncode != 0 or check.stdout.strip() != "VALID BLOCKED":
            raise AssertionError(f"BLOCKED report invalid: {check.stdout}{check.stderr}")

        answered = Path(temporary) / "answered.json"
        result = compile_cli(clean_env(), "--user-host", "--report", str(answered))
        if result.returncode != 0:
            raise AssertionError(f"user-bound host failed: {result.stderr}")
        host = json.loads(answered.read_text(encoding="utf-8"))["host"]
        if host != {"key": "grok", "status": "OVERRIDE", "detected_from": "user:grok"}:
            raise AssertionError(f"user-bound host recorded wrong: {host}")


def test_compile_cli_refuses_report_inside_repo() -> None:
    """Why: temporary reports stay outside the repository; a typed rule alone let one land in it."""
    env = clean_env()
    env["GROK_AGENT"] = "1"
    with tempfile.TemporaryDirectory(prefix="sam-gauntlet-") as temporary:
        repo = Path(temporary)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        inside = repo / "report.json"
        command = [sys.executable, "-B", str(COMPILE), "--host", "grok", "--goal", "a landing page",
                   "--bar-name", "Nike current running campaign page", "--bar-locator",
                   "https://www.nike.com/running", "--fetch-method", "screenshot", "--kind", "visual",
                   "--report", str(inside)]
        result = subprocess.run(command, cwd=repo, env=env, text=True, capture_output=True, check=False)
        if result.returncode != 2 or "outside the repository" not in result.stderr or inside.exists():
            raise AssertionError(f"report inside the repo was written: {result.returncode} {result.stderr}")
        # Why: a caller whose cwd is outside the repo must not land a report in it either.
        with tempfile.TemporaryDirectory(prefix="sam-gauntlet-cwd-") as outside:
            result = subprocess.run(command, cwd=outside, env=env, text=True, capture_output=True, check=False)
        if result.returncode != 2 or "outside the repository" not in result.stderr or inside.exists():
            raise AssertionError(f"report path inside a repo was written from outside it: {result.returncode} {result.stderr}")


def test_compile_cli_reports_unwritable_report_path() -> None:
    """Why: a bad --report path must fail as one ERROR line with nothing printed as VALID, not a traceback."""
    env = clean_env()
    env["GROK_AGENT"] = "1"
    with tempfile.TemporaryDirectory(prefix="sam-gauntlet-") as temporary:
        missing = Path(temporary) / "nope" / "report.json"
        result = compile_cli(env, "--report", str(missing))
        if result.returncode != 2 or "ERROR: cannot write --report" not in result.stderr:
            raise AssertionError(f"unwritable report path not reported: {result.returncode} {result.stderr}")
        if "Traceback" in result.stderr or "VALID" in result.stdout or missing.exists():
            raise AssertionError(f"unwritable report path leaked output: {result.stdout}{result.stderr}")


def test_cli_validate_and_suite_accept_package() -> None:
    """Why: this package must stay valid even if a sibling skill is dirty."""
    report = prompt_only_report("grok")
    with tempfile.TemporaryDirectory(prefix="sam-gauntlet-") as temporary:
        path = Path(temporary) / "report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        result = run([sys.executable, "-B", str(VALIDATE), str(path)], clean_env())
        if result.returncode != 0:
            raise AssertionError(f"validator cli failed: {result.stderr}")
    sys.path.insert(0, str(SUITE.parent))
    import validate_skill_suite as suite_mod

    skill = suite_mod.load_skill(SKILL_DIR)
    errors: list[str] = []
    suite_mod.validate_frontmatter(skill, errors)
    suite_mod.validate_layout(skill, errors)
    suite_mod.validate_agent_metadata(skill, errors)
    suite_mod.validate_references(skill, errors)
    suite_mod.validate_scripts(skill, errors)
    suite_mod.validate_links(skill, errors)
    suite_mod.validate_portability(skill, errors)
    if errors:
        raise AssertionError(f"skill suite rejected package: {errors}")


def main() -> int:
    tests = [
        test_detects_each_host_from_process_env,
        test_override_wins_and_conflict_is_loud,
        test_home_directory_presence_is_ignored,
        test_compile_binds_host_safe_tokens,
        test_compile_cli_rejects_vague_bar,
        test_compile_rejects_compound_bar,
        test_report_validator_accepts_prompt_only_and_rejects_run,
        test_unfetched_bar_cannot_be_ready,
        test_blocked_reports_validate,
        test_blocked_and_ready_stay_fail_closed,
        test_compile_cli_self_validates_report,
        test_compile_cli_binds_host_from_env,
        test_compile_cli_refuses_report_inside_repo,
        test_compile_cli_reports_unwritable_report_path,
        test_skill_returns_prompt_and_does_not_start,
        test_cli_validate_and_suite_accept_package,
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} gauntlet harness checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
