#!/usr/bin/env python3
"""Self-test the perception budget table, receipt coupling, and honesty gates."""

from __future__ import annotations

import copy
import json
import pathlib
import shlex
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
CAPTURE = HERE / "capture_scope.py"
CLASSIFY = HERE / "classify_latency.py"
RUN_CHECKED = HERE / "run_checked.py"
VALIDATOR = HERE / "validate_perceived_report.py"


def run(
    *command: str,
    cwd: pathlib.Path | None = None,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False
    )
    if result.returncode != expected:
        raise AssertionError(
            f"expected {expected}, got {result.returncode}: {' '.join(command)}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def verify_classification() -> None:
    """The class table and its budgets must be exactly what the report is graded on."""
    cases = {
        60: "INSTANT",
        100: "INSTANT",
        101: "RESPONSIVE",
        300: "RESPONSIVE",
        900: "NOTICEABLE",
        4200: "SLOW",
        9000: "TEDIOUS",
        45000: "BACKGROUND",
    }
    for settled, expected in cases.items():
        result = run(
            sys.executable,
            str(CLASSIFY),
            "--settled-ms",
            str(settled),
            "--feedback-ms",
            "40",
            "--dead-time-ms",
            "0",
        )
        verdict = json.loads(result.stdout)
        if verdict["class"] != expected:
            raise AssertionError(f"{settled}ms classified {verdict['class']}, want {expected}")
        if not verdict["feels_instantaneous"]:
            raise AssertionError(f"{settled}ms with 40ms feedback should feel instant")

    # Late first feedback is out of budget in every class, at any real duration.
    late = run(
        sys.executable,
        str(CLASSIFY),
        "--settled-ms",
        "2000",
        "--feedback-ms",
        "700",
        "--dead-time-ms",
        "700",
        expected=1,
    )
    verdict = json.loads(late.stdout)
    if verdict["status"] != "OUT_OF_BUDGET" or verdict["feels_instantaneous"]:
        raise AssertionError("late feedback passed the budget gate")

    # Impossible orderings fail before any budget is considered.
    impossible = run(
        sys.executable,
        str(CLASSIFY),
        "--settled-ms",
        "500",
        "--feedback-ms",
        "50",
        "--meaningful-ms",
        "900",
        "--dead-time-ms",
        "0",
        expected=1,
    )
    if "after settlement" not in impossible.stdout:
        raise AssertionError("meaningful content after settlement was accepted")

    # Real latency may not grow past the noise budget to buy a nicer feel.
    regressed = run(
        sys.executable,
        str(CLASSIFY),
        "--settled-ms",
        "2400",
        "--feedback-ms",
        "40",
        "--dead-time-ms",
        "0",
        "--baseline-settled-ms",
        "2000",
        expected=1,
    )
    if "real latency regressed" not in regressed.stdout:
        raise AssertionError("real-latency regression passed the budget gate")

    # A 5% band absorbs measurement noise without licensing a real slowdown.
    run(
        sys.executable,
        str(CLASSIFY),
        "--settled-ms",
        "2080",
        "--feedback-ms",
        "40",
        "--dead-time-ms",
        "0",
        "--baseline-settled-ms",
        "2000",
    )


def make_receipt(
    receipts: pathlib.Path,
    evidence_id: str,
    classification: str,
    script: str,
    repeat: int = 2,
) -> dict[str, Any]:
    receipts.mkdir(parents=True, exist_ok=True)
    argv = ["/bin/sh", "-c", script]
    result = run(
        sys.executable,
        str(RUN_CHECKED),
        "--id",
        evidence_id,
        "--receipts-dir",
        str(receipts),
        "--classification",
        classification,
        "--repeat",
        str(repeat),
        "--",
        *argv,
    )
    receipt = json.loads(result.stdout)
    return {
        "path": receipt["receipt"],
        "command": " ".join(argv),
        "status": receipt["status"],
    }


def build_fixture(root: pathlib.Path) -> dict[str, Any]:
    """A repo with unrelated dirty work plus one applied perceived-performance change."""
    run("git", "init", "-q", cwd=root)
    run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
    run("git", "config", "user.name", "Fixture", cwd=root)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "cart.js").write_text("export const submit = () => post();\n", encoding="utf-8")
    (root / "src" / "unrelated.js").write_text("export const other = 1;\n", encoding="utf-8")
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-qm", "base", cwd=root)

    # Pre-existing dirty work that this skill must never touch or claim.
    (root / "src" / "unrelated.js").write_text("export const other = 2;\n", encoding="utf-8")
    baseline = json.loads(run(sys.executable, str(CAPTURE), "--repo", str(root)).stdout)

    (root / "src" / "cart.js").write_text(
        "export const submit = () => { showPending(); return post(); };\n", encoding="utf-8"
    )
    (root / "tests" / "cart.rollback.test.js").write_text(
        "test('reverts the row when the server declines', () => {});\n", encoding="utf-8"
    )
    current = json.loads(run(sys.executable, str(CAPTURE), "--repo", str(root)).stdout)
    return {"baseline": baseline, "current": current}


