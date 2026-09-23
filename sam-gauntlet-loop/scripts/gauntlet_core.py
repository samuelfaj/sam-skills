#!/usr/bin/env python3
"""Host tables, bar checks, prompt compile, and report validation."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping


HOSTS = ("claude-code", "codex", "grok")
OVERRIDE_KEYS = ("SAM_GAUNTLET_HOST", "SAM_ACTIVE_HOST")
SIGNAL_ENV: dict[str, tuple[str, ...]] = {
    "claude-code": (
        "CLAUDECODE",
        "CLAUDE_CODE",
        "CLAUDE_PLUGIN_ROOT",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_SESSION",
    ),
    "codex": (
        "CODEX_HOME",
        "CODEX_THREAD_ID",
        "CODEX_SANDBOX",
        "CODEX_CI",
        "CODEX_TASK",
    ),
    "grok": (
        "GROK_AGENT",
        "GROK_HOME",
        "GROK_SESSION",
        "GROK_SESSION_ID",
    ),
}
FETCH_METHODS = ("screenshot", "read", "run", "open")
KINDS = ("visual", "writing", "code", "research", "other")
MODES = ("PROMPT_ONLY",)
DECISIONS = ("PROMPT_READY", "BLOCKED")
HOST_STATUSES = ("DETECTED", "OVERRIDE")
DETECT_STATUSES = ("DETECTED", "OVERRIDE", "UNKNOWN", "CONFLICT", "INVALID")
PICKS = ("ours", "bar", "unfetched")
MIN_WORDS = 80
MAX_WORDS = 220

# Per-host token semantics for the pasted session (why these tables exist):
# - claude-code: `/loop` is a quality retry on a piece until the critic picks
#   ours; `ultracode` opts the turn into a dynamic workflow; nesting is allowed.
# - codex: `max_depth` is 1, so the lead owns the loop and children never spawn
#   children; `/loop` is not a quality retry there and `ultracode` does not exist.
# - grok: `/loop` is a recurring scheduler, not a retry; there is no `ultracode`;
#   a builder that fans out its critic dies silently, so a workflow (`agent`,
#   `parallel`) must own the loop, watched at `/workflows`. An equal-choice
#   "or top-level subagents" close is forbidden. `/goal` is a weaker fallback.
# Every host: the critic is a new agent with no builder transcript, never resumed.
FORBIDDEN_IN_PROMPT: dict[str, tuple[str, ...]] = {
    "claude-code": (),
    "codex": (r"/loop\b", r"\bultracode\b"),
    "grok": (r"/loop\b", r"\bultracode\b", r"top-level subagents"),
}
REQUIRED_IN_PROMPT: dict[str, tuple[str, ...]] = {
    "claude-code": (r"/loop\b", r"\bultracode\b"),
    "codex": (r"lead owns the loop", r"fresh context"),
    "grok": (r"workflow", r"/workflows", r"owns the loop", r"Children do not spawn children"),
}
VAGUE_BAR = re.compile(
    r"\b(?:award[ -]?winning|best[ -]?in[ -]?class|world[ -]?class|"
    r"industry[ -]?leading|modern saas|good landing page|"
    r"top[- ]tier|beautiful design)\b",
    re.IGNORECASE,
)
CATEGORY_LOCATOR = re.compile(
    r"^(?:saas sites|landing pages|good (?:writing|code|design)|"
    r"the market leader|a competitor)\Z",
    re.IGNORECASE,
)
URL_SCHEME = re.compile(r"https?://", re.IGNORECASE)
COMPOUND_JOIN = re.compile(r"\splus\s|\band\s+https?://", re.IGNORECASE)

HOST_CLOSE = {
    "claude-code": (
        "/loop on each piece until the critic picks ours blind. Do not stop "
        "before that. Keep a live progress page updating as the work evolves "
        "so I can watch it. Fan out subagents and ultracode."
    ),
    "codex": (
        "Keep looping in the lead until the critic picks ours blind, or I stop "
        "the run. Spawn builders and critics as distinct agents with fresh "
        "context. The lead owns the loop. Never resume the critic from the "
        "builder."
    ),
    "grok": (
        "Keep looping until the critic picks ours blind, or I stop the run. "
        "Launch a workflow that owns the loop with agent and parallel. "
        "Children do not spawn children. Never resume the critic from the "
        "builder. Watch /workflows."
    ),
}


def word_count(text: str) -> int:
    return len(text.split())


def env_present(value: str | None) -> bool:
    return bool(value and value.strip())


def detect_host(
    environ: Mapping[str, str] | None = None,
    *,
    override: str | None = None,
) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    chosen_override = (override or "").strip()
    if not chosen_override:
        for key in OVERRIDE_KEYS:
            raw = env.get(key, "")
            if env_present(raw):
                chosen_override = raw.strip()
                break
    signals: list[dict[str, str]] = []
    for host, keys in SIGNAL_ENV.items():
        for key in keys:
            if env_present(env.get(key)):
                signals.append({"host": host, "source": f"env:{key}"})
                break
    hosts_found = sorted({item["host"] for item in signals})
    if chosen_override:
        if chosen_override not in HOSTS:
            return {
                "host": None,
                "status": "INVALID",
                "signals": signals,
                "override": chosen_override,
                "detected_from": f"override:{chosen_override}",
            }
        source = f"override:{chosen_override}"
        return {
            "host": chosen_override,
            "status": "OVERRIDE",
            "signals": signals,
            "override": chosen_override,
            "detected_from": source,
        }
    if len(hosts_found) == 1:
        match = next(item for item in signals if item["host"] == hosts_found[0])
        return {
            "host": hosts_found[0],
            "status": "DETECTED",
            "signals": signals,
            "override": None,
            "detected_from": match["source"],
        }
    if len(hosts_found) > 1:
        return {
            "host": None,
            "status": "CONFLICT",
            "signals": signals,
            "override": None,
            "detected_from": "conflict",
        }
    return {
        "host": None,
        "status": "UNKNOWN",
        "signals": signals,
        "override": None,
        "detected_from": "none",
    }


def is_compound_bar(name: str, locator: str) -> bool:
    """True when name/locator joins two artifacts a critic cannot A/B as one."""
    if len(URL_SCHEME.findall(locator)) >= 2:
        return True
    blob = f"{name} {locator}"
    return bool(COMPOUND_JOIN.search(blob))


def bar_problems(
    name: str,
    locator: str,
    fetch_method: str,
    kind: str,
) -> list[tuple[str, str]]:
    """Return (gap code, message) pairs; the code is the BLOCKED remaining item."""
    problems: list[tuple[str, str]] = []
    if not name.strip():
        problems.append(("missing_bar", "bar name must be non-empty"))
    if VAGUE_BAR.search(name):
        problems.append(("vague_bar", "bar name is vague; name a specific fetchable artifact"))
    if not locator.strip():
        problems.append(("missing_bar", "bar locator must be non-empty"))
    if CATEGORY_LOCATOR.match(locator.strip()):
        problems.append(("vague_bar", "bar locator is a category, not a fetchable artifact"))
    if is_compound_bar(name, locator):
        problems.append(
            ("compound_bar", "bar is a union of artifacts; name one comparable locator")
        )
    if fetch_method not in FETCH_METHODS:
        problems.append(
            ("bad_bar", f"fetch_method must be one of {', '.join(FETCH_METHODS)}")
        )
    if kind not in KINDS:
        problems.append(("bad_bar", f"kind must be one of {', '.join(KINDS)}"))
    return problems


def bar_errors(
    name: str,
    locator: str,
    fetch_method: str,
    kind: str,
) -> list[str]:
    return [message for _, message in bar_problems(name, locator, fetch_method, kind)]


def compile_prompt(
    *,
    host: str,
    goal: str,
    bar_name: str,
    bar_locator: str,
    fetch_method: str,
    kind: str,
    budget: str | None = None,
) -> dict[str, Any]:
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    if not goal.strip():
        raise ValueError("goal must be non-empty")
    problems = bar_errors(bar_name, bar_locator, fetch_method, kind)
    if problems:
        raise ValueError("; ".join(problems))
    fetch_line = {
        "screenshot": "Screenshot it at the same viewport and compare against those captures directly, not against a description of them.",
        "read": "Read the real piece and compare against that text directly, not against a description of it.",
        "run": "Run the real reference and compare against that output or benchmark directly, not against a description of it.",
        "open": "Open the real artifact and compare against it directly, not against a description of it.",
    }[fetch_method]
    budget_line = ""
    if budget and budget.strip():
        budget_line = f" Stay inside this ceiling: {budget.strip()}."
    prompt = (
        f"Build {goal.strip()}. "
        f"The bar is {bar_name.strip()} ({bar_locator.strip()}). "
        f"Get the real thing first. {fetch_line} "
        "Break this into the smallest pieces that can be improved and judged "
        "on their own. For each piece, fan out a builder and a separate critic "
        "with fresh context. The critic inspects the actual output, puts it "
        "next to the bar blind with the labels stripped, says which one is "
        "better, and names the single biggest remaining gap. Then it goes "
        "back to the builder. "
        "The critic should be a harsh critic. Praise is not useful. If ours "
        f"does not win, it keeps going.{budget_line} "
        f"{HOST_CLOSE[host]}"
    )
    token_errors = prompt_token_errors(host, prompt)
    if token_errors:
        raise ValueError("; ".join(token_errors))
    count = word_count(prompt)
    if count < MIN_WORDS or count > MAX_WORDS:
        raise ValueError(f"compiled prompt has {count} words; need {MIN_WORDS}-{MAX_WORDS}")
    return {
        "host": host,
        "goal": goal.strip(),
        "bar": {
            "name": bar_name.strip(),
            "locator": bar_locator.strip(),
            "fetch_method": fetch_method,
            "kind": kind,
        },
        "budget": budget.strip() if budget and budget.strip() else None,
        "prompt": prompt,
        "word_count": count,
    }


def prompt_token_errors(host: str, prompt: str) -> list[str]:
    errors: list[str] = []
    if host not in HOSTS:
        return [f"unsupported host: {host}"]
    for pattern in FORBIDDEN_IN_PROMPT[host]:
        if re.search(pattern, prompt, re.IGNORECASE):
            errors.append(f"{host} prompt contains forbidden token matching {pattern}")
    for pattern in REQUIRED_IN_PROMPT[host]:
        if not re.search(pattern, prompt, re.IGNORECASE):
            errors.append(f"{host} prompt missing required token matching {pattern}")
    return errors


def bind_host(
    host: str,
    environ: Mapping[str, str] | None = None,
    *,
    user_host: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Re-detect from process env; return the report host object and any gaps."""
    found = detect_host(environ)
    status = found["status"]
    if status in HOST_STATUSES:
        bound = {"key": found["host"], "status": status, "detected_from": found["detected_from"]}
        if found["host"] != host:
            return bound, [f"host_mismatch: --host {host} but env binds {found['host']}"]
        return bound, []
    if user_host and host in HOSTS:
        return {"key": host, "status": "OVERRIDE", "detected_from": f"user:{host}"}, []
    gap = f"host_{status.lower()}: needs the user's host choice (--user-host)"
    return {"key": None, "status": status, "detected_from": found["detected_from"]}, [gap]


