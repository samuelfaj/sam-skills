#!/usr/bin/env python3
"""Re-verify execution receipts and test-wiring proof without trusting the report.

Canonical shared implementation. Every skill that ships this file must ship a
byte-identical copy; the repository suite validator enforces that.

Imported by the report validators so a VALID report always implies:

- every reported PASS/FAIL is backed by a receipt from run_checked.py;
- the receipt hash and every captured log hash recompute on disk;
- the reported status, classification, and command text match the receipt;
- a PASS has exit code 0 in every recorded run;
- TARGET commands ran at least twice with identical exit codes (STABLE), so a
  flaky green cannot close a gate;
- a claimed new test is discovered by the runner only after it was added.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

MIN_TARGET_RUNS = 2
# Classifications whose green result is the proof of the reviewed change itself.
TARGET_CLASSES = {"TARGET", "INTRODUCED"}


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_receipt(raw_path: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"{label} requires a receipt path from run_checked.py")
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        errors.append(f"{label} receipt path must be absolute: {raw_path}")
        return None
    if not path.is_file():
        errors.append(f"{label} receipt file is missing: {raw_path}")
        return None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"{label} receipt is unreadable: {error}")
        return None
    if not isinstance(receipt, dict):
        errors.append(f"{label} receipt root must be an object")
        return None

    stored = receipt.get("receipt_sha256")
    recomputed = canonical_sha256({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    if stored != recomputed:
        errors.append(f"{label} receipt_sha256 does not match its content (edited receipt)")

    runs = receipt.get("runs")
    if not isinstance(runs, list) or not runs:
        errors.append(f"{label} receipt has no recorded runs")
        return receipt
    for run in runs:
        if not isinstance(run, dict):
            errors.append(f"{label} receipt run entry must be an object")
            continue
        log_path = run.get("log_path")
        if not isinstance(log_path, str) or not Path(log_path).is_file():
            errors.append(f"{label} captured log is missing: {log_path}")
            continue
        if file_sha256(Path(log_path)) != run.get("log_sha256"):
            errors.append(f"{label} captured log hash does not match: {log_path}")
    return receipt


def command_entries(commands: Any) -> list[tuple[str, dict[str, Any]]]:
    """Accept either an id-keyed table or a positional list of command records."""
    if isinstance(commands, dict):
        return [
            (str(key), value)
            for key, value in sorted(commands.items())
            if isinstance(value, dict)
        ]
    if isinstance(commands, list):
        entries: list[tuple[str, dict[str, Any]]] = []
        for index, value in enumerate(commands):
            if isinstance(value, dict):
                entries.append((str(value.get("id") or f"validations[{index}]"), value))
        return entries
    return []


def verify_commands(commands: Any, errors: list[str]) -> dict[str, Any]:
    """Verify every reported command against its receipt. Returns a summary."""
    summary: dict[str, Any] = {"verified": 0, "flaky": [], "unstable_target": []}
    if not isinstance(commands, (dict, list)):
        errors.append("commands table must be an object or array")
        return summary

    for command_id, command in command_entries(commands):
        status = command.get("status")
        classification = command.get("classification")
        reason = command.get("evidence") or command.get("reason")
        if status == "NOT_RUN":
            if command.get("receipt"):
                errors.append(f"{command_id} is NOT_RUN but cites an execution receipt")
            if not str(reason or "").strip():
                errors.append(f"{command_id} NOT_RUN requires a stated reason")
            continue

        receipt = load_receipt(command.get("receipt"), command_id, errors)
        if receipt is None:
            continue
        summary["verified"] += 1

        # Only an id-bearing record can be checked for receipt ownership; a
        # positional list entry has no id of its own to compare against.
        if command.get("id") is not None and receipt.get("id") != command.get("id"):
            errors.append(
                f"{command_id} receipt belongs to {receipt.get('id')!r}"
            )
        if receipt.get("status") != status:
            errors.append(
                f"{command_id} reports {status} but its receipt records "
                f"{receipt.get('status')}"
            )
        if receipt.get("classification") != classification:
            errors.append(
                f"{command_id} classification does not match its receipt"
            )
        argv = receipt.get("argv")
        if isinstance(argv, list) and command.get("command") != " ".join(
            str(item) for item in argv
        ):
            errors.append(
                f"{command_id} command text does not match the executed argv"
            )
        runs = receipt.get("runs") if isinstance(receipt.get("runs"), list) else []
        exit_codes = [run.get("exit_code") for run in runs if isinstance(run, dict)]
        if status == "PASS" and any(code != 0 for code in exit_codes):
            errors.append(f"{command_id} claims PASS with a non-zero recorded exit code")
        if status == "FAIL" and exit_codes and all(code == 0 for code in exit_codes):
            errors.append(f"{command_id} claims FAIL with only zero exit codes")

        determinism = receipt.get("determinism")
        if determinism == "FLAKY":
            summary["flaky"].append(command_id)
        if classification in TARGET_CLASSES and determinism != "STABLE":
            summary["unstable_target"].append(command_id)
        if classification in TARGET_CLASSES and len(exit_codes) < MIN_TARGET_RUNS:
            errors.append(
                f"{command_id} is TARGET proof and must run at least "
                f"{MIN_TARGET_RUNS} times (use run_checked.py --repeat)"
            )
    return summary


def verify_wiring(wiring: Any, errors: list[str]) -> str:
    """Prove the runner discovers each claimed new test only after it was added."""
    if not isinstance(wiring, dict):
        errors.append("test_wiring object is required")
        return "NOT_PROVEN"
    status = wiring.get("status")
    if status not in {"PROVEN", "NOT_PROVEN", "NOT_APPLICABLE"}:
        errors.append("test_wiring.status must be PROVEN, NOT_PROVEN, or NOT_APPLICABLE")
        return "NOT_PROVEN"
    if status != "PROVEN":
        if not str(wiring.get("reason") or "").strip():
            errors.append(f"test_wiring {status} requires a reason")
        return str(status)

    names = wiring.get("discovered_tests")
    if not isinstance(names, list) or not names:
        errors.append("test_wiring PROVEN requires discovered_tests")
        return "NOT_PROVEN"

    before = load_receipt(wiring.get("before_receipt"), "test_wiring.before", errors)
    after = load_receipt(wiring.get("after_receipt"), "test_wiring.after", errors)
    if before is None or after is None:
        return "NOT_PROVEN"

    def logs(receipt: dict[str, Any]) -> str:
        text = ""
        for run in receipt.get("runs", []):
            if not isinstance(run, dict):
                continue
            path = run.get("log_path")
            if isinstance(path, str) and Path(path).is_file():
                text += Path(path).read_text(encoding="utf-8", errors="replace")
        return text

    before_text = logs(before)
    after_text = logs(after)
    for name in names:
        token = str(name)
        if token in before_text:
            errors.append(
                f"test_wiring: {token!r} was already discovered before the change"
            )
        if token not in after_text:
            errors.append(
                f"test_wiring: {token!r} is not discovered by the runner after the "
                "change (test exists but never executes)"
            )
    return "PROVEN"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    args = parser.parse_args()
    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"verify_receipts: cannot read report: {error}", file=sys.stderr)
        return 2
    if not isinstance(report, dict):
        print("verify_receipts: report root must be an object", file=sys.stderr)
        return 2

    errors: list[str] = []
    # Coverage and E2E reports use `commands`; review reports use `validations`.
    if "commands" in report:
        entries = report.get("commands")
    elif "validations" in report:
        entries = report.get("validations")
    else:
        print(
            "verify_receipts: report has no commands or validations table",
            file=sys.stderr,
        )
        return 2
    summary = verify_commands(entries, errors)
    if "test_wiring" in report:
        verify_wiring(report.get("test_wiring"), errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "PASS: {verified} command receipt(s) re-verified; flaky={flaky}".format(
            verified=summary["verified"], flaky=summary["flaky"] or "none"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
