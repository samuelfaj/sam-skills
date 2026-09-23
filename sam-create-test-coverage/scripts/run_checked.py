#!/usr/bin/env python3
"""Run a validation command and emit a re-verifiable execution receipt.

Canonical shared implementation. Every skill that ships this file must ship a
byte-identical copy; the repository suite validator enforces that.

A reported PASS must be derived from a receipt, never asserted. The receipt
records argv, cwd, exit code per run, and the SHA-256 of the captured output so
a validator can recompute both without trusting the caller.

Use --repeat to prove determinism: differing exit codes across runs mark the
command FLAKY, which is not proof.

Stdout is one JSON line: receipt, id, status, determinism, exit_codes, command
(the exact argv text a report must cite). The full receipt is written to disk.
On FAIL, stderr also carries a capped, best-effort secret-redacted tail of the
first failing run's log; the log file itself stays complete and unredacted.
Logs: <receipts-dir>/<id>.run<N>.log (N = 1..repeat), next to <id>.receipt.json.

Exit status: 0 when a receipt was written (regardless of the wrapped command's
result), 2 when the receipt could not be produced. Pass --expect-pass to instead
mirror a failing command as exit 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_LOG_BYTES = 4 * 1024 * 1024
CLASSIFICATIONS = ("TARGET", "INTRODUCED", "BASELINE", "ENVIRONMENT", "EXTERNAL")
TAIL_WINDOW_BYTES = 64 * 1024
TAIL_MAX_LINES = 40
TAIL_MAX_CHARS = 4096
REDACTED = "[REDACTED]"
# Group 1 of each rule is kept and the rest of the match becomes REDACTED. Rules
# apply in order, so whole-value shapes run before the generic key=value rule.
# Bounded repeats keep a long single line from making a rule quadratic.
SECRET_RULES = tuple(
    re.compile(pattern)
    for pattern in (
        r"(?s)()-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----.*?"
        r"(?:-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----|\Z)",
        r"(?s)\A().*?-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----",
        r"(?i)(authorization[\"']?\s*[:=]\s*)[^\r\n]+",
        r"(?i)((?:set-)?cookie[\"']?\s*[:=]\s*)[^\r\n]+",
        r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{16,}",
        r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://[^/\s:@]*:)[^@\s]{1,256}(?=@)",
        r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^/\s:@]{20,256}(?=@)",
        r"(?m)((?:^|\s)(?:-u|--user)[ \t=]*[^:\s=][^:\s]*:)\S+",
        r"(?i)(\b(?:mysql(?:dump|admin)?|mariadb)\b[^\r\n]{0,256}?\s-p)\S+",
        r"(?i)(--(?:pass\b|passphrase|password|passwd|token|secret|api[_-]?key)[\w-]{0,64}"
        r"[= \t]+)\S+",
        r"()\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|(?:xox[abprs]|xapp)-[\w-]{10,}"
        r"|(?:AKIA|ASIA)[0-9A-Z]{16}|sk-[\w-]{20,}|[rs]k_(?:live|test)_[A-Za-z0-9]{10,}"
        r"|glpat-[\w-]{20,}|npm_[A-Za-z0-9]{20,}|AIza[\w-]{30,}|whsec_[A-Za-z0-9+/=]{20,}"
        r"|hf_[A-Za-z0-9]{30,}|pypi-AgE[\w-]{20,}|hooks\.slack\.com/services/[\w/]+"
        r"|(?<![\w-])eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,})",
        # An unquoted value runs to the end of the line: it may contain spaces.
        r"(?i)((?:api[_-]?key|secret|token|password|passwd|passphrase|[_-]pass\b"
        r"|\bpass(?=\s*=)|pwd|credentials?|session[_-]?id|private[_-]?key|key-data)[\w-]{0,64}"
        r"[\"']?\s*(?:=>|[:=])\s*)(?:\"(?:[^\"\\\r\n]|\\.)*\"|'(?:[^'\\\r\n]|\\.)*'|[^\r\n]+)",
    )
)


def canonical_sha256(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute(argv: list[str], cwd: Path, log_path: Path) -> dict[str, Any]:
    started = time.monotonic()
    truncated = False
    written = 0
    with log_path.open("wb") as sink:
        process = subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.read(65536), b""):
            if written >= MAX_LOG_BYTES:
                truncated = True
                continue
            room = MAX_LOG_BYTES - written
            sink.write(chunk[:room])
            written += min(len(chunk), room)
        exit_code = process.wait()
    return {
        "exit_code": exit_code,
        "log_path": str(log_path),
        "log_sha256": file_sha256(log_path),
        "log_bytes": written,
        "truncated": truncated,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def build_receipt(args: argparse.Namespace, argv: list[str]) -> dict[str, Any]:
    receipts_dir = Path(args.receipts_dir).resolve()
    receipts_dir.mkdir(parents=True, exist_ok=True)
    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()
    if not cwd.is_dir():
        raise ValueError(f"working directory does not exist: {cwd}")

    runs: list[dict[str, Any]] = []
    for sequence in range(1, args.repeat + 1):
        log_path = receipts_dir / f"{args.id}.run{sequence}.log"
        record = execute(argv, cwd, log_path)
        record["sequence"] = sequence
        runs.append(record)

    exit_codes = {run["exit_code"] for run in runs}
    if len(runs) == 1:
        determinism = "SINGLE_RUN"
    elif len(exit_codes) == 1:
        determinism = "STABLE"
    else:
        determinism = "FLAKY"

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "id": args.id,
        "label": args.label or " ".join(argv),
        "argv": argv,
        "cwd": str(cwd),
        "classification": args.classification,
        "repeat_requested": args.repeat,
        "runs": runs,
        "status": "PASS" if exit_codes == {0} else "FAIL",
        "determinism": determinism,
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def redact(text: str) -> str:
    for pattern in SECRET_RULES:
        text = pattern.sub(lambda match: match.group(1) + REDACTED, text)
    return text


def failure_tail(run: dict[str, Any]) -> str:
    """Last lines of a failing run's log, redacted before capping.

    Redaction runs on whole lines only: a line cut by the read window could hide
    the key that marks its value as secret, so it is dropped.
    """
    path = Path(run["log_path"])
    size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(max(0, size - TAIL_WINDOW_BYTES))
        text = handle.read().decode("utf-8", errors="replace")
    lines = text.splitlines()
    if size > TAIL_WINDOW_BYTES and lines:
        lines = lines[1:]
    body = redact("\n".join(lines))
    body = "\n".join(body.splitlines()[-TAIL_MAX_LINES:])[-TAIL_MAX_CHARS:]
    note = "; capture truncated at the log cap" if run.get("truncated") else ""
    header = (
        f"run_checked: FAIL run {run['sequence']} exit {run['exit_code']}{note}; "
        f"best-effort redacted tail (max {TAIL_MAX_LINES} lines/{TAIL_MAX_CHARS} chars) "
        f"of {path}; verify before quoting:"
    )
    if size == 0:
        body = "(log is empty)"
    elif not body.strip():
        body = "(only blank lines in the tail)" if lines else (
            "(no complete line in the tail window)"
        )
    return header + "\n" + body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="stable command id, e.g. CMD-001")
    parser.add_argument("--receipts-dir", required=True)
    parser.add_argument("--classification", required=True, choices=CLASSIFICATIONS)
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="run count; >=2 proves determinism for required-risk proof",
    )
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--expect-pass", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    argv = [item for item in args.command if item != "--"] if args.command else []
    if args.command and args.command[0] == "--":
        argv = args.command[1:]
    if not argv:
        print("run_checked: no command given after --", file=sys.stderr)
        return 2
    if args.repeat < 1:
        print("run_checked: --repeat must be at least 1", file=sys.stderr)
        return 2

    try:
        receipt = build_receipt(args, argv)
    except (OSError, ValueError) as error:
        print(f"run_checked: cannot produce receipt: {error}", file=sys.stderr)
        return 2

    receipt_path = Path(args.receipts_dir).resolve() / f"{args.id}.receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + os.linesep, encoding="utf-8"
    )
    summary = {
        "receipt": str(receipt_path),
        "id": receipt["id"],
        "status": receipt["status"],
        "determinism": receipt["determinism"],
        "exit_codes": [run["exit_code"] for run in receipt["runs"]],
        "command": " ".join(argv),
    }
    print(json.dumps(summary), flush=True)
    if receipt["status"] != "PASS":
        failing = next(run for run in receipt["runs"] if run["exit_code"] != 0)
        try:
            tail = failure_tail(failing)
        except OSError as error:
            tail = f"run_checked: cannot read failure log: {error}"
        try:
            print(tail, file=sys.stderr, flush=True)
        except BrokenPipeError:
            # The reader left early (`2>&1 | head -1`); the receipt is written, so
            # keep the exit status and let the exit-time flush go to devnull.
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stderr.fileno())
    if args.expect_pass and receipt["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