def build_report(
    *,
    host: str,
    goal: str,
    bar_name: str,
    bar_locator: str,
    fetch_method: str,
    kind: str,
    budget: str | None = None,
    user_host: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build the PROMPT_ONLY report: PROMPT_READY with a prompt, or BLOCKED with gaps."""
    if not goal.strip():
        raise ValueError("goal must be non-empty")
    host_obj, gaps = bind_host(host, environ, user_host=user_host)
    gaps += [
        f"{code}: {message}"
        for code, message in bar_problems(bar_name, bar_locator, fetch_method, kind)
    ]
    prompt = ""
    if not gaps:
        try:
            prompt = compile_prompt(
                host=host,
                goal=goal,
                bar_name=bar_name,
                bar_locator=bar_locator,
                fetch_method=fetch_method,
                kind=kind,
                budget=budget,
            )["prompt"]
        except ValueError as error:
            gaps.append(f"prompt_invalid: {error}")
    return {
        "schema_version": 1,
        "goal": goal.strip(),
        "bar": {
            "name": bar_name.strip(),
            "locator": bar_locator.strip(),
            "fetch_method": fetch_method,
            "kind": kind,
        },
        "host": host_obj,
        "mode": "PROMPT_ONLY",
        "prompt": prompt,
        "pieces": [],
        "rounds": [],
        "decision": {
            "result": "BLOCKED" if gaps else "PROMPT_READY",
            "critic_pick": None,
            "remaining": gaps,
        },
    }


def require_keys(
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
    label: str,
    errors: list[str],
) -> None:
    missing = sorted(required - value.keys())
    extra = sorted(value.keys() - allowed)
    if missing:
        errors.append(f"{label} missing keys: {', '.join(missing)}")
    if extra:
        errors.append(f"{label} has unsupported keys: {', '.join(extra)}")


def nonempty_string(value: Any, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    return value


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report root must be an object"]
    keys = {"schema_version", "goal", "bar", "host", "mode", "prompt", "pieces", "rounds", "decision"}
    require_keys(report, keys, keys, "report", errors)
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    nonempty_string(report.get("goal"), "goal", errors)
    if report.get("mode") not in MODES:
        errors.append(f"mode must be one of {', '.join(MODES)}")

    decision = report.get("decision")
    result = ""
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
    else:
        fields = {"result", "critic_pick", "remaining"}
        require_keys(decision, fields, fields, "decision", errors)
        result = str(decision.get("result", ""))
        if result not in DECISIONS:
            errors.append(f"decision.result must be one of {', '.join(DECISIONS)}")
        pick = decision.get("critic_pick")
        if pick is not None and pick not in PICKS:
            errors.append("decision.critic_pick must be ours, bar, unfetched, or null")
        remaining = decision.get("remaining")
        if not isinstance(remaining, list) or any(
            not isinstance(item, str) or not item.strip() for item in remaining
        ):
            errors.append("decision.remaining must be a list of non-empty strings")
            remaining = []
        if result == "BLOCKED" and not remaining:
            errors.append("BLOCKED requires a concrete remaining item")
        if pick == "unfetched" and result != "BLOCKED":
            errors.append("unfetched bar must be BLOCKED")
    # BLOCKED ships nothing to paste; anything else must be a fully valid prompt.
    blocked = result == "BLOCKED"

    prompt = report.get("prompt")
    if blocked:
        if prompt != "":
            errors.append("BLOCKED requires an empty prompt")
        prompt = ""
    else:
        prompt = nonempty_string(prompt, "prompt", errors)

    bar = report.get("bar")
    if not isinstance(bar, dict):
        errors.append("bar must be an object")
    else:
        fields = {"name", "locator", "fetch_method", "kind"}
        require_keys(bar, fields, fields, "bar", errors)
        if any(not isinstance(bar.get(field, ""), str) for field in fields):
            errors.append("bar fields must be strings")
        elif not blocked:
            errors.extend(
                bar_errors(
                    bar.get("name", ""),
                    bar.get("locator", ""),
                    bar.get("fetch_method", ""),
                    bar.get("kind", ""),
                )
            )

    host = report.get("host")
    if not isinstance(host, dict):
        errors.append("host must be an object")
    else:
        fields = {"key", "status", "detected_from"}
        require_keys(host, fields, fields, "host", errors)
        status = host.get("status")
        host_key = host.get("key")
        nonempty_string(host.get("detected_from"), "host.detected_from", errors)
        if status not in DETECT_STATUSES:
            errors.append(f"host.status must be one of {', '.join(DETECT_STATUSES)}")
        elif status in HOST_STATUSES:
            if host_key not in HOSTS:
                errors.append("host.key must be a supported host")
        elif host_key is not None:
            errors.append("host.key must be null unless status is DETECTED or OVERRIDE")
        if not blocked:
            if status not in HOST_STATUSES:
                errors.append("host.status must be DETECTED or OVERRIDE")
            if host_key in HOSTS and prompt:
                errors.extend(prompt_token_errors(host_key, prompt))
                count = word_count(prompt)
                if count < MIN_WORDS or count > MAX_WORDS:
                    errors.append(
                        f"prompt has {count} words; need {MIN_WORDS}-{MAX_WORDS}"
                    )

    pieces = report.get("pieces")
    rounds = report.get("rounds")
    for label, value in (("pieces", pieces), ("rounds", rounds)):
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            errors.append(f"{label} must be a list of objects")
    if pieces or rounds:
        errors.append("PROMPT_ONLY must keep pieces and rounds empty")
    return errors


def load_json_object(path_text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"cannot parse {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value
