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


def validate(
    path: Path,
    *,
    require_html: bool = False,
    repo_root: Path | None = None,
    check_locators: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-B", str(SCRIPTS / "validate_plan_report.py"), str(path)]
    if require_html:
        command.append("--require-html")
    if repo_root is not None:
        command.extend(["--repo-root", str(repo_root)])
    if check_locators:
        command.append("--check-locators")
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


def base_simple_report(plan_dir: str, *, repo_root: str | None = None) -> JsonObject:
    surface = "src/views/InvoiceDetail.tsx"
    criterion = "Page renders with a safe empty total state"
    report: JsonObject = {
        "schema_version": 1,
        "workflow": "plan",
        "status": "READY_TO_EXECUTE",
        "depth": "simple",
        "case_type": "BUG",
        "complexity_rationale": (
            "Single clear bug fix on one module with no migration, auth, or "
            "irreversible rollout risk."
        ),
        "risk_flags": [],
        "study": {
            "tools_used": ["rg InvoiceDetail", "read InvoiceDetail.tsx"],
            "surfaces_mapped": [surface],
            "prompt_ambiguities": [],
        },
        "frozen": {
            "prompt_hash": "abc123",
            "prompt_summary": "Fix null crash on invoice total",
            "goal": "Stop the invoice detail page from crashing when total is null.",
            "non_goals": ["Rewrite billing", "Change invoice schema"],
            "success_criteria": [criterion],
            "invariants": ["Do not change payment capture"],
            "constraints": ["Minimal diff"],
            "no_go": ["Production data edits"],
        },
        "output": {
            "plan_dir": plan_dir,
            "html_files": [],
        },
        "evidence": [
            {
                "id": "E-001",
                "kind": "CODE",
                "classification": "FACT",
                "claim": "Invoice view reads total without a null guard.",
                "locator": f"{surface}:1",
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
                "surfaces": [surface],
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
        "acceptance_trace": [
            {
                "criterion": criterion,
                "step_ids": ["S-001"],
                "proof_ids": ["V-001"],
            }
        ],
        "chapters": [],
        "council": {
            "required": False,
            "skip_reason": "no risk_flags; local reversible UI guard only",
            "runs": [],
        },
        "simplicity": {
            "cuts": ["No schema migration", "No billing rewrite"],
            "retained_complexity_justifications": [],
        },
        "residuals": [],
        "blockers": [],
    }
    if repo_root:
        study = report["study"]
        assert isinstance(study, dict)
        study["repo_root"] = repo_root
    return report


def base_standard_report(plan_dir: str) -> JsonObject:
    """Standard depth without forced council when risk_flags empty."""
    report = base_simple_report(plan_dir)
    report.update(
        {
            "status": "READY_TO_EXECUTE",
            "depth": "standard",
            "case_type": "FEATURE",
            "complexity_rationale": (
                "Multi-step feature across API and UI with a clear but non-trivial seam."
            ),
            "risk_flags": [],
            "council": {
                "required": False,
                "skip_reason": (
                    "no risk_flags; multi-step feature without security, migration, "
                    "or public-contract trigger"
                ),
                "runs": [],
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
            ],
            "output": {
                "plan_dir": plan_dir,
                "html_files": [
                    "00-visao-objetivo.html",
                    "04-passos.html",
                ],
            },
        }
    )
    return report


def base_risk_council_report(plan_dir: str) -> JsonObject:
    report = base_simple_report(plan_dir)
    report.update(
        {
            "depth": "standard",
            "case_type": "MIGRATION",
            "complexity_rationale": "Schema migration with irreversible backfill risk.",
            "risk_flags": ["data_migration", "irreversible"],
            "frozen": {
                **report["frozen"],  # type: ignore[misc]
                "goal": "Run a one-way schema migration with backfill for order totals.",
                "prompt_summary": "Irreversible data migration for order totals",
            },
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
        }
    )
    return report


def assert_valid(
    path: Path,
    *,
    require_html: bool = False,
    repo_root: Path | None = None,
    check_locators: bool = False,
) -> None:
    result = validate(
        path,
        require_html=require_html,
        repo_root=repo_root,
        check_locators=check_locators,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"expected VALID, got {result.returncode}: {result.stdout}{result.stderr}"
        )
    if "VALID" not in result.stdout:
        raise AssertionError(f"missing VALID marker: {result.stdout}")


def assert_invalid(
    path: Path,
    snippet: str,
    *,
    repo_root: Path | None = None,
    check_locators: bool = False,
) -> None:
    result = validate(path, repo_root=repo_root, check_locators=check_locators)
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

        # Real mini-repo for locator resolution
        repo = root / "app"
        target = repo / "src" / "views" / "InvoiceDetail.tsx"
        target.parent.mkdir(parents=True)
        target.write_text(
            "export function InvoiceDetail() { return total; }\n",
            encoding="utf-8",
        )

        # Compact freeze READY without chapters/HTML
        simple_path = root / "simple.json"
        simple = base_simple_report(str(plan_dir), repo_root=str(repo))
        write_report(simple_path, simple)
        assert_valid(simple_path)
        assert_valid(simple_path, repo_root=repo, check_locators=True)

        # Optional pack: render synthesizes or uses chapters
        render_result = render(simple_path, plan_dir)
        if render_result.returncode != 0:
            raise AssertionError(render_result.stderr)
        rendered_report = plan_dir / "plan-report.json"
        assert_valid(rendered_report, require_html=True)
        html = (plan_dir / "00-plano.html").read_text(encoding="utf-8")
        if "<nav" not in html or "S-001" not in html:
            raise AssertionError("rendered HTML missing nav or step content")

        # Standard without forced council
        standard_dir = root / "plan-standard"
        standard_path = root / "standard.json"
        standard = base_standard_report(str(standard_dir))
        write_report(standard_path, standard)
        assert_valid(standard_path)
        render_result = render(standard_path, standard_dir)
        if render_result.returncode != 0:
            raise AssertionError(render_result.stderr)
        assert_valid(standard_dir / "plan-report.json", require_html=True)

        # Risk flags require council runs
        risk_ok = base_risk_council_report(str(root / "risk-ok"))
        risk_ok_path = root / "risk-ok.json"
        write_report(risk_ok_path, risk_ok)
        assert_valid(risk_ok_path)

        risk_bad = deepcopy(risk_ok)
        risk_bad["council"] = {
            "required": False,
            "skip_reason": "wrongly skipped",
            "runs": [],
        }
        risk_bad_path = root / "risk-bad.json"
        write_report(risk_bad_path, risk_bad)
        assert_invalid(risk_bad_path, "risk_flags require council.required=true")

        no_council_run = deepcopy(risk_ok)
        no_council_run["council"] = {
            "required": True,
            "skip_reason": None,
            "runs": [],
        }
        no_council_path = root / "no-council.json"
        write_report(no_council_path, no_council_run)
        assert_invalid(no_council_path, "council.runs must not be empty")

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

        # READY without rejected alternatives
        no_reject = deepcopy(simple)
        no_reject["thesis"]["rejected_alternatives"] = []
        no_reject_path = root / "no-reject.json"
        write_report(no_reject_path, no_reject)
        assert_invalid(no_reject_path, "rejected_alternatives")

        # READY without FACT locator
        no_fact = deepcopy(simple)
        no_fact["evidence"] = [
            {
                "id": "E-001",
                "kind": "NOTE",
                "classification": "ASSUMPTION",
                "claim": "Maybe totals are null",
                "locator": "",
            }
        ]
        no_fact_path = root / "no-fact.json"
        write_report(no_fact_path, no_fact)
        assert_invalid(no_fact_path, "FACT evidence with locator")

        # READY without study surfaces
        no_surfaces = deepcopy(simple)
        no_surfaces["study"]["surfaces_mapped"] = []
        no_surfaces_path = root / "no-surfaces.json"
        write_report(no_surfaces_path, no_surfaces)
        assert_invalid(no_surfaces_path, "surfaces_mapped")

        # READY without tools_used
        no_tools = deepcopy(simple)
        no_tools["study"]["tools_used"] = []
        no_tools_path = root / "no-tools.json"
        write_report(no_tools_path, no_tools)
        assert_invalid(no_tools_path, "tools_used")

        # Missing acceptance_trace for success criterion
        no_trace = deepcopy(simple)
        no_trace["acceptance_trace"] = []
        no_trace_path = root / "no-trace.json"
        write_report(no_trace_path, no_trace)
        assert_invalid(no_trace_path, "acceptance_trace")

        # Fake locator fails with --repo-root
        bad_loc = deepcopy(simple)
        bad_loc["evidence"][0]["locator"] = "src/views/DoesNotExist.tsx:1"
        bad_loc_path = root / "bad-loc.json"
        write_report(bad_loc_path, bad_loc)
        assert_invalid(
            bad_loc_path,
            "locator path does not exist",
            repo_root=repo,
            check_locators=True,
        )

        # Heuristic: migration language without flags
        underflag = deepcopy(simple)
        underflag["frozen"]["goal"] = (
            "Apply an irreversible schema migration with backfill for users."
        )
        underflag["risk_flags"] = []
        underflag_path = root / "underflag.json"
        write_report(underflag_path, underflag)
        assert_invalid(underflag_path, "missing risk_flags suggested by heuristics")

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

        # HTML files mismatch when chapters present
        mismatch = deepcopy(standard)
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
