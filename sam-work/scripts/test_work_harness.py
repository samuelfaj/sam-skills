#!/usr/bin/env python3
"""Run adversarial checks against the sam-work report validator and scaffold.

The real validator and scaffold are copied into a temporary skills tree whose
sibling child validators are stubs, so child-report re-validation, head checks,
fingerprint pinning, and git-verified carry-forward run for real. Scope captures
for the committed-delta cases come from the real sam-fix-bug capture_scope.py.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
CAPTURE_SCOPE = SCRIPT_DIR.parents[1] / "sam-fix-bug" / "scripts" / "capture_scope.py"
CAPTURE_PHASES = {"implementation", "refine", "simplify"}
# main() replaces HEAD, BASE, and REPO with a real repository: the validator
# recomputes target.final_change_fingerprint from git.
HEAD = "a" * 40
BASE = "b" * 40
REPO = "/tmp/repository"
FP = "c" * 64
CHILD_FP = "9" * 64
STUB = """import json, sys
report = json.load(open(sys.argv[-1], encoding="utf-8"))
if report.get("stub_invalid"):
    print("FAIL: stub rejects report", file=sys.stderr)
    sys.exit(1)
if report.get("stub_bytes"):
    sys.stderr.buffer.write(b"FAIL: non-UTF-8 caf\\xe9\\n")
    sys.exit(1)