def build_report(
    bundles: dict[str, Any], receipts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    def evidence(evidence_id: str, kind: str, classification: str, detail: str) -> dict[str, Any]:
        return {
            "id": evidence_id,
            "kind": kind,
            "classification": classification,
            "status": receipts[evidence_id]["status"],
            "command": receipts[evidence_id]["command"],
            "receipt": receipts[evidence_id]["path"],
            "detail": detail,
        }

    return {
        "schema_version": 1,
        "workflow": "perceived-performance",
        "target": {
            "baseline_fingerprint": bundles["baseline"]["fingerprint"],
            "current_fingerprint": bundles["current"]["fingerprint"],
            "paths": bundles["current"]["paths"],
        },
        "intent": {
            "goal": "make cart submission acknowledge instantly while the order posts",
            "owner_boundary": "cart submit component and its rollback test",
            "must_not_change": ["order totals", "server contract"],
            "invariants": ["a declined order never appears as accepted"],
        },
        "environment": {
            "kind": "local",
            "identity": "fixture workstation",
            "device_profile": "4x CPU throttle, warm cache",
            "network_profile": "regular 4G profile, 150ms RTT",
        },
        "evidence": [
            evidence("E-001", "MEASUREMENT", "BASELINE", "baseline timings, 7 samples"),
            evidence("E-002", "MEASUREMENT", "TARGET", "post-change timings, 7 samples"),
            evidence("E-003", "TEST", "INTRODUCED", "optimistic row renders on submit"),
            evidence("E-004", "TEST", "INTRODUCED", "declined order rolls the row back"),
            evidence("E-005", "TEST", "INTRODUCED", "live region announces pending state"),
        ],
        "interactions": [
            {
                "id": "I-001",
                "name": "submit cart",
                "entry_point": "src/cart.js:1",
                "trigger": "user activates Submit",
                "blocking_work": "POST /orders and two downstream calls",
                "technique_ids": ["T-001"],
                "status": "IMPROVED",
                "baseline": {
                    "feedback_ms": 1820,
                    "meaningful_ms": 1820,
                    "settled_ms": 1840,
                    "dead_time_ms": 1820,
                    "samples": 7,
                    "evidence_ids": ["E-001"],
                },
                "after": {
                    "feedback_ms": 40,
                    "meaningful_ms": 120,
                    "settled_ms": 1830,
                    "dead_time_ms": 0,
                    "samples": 7,
                    "evidence_ids": ["E-002"],
                },
            }
        ],
        "techniques": [
            {
                "id": "T-001",
                "name": "optimistic-update",
                "status": "APPLIED",
                "interaction_ids": ["I-001"],
                "paths": ["src/cart.js", "tests/cart.rollback.test.js"],
                "optimistic": True,
                "reversible": True,
                "irreversible_effect": False,
                "failure_mode": "server declines the order",
                "rollback": "remove the optimistic row and restore prior cart state",
                "on_failure_ui": "inline decline message with a retry action",
                "accessibility": "pending and failure states announced through a polite live region",
                "progress_signal": "NONE",
                "progress_presentation": "NONE",
                "added_delay_ms": 0,
                "evidence_ids": ["E-003"],
                "failure_path_evidence_ids": ["E-004"],
            }
        ],
        "file_coverage": [
            {"path": "src/cart.js", "reason": "optimistic submit acknowledgement"},
            {"path": "tests/cart.rollback.test.js", "reason": "rollback proof for T-001"},
        ],
        "scope": {
            "initial_owned_paths": ["src/cart.js"],
            "current_owned_paths": ["src/cart.js", "tests/cart.rollback.test.js"],
            "scope_expansion_approved": False,
            "cycle": 1,
        },
        "gates": [
            {
                "name": "honest-feedback",
                "mandatory": True,
                "status": "PASS",
                "evidence_ids": ["E-002"],
            },
            {
                "name": "real-latency-non-regression",
                "mandatory": True,
                "status": "PASS",
                "evidence_ids": ["E-002"],
            },
            {
                "name": "failure-path-proof",
                "mandatory": True,
                "status": "PASS",
                "evidence_ids": ["E-004"],
            },
            {
                "name": "accessibility-announcement",
                "mandatory": True,
                "status": "PASS",
                "evidence_ids": ["E-005"],
            },
        ],
        "decision": {"result": "PERCEIVED_INSTANT", "remaining": []},
    }


def main() -> int:
    verify_classification()
    with tempfile.TemporaryDirectory(prefix="sam-perceived-") as temporary:
        root = pathlib.Path(temporary) / "repo"
        root.mkdir()
        bundles = build_fixture(root)
        receipts_dir = pathlib.Path(temporary) / "receipts"
        receipts = {
            evidence_id: make_receipt(receipts_dir, evidence_id, classification, "exit 0")
            for evidence_id, classification in (
                ("E-001", "BASELINE"),
                ("E-002", "TARGET"),
                ("E-003", "INTRODUCED"),
                ("E-004", "INTRODUCED"),
                ("E-005", "INTRODUCED"),
            )
        }
        baseline_path = pathlib.Path(temporary) / "baseline.json"
        current_path = pathlib.Path(temporary) / "current.json"
        baseline_path.write_text(json.dumps(bundles["baseline"]), encoding="utf-8")
        current_path.write_text(json.dumps(bundles["current"]), encoding="utf-8")
        report_path = pathlib.Path(temporary) / "report.json"
        valid = build_report(bundles, receipts)

        def check(report: dict[str, Any], expected: int, needle: str | None = None) -> None:
            report_path.write_text(json.dumps(report), encoding="utf-8")
            result = run(
                sys.executable,
                str(VALIDATOR),
                "--baseline",
                str(baseline_path),
                "--current",
                str(current_path),
                str(report_path),
                expected=expected,
            )
            if needle is not None and needle not in result.stderr:
                raise AssertionError(f"expected {needle!r} in:\n{result.stderr}")

        check(valid, 0)

        # Synthetic percentages are the canonical perceived-performance lie.
        fake_progress = copy.deepcopy(valid)
        fake_progress["techniques"][0].update(
            {"progress_signal": "SYNTHETIC", "progress_presentation": "DETERMINATE"}
        )
        check(fake_progress, 1, "fake progress is never allowed")

        no_signal = copy.deepcopy(valid)
        no_signal["techniques"][0]["progress_presentation"] = "INDETERMINATE"
        check(no_signal, 1, "shows progress with no underlying signal")

        # Never pretend an irreversible effect already succeeded.
        irreversible = copy.deepcopy(valid)
        irreversible["techniques"][0]["irreversible_effect"] = True
        check(irreversible, 1, "irreversible")

        unrecoverable = copy.deepcopy(valid)
        unrecoverable["techniques"][0]["reversible"] = False
        check(unrecoverable, 1, "cannot take back")

        for field in ("failure_mode", "rollback", "on_failure_ui"):
            missing = copy.deepcopy(valid)
            missing["techniques"][0][field] = ""
            check(missing, 1, f"T-001.{field} must be non-empty text")

        # The rollback must be proven, not described.
        unproven_rollback = copy.deepcopy(valid)
        unproven_rollback["techniques"][0]["failure_path_evidence_ids"] = []
        check(unproven_rollback, 1, "failure_path_evidence_ids must not be empty")

        inspection_proof = copy.deepcopy(valid)
        inspection_proof["evidence"].append(
            {
                "id": "E-006",
                "kind": "INSPECTION",
                "classification": "INTRODUCED",
                "status": "PASS",
                "detail": "read the rollback branch and it looks right",
            }
        )
        inspection_proof["techniques"][0]["failure_path_evidence_ids"] = ["E-006"]
        check(inspection_proof, 1, "requires executed MEASUREMENT or TEST evidence")

        no_accessibility = copy.deepcopy(valid)
        no_accessibility["techniques"][0]["accessibility"] = ""
        check(no_accessibility, 1, "T-001.accessibility must be non-empty text")

        # Feeling faster may not cost real speed.
        regressed = copy.deepcopy(valid)
        regressed["interactions"][0]["after"]["settled_ms"] = 2400
        check(regressed, 1, "real latency regressed")

        # Masking latency with sleep is not perceived performance.
        padded = copy.deepcopy(valid)
        padded["techniques"][0]["added_delay_ms"] = 900
        check(padded, 1, "anti-flicker ceiling")

        unjustified_delay = copy.deepcopy(valid)
        unjustified_delay["techniques"][0]["added_delay_ms"] = 120
        check(unjustified_delay, 1, "added_delay_reason must be non-empty")

        justified_delay = copy.deepcopy(valid)
        justified_delay["techniques"][0].update(
            {
                "added_delay_ms": 120,
                "added_delay_reason": "skeleton floor prevents a sub-frame flash",
            }
        )
        check(justified_delay, 0)

        # Budget and instantaneity claims are recomputed, never trusted.
        late_feedback = copy.deepcopy(valid)
        late_feedback["interactions"][0]["after"]["feedback_ms"] = 260
        check(late_feedback, 1, "allows first feedback within 100ms")

        dead_time = copy.deepcopy(valid)
        dead_time["interactions"][0]["after"]["dead_time_ms"] = 250
        check(dead_time, 1, "requires zero unacknowledged pending time")

        not_earlier = copy.deepcopy(valid)
        not_earlier["interactions"][0]["baseline"]["feedback_ms"] = 30
        check(not_earlier, 1, "first feedback did not get earlier")

        thin_samples = copy.deepcopy(valid)
        thin_samples["interactions"][0]["after"]["samples"] = 2
        check(thin_samples, 1, "samples to survive wall-clock noise")

        # Applicable gates cannot be waived, dropped, or downgraded.
        for name in (
            "honest-feedback",
            "real-latency-non-regression",
            "failure-path-proof",
            "accessibility-announcement",
        ):
            dropped = copy.deepcopy(valid)
            dropped["gates"] = [gate for gate in dropped["gates"] if gate["name"] != name]
            check(dropped, 1, f"must include the mandatory gate {name}")

            waived = copy.deepcopy(valid)
            for gate in waived["gates"]:
                if gate["name"] == name:
                    gate.update({"status": "NOT_APPLICABLE", "reason": "felt fine"})
                    gate.pop("evidence_ids", None)
            check(waived, 1, "cannot be")

        failed_gate = copy.deepcopy(valid)
        for gate in failed_gate["gates"]:
            if gate["name"] == "failure-path-proof":
                gate.update({"status": "FAIL", "reason": "rollback test is red"})
                gate.pop("evidence_ids", None)
        check(failed_gate, 1, "mandatory gate failure-path-proof did not pass")

        # Scope: unrelated dirty work stays untouched and unclaimed.
        claim_unrelated = copy.deepcopy(valid)
        claim_unrelated["scope"]["current_owned_paths"].append("src/unrelated.js")
        check(claim_unrelated, 1, "owned scope expanded beyond two times")

        # Editing someone else's pending work is a breach even if the report is tidy.
        (root / "src" / "unrelated.js").write_text(
            "export const other = 3;\n", encoding="utf-8"
        )
        tampered_bundle = json.loads(
            run(sys.executable, str(CAPTURE), "--repo", str(root)).stdout
        )
        tampered_path = pathlib.Path(temporary) / "tampered.json"
        tampered_path.write_text(json.dumps(tampered_bundle), encoding="utf-8")
        tampered_report = copy.deepcopy(valid)
        tampered_report["target"]["current_fingerprint"] = tampered_bundle["fingerprint"]
        tampered_report["file_coverage"].append(
            {"path": "src/unrelated.js", "reason": "collateral edit"}
        )
        report_path.write_text(json.dumps(tampered_report), encoding="utf-8")
        breach = run(
            sys.executable,
            str(VALIDATOR),
            "--baseline",
            str(baseline_path),
            "--current",
            str(tampered_path),
            str(report_path),
            expected=1,
        )
        if "pre-existing dirty work changed" not in breach.stderr:
            raise AssertionError(f"collateral edit was accepted:\n{breach.stderr}")
        (root / "src" / "unrelated.js").write_text(
            "export const other = 2;\n", encoding="utf-8"
        )

        unowned = copy.deepcopy(valid)
        unowned["scope"]["current_owned_paths"] = ["src/cart.js"]
        check(unowned, 1, "scope changed outside owned paths")

        phantom_path = copy.deepcopy(valid)
        phantom_path["techniques"][0]["paths"].append("src/never-touched.js")
        phantom_path["scope"]["current_owned_paths"].append("src/never-touched.js")
        check(phantom_path, 1, "is APPLIED but src/never-touched.js did not change")

        missing_coverage = copy.deepcopy(valid)
        missing_coverage["file_coverage"] = missing_coverage["file_coverage"][:1]
        check(missing_coverage, 1, "file_coverage must equal the scope delta")

        # Decision consistency.
        no_change = copy.deepcopy(valid)
        no_change["decision"] = {"result": "NO_CHANGE", "remaining": []}
        check(no_change, 1, "NO_CHANGE contradicts applied techniques")

        blocked_but_instant = copy.deepcopy(valid)
        blocked_but_instant["interactions"].append(
            {
                "id": "I-002",
                "name": "load history",
                "entry_point": "src/history.js:1",
                "trigger": "user opens history",
                "blocking_work": "GET /history",
                "technique_ids": [],
                "status": "BLOCKED",
                "reason": "no staging data to measure against",
            }
        )
        check(blocked_but_instant, 1, "completion contradicts blockers")

        unchanged_with_applied = copy.deepcopy(valid)
        unchanged_with_applied["interactions"][0].update(
            {"status": "UNCHANGED", "reason": "already fast"}
        )
        check(unchanged_with_applied, 1, "claims UNCHANGED while citing applied")

        broken_backlink = copy.deepcopy(valid)
        broken_backlink["techniques"][0]["interaction_ids"] = ["I-999"]
        check(broken_backlink, 1, "references unknown interaction I-999")

        # Receipts: the report cannot outrun what actually ran.
        failing = make_receipt(receipts_dir / "failing", "E-002", "TARGET", "exit 1")
        lying = copy.deepcopy(valid)
        for item in lying["evidence"]:
            if item["id"] == "E-002":
                item.update({"receipt": failing["path"], "command": failing["command"]})
        check(lying, 1, "its receipt records")

        single = make_receipt(receipts_dir / "single", "E-002", "TARGET", "exit 0", repeat=1)
        unrepeated = copy.deepcopy(valid)
        for item in unrepeated["evidence"]:
            if item["id"] == "E-002":
                item.update({"receipt": single["path"], "command": single["command"]})
        check(unrepeated, 1, "must run at least")

        flake_flag = receipts_dir / "flake.flag"
        flaky = make_receipt(
            receipts_dir / "flaky",
            "E-002",
            "TARGET",
            f"test -f {shlex.quote(str(flake_flag))} && exit 1; "
            f"touch {shlex.quote(str(flake_flag))}; exit 0",
            repeat=3,
        )
        flaky_report = copy.deepcopy(valid)
        for item in flaky_report["evidence"]:
            if item["id"] == "E-002":
                item.update(
                    {
                        "receipt": flaky["path"],
                        "command": flaky["command"],
                        "status": flaky["status"],
                    }
                )
        check(flaky_report, 1, "flaky")

        wrong_command = copy.deepcopy(valid)
        for item in wrong_command["evidence"]:
            if item["id"] == "E-002":
                item["command"] = "/bin/sh -c 'some other measurement'"
        check(wrong_command, 1, "does not match the executed argv")

        log = receipts_dir / "E-002.run1.log"
        original = log.read_bytes()
        log.write_bytes(original + b"fabricated 40ms\n")
        check(copy.deepcopy(valid), 1, "log hash does not match")
        log.write_bytes(original)

        no_receipt = copy.deepcopy(valid)
        for item in no_receipt["evidence"]:
            if item["id"] == "E-002":
                item.pop("receipt")
        check(no_receipt, 1, "requires a receipt path")

        # Measurement without a stated device and network profile is uncomparable.
        for field in ("device_profile", "network_profile", "identity"):
            vague = copy.deepcopy(valid)
            vague["environment"][field] = ""
            check(vague, 1, f"environment.{field} must be non-empty text")

        stale_bundle = copy.deepcopy(valid)
        stale_bundle["target"]["current_fingerprint"] = "0" * 64
        check(stale_bundle, 1, "target.current_fingerprint does not match")

    print(
        "PASS: perception budget table, receipt coupling, honesty, accessibility, "
        "scope, and decision fixtures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
