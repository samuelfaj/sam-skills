#!/usr/bin/env python3
"""Detect the active sam-goal host from process environment only."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Mapping


HOSTS = ("claude-code", "codex", "grok")
OVERRIDE_KEYS = ("SAM_GOAL_HOST", "SAM_ACTIVE_HOST")
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
DETECT_STATUSES = ("DETECTED", "OVERRIDE", "UNKNOWN", "CONFLICT", "INVALID")


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
        return {
            "host": chosen_override,
            "status": "OVERRIDE",
            "signals": signals,
            "override": chosen_override,
            "detected_from": f"override:{chosen_override}",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=HOSTS, help="Explicit host override")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = detect_host(override=args.host)
    print(json.dumps(result, indent=2))
    if result["status"] not in DETECT_STATUSES:
        print("ERROR: unknown detector status", file=sys.stderr)
        return 2
    if result["status"] in {"DETECTED", "OVERRIDE"}:
        return 0
    print(f"ERROR: host {result['status']}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
