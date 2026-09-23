#!/usr/bin/env python3
"""Exercise sam-plan scaffold, render, and validation with adversarial fixtures."""

from __future__ import annotations

import hashlib
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


def scaffold(out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS / "scaffold_plan_dir.py"),
            "--out",
            str(out),
            "--json",
            *extra,
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
                "decision_reason": "Accepted for local UI guard; drafts only in this module.",
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
                "how": [
                    "Guard total before format/render in InvoiceDetail",
                    "Show an em dash when total is null; keep existing path when present",
                ],
                "depends_on": [],
                "surfaces": [surface],
                "preconditions": ["E-001"],
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
    council_report = Path(plan_dir).parent / f"{Path(plan_dir).name}-council-report.json"
    council_report.parent.mkdir(parents=True, exist_ok=True)
    council_report.write_text(json.dumps({"status": "TRIAGE_PASS"}), encoding="utf-8")
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
                        "report_path": str(council_report),
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


def assert_anti_loop_contract() -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    council = (ROOT / "references/council-integration.md").read_text(encoding="utf-8")
    if "One council run per freeze" not in skill:
        raise AssertionError("sam-plan must cap council to one run per freeze")
    if "One council run per plan freeze" not in council:
        raise AssertionError("council integration must forbid T-00N auto-redispatch")
    if "author-revised thesis" not in skill and "T-00N" not in council:
        raise AssertionError("sam-plan must not treat author thesis bumps as new rounds")