print("PASS: stub {name}")
"""
CHILD_SCRIPTS = [
    ("sam-fix-bug", "validate_report.py"),
    ("sam-create-feature", "validate_report.py"),
    ("sam-refine-task", "validate_report.py"),
    ("sam-review", "validate_review.py"),
    ("sam-simplify-task", "validate_report.py"),
    ("sam-create-test-coverage", "validate_coverage_report.py"),
    ("sam-pr-description", "validate_description.py"),
    ("sam-create-playwright-tests", "validate_e2e_report.py"),
    ("sam-create-task-demo-video", "validate_demo_report.py"),
]
GIT_ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="harness",
    GIT_AUTHOR_EMAIL="harness@example.test",
    GIT_COMMITTER_NAME="harness",
    GIT_COMMITTER_EMAIL="harness@example.test",
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_CONFIG_SYSTEM=os.devnull,
)


class Tree:
    """Temporary skills root with the real sam-work scripts and stub children."""

    def __init__(self, root: Path) -> None:
        self.root = root
        skills = root / "skills"
        work = skills / "sam-work" / "scripts"
        work.mkdir(parents=True)
        for name in ("validate_work_report.py", "scaffold_work_report.py"):
            shutil.copy2(SCRIPT_DIR / name, work / name)
        for skill, script in CHILD_SCRIPTS:
            path = skills / skill / "scripts" / script
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(STUB.format(name=skill), encoding="utf-8")
        self.scaffold = work / "scaffold_work_report.py"
        spec = importlib.util.spec_from_file_location(
            "validate_work_report_copy", work / "validate_work_report.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load copied sam-work validator")
        self.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.validator)
        self.reports = root / "reports"
        self.reports.mkdir()
        self.counter = 0

    def synthetic_capture(self, repo_root: str, head: str) -> Path:
        """A clean scope capture (no dirty files) for reports without a real repository."""
        self.counter += 1
        path = self.reports / f"{self.counter:03d}-capture.json"
        body = {"capture_read_only": True, "files": [], "head_sha": head, "repo_root": repo_root}
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def capture(self, repo: Path, name: str) -> Path:
        """Run the real capture_scope.py against the repository's current state."""
        result = subprocess.run(
            [sys.executable, "-B", str(CAPTURE_SCOPE), "--repo", str(repo)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        path = self.reports / name
        path.write_text(result.stdout, encoding="utf-8")
        return path

    def child(self, phase_id: str, head: str, status: str | None, **extra: Any) -> Path:
        self.counter += 1
        if phase_id in {"implementation", "refine", "simplify"}:
            target = {"current_head_sha": head, "current_fingerprint": CHILD_FP}
        elif phase_id == "proposal":
            target = {"head_sha": head, "context_fingerprint": CHILD_FP}
        else:
            target = {"head_sha": head, "bundle_fingerprint": CHILD_FP}
        body: dict[str, Any] = {"schema_version": 1, "target": target}
        if status is not None:
            body["decision"] = {"result": status}
        body.update(extra)
        path = self.reports / f"{self.counter:03d}-{phase_id}.json"
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iteration(status: str, report: Path | None = None) -> dict[str, Any]:
    return {
        "sequence": 1,
        "input_fingerprint": CHILD_FP if report else "d" * 64,
        "output_fingerprint": sha256(report) if report else "e" * 64,
        "status": status,
        "open_required_items": [],
        "correction_receipts": [],
        "evidence": [f"receipt for {status}"],
    }


def phase(
    tree: Tree,
    phase_id: str,
    skill: str,
    status: str,
    *,
    head: str | None = None,
    child_head: str | None = None,
    carried: str | None = None,
    committed: str | None = None,
    captures: tuple[Path, Path] | None = None,
    repo_root: str | None = None,
    applicability: str = "REQUIRED",
    reason: str | None = None,
    child_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    head = head or HEAD
    repo_root = repo_root or REPO
    report: Path | None = None
    validator_args: list[str] = []
    if applicability == "REQUIRED":
        child_status = None if phase_id == "proposal" else status
        report = tree.child(phase_id, child_head or head, child_status, **(child_extra or {}))
        if phase_id in CAPTURE_PHASES:
            if captures is None:
                clean = tree.synthetic_capture(repo_root, child_head or head)
                captures = (clean, clean)
            validator_args = ["--baseline", str(captures[0]), "--current", str(captures[1])]
    return {
        "id": phase_id,
        "skill": skill,
        "applicability": applicability,
        "status": status,
        "current": True,
        "validated_head_sha": head,
        "not_applicable_reason": reason,
        "report_path": str(report) if report else None,
        "validator_args": validator_args,
        "carried_forward_from": carried,
        "committed_head_sha": committed,
        "evidence": [f"evidence for {phase_id}"],
        "validator_receipts": [f"PASS: stub {skill}"],
        "iterations": [iteration(status, report)],
    }


def environment() -> dict[str, Any]:
    return {
        "kind": "DEVELOPMENT",
        "identity_verified": True,
        "identity_evidence": ["verified isolated development database"],
        "real_data": True,
        "dedicated_data": True,
        "cleanup_status": "COMPLETE",
        "privacy_review": "PASS",
    }


def artifact(phase_id: str, suffix: str) -> dict[str, Any]:
    extension = "webm" if phase_id == "playwright" else "mp4"
    return {
        "phase": phase_id,
        "local_path": f"/tmp/{phase_id}-{suffix}.{extension}",
        "sha256": ("1" if phase_id == "playwright" else "2") * 64,
        "uploaded_url": f"https://example.test/assets/{phase_id}-{suffix}",
        "upload_receipt": f"uploaded {phase_id}-{suffix}",
        "player_verified": True,
        "readback_evidence": [f"rendered player for {phase_id}-{suffix}"],
    }


def diff_fingerprint(repo_root: str, base: str, head: str) -> str:
    """sha256 of the raw diff bytes; FP when repo_root is not a repository."""
    result = subprocess.run(
        ["git", "-C", repo_root, "diff", "--binary", "--no-color", "--no-ext-diff", "--no-renames", base, head],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=GIT_ENV,
    )
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else FP


def valid_report(
    tree: Tree,
    *,
    web: bool = True,
    classification: str = "BUG",
    head: str | None = None,
    base: str | None = None,
    repo_root: str | None = None,
    carried_from: str | None = None,
    coverage_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    head, base, repo_root = head or HEAD, base or BASE, repo_root or REPO
    fingerprint = diff_fingerprint(repo_root, base, head)
    implementation_skill = "sam-fix-bug" if classification == "BUG" else "sam-create-feature"

    def carried_phase(phase_id: str, skill: str, status: str) -> dict[str, Any]:
        return phase(
            tree,
            phase_id,
            skill,
            status,
            head=head,
            child_head=carried_from,
            carried=carried_from,
            repo_root=repo_root,
        )

    playwright = (
        phase(tree, "playwright", "sam-create-playwright-tests", "COMPLETE", head=head)
        if web
        else phase(
            tree,
            "playwright",
            "sam-create-playwright-tests",
            "NOT_APPLICABLE",
            head=head,
            applicability="NOT_APPLICABLE",
            reason="repository exposes no browser-accessible runtime",
        )
    )
    artifacts = [artifact("demo", "one")]
    if web:
        artifacts.insert(0, artifact("playwright", "one"))
    return {
        "schema_version": 2,
        "workflow_id": "work-001",
        "request": {
            "prompt_sha256": "3" * 64,
            "classification": classification,
            "web_system": web,
            "classification_evidence": ["expected existing behavior is broken"],
        },
        "authorization": {
            "create_or_update_proposal": True,
            "publish_playwright_videos": True,
            "publish_demo_video": True,
            "merge": False,
            "deploy": False,
        },
        "target": {
            "repo_root": repo_root,
            "base_ref": "main",
            "base_sha": base,
            "final_head_sha": head,
            "final_change_fingerprint": fingerprint,
        },
        "phases": [
            carried_phase("implementation", implementation_skill, "COMPLETE"),
            carried_phase("refine", "sam-refine-task", "HIGH_CONFIDENCE"),
            phase(tree, "review", "sam-review", "APPROVE", head=head),
            carried_phase("simplify", "sam-simplify-task", "SIMPLEST_DEFENSIBLE"),
            phase(
                tree,
                "coverage",
                "sam-create-test-coverage",
                "FULL",
                head=head,
                child_extra=coverage_extra,
            ),
            phase(tree, "proposal", "sam-pr-description", "READY", head=head),
            playwright,
            phase(tree, "demo", "sam-create-task-demo-video", "PUBLISHED", head=head),
        ],
        "proposal": {
            "platform": "example",
            "url": "https://example.test/proposals/1",
            "proposal_id": "1",
            "created_by_workflow": True,
            "description_validated": True,
            "description_receipt": "PASS: proposal body",
            "remote_head_sha": head,
            "rendered_readback_evidence": ["read back description and players"],
            "required_ci_status": "PASS",
        },
        "environments": {
            "demo": environment(),
            "playwright": environment() if web else None,
        },
        "video_inventory": {
            "playwright_discovered": 1 if web else 0,
            "playwright_uploaded": 1 if web else 0,
            "demo_discovered": 1,
            "demo_uploaded": 1,
        },
        "artifacts": artifacts,
        "final": {
            "result": "COMPLETE",
            "completed_phase_ids": list(tree.validator.PHASE_IDS),
            "blockers": [],
            "final_head_sha": head,
            "final_change_fingerprint": fingerprint,
        },
    }


def expect_valid(tree: Tree, name: str, report: dict[str, Any]) -> None:
    errors = tree.validator.validate(report)
    if errors:
        raise AssertionError(f"{name}: expected valid report, got {errors}")


def expect_invalid(
    tree: Tree,
    name: str,
    report: dict[str, Any],
    expected_fragment: str,
) -> None:
    errors = tree.validator.validate(report)
    if not any(expected_fragment in error for error in errors):
        raise AssertionError(
            f"{name}: expected error containing {expected_fragment!r}, got {errors}"
        )


def mutate(report: dict[str, Any], fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    changed = copy.deepcopy(report)
    fn(changed)
    return changed


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=GIT_ENV,
    )
    return result.stdout.strip()


def commit(repo: Path, files: dict[str, str], message: str, moves: dict[str, str] | None = None) -> str:
    for source, destination in (moves or {}).items():
        (repo / destination).parent.mkdir(parents=True, exist_ok=True)
        git(repo, "mv", source, destination)
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def run_scaffold(tree: Tree, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, "-B", str(tree.scaffold), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    if result.returncode != 0:
        raise AssertionError(f"scaffold {args[0]} failed: {result.stdout}{result.stderr}")
    return result.stdout.strip()


def fill_placeholders(report: dict[str, Any]) -> None:
    """What the agent types after the scaffold: evidence, readback, environments."""
    report["request"]["classification_evidence"] = ["expected existing behavior is broken"]
    report["proposal"].update(
        {
            "platform": "example",
            "url": "https://example.test/proposals/9",
            "proposal_id": "9",
            "created_by_workflow": True,
            "description_validated": True,
            "description_receipt": "PASS: proposal body",
            "remote_head_sha": report["target"]["final_head_sha"],
            "rendered_readback_evidence": ["body markup lists 2 expected embeds"],
            "required_ci_status": "PASS",
        }
    )
    for name in ("demo", "playwright"):
        report["environments"][name] = environment()
    report["video_inventory"].update(
        playwright_discovered=1, playwright_uploaded=1, demo_discovered=1, demo_uploaded=1
    )
    report["artifacts"] = [artifact("playwright", "rt"), artifact("demo", "rt")]
    for phase_record in report["phases"]:
        for item in phase_record["iterations"]:
            item["correction_receipts"] = [
                "fixed authorization gap with regression test"
                if receipt.startswith("SCAFFOLD:")
                else receipt
                for receipt in item["correction_receipts"]
            ]
    report["final"]["result"] = "COMPLETE"


def new_repo(tree: Tree, name: str) -> tuple[Path, str]:
    repo = tree.root / name
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    return repo, commit(repo, {"src/app.py": "v1\n", "src/other.py": "o1\n"}, "base")


def worker_phase_dir(tree: Tree, phase_id: str) -> Path:
    phase_dir = tree.root / "work" / phase_id
    phase_dir.mkdir(parents=True, exist_ok=True)
    return phase_dir


def captured_child(
    tree: Tree, repo: Path, phase_id: str, status: str, edit: dict[str, str] | None = None
) -> tuple[Path, list[str]]:
    """A worker's capture-based child run: baseline, optional uncommitted edit, current.

    Edits change file size: a same-size edit inside the index's mtime window can
    be captured as clean (racy stat), which would make this harness flaky.
    """
    phase_dir = worker_phase_dir(tree, phase_id)
    baseline = tree.capture(repo, f"{phase_id}-{tree.counter}-baseline.json")
    for name, text in (edit or {}).items():
        (repo / name).write_text(text, encoding="utf-8")
    current = tree.capture(repo, f"{phase_id}-{tree.counter}-current.json")
    head = git(repo, "rev-parse", "HEAD")
    report = Path(shutil.move(str(tree.child(phase_id, head, status)), phase_dir / "report.json"))
    args = ["--baseline", str(baseline), "--current", str(current)]
    (phase_dir / "validator-args.json").write_text(json.dumps(args), encoding="utf-8")
    return report, args


def scaffold_round_trip(tree: Tree) -> None:
    """Realistic run: the implementation child reports on uncommitted work, sam-work commits it."""
    repo, base = new_repo(tree, "repo-rt")
    out = tree.root / "work-report.json"
    run_scaffold(
        tree,
        "init",
        "--out", str(out),
        "--repo", str(repo),
        "--base-ref", "main",
        "--base-sha", base,
        "--classification", "BUG",
        "--web-system", "true",
        "--prompt-sha256", "3" * 64,
        "--workflow-id", "work-rt",
    )
    initial = json.loads(out.read_text(encoding="utf-8"))
    fail_closed = [
        initial["environments"]["demo"]["real_data"],
        initial["environments"]["playwright"]["dedicated_data"],
        initial["proposal"]["created_by_workflow"],
        initial["proposal"]["description_validated"],
    ]
    if not all(isinstance(value, str) and value.startswith("SCAFFOLD:") for value in fail_closed):
        raise AssertionError(f"init must leave safety attestations fail-closed: {fail_closed}")

    def record(phase_id: str, child: Path) -> None:
        line = run_scaffold(tree, "record", str(out), "--phase", phase_id, "--child", str(child))
        if f"recorded {phase_id}" not in line:
            raise AssertionError(f"scaffold record printed {line!r}")

    implementation, _ = captured_child(tree, repo, "implementation", "COMPLETE", {"src/app.py": "v2 fixed\n"})
    record("implementation", implementation)
    h1 = commit(repo, {"src/app.py": "v2 fixed\n"}, "fix, committed by sam-work after the child report")
    refine, _ = captured_child(tree, repo, "refine", "HIGH_CONFIDENCE")
    record("refine", refine)
    first_review = tree.child(
        "review", h1, "CHANGES_REQUIRED",
        decision={"result": "CHANGES_REQUIRED", "remaining_corrections": ["authorization gap"]},
    )
    record("review", first_review)
    simplify, _ = captured_child(tree, repo, "simplify", "NO_CHANGE")
    record("simplify", simplify)
    h2 = commit(repo, {"tests/test_app.py": "t1\n"}, "coverage tests")
    for phase_id in ("review", "coverage", "proposal", "playwright", "demo"):
        status = None if phase_id == "proposal" else sorted(tree.validator.FINAL_STATUSES[phase_id])[0]
        child = tree.child(phase_id, h2, status)
        if phase_id == "demo":
            # A worker leaves validator-args.json beside its report; record picks it up.
            phase_dir = worker_phase_dir(tree, "demo")
            child = Path(shutil.move(str(child), phase_dir / "report.json"))
            (phase_dir / "validator-args.json").write_text(
                json.dumps(["--manifest", str(phase_dir / "manifest.json")]), encoding="utf-8"
            )
            record(phase_id, child)
            continue
        flag = "--context" if phase_id == "proposal" else "--bundle"
        line = run_scaffold(
            tree, "record", str(out), "--phase", phase_id, "--child", str(child),
            f"--validator-arg={flag}", f"--validator-arg={child}",
        )
        if f"recorded {phase_id}" not in line:
            raise AssertionError(f"scaffold record printed {line!r}")
    summary = run_scaffold(tree, "finalize", str(out))
    expected = ("stale=none", "committed=implementation", "carried=implementation,refine,simplify")
    if not all(part in summary for part in expected):
        raise AssertionError(f"scaffold finalize did not derive the commit anchor: {summary}")
    report = json.loads(out.read_text(encoding="utf-8"))
    implementation_phase = report["phases"][0]
    if (
        report["target"]["final_head_sha"] != h2
        or implementation_phase["committed_head_sha"] != h1
        or implementation_phase["carried_forward_from"] != h1
        or report["phases"][1]["committed_head_sha"] is not None
    ):
        raise AssertionError("scaffold did not derive heads from git, captures, and child reports")
    expect_invalid(tree, "scaffold leaves typed fields fail-closed", report, "unfilled scaffold placeholder")
    if report["phases"][7]["validator_args"] != ["--manifest", str(tree.root / "work" / "demo" / "manifest.json")]:
        raise AssertionError("scaffold record did not read validator-args.json")
    review = report["phases"][2]
    if len(review["iterations"]) != 2 or review["iterations"][0]["status"] != "CHANGES_REQUIRED":
        raise AssertionError("scaffold did not keep the review rewind as iteration 1")
    fill_placeholders(report)
    expect_valid(tree, "scaffold round-trip", report)


def committed_delta_cases(tree: Tree) -> int:
    """Implementation proof anchors at the commit holding its captured uncommitted delta."""
    repo, base = new_repo(tree, "repo-commit")
    root = str(repo)
    baseline = tree.capture(repo, "commit-baseline.json")
    (repo / "src/app.py").write_text("v2 fixed\n", encoding="utf-8")
    current = tree.capture(repo, "commit-current.json")
    h1 = commit(repo, {"src/app.py": "v2 fixed\n"}, "commit exactly the captured delta")
    h2 = commit(repo, {"tests/test_app.py": "t1\n"}, "tests only")

    def with_implementation(head: str, committed: str | None, carried: str | None) -> dict[str, Any]:
        report = valid_report(tree, head=head, base=base, repo_root=root)
        report["phases"][0] = phase(
            tree, "implementation", "sam-fix-bug", "COMPLETE", head=head, child_head=base,
            committed=committed, carried=carried, captures=(baseline, current), repo_root=root,
        )
        return report

    expect_valid(
        tree,
        "implementation delta committed unchanged, then a test-only delta",
        with_implementation(h2, h1, h1),
    )
    expect_valid(tree, "implementation delta committed as the final head", with_implementation(h1, h1, None))
    expect_invalid(
        tree,
        "a report head without the commit anchor is stale",
        with_implementation(h1, None, None),
        "child delta is not committed",
    )
    expect_invalid(
        tree,
        "carry-forward from the pre-commit head is rejected",
        with_implementation(h2, None, base),
        "child delta is not committed",
    )
    # Refine is read-only: run on the uncommitted implementation, its proof covers
    # every captured dirty file, so the implementation commit anchors it too.
    refine_dirty = valid_report(tree, head=h1, base=base, repo_root=root)
    refine_dirty["phases"][1] = phase(
        tree, "refine", "sam-refine-task", "HIGH_CONFIDENCE", head=h1, child_head=base,
        committed=h1, captures=(current, current), repo_root=root,
    )
    expect_valid(tree, "refine on the uncommitted implementation anchors at its commit", refine_dirty)
    borrowed = valid_report(tree, head=h1, base=base, repo_root=root)
    borrowed["phases"][0] = phase(
        tree, "implementation", "sam-fix-bug", "COMPLETE", head=h1, child_head=base,
        committed=h1, captures=(current, current), repo_root=root,
    )
    expect_invalid(
        tree,
        "implementation cannot claim a commit of pre-existing dirty work it did not change",
        borrowed,
        "does not match the child's captured delta: src/app.py",
    )
    git(repo, "checkout", "-q", "-b", "extra", base)
    extra = commit(repo, {"src/app.py": "v2 fixed\n", "src/other.py": "o2 extra\n"}, "delta plus an extra production edit")
    expect_invalid(
        tree,
        "an extra production edit in the commit is not the captured delta",
        with_implementation(extra, extra, None),
        "does not match the child's captured delta: src/other.py",
    )
    git(repo, "checkout", "-q", "-b", "partial", base)
    partial = commit(repo, {"src/other.py": "o2 extra\n"}, "unrelated commit without the captured delta")
    expect_invalid(
        tree,
        "a commit missing the captured delta is rejected",
        with_implementation(partial, partial, None),
        "does not match the child's captured delta: src/app.py",
    )
    return 8


def carry_forward_cases(tree: Tree) -> int:
    repo, base = new_repo(tree, "repo")
    h1 = commit(repo, {"src/app.py": "v2\n"}, "fix")
    h2 = commit(
        repo,
        {
            "tests/test_app.py": "t1\n",
            "web/app.spec.ts": "s1\n",
            "pkg/app_test.go": "g1\n",
            "spec/app_spec.rb": "r1\n",
        },
        "tests only",
    )
    root = str(repo)

    expect_valid(
        tree,
        "test-only delta carries implementation/refine/simplify forward",
        valid_report(tree, head=h2, base=base, repo_root=root, carried_from=h1),
    )
    cases = 1

    h3 = commit(repo, {"src/app.py": "v3\n"}, "production delta")
    expect_invalid(
        tree,
        "production delta cannot carry forward",
        valid_report(tree, head=h3, base=base, repo_root=root, carried_from=h1),
        "carry-forward rejected",
    )
    cases += 1

    h4 = commit(repo, {}, "move production file under tests", moves={"src/other.py": "tests/other.py"})
    expect_invalid(
        tree,
        "a rename out of production is not test-only",
        valid_report(tree, head=h4, base=base, repo_root=root, carried_from=h3),
        "carry-forward rejected",
    )
    cases += 1

    review_carried = valid_report(tree, head=h2, base=base, repo_root=root, carried_from=h1)
    review_carried["phases"][2] = phase(
        tree, "review", "sam-review", "APPROVE", head=h2, child_head=h1, carried=h1
    )
    expect_invalid(tree, "review proof never carries forward", review_carried, "carry-forward is allowed only")
    cases += 1

    typed_claim = valid_report(tree, head=h2, base=base, repo_root="/tmp/not-a-repo", carried_from=h1)
    expect_invalid(tree, "carry-forward needs a verifiable repository", typed_claim, "cannot verify carry-forward")
    cases += 1

    # Contracts under spec/e2e directories, production classes named *Test, modules
    # named like tests, and test-looking config/contract files are implementation
    # inputs: stale proof must not carry across them.
    for production in (
        "api/specs/openapi.yaml",
        "src/main/kotlin/AbTest.kt",
        "src/e2e/server.ts",
        "api/openapi.spec.yaml",
        "api/openapi_spec.json",
        "db/schema_spec.sql",
        "config/app.test.env",
        "src/ab_test.py",
        "app/models/ab_test.rb",
    ):
        git(repo, "checkout", "-q", "-B", "look-alike", h2)
        look_alike = commit(repo, {production: "x\n"}, f"production edit {production}")
        expect_invalid(
            tree,
            f"{production} is not test-only",
            valid_report(tree, head=look_alike, base=base, repo_root=root, carried_from=h1),
            f"carry-forward rejected: production paths changed since {h1[:12]}: {production}",
        )
        cases += 1

    scaffold_round_trip(tree)
    return cases + 1 + committed_delta_cases(tree) + byte_exact_cases(tree)


def byte_exact_cases(tree: Tree) -> int:
    """Git output is bytes: Latin-1 content, CRLF, and non-UTF-8 paths never crash or drift."""
    repo, base = new_repo(tree, "repo-bytes")
    (repo / "latin.txt").write_bytes(b"caf\xe9\r\nline2\r\n")
    (repo / "crlf.txt").write_bytes("utf é\r\nx\r\n".encode("utf-8"))
    git(repo, "add", "latin.txt", "crlf.txt")
    git(repo, "commit", "-q", "-m", "latin-1 and CRLF content")
    out = tree.root / "bytes-work-report.json"
    run_scaffold(
        tree, "init", "--out", str(out), "--repo", str(repo), "--base-ref", "main", "--base-sha", base,
        "--classification", "BUG", "--web-system", "false", "--prompt-sha256", "3" * 64,
        "--workflow-id", "work-bytes",
    )
    run_scaffold(tree, "finalize", str(out))
    raw = subprocess.run(
        ["git", "-C", str(repo), "diff", "--binary", "--no-color", "--no-ext-diff", "--no-renames", base, "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        env=GIT_ENV,
    ).stdout
    fingerprint = json.loads(out.read_text(encoding="utf-8"))["target"]["final_change_fingerprint"]
    if fingerprint != hashlib.sha256(raw).hexdigest():
        raise AssertionError("final_change_fingerprint must be sha256 of the raw git diff --binary bytes")

    # A non-UTF-8 path (plumbing: APFS rejects such file names) must yield an INVALID line.
    h1 = git(repo, "rev-parse", "HEAD")
    blob_source = tree.root / "blob.txt"
    blob_source.write_text("x\n", encoding="utf-8")
    blob = git(repo, "hash-object", "-w", str(blob_source))
    subprocess.run(
        [b"git", b"-C", os.fsencode(repo), b"update-index", b"--add", b"--cacheinfo",
         b"100644," + blob.encode() + b",src/caf\xe9.py"],
        check=True,
        env=GIT_ENV,
    )
    git(repo, "commit", "-q", "-m", "non-UTF-8 production path")
    h2 = git(repo, "rev-parse", "HEAD")
    report_file = tree.root / "bytes-carry.json"
    report_file.write_text(
        json.dumps(valid_report(tree, head=h2, base=base, repo_root=str(repo), carried_from=h1)),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-B", str(tree.scaffold.parent / "validate_work_report.py"), str(report_file)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    if result.returncode != 1 or "ERROR:" not in result.stderr or "carry-forward rejected" not in result.stderr:
        raise AssertionError(f"non-UTF-8 production path must be rejected, not crash: {result.stderr[-400:]}")
    return 2


def main() -> int:
    skill = (SCRIPT_DIR.parent / "SKILL.md").read_text(encoding="utf-8")
    if "Exclusive top pipeline" not in skill:
        raise AssertionError("sam-work must declare Exclusive top pipeline")
    if "same branch" not in skill:
        raise AssertionError("sam-work must fix forward on the same branch")
    if "FOLLOW_UP" not in skill or "parked" not in skill:
        raise AssertionError("sam-work must park FOLLOW_UP findings")

    global HEAD, BASE, REPO
    with tempfile.TemporaryDirectory(prefix="sam-work-harness-") as raw:
        tree = Tree(Path(raw))
        default_repo, BASE = new_repo(tree, "repo-default")
        HEAD = commit(default_repo, {"src/app.py": "v2 fixed\n"}, "fix")
        REPO = str(default_repo)
        bug_web = valid_report(tree, web=True, classification="BUG")
        feature_nonweb = valid_report(tree, web=False, classification="FEATURE")
        expect_valid(tree, "bug web happy path", bug_web)
        expect_valid(tree, "feature non-web happy path", feature_nonweb)

        rewound = copy.deepcopy(bug_web)
        rewound["phases"][0]["iterations"].insert(
            0,
            {
                **iteration("CHANGES_REQUIRED"),
                "open_required_items": ["regression test missing"],
                "correction_receipts": ["added regression test"],
            },
        )
        rewound["phases"][0]["iterations"][1]["sequence"] = 2
        expect_valid(tree, "implementation child CHANGES_REQUIRED is a recordable iteration", rewound)

        delegated = {"real_system_proof": {"status": "NOT_APPLICABLE", "reason": "delegated to playwright phase"}}
        expect_valid(
            tree,
            "coverage delegation with playwright COMPLETE on the final head",
            valid_report(tree, coverage_extra=delegated),
        )

        stale_child = copy.deepcopy(bug_web)
        stale_child["phases"][2] = phase(tree, "review", "sam-review", "APPROVE", child_head=BASE)
        edited = copy.deepcopy(bug_web)
        edited_path = Path(edited["phases"][4]["report_path"])
        edited_path.write_text(edited_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        status_drift = copy.deepcopy(bug_web)
        status_drift["phases"][2] = phase(tree, "review", "sam-review", "APPROVE")
        drift_path = Path(status_drift["phases"][2]["report_path"])
        drift_body = json.loads(drift_path.read_text(encoding="utf-8"))
        drift_body["decision"]["result"] = "CHANGES_REQUIRED"
        drift_path.write_text(json.dumps(drift_body), encoding="utf-8")
        status_drift["phases"][2]["iterations"][0]["output_fingerprint"] = sha256(drift_path)

        cases: list[tuple[str, dict[str, Any], str]] = [
            (
                "missing phase",
                mutate(bug_web, lambda r: r["phases"].pop(2)),
                "exactly all eight",
            ),
            (
                "wrong implementation router",
                mutate(
                    bug_web,
                    lambda r: r["phases"][0].update(skill="sam-create-feature"),
                ),
                "must use sam-fix-bug",
            ),
            (
                "review not closed",
                mutate(
                    bug_web,
                    lambda r: (
                        r["phases"][2].update(status="CHANGES_REQUIRED"),
                        r["phases"][2]["iterations"][0].update(
                            status="CHANGES_REQUIRED",
                            open_required_items=["authorization gap"],
                            correction_receipts=["pending correction"],
                        ),
                    ),
                ),
                "does not have an accepted final status",
            ),
            (
                "stale refinement",
                mutate(
                    bug_web,
                    lambda r: r["phases"][1].update(validated_head_sha=BASE),
                ),
                "proof is stale",
            ),
            (
                "missing child validator",
                mutate(
                    bug_web,
                    lambda r: r["phases"][4].update(validator_receipts=[]),
                ),
                "requires validator receipts",
            ),
            (
                "web Playwright skipped",
                mutate(
                    bug_web,
                    lambda r: r["phases"][6].update(
                        applicability="NOT_APPLICABLE",
                        status="NOT_APPLICABLE",
                        not_applicable_reason="too difficult",
                    ),
                ),
                "must be REQUIRED",
            ),
            (
                "non-web without applicability proof",
                mutate(
                    feature_nonweb,
                    lambda r: r["phases"][6].update(not_applicable_reason=""),
                ),
                "requires a concrete reason",
            ),
            (
                "unverified development environment",
                mutate(
                    bug_web,
                    lambda r: r["environments"]["playwright"].update(
                        identity_verified=False
                    ),
                ),
                "identity must be verified",
            ),
            (
                "missing browser upload",
                mutate(
                    bug_web,
                    lambda r: r["video_inventory"].update(playwright_uploaded=0),
                ),
                "every discovered Playwright video",
            ),
            (
                "unverified player",
                mutate(
                    bug_web,
                    lambda r: r["artifacts"][0].update(player_verified=False),
                ),
                "verified rendered video player",
            ),
            (
                "demo is not MP4",
                mutate(
                    bug_web,
                    lambda r: r["artifacts"][1].update(local_path="/tmp/demo.webm"),
                ),
                "demo video must be an MP4",
            ),
            (
                "proposal head drift",
                mutate(
                    bug_web,
                    lambda r: r["proposal"].update(remote_head_sha=BASE),
                ),
                "remote head does not match",
            ),
            (
                "merge authorization widened",
                mutate(
                    bug_web,
                    lambda r: r["authorization"].update(merge=True),
                ),
                "write boundary",
            ),
            (
                "blocked declared complete",
                mutate(
                    bug_web,
                    lambda r: r["final"].update(blockers=["demo upload failed"]),
                ),
                "cannot have blockers",
            ),
            # Freshness is proven from the child report files, not typed strings.
            (
                "typed head without a child report",
                mutate(bug_web, lambda r: r["phases"][3].update(report_path=None)),
                "report_path must be an absolute path",
            ),
            ("child report from an older head", stale_child, "child report head"),
            (
                "child validator rejects the cited report",
                mutate(
                    bug_web,
                    lambda r: r["phases"].__setitem__(
                        5,
                        phase(tree, "proposal", "sam-pr-description", "READY", child_extra={"stub_invalid": True}),
                    ),
                ),
                "child validator failed",
            ),
            (
                "typed receipt instead of a fresh validator line",
                mutate(bug_web, lambda r: r["phases"][2].update(validator_receipts=["PASS: looks fine"])),
                "does not match a fresh child validator run",
            ),
            ("child report edited after it was recorded", edited, "output_fingerprint must equal sha256"),
            ("phase status disagrees with the child report", status_drift, "must match the child report status"),
            (
                "input fingerprint not derived from the child report",
                mutate(bug_web, lambda r: r["phases"][6]["iterations"][0].update(input_fingerprint="d" * 64)),
                "input fingerprint",
            ),
            (
                "relative validator input path",
                mutate(bug_web, lambda r: r["phases"][2].update(validator_args=["--bundle", "work/bundle.json"])),
                "validator_args must be",
            ),
            (
                "relative path hidden in --flag=value",
                mutate(bug_web, lambda r: r["phases"][2].update(validator_args=["--bundle=work/bundle.json"])),
                "validator_args must be",
            ),
            (
                "validator flag that rewrites the child report",
                mutate(bug_web, lambda r: r["phases"][2].update(validator_args=["--scaffold"])),
                "validator_args must be",
            ),
            (
                "capture phase without its scope captures",
                mutate(bug_web, lambda r: r["phases"][0].update(validator_args=[])),
                "must name readable --baseline and --current",
            ),
            (
                "unfilled scaffold placeholder",
                mutate(bug_web, lambda r: r["proposal"].update(platform="SCAFFOLD: host name")),
                "unfilled scaffold placeholder",
            ),
            (
                "intermediate iteration without invalidation receipt",
                mutate(
                    bug_web,
                    lambda r: r["phases"][2]["iterations"].insert(
                        0, {**iteration("APPROVE"), "sequence": 1}
                    )
                    or r["phases"][2]["iterations"][1].update(sequence=2),
                ),
                "must record either corrected findings or a later invalidation",
            ),
            (
                "coverage delegated browser proof on a non-web run",
                valid_report(tree, web=False, classification="FEATURE", coverage_extra=delegated),
                "coverage delegated browser proof",
            ),
            # The change fingerprint is recomputed from git, never taken as typed.
            (
                "typed change fingerprint that is not the git diff",
                mutate(
                    bug_web,
                    lambda r: (
                        r["target"].update(final_change_fingerprint=FP),
                        r["final"].update(final_change_fingerprint=FP),
                    ),
                ),
                "final_change_fingerprint must equal sha256 of git diff --binary",
            ),
            (
                "change fingerprint that git cannot verify",
                mutate(bug_web, lambda r: r["target"].update(repo_root=str(tree.root / "not-a-repo"))),
                "cannot verify target final_change_fingerprint",
            ),
            (
                "non-UTF-8 child validator output",
                mutate(
                    bug_web,
                    lambda r: r["phases"].__setitem__(
                        5,
                        phase(tree, "proposal", "sam-pr-description", "READY", child_extra={"stub_bytes": True}),
                    ),
                ),
                "child validator failed: FAIL: non-UTF-8 caf",
            ),
        ]
        for name, report, fragment in cases:
            expect_invalid(tree, name, report, fragment)

        extra = carry_forward_cases(tree)

    print(f"PASS: {5 + len(cases) + extra} sam-work harness scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
