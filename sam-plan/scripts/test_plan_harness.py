#!/usr/bin/env python3
"""Exercise sam-plan scaffold, render, and validation with adversarial fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
JsonObject = dict[str, Any]


def run(
    command: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def validate(path: Path, *, require_html: bool = False) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-B", str(SCRIPTS / "validate_plan_report.py"), str(path)]
    if require_html:
        command.append("--require-html")
    return run(command, check=False)


def render(report: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "render_plan_html.py"),
            str(report),
            "--out",
            str(out),
        ],
        check=False,
    )


def scaffold(out: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "scaffold_plan_dir.py"),
            "--out",
            str(out),
            "--json",
        ],
        check=False,
    )


def base_simple_report(plan_dir: str) -> JsonObject:
    return {
        "schema_version": 1,
        "workflow": "plan",
        "status": "READY_TO_EXECUTE",
        "depth": "simple",
        "case_type": "BUG",
        "complexity_rationale": (
            "Single clear bugfix on one module with no migration, auth, or "
            "irreversible rollout risk."
        ),
        "frozen": {
            "prompt_hash": "abc123",
            "prompt_summary": "Fix null crash on invoice total",
            "goal": "Stop the invoice detail page from crashing when total is null.",
            "non_goals": ["Rewrite billing", "Change invoice schema"],
            "success_criteria": ["Page renders with a safe empty total state"],
            "invariants": ["Do not change payment capture"],
            "constraints": ["Minimal diff"],
            "no_go": ["Production data edits"],
        },
        "output": {
            "plan_dir": plan_dir,
            "html_files": ["00-plano.html"],
        },
        "evidence": [
            {
                "id": "E-001",
                "kind": "CODE",
                "classification": "FACT",
                "claim": "Invoice view reads total without a null guard.",
                "locator": "src/views/InvoiceDetail.tsx:42",
            }
        ],
        "assumptions": [
            {
                "id": "A-001",
                "claim": "Null totals only appear for draft invoices.",
                "state": "ACCEPTED",
                "evidence_ids": [],
            }
        ],
        "unknowns": [],
        "thesis": {
            "id": "T-001",
            "summary": "Add a local null-safe display path.",
            "approach": "Guard the render path and show an em dash when total is null.",
            "rejected_alternatives": ["Backfill all null totals in the database"],
        },
        "steps": [
            {
                "id": "S-001",
                "title": "Add null-safe total rendering",
                "why": "Removes the crash without schema churn.",
                "depends_on": [],
                "surfaces": ["src/views/InvoiceDetail.tsx"],
                "dod": ["No throw on null total", "Draft invoices still open"],
                "proof_ids": ["V-001"],
                "simpler_rejected": None,
            }
        ],
        "risks": [],
        "verifications": [
            {
                "id": "V-001",
                "proof": "Unit or component test for null total render",
                "status": "PLANNED",
                "reason": "Executable only after the code change exists",
                "claim_ids": ["S-001"],
            }
        ],
        "chapters": [
            {
                "id": "00",
                "slug": "plano",
                "title": "Plano simples",
                "summary": "Compact plan for a single null-guard fix.",
                "sections": [
                    {
                        "heading": "Objetivo",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": "Corrigir o crash quando total e null.",
                            }
                        ],
                    },
                    {
                        "heading": "Passos",
                        "blocks": [
                            {
                                "type": "table",
                                "headers": ["ID", "Passo", "DoD"],
                                "rows": [
                                    [
                                        "S-001",
                                        "Null-safe total rendering",
                                        "Sem throw; draft abre",
                                    ]
                                ],
                            }
                        ],
                    },
                ],
            }
        ],
        "council": {
            "required": False,
            "skip_reason": (
                "depth=simple with no high-risk trigger; local reversible UI guard only"
            ),
            "runs": [],
        },
        "simplicity": {
            "cuts": ["No schema migration", "No billing rewrite"],
            "retained_complexity_justifications": [],
        },
        "residuals": [],
        "blockers": [],
    }


def base_standard_report(plan_dir: str) -> JsonObject:
    report = base_simple_report(plan_dir)
    report.update(
        {
            "status": "READY_TO_EXECUTE",
            "depth": "standard",
            "case_type": "FEATURE",
            "complexity_rationale": (
                "Multi-step feature across API and UI with a clear but non-trivial seam."
            ),
            "council": {
                "required": True,
                "skip_reason": None,
                "runs": [
                    {
                        "profile": "fast",
                        "status": "TRIAGE_PASS",
                        "thesis_id": "T-001",
                        "report_path": "scratch/council-report.json",
                        "material_objections_closed": True,
                    }
                ],
            },
            "chapters": [
                {
                    "id": "00",
                    "slug": "visao-objetivo",
                    "title": "Visao e objetivo",
                    "summary": "Why this feature and what success means.",
                    "sections": [
                        {
                            "heading": "Goal",
                            "blocks": [
                                {
                                    "type": "paragraph",
                                    "text": "Add export CSV for invoices.",
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "04",
                    "slug": "passos",
                    "title": "Passos",
                    "summary": "Ordered implementation steps.",
                    "sections": [
                        {
                            "heading": "Sequence",
                            "blocks": [
                                {
                                    "type": "list",
                                    "items": ["S-001 Add null-safe total rendering"],
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "06",
                    "slug": "verificacao",
                    "title": "Verificacao",
                    "summary": "Proof plan.",
                    "sections": [
                        {
                            "heading": "Checks",
                            "blocks": [
                                {
                                    "type": "callout",
                                    "tone": "ok",
                                    "text": "V-001 planned after implementation.",
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "99",
                    "slug": "execution-log",
                    "title": "Execution log",
                    "summary": "Planning receipts.",
                    "sections": [
                        {
                            "heading": "Council",
                            "blocks": [
                                {
                                    "type": "paragraph",
                                    "text": "fast TRIAGE_PASS on T-001.",
                                }
                            ],
                        }
                    ],
                },
            ],
            "output": {
                "plan_dir": plan_dir,
                "html_files": [
                    "00-visao-objetivo.html",
                    "04-passos.html",
                    "06-verificacao.html",
                    "99-execution-log.html",
                ],
            },
        }
    )
    return report


def assert_valid(path: Path, *, require_html: bool = False) -> None:
    result = validate(path, require_html=require_html)
    if result.returncode != 0:
        raise AssertionError(
            f"expected VALID, got {result.returncode}: {result.stdout}{result.stderr}"
        )
    if "VALID" not in result.stdout:
        raise AssertionError(f"missing VALID marker: {result.stdout}")


def assert_invalid(path: Path, snippet: str) -> None:
    result = validate(path)
    if result.returncode == 0:
        raise AssertionError(f"expected INVALID for {snippet}")
    if snippet not in result.stdout:
        raise AssertionError(
            f"expected error containing {snippet!r}, got:\n{result.stdout}"
        )


def write_report(path: Path, report: JsonObject) -> None:
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sam-plan-harness-") as raw:
        root = Path(raw)
        plan_dir = root / "plan"
        scaffold_result = scaffold(plan_dir)
        if scaffold_result.returncode != 0:
            raise AssertionError(scaffold_result.stderr)
        payload = json.loads(scaffold_result.stdout)
        if not Path(payload["plan_dir"]).is_dir():
            raise AssertionError("scaffold did not create plan_dir")

        simple_path = root / "simple.json"
        simple = base_simple_report(str(plan_dir))
        write_report(simple_path, simple)
        assert_valid(simple_path)

        render_result = render(simple_path, plan_dir)
        if render_result.returncode != 0:
            raise AssertionError(render_result.stderr)
        rendered_report = plan_dir / "plan-report.json"
        assert_valid(rendered_report, require_html=True)
        html = (plan_dir / "00-plano.html").read_text(encoding="utf-8")
        if "<nav" not in html or "S-001" not in html:
            raise AssertionError("rendered HTML missing nav or step content")

        standard_dir = root / "plan-standard"
        standard_path = root / "standard.json"
        standard = base_standard_report(str(standard_dir))
        write_report(standard_path, standard)
        assert_valid(standard_path)
        render_result = render(standard_path, standard_dir)
        if render_result.returncode != 0:
            raise AssertionError(render_result.stderr)
        assert_valid(standard_dir / "plan-report.json", require_html=True)

        # Adversarial: simple depth with too many chapters
        too_many = deepcopy(simple)
        too_many["chapters"] = [
            deepcopy(simple["chapters"][0]),
            {
                "id": "01",
                "slug": "dois",
                "title": "Dois",
                "summary": "x",
                "sections": [
                    {
                        "heading": "H",
                        "blocks": [{"type": "paragraph", "text": "y"}],
                    }
                ],
            },
            {
                "id": "02",
                "slug": "tres",
                "title": "Tres",
                "summary": "x",
                "sections": [
                    {
                        "heading": "H",
                        "blocks": [{"type": "paragraph", "text": "y"}],
                    }
                ],
            },
            {
                "id": "03",
                "slug": "quatro",
                "title": "Quatro",
                "summary": "x",
                "sections": [
                    {
                        "heading": "H",
                        "blocks": [{"type": "paragraph", "text": "y"}],
                    }
                ],
            },
        ]
        too_many["output"]["html_files"] = [
            f"{c['id']}-{c['slug']}.html" for c in too_many["chapters"]
        ]
        bad_path = root / "too-many.json"
        write_report(bad_path, too_many)
        assert_invalid(bad_path, "at most 3 chapters")

        # READY with material unknown
        unknown_ready = deepcopy(simple)
        unknown_ready["unknowns"] = [
            {
                "id": "U-001",
                "claim": "Whether production has null totals",
                "material": True,
            }
        ]
        unknown_path = root / "unknown-ready.json"
        write_report(unknown_path, unknown_ready)
        assert_invalid(unknown_path, "material unknowns")

        # standard without council run
        no_council = deepcopy(standard)
        no_council["council"] = {
            "required": True,
            "skip_reason": None,
            "runs": [],
        }
        no_council_path = root / "no-council.json"
        write_report(no_council_path, no_council)
        assert_invalid(no_council_path, "council.runs must not be empty")

        # READY with unverified assumption
        unverified = deepcopy(simple)
        unverified["assumptions"][0]["state"] = "UNVERIFIED"
        unverified_path = root / "unverified.json"
        write_report(unverified_path, unverified)
        assert_invalid(unverified_path, "UNVERIFIED assumptions")

        # BLOCKED without remaining work
        blocked_empty = deepcopy(simple)
        blocked_empty["status"] = "BLOCKED"
        blocked_empty["blockers"] = []
        blocked_empty["residuals"] = []
        blocked_path = root / "blocked-empty.json"
        write_report(blocked_path, blocked_empty)
        assert_invalid(blocked_path, "requires residuals")

        # valid BLOCKED
        blocked_ok = deepcopy(simple)
        blocked_ok["status"] = "BLOCKED"
        blocked_ok["blockers"] = ["Missing repository access for invoice module"]
        blocked_ok_path = root / "blocked-ok.json"
        write_report(blocked_ok_path, blocked_ok)
        assert_valid(blocked_ok_path)

        # HTML files mismatch
        mismatch = deepcopy(simple)
        mismatch["output"]["html_files"] = ["99-missing.html"]
        mismatch_path = root / "mismatch.json"
        write_report(mismatch_path, mismatch)
        assert_invalid(mismatch_path, "missing chapter files")

        print("sam-plan harness passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