def main() -> int:
    assert_anti_loop_contract()
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

        # Compact freeze READY (machine core may validate before HTML render)
        simple_path = root / "simple.json"
        simple = base_simple_report(str(plan_dir), repo_root=str(repo))
        write_report(simple_path, simple)
        assert_valid(simple_path)
        assert_valid(simple_path, repo_root=repo, check_locators=True)

        # Required human pack: render synthesizes light HTML or uses chapters
        render_result = render(simple_path, plan_dir)
        if render_result.returncode != 0:
            raise AssertionError(render_result.stderr)
        rendered_report = plan_dir / "plan-report.json"
        assert_valid(rendered_report, require_html=True)
        html = (plan_dir / "00-plano.html").read_text(encoding="utf-8")
        if "<nav" not in html or "S-001" not in html:
            raise AssertionError("rendered HTML missing nav or step content")
        if 'name="color-scheme" content="light"' not in html:
            raise AssertionError("rendered HTML missing light color-scheme meta")
        if "color-scheme: light" not in html:
            raise AssertionError("rendered HTML missing light theme CSS")
        for required_heading in (
            "Status",
            "Goal &amp; scope",
            "Steps (what / how / where / done)",
            "Acceptance map",
        ):
            if required_heading not in html:
                raise AssertionError(
                    f"compact HTML missing required section {required_heading!r}"
                )
        if "Guard total before format/render" not in html:
            raise AssertionError("compact HTML missing step how content")
        compact_surface = simple["steps"][0]["surfaces"][0]
        compact_criterion = simple["frozen"]["success_criteria"][0]
        if compact_surface not in html:
            raise AssertionError("compact HTML missing step surface path")
        if compact_criterion not in html:
            raise AssertionError("compact HTML missing success criterion in acceptance")

        # One render+validate pass per edit: locator checks apply to the final artifact.
        assert_valid(rendered_report, require_html=True, repo_root=repo)

        # Stale-chapter regression: the synthesized page must stay in memory, so a
        # re-render after an edit shows the edited freeze, not the first render.
        persisted = json.loads(rendered_report.read_text(encoding="utf-8"))
        if persisted.get("chapters") != []:
            raise AssertionError("renderer persisted a synthesized chapter into the freeze")
        persisted["steps"][0]["how"][0] = "Guard total with an explicit null branch first"
        write_report(rendered_report, persisted)
        render_result = render(rendered_report, plan_dir)
        if render_result.returncode != 0:
            raise AssertionError(render_result.stderr)
        html = (plan_dir / "00-plano.html").read_text(encoding="utf-8")
        if "explicit null branch" not in html or "Guard total before format/render" in html:
            raise AssertionError("re-render reused a stale chapter instead of the edited freeze")
        assert_valid(rendered_report, require_html=True, repo_root=repo)

        # Scaffold skeleton: prompt_hash derived from the real prompt bytes, never
        # overwritten, and fail-closed until the planner fills it.
        prompt_file = root / "prompt.txt"
        prompt_file.write_bytes("Fix the invoice null crash.".encode("utf-8"))
        skeleton_dir = root / "plan-skeleton"
        skeleton_result = scaffold(
            skeleton_dir, "--prompt-file", str(prompt_file), "--repo-root", str(repo)
        )
        if skeleton_result.returncode != 0:
            raise AssertionError(skeleton_result.stderr)
        skeleton_payload = json.loads(skeleton_result.stdout)
        if not skeleton_payload.get("report_created") or not Path(
            skeleton_payload["plan_dir"]
        ).is_dir():
            raise AssertionError("scaffold with a prompt must create plan-report.json")
        skeleton_path = skeleton_dir / "plan-report.json"
        skeleton = json.loads(skeleton_path.read_text(encoding="utf-8"))
        expected_hash = hashlib.sha256(prompt_file.read_bytes()).hexdigest()
        if skeleton["frozen"]["prompt_hash"] != expected_hash:
            raise AssertionError("scaffold prompt_hash must be sha256 of the prompt bytes")
        if skeleton["output"]["plan_dir"] != str(skeleton_dir.resolve()):
            raise AssertionError("scaffold must prefill output.plan_dir")
        if skeleton["study"].get("repo_root") != str(repo.resolve()):
            raise AssertionError("scaffold must prefill study.repo_root")
        assert_invalid(skeleton_path, "status must be one of")
        skeleton["frozen"]["goal"] = "planner-authored goal"
        write_report(skeleton_path, skeleton)
        # Refine-again on the same prompt reuses the freeze untouched.
        rerun = scaffold(skeleton_dir, "--prompt-file", str(prompt_file))
        if rerun.returncode != 0 or json.loads(rerun.stdout).get("report_created"):
            raise AssertionError("scaffold must reuse, not overwrite, a same-prompt freeze")
        # Another prompt's freeze (e.g. a stale <cwd>/plan) is refused, never planned on.
        other = scaffold(skeleton_dir, "--prompt-hash", "0" * 64)
        if other.returncode == 0 or "different prompt" not in other.stderr:
            raise AssertionError("scaffold reused a freeze of a different prompt")
        if json.loads(skeleton_path.read_text(encoding="utf-8"))["frozen"]["goal"] != (
            "planner-authored goal"
        ):
            raise AssertionError("scaffold rewrote planner-authored fields")
        legacy_dir = root / "plan-legacy"
        legacy_dir.mkdir()
        legacy = deepcopy(skeleton)
        del legacy["frozen"]["prompt_hash"]
        write_report(legacy_dir / "plan-report.json", legacy)
        if scaffold(legacy_dir, "--prompt-file", str(prompt_file)).returncode == 0:
            raise AssertionError("scaffold reused a freeze with no prompt_hash")
        if scaffold(root / "plan-bad-hash", "--prompt-hash", "abc").returncode == 0:
            raise AssertionError("scaffold accepted a malformed --prompt-hash")

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

        # A non-terminal council status (e.g. a pending run) must not satisfy READY.
        pending_council = deepcopy(risk_ok)
        pending_council["council"]["runs"][0]["status"] = "PENDING"
        pending_council_path = root / "pending-council.json"
        write_report(pending_council_path, pending_council)
        assert_invalid(pending_council_path, "council.runs[0].status must be a council terminal")
        # The council run is proven by its report on disk, not by the typed status.
        for name, change, snippet in (
            ("council-no-report", lambda run: run.pop("report_path"), "report_path must be an absolute path"),
            ("council-relative-report", lambda run: run.update(report_path="council.json"), "report_path must be an absolute path"),
            ("council-missing-report", lambda run: run.update(report_path=str(root / "absent.json")), "report_path is unreadable"),
            ("council-status-mismatch", lambda run: run.update(status="APPROVED"), "must equal its council report status"),
        ):
            case = deepcopy(risk_ok)
            change(case["council"]["runs"][0])
            case_path = root / f"{name}.json"
            write_report(case_path, case)
            assert_invalid(case_path, snippet)
        bad_profile = deepcopy(risk_ok)
        bad_profile["council"]["runs"][0]["profile"] = "medium"
        bad_profile_path = root / "bad-council-profile.json"
        write_report(bad_profile_path, bad_profile)
        assert_invalid(bad_profile_path, "council.runs[0].profile must be one of")

        # Keyword-heuristic false positive: a UI-only path segment named "session".
        timer = repo / "src" / "session" / "Timer.tsx"
        timer.parent.mkdir(parents=True)
        timer.write_text("export const Timer = () => null;\n", encoding="utf-8")
        session_path = "src/session/Timer.tsx"
        session_hit = deepcopy(simple)
        session_hit["study"]["surfaces_mapped"].append(session_path)
        session_hit["steps"][0]["surfaces"].append(session_path)
        session_hit_path = root / "session-hit.json"
        write_report(session_hit_path, session_hit)
        assert_invalid(session_hit_path, "missing risk_flags suggested by heuristics")

        dismissed = deepcopy(session_hit)
        dismissed["evidence"].append(
            {
                "id": "E-002",
                "kind": "CODE",
                "classification": "FACT",
                "claim": "Timer.tsx renders a countdown with no login, role, or identity logic.",
                "locator": f"{session_path}:1",
            }
        )
        dismissed["risk_flag_dismissals"] = [
            {
                "flag": "auth_boundary",
                "reason": "'session' is a UI folder name; no auth or identity code is touched.",
                "evidence_ids": ["E-002"],
            }
        ]
        dismissed_path = root / "dismissed.json"
        write_report(dismissed_path, dismissed)
        assert_valid(dismissed_path, repo_root=repo, check_locators=True)

        no_reason = deepcopy(dismissed)
        no_reason["risk_flag_dismissals"][0]["reason"] = ""
        no_reason_path = root / "dismissal-no-reason.json"
        write_report(no_reason_path, no_reason)
        assert_invalid(no_reason_path, "risk_flag_dismissals[0].reason")

        non_fact = deepcopy(dismissed)
        non_fact["evidence"][1]["classification"] = "ASSUMPTION"
        non_fact_path = root / "dismissal-non-fact.json"
        write_report(non_fact_path, non_fact)
        assert_invalid(non_fact_path, "requires FACT evidence with locator")

        migration_dismissal = deepcopy(risk_ok)
        migration_dismissal["risk_flags"] = ["data_migration"]
        migration_dismissal["risk_flag_dismissals"] = [
            {
                "flag": "irreversible",
                "reason": "Backfill is idempotent.",
                "evidence_ids": ["E-001"],
            }
        ]
        migration_dismissal_path = root / "dismissal-migration.json"
        write_report(migration_dismissal_path, migration_dismissal)
        assert_invalid(migration_dismissal_path, "cannot be dismissed for case_type=MIGRATION")

        # A dismissal is a typed claim only when backed by known FACT evidence, and
        # only for a keyword false positive; each mutation must stay INVALID.
        def dismissal_case(name: str, snippet: str, edit: Any) -> None:
            case = deepcopy(dismissed)
            edit(case)
            case_path = root / f"dismissal-{name}.json"
            write_report(case_path, case)
            assert_invalid(case_path, snippet)

        dismissal_case(
            "empty-evidence",
            "risk_flag_dismissals[0].evidence_ids must not be empty",
            lambda r: r["risk_flag_dismissals"][0].update(evidence_ids=[]),
        )
        dismissal_case(
            "missing-evidence",
            "risk_flag_dismissals[0].evidence_ids must not be empty",
            lambda r: r["risk_flag_dismissals"][0].pop("evidence_ids"),
        )
        dismissal_case(
            "unknown-evidence",
            "risk_flag_dismissals[0].evidence_ids unknown id E-999",
            lambda r: r["risk_flag_dismissals"][0].update(evidence_ids=["E-999"]),
        )
        dismissal_case(
            "not-keyword",
            "flag material_uncertainty is not a dismissible keyword-heuristic flag",
            lambda r: r["risk_flag_dismissals"][0].update(flag="material_uncertainty"),
        )
        dismissal_case(
            "repeat",
            "risk_flag_dismissals repeats flag auth_boundary",
            lambda r: r["risk_flag_dismissals"].append(deepcopy(r["risk_flag_dismissals"][0])),
        )
        # With a known repo, a dismissal's proof of absence is a file in it: a
        # bare word or a path outside the repo proves nothing about this code.
        for name, locator in (("bare-word-locator", "ui-only"), ("outside-repo-locator", "/etc/hosts:1")):
            dismissal_case(
                name,
                "risk_flag_dismissals[0] requires a FACT path locator under the repo; E-002 is not",
                lambda r, locator=locator: r["evidence"][1].update(locator=locator),
            )

        def flag_and_dismiss(case: JsonObject) -> None:
            case["risk_flags"] = ["auth_boundary"]
            case["council"] = deepcopy(risk_ok["council"])

        dismissal_case(
            "also-flagged", "flag auth_boundary is also listed in risk_flags", flag_and_dismiss
        )
        # The user's own goal wording is intent, not a keyword false positive.
        dismissal_case(
            "intent",
            "flag auth_boundary matches frozen.goal or prompt_summary",
            lambda r: r["frozen"].update(goal="Fix the session timer countdown display."),
        )

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


        surface = "src/views/InvoiceDetail.tsx"
        criterion = simple["frozen"]["success_criteria"][0]

        # P1: empty success_criteria fails READY
        empty_sc = deepcopy(simple)
        empty_sc["frozen"]["success_criteria"] = []
        empty_sc["acceptance_trace"] = []
        empty_sc_path = root / "empty-success-criteria.json"
        write_report(empty_sc_path, empty_sc)
        assert_invalid(empty_sc_path, "non-empty frozen.success_criteria")

        # P1: acceptance_trace without proof_ids
        no_proof_ids = deepcopy(simple)
        no_proof_ids["acceptance_trace"][0]["proof_ids"] = []
        no_proof_path = root / "trace-no-proof.json"
        write_report(no_proof_path, no_proof_ids)
        assert_invalid(no_proof_path, "requires ≥1 proof_ids")

        # P1: depends_on cycle
        cyclic = deepcopy(simple)
        cyclic["steps"] = [
            {
                "id": "S-001",
                "title": "A",
                "why": "a",
                "how": ["Do step A work on the invoice view path"],
                "depends_on": ["S-002"],
                "surfaces": [surface],
                "dod": ["done"],
                "proof_ids": ["V-001"],
            },
            {
                "id": "S-002",
                "title": "B",
                "why": "b",
                "how": ["Do step B work on the invoice view path"],
                "depends_on": ["S-001"],
                "surfaces": [surface],
                "dod": ["done"],
                "proof_ids": ["V-001"],
            },
        ]
        cyclic["acceptance_trace"] = [
            {
                "criterion": criterion,
                "step_ids": ["S-001", "S-002"],
                "proof_ids": ["V-001"],
            }
        ]
        cyclic_path = root / "cyclic-depends.json"
        write_report(cyclic_path, cyclic)
        assert_invalid(cyclic_path, "acyclic")

        # P1: step with dod but no proof_ids
        no_step_proof = deepcopy(simple)
        no_step_proof["steps"][0]["proof_ids"] = []
        no_step_proof_path = root / "step-no-proof.json"
        write_report(no_step_proof_path, no_step_proof)
        assert_invalid(no_step_proof_path, "with dod requires")

        # P1: ACCEPTED without decision_reason/evidence
        bare_accept = deepcopy(simple)
        bare_accept["assumptions"][0]["decision_reason"] = ""
        bare_accept["assumptions"][0]["evidence_ids"] = []
        bare_accept_path = root / "bare-accept.json"
        write_report(bare_accept_path, bare_accept)
        assert_invalid(bare_accept_path, "decision_reason or evidence_ids")

        # P1: FACT with hedge language
        hedge = deepcopy(simple)
        hedge["evidence"][0]["claim"] = "This appears to be a null total crash."
        hedge_path = root / "hedge-fact.json"
        write_report(hedge_path, hedge)
        assert_invalid(hedge_path, "hedge language")

        # Benign: hedge word only outside FACT
        benign = deepcopy(simple)
        benign["frozen"]["goal"] = "Fix render so the UI never appears broken on null."
        benign_path = root / "benign-hedge-nonfact.json"
        write_report(benign_path, benign)
        assert_valid(benign_path)

        # P1: standard depth unreachable step without out_of_acceptance
        orphan_step = deepcopy(simple)
        orphan_step["depth"] = "standard"
        orphan_step["steps"].append(
            {
                "id": "S-002",
                "title": "Unrelated cleanup",
                "why": "should be linked or marked",
                "how": ["Remove dead imports only if already touched in S-001"],
                "depends_on": [],
                "surfaces": [surface],
                "dod": ["cleanup done"],
                "proof_ids": ["V-001"],
            }
        )
        orphan_step_path = root / "orphan-step.json"
        write_report(orphan_step_path, orphan_step)
        assert_invalid(orphan_step_path, "reachable from acceptance_trace")

        # P0: READY without how[]
        no_how = deepcopy(simple)
        no_how["steps"][0].pop("how", None)
        no_how_path = root / "no-how.json"
        write_report(no_how_path, no_how)
        assert_invalid(no_how_path, "requires non-empty how[]")

        # P0: how that only restates the title
        title_only_how = deepcopy(simple)
        title_only_how["steps"][0]["how"] = [
            title_only_how["steps"][0]["title"]
        ]
        title_how_path = root / "title-only-how.json"
        write_report(title_how_path, title_only_how)
        assert_invalid(title_how_path, "not only restating the title")

        # P0: READY step without surfaces (non-SPIKE)
        no_step_surfaces = deepcopy(simple)
        no_step_surfaces["steps"][0]["surfaces"] = []
        no_step_surfaces_path = root / "no-step-surfaces.json"
        write_report(no_step_surfaces_path, no_step_surfaces)
        assert_invalid(no_step_surfaces_path, "requires non-empty surfaces")

        print("sam-plan harness passed")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
