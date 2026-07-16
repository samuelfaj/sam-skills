#!/usr/bin/env python3
"""Run every deterministic skill harness and return one compact result."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


TIMEOUT_SECONDS = 180


def discover(root: Path) -> list[Path]:
    harnesses = [root / "scripts/test_skill_suite.py"]
    harnesses.extend(sorted(root.glob("sam-*/scripts/test_*_harness.py")))
    harnesses.extend(sorted(root.glob("sam-*/scripts/test_harness.py")))
    return sorted({path for path in harnesses if path.is_file()})


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    harnesses = discover(root)
    if not harnesses:
        print("NO HARNESSES")
        return 1
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    failures: list[str] = []
    for path in harnesses:
        relative = path.relative_to(root).as_posix()
        try:
            result = subprocess.run(
                [sys.executable, "-B", str(path)],
                cwd=root,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            failures.append(f"{relative}: TIMEOUT after {TIMEOUT_SECONDS}s")
            print(f"FAIL {relative}: timeout")
            continue
        output = result.stdout.strip().splitlines()
        summary = output[-1] if output else "no stdout"
        if result.returncode == 0:
            print(f"PASS {relative}: {summary}")
            continue
        error = result.stderr.strip().splitlines()
        detail = error[-1] if error else summary
        failures.append(f"{relative}: {detail}")
        print(f"FAIL {relative}: {detail}")
    if failures:
        print(f"FAILED: {len(failures)}/{len(harnesses)} harnesses")
        return 1
    print(f"PASS: {len(harnesses)} harnesses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
