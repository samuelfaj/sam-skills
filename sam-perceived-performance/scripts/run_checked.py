#!/usr/bin/env python3
"""Run a validation command and emit a re-verifiable execution receipt.

Canonical shared implementation. Every skill that ships this file must ship a
byte-identical copy; the repository suite validator enforces that.

A reported PASS must be derived from a receipt, never asserted. The receipt
records argv, cwd, exit code per run, and the SHA-256 of the captured output so
a validator can recompute both without trusting the caller.

Use --repeat to prove determinism: differing exit codes across runs mark the
command FLAKY, which is not proof.

Exit status: 0 when a receipt was written (regardless of the wrapped command's
result), 2 when the receipt could not be produced. Pass --expect-pass to instead
mirror a failing command as exit 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_LOG_BYTES = 4 * 1024 * 1024
CLASSIFICATIONS = ("TARGET", "INTRODUCED", "BASELINE", "ENVIRONMENT", "EXTERNAL")


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
    print(json.dumps({"receipt": str(receipt_path), **receipt}, indent=2, sort_keys=True))
    if args.expect_pass and receipt["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
