#!/usr/bin/env python3
"""Scaffold an orchestration report from a short judgment-only spec.

Derives owners, runtime rows, artifact classes, changed-file producers, evidence
ids, blocker evidence, the review gate and the decision. With --freeze, changed
files are exactly those that differ from the run-start workspace snapshot
(--freeze-out), so pre-existing dirty or untracked work is never credited and
commits made during the run hide nothing. --diff-out writes the review diff and
--tree prints the workspace fingerprint. Snapshots use a scratch index; the
repository index and working tree are never modified.
validate_orchestration.py stays the gate on the written report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_orchestration as v  # noqa: E402

OWNER_PREFIX = {"EXECUTION": "worker", "ORCHESTRATION": "controller", "REVIEW": "reviewer"}
BLOCKER_CLASSES = {"ENVIRONMENT", "EXTERNAL"}
TREE_ID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


def runtime_row(host: Any, key: str) -> tuple[str, str, str, str] | None:
    """Return (host, role, model, effort) for a capability or GENIUS row."""
    if hasattr(v, "PROFILE_MATRIX"):
        return v.PROFILE_MATRIX.get(key)
    row = v.RUNTIME_MATRIX.get(host, {}).get(key)
    return None if row is None else (host, *row)


def git(repo: str, *args: str, env: dict[str, str] | None = None) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True, env=env
    ).stdout


def repo_root(repo: str) -> str:
    return git(repo, "rev-parse", "--show-toplevel").strip()


def workspace_tree(root: str) -> str:
    """Tree id of the working tree, untracked (unignored) files included."""
    index = Path(root, git(root, "rev-parse", "--git-path", "index").strip())
    with tempfile.TemporaryDirectory() as temp_dir:
        scratch = Path(temp_dir) / "index"
        if index.is_file():
            # copy2 keeps the index mtime, so git still re-hashes racily clean
            # entries (same-second edits after the last index write).
            shutil.copy2(index, scratch)
        env = {**os.environ, "GIT_INDEX_FILE": str(scratch)}
        # Assume-unchanged and skip-worktree bits would hide edits from `add -A`;
        # update-index applies only its last such flag, so clear each separately.
        entries = [e for e in git(root, "ls-files", "-v", "-z", env=env).split("\0") if e]
        for flag, hidden in (("--no-assume-unchanged", str.islower),
                             ("--no-skip-worktree", lambda tag: tag in "Ss")):
            paths = [entry[2:] for entry in entries if hidden(entry[0])]
            if paths:
                subprocess.run(["git", "-C", root, "update-index", flag, "-z", "--stdin"],
                               input="\0".join(paths) + "\0", check=True,
                               capture_output=True, text=True, env=env)
        git(root, "add", "-A", env=env)
        return git(root, "write-tree", env=env).strip()


def changed_paths(root: str, old: str, new: str) -> list[str]:
    names = git(root, "diff", "--no-renames", "--name-only", "-z", old, new)
    return [name for name in names.split("\0") if name]


def write_diff(snapshot: dict[str, Any], out: Path, since: str | None) -> str:
    root, old = snapshot["repo"], since or snapshot["tree"]
    new = workspace_tree(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Move into place only after git succeeds: a failed attempt must never leave
    # a review-<n>.diff behind that would count as a review round.
    partial = out.with_name(f".{out.name}.partial")
    try:
        with partial.open("wb") as handle:
            subprocess.run(["git", "-C", root, "diff", "--no-color", "--no-ext-diff", old, new],
                           check=True, stdout=handle, stderr=subprocess.PIPE)
        os.replace(partial, out)
    finally:
        partial.unlink(missing_ok=True)
    lines = out.read_bytes().count(b"\n")
    return (f"DIFF {out}: from={old} tree={new} "
            f"files={len(changed_paths(root, old, new))} lines={lines}")


def build(
    spec: dict[str, Any], run_paths: list[str] | None, review_diffs: int | None = None
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    task_in = spec.get("task") or {}
    host = task_in.get("active_host") or getattr(v, "CONTROLLER_HOST", None)
    nodes_in = spec.get("nodes") or []
    evidence_in = spec.get("evidence") or []
    by_id = {node.get("id"): node for node in nodes_in}

    scopes: dict[str, list[tuple[str, ...]]] = {}
    for node in nodes_in:
        parsed = [v.normalized_path(p, f"{node.get('id')}.writable_paths", errors)
                  for p in node.get("writable_paths", [])]
        if node.get("kind") != "REVIEW":
            scopes[node.get("id")] = [p for p in parsed if p]

    files_in: dict[str, Any] = dict(spec.get("files") or {})
    if run_paths is not None:
        for path in sorted(set(files_in) - set(run_paths)):
            errors.append(f"files[{path}] did not change after the freeze")
            del files_in[path]
        for path in run_paths:
            files_in.setdefault(path, None)
    changed_files = []
    for path in sorted(files_in):
        entry = files_in[path] if isinstance(files_in[path], dict) else {"class": files_in[path]}
        parsed = v.normalized_path(path, f"files[{path}]", errors)
        producer = entry.get("producer")
        if producer is None and parsed:
            owners = [nid for nid, paths in scopes.items()
                      if any(v.path_within(parsed, scope) for scope in paths)]
            if not owners:
                errors.append(f"changed path {path} is outside every writable scope")
                continue
            if len(owners) > 1:
                errors.append(f"changed path {path} matches producers {owners}; set files[{path}].producer")
                continue
            producer = owners[0]
        declared = by_id.get(producer, {}).get("artifact_classes") or []
        artifact_class = entry.get("class") or (declared[0] if len(declared) == 1 else None)
        if artifact_class is None:
            errors.append(f"set files[{path}] to an artifact class")
            continue
        changed_files.append(
            {"path": path, "artifact_class": artifact_class, "producer_task_id": producer}
        )

    evidence = []
    for item in evidence_in:
        requirements = by_id.get(item.get("task_id"), {}).get("proof_requirements", [])
        requirement = item.get("requirement") or (requirements[0] if len(requirements) == 1 else None)
        evidence.append({key: (requirement if key == "requirement" else item.get(key))
                         for key in ("id", "task_id", "requirement", "type", "status",
                                     "classification", "detail")})

    dag, counters = [], {}
    for node in nodes_in:
        node_id, kind = node.get("id"), node.get("kind")
        counters[kind] = counters.get(kind, 0) + 1
        runtime = None
        if kind in {"EXECUTION", "REVIEW"}:
            key = "GENIUS" if node.get("genius") else node.get("capability")
            row = runtime_row(host, key)
            if row is None:
                errors.append(f"node {node_id}: no matrix row for {key} on host {host}")
            else:
                runtime = dict(zip(("host", "role", "model", "effort"), row))
                runtime["fallback_reason"] = node.get("fallback_reason")
        writable = node.get("writable_paths", [])
        classes = node.get("artifact_classes") or sorted(
            {f["artifact_class"] for f in changed_files if f["producer_task_id"] == node_id}
        )
        if writable and kind != "REVIEW" and not classes:
            errors.append(f"node {node_id}: declare artifact_classes (no changed files yet)")
        status = node.get("status", "PENDING")
        evidence_ids = [e["id"] for e in evidence if e["task_id"] == node_id]
        blocker = None
        if status == "BLOCKED":
            blocker = dict(node.get("blocker") or {})
            blocker.setdefault("evidence_ids", [
                e["id"] for e in evidence
                if e["task_id"] == node_id and e["classification"] in BLOCKER_CLASSES
            ])
        dag.append({
            "id": node_id, "kind": kind,
            "owner": f"{OWNER_PREFIX.get(kind, 'worker')}-{counters[kind]}",
            "capability": node.get("capability"), "runtime": runtime,
            "depends_on": node.get("depends_on", []), "objective": node.get("objective"),
            "no_go": node.get("no_go"), "proof_requirements": node.get("proof_requirements"),
            "artifact_classes": classes if writable and kind != "REVIEW" else [],
            "writable_paths": writable,
            "direct_action_reason": node.get("direct_action_reason"),
            "status": status, "evidence_ids": evidence_ids, "blocker": blocker,
        })

    artifacts = sorted({f["artifact_class"] for f in changed_files})
    task = {
        "classification": task_in.get("classification"), "goal": task_in.get("goal"),
        "success_criteria": task_in.get("success_criteria"),
        "constraints": task_in.get("constraints", []), "no_go": task_in.get("no_go"),
        "risk_flags": task_in.get("risk_flags", []), "active_host": host,
        "changed_artifacts": artifacts, "changed_files": changed_files,
        "review_requested": task_in.get("review_requested", False),
    }
    if task_in.get("controller_certainty") is not None:
        task["controller_certainty"] = task_in["controller_certainty"]

    producers = [n for n in dag if n["kind"] != "REVIEW" and n["writable_paths"]]
    reviews = [n for n in dag if n["kind"] == "REVIEW"]
    unproven = any(e["classification"] == "TARGET" and e["status"] != "PASS" for e in evidence)
    trigger_classes = set(artifacts).union(*(n["artifact_classes"] for n in producers))
    certainty = task_in.get("controller_certainty") or "medium"
    base_skip = (not task["risk_flags"] and len(producers) <= 1 and not unproven
                 and not task["review_requested"])
    skip_absolute = base_skip and certainty == "absolute" and task["classification"] == "T0"
    skip_high = (base_skip and certainty == "high" and task["classification"] in {"T0", "T1"}
                 and {n["capability"] for n in producers} <= {"LIGHT", "STANDARD"})
    triggers = [reason for reason, fired in (
        ("T3 classification", task["classification"] == "T3"),
        ("risk_flags present", bool(task["risk_flags"])),
        ("DATA/RELEASE artifacts", bool({"DATA", "RELEASE"} & trigger_classes)),
        ("multiple producers contributed", len(producers) > 1),
        ("TARGET proof missing or not PASS", unproven),
        ("review requested", task["review_requested"]),
        ("CODE/TEST changed without certainty skip",
         bool({"CODE", "TEST"} & trigger_classes) and not (skip_absolute or skip_high)),
    ) if fired]
    if reviews or triggers:
        review = reviews[-1] if reviews else None
        review_evidence = [e for e in evidence if review and e["task_id"] == review["id"]]
        if any(e["status"] == "FAIL" for e in review_evidence):
            gate_status = "FAIL"
        elif review and review["status"] == "COMPLETE" and any(
            e["classification"] == "TARGET" and e["status"] == "PASS" for e in review_evidence
        ):
            gate_status = "PASS"
        else:
            gate_status = "NOT_RUN"
        rounds = spec.get("review_rounds")
        if review_diffs is not None:
            # Each review round reviews its own <run>/review-<n>.diff.
            if rounds is not None and rounds != review_diffs:
                errors.append(
                    f"spec review_rounds {rounds} disagrees with {review_diffs} "
                    "review-<n>.diff file(s) beside the freeze"
                )
            rounds = review_diffs
        gate = {"required": True, "reasons": triggers or ["review node present"],
                "status": gate_status, "review_task_id": review and review["id"],
                "rounds": rounds}
    else:
        reason = ("micro_task_absolute_certainty" if skip_absolute else
                  "micro_task_high_certainty" if skip_high else "no review trigger fired")
        gate = {"required": False, "reasons": [reason], "status": "NOT_REQUIRED",
                "review_task_id": None}

    statuses = {n["id"]: n["status"] for n in dag}
    incomplete = [n["id"] for n in dag if n["status"] != "COMPLETE"]
    runnable = [n["id"] for n in dag if n["status"] == "RUNNING" or (
        n["status"] == "PENDING"
        and all(statuses.get(d) == "COMPLETE" for d in n["depends_on"]))]
    if not incomplete and not unproven and gate["status"] in {"PASS", "NOT_REQUIRED"}:
        result = "COMPLETE"
    elif "BLOCKED" in statuses.values() and not runnable:
        result = "BLOCKED"
    else:
        result = "IN_PROGRESS"
    report = {"schema_version": 2, "task": task, "dag": dag, "evidence": evidence,
              "review_gate": gate,
              "decision": {"result": result, "remaining_task_ids": incomplete}}
    return report, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-out", help="write the run-start workspace snapshot here and exit")
    parser.add_argument("--tree", action="store_true", help="print the workspace tree id and exit")
    parser.add_argument("--repo", default=".", help="any path in the repository (--freeze-out, --tree)")
    parser.add_argument("--freeze", help="snapshot from --freeze-out; only later changes count")
    parser.add_argument("--diff-out", help="with --freeze: write the diff since the snapshot and exit")
    parser.add_argument("--since", help="with --diff-out: tree id of the previously reviewed state")
    parser.add_argument("--spec", help="absolute path to the spec JSON")
    parser.add_argument("--out", help="absolute path for the report JSON")
    args = parser.parse_args()
    if args.diff_out and not args.freeze:
        parser.error("--diff-out needs --freeze")
    if not (args.freeze_out or args.tree or args.diff_out or (args.spec and args.out)):
        parser.error("give --freeze-out, --tree, --diff-out with --freeze, or --spec with --out")
    try:
        if args.freeze_out:
            root = repo_root(args.repo)
            snapshot = {"repo": root, "tree": workspace_tree(root)}
            out = Path(args.freeze_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(snapshot) + "\n", encoding="utf-8")
            print(f"FROZE {out}: repo={root} tree={snapshot['tree']}")
            return 0
        if args.tree:
            print(f"tree={workspace_tree(repo_root(args.repo))}")
            return 0
        snapshot = json.loads(Path(args.freeze).read_text(encoding="utf-8")) if args.freeze else None
        for rev in (args.since, snapshot and snapshot["tree"]):
            if rev is not None and not TREE_ID.fullmatch(str(rev)):
                raise ValueError(f"not a tree id: {rev!r}")
        if args.diff_out:
            print(write_diff(snapshot, Path(args.diff_out), args.since))
            return 0
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        run_paths = review_diffs = None
        if snapshot is not None:
            root = snapshot["repo"]
            run_paths = changed_paths(root, snapshot["tree"], workspace_tree(root))
            review_diffs = len(list(Path(args.freeze).resolve().parent.glob("review-*.diff")))
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", None)
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        print(f"ERROR: {(stderr or '').strip() or exc}", file=sys.stderr)
        return 1
    report, errors = build(spec, run_paths, review_diffs)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    gate = report["review_gate"]
    print(f"WROTE {out}: nodes={len(report['dag'])} files={len(report['task']['changed_files'])} "
          f"review={gate['status']} decision={report['decision']['result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
