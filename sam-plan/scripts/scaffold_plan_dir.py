#!/usr/bin/env python3
"""Create a plan output directory and, given a prompt, a skeleton plan-report.json.

The skeleton is written only when no plan-report.json exists. It prefills mechanical
fields (prompt_hash, plan_dir, repo_root, empty arrays) and fail-closed placeholders
that the validator rejects until the planner replaces them. An existing freeze is
reused only when its frozen.prompt_hash equals the given prompt's; otherwise exit 2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


HEX64 = re.compile(r"^[0-9a-f]{64}$")


def skeleton(prompt_hash: str, plan_dir: Path, repo_root: str | None) -> dict:
    study: dict = {"tools_used": [], "surfaces_mapped": [], "prompt_ambiguities": []}
    if repo_root:
        study["repo_root"] = repo_root
    return {
        "schema_version": 1,
        "workflow": "plan",
        "status": "READY_TO_EXECUTE|NOT_CONFIDENT|BLOCKED",
        "depth": "simple|standard|deep",
        "case_type": "BUG|FEATURE|PRODUCT|MIGRATION|OPS|SPIKE",
        "complexity_rationale": "",
        "risk_flags": [],
        "study": study,
        "frozen": {
            "prompt_hash": prompt_hash,
            "prompt_summary": "",
            "goal": "",
            "non_goals": [],
            "success_criteria": [],
            "invariants": [],
            "constraints": [],
            "no_go": [],
        },
        "output": {"plan_dir": str(plan_dir), "html_files": []},
        "evidence": [],
        "assumptions": [],
        "unknowns": [],
        "thesis": {"id": "T-001", "summary": "", "approach": "", "rejected_alternatives": []},
        "steps": [],
        "risks": [],
        "verifications": [],
        "acceptance_trace": [],
        "chapters": [],
        "council": {"required": False, "skip_reason": "", "runs": []},
        "simplicity": {"cuts": [], "retained_complexity_justifications": []},
        "residuals": [],
        "blockers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        help="Absolute or relative path for the plan directory",
    )
    prompt = parser.add_mutually_exclusive_group()
    prompt.add_argument(
        "--prompt-file",
        type=Path,
        help="File holding the exact prompt; frozen.prompt_hash = sha256 of its bytes",
    )
    prompt.add_argument(
        "--prompt-hash",
        help="Parent-frozen prompt sha256 (64 lowercase hex) to copy into frozen.prompt_hash",
    )
    parser.add_argument(
        "--repo-root",
        help="Target repository root recorded as study.repo_root in the skeleton",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable result on stdout",
    )
    args = parser.parse_args()

    plan_dir = Path(args.out).expanduser()
    if not plan_dir.is_absolute():
        plan_dir = (Path.cwd() / plan_dir).resolve()
    else:
        plan_dir = plan_dir.resolve()

    if plan_dir.exists() and not plan_dir.is_dir():
        print(f"error: path exists and is not a directory: {plan_dir}", file=sys.stderr)
        return 2

    prompt_hash = None
    if args.prompt_file is not None:
        try:
            prompt_hash = hashlib.sha256(args.prompt_file.read_bytes()).hexdigest()
        except OSError as error:
            print(f"error: cannot read prompt file: {error}", file=sys.stderr)
            return 2
    elif args.prompt_hash is not None:
        if not HEX64.fullmatch(args.prompt_hash):
            print("error: --prompt-hash must be 64 lowercase hex characters", file=sys.stderr)
            return 2
        prompt_hash = args.prompt_hash

    repo_root = None
    if args.repo_root:
        root = Path(args.repo_root).expanduser().resolve()
        if not root.is_dir():
            print(f"error: --repo-root is not a directory: {root}", file=sys.stderr)
            return 2
        repo_root = str(root)

    plan_dir.mkdir(parents=True, exist_ok=True)
    assets = plan_dir / "assets"
    assets.mkdir(exist_ok=True)
    gitkeep = assets / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    report_path = plan_dir / "plan-report.json"
    report_created = False
    if prompt_hash is not None and report_path.exists():
        # Reuse only a freeze of this same prompt (refine-again); never plan on top
        # of another task's freeze.
        try:
            existing = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            print(f"error: existing {report_path} is unreadable: {error}", file=sys.stderr)
            return 2
        frozen = existing.get("frozen") if isinstance(existing, dict) else None
        existing_hash = frozen.get("prompt_hash") if isinstance(frozen, dict) else None
        if existing_hash != prompt_hash:
            print(
                f"error: existing freeze {report_path} is for a different prompt "
                f"(frozen.prompt_hash={existing_hash!r}); use a fresh PLAN_DIR or remove it",
                file=sys.stderr,
            )
            return 2
    elif prompt_hash is not None:
        report_path.write_text(
            json.dumps(skeleton(prompt_hash, plan_dir, repo_root), indent=2) + "\n",
            encoding="utf-8",
        )
        report_created = True

    result = {
        "plan_dir": str(plan_dir),
        "assets_dir": str(assets),
        "created": True,
        "report": str(report_path),
        "report_created": report_created,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(str(plan_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
