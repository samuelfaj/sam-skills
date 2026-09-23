#!/usr/bin/env python3
"""Regression tests for the repository skill-suite validator and the shared
run_checked.py output contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType

# Loading skill scripts must not leave __pycache__ in a skill package (the suite
# validator rejects it), even when this file is run without -B.
sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parent.parent


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_validator() -> ModuleType:
    return load_module(
        Path(__file__).with_name("validate_skill_suite.py"), "validate_skill_suite"
    )


def write_valid_skill(root: Path) -> Path:
    skill = root / "sam-example"
    (skill / "agents").mkdir(parents=True)
    (skill / "references").mkdir()
    (skill / "scripts").mkdir()
    (skill / "SKILL.md").write_text(
        """---
name: sam-example
description: "Perform an evidence-backed example workflow. Use when validating a reusable skill package."
---

# Sam Example

## Non-Negotiable Contract

- Preserve scope and report exact evidence.

## Workflow

Read [references/policy.md](references/policy.md), then run
`scripts/validate_report.py` before completion.

## Output Contract

Return the decision and validation proof.
""",
        encoding="utf-8",
    )
    (skill / "agents/openai.yaml").write_text(
        """interface:
  display_name: "Sam Example"
  short_description: "Validate an evidence-backed example workflow"
  default_prompt: "Use $sam-example to validate this example workflow."
""",
        encoding="utf-8",
    )
    (skill / "references/policy.md").write_text(
        "# Policy\n\nRequire evidence.\n", encoding="utf-8"
    )
    script = skill / "scripts/validate_report.py"
    script.write_text("#!/usr/bin/env python3\nprint('VALID')\n", encoding="utf-8")
    script.chmod(0o755)
    return skill


def expect_error(module: ModuleType, root: Path, fragment: str) -> None:
    errors = module.validate_root(root)
    if not any(fragment in error for error in errors):
        raise RuntimeError(f"expected {fragment!r}, got {errors}")


def expect_valid(module: ModuleType, root: Path, context: str) -> None:
    errors = module.validate_root(root)
    if errors:
        raise RuntimeError(f"{context}: {errors}")


def write_routed_skill(root: Path, name: str, files: dict[str, str]) -> None:
    """A minimal valid skill whose SKILL.md routes every given file."""
    skill = root / name
    (skill / "agents").mkdir(parents=True)
    routes = "\n".join(f"- `{relative}`" for relative in sorted(files))
    (skill / "SKILL.md").write_text(
        f"""---
name: {name}
description: "Perform an evidence-backed example workflow. Use when validating a reusable skill package."
---

# Example

## Non-Negotiable Contract

- Preserve scope and report exact evidence.

## Output Contract

{routes}
""",
        encoding="utf-8",
    )
    (skill / "agents/openai.yaml").write_text(
        f"""interface:
  display_name: "Example"
  short_description: "Validate an evidence-backed example workflow"
  default_prompt: "Use ${name} to validate this example workflow."
""",
        encoding="utf-8",
    )
    for relative, body in files.items():
        path = skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        if path.suffix == ".py":
            path.chmod(0o755)


def check_shared_file_groups(module: ModuleType) -> None:
    """Agents skip re-reading a byte-identical sibling copy, so a drifted copy
    would silently apply different rules. Only the declared skill sets are bound;
    same-named files elsewhere (sam-plan policy and capture, sam-review lenses,
    the refine validator, the coverage scaffold) legitimately differ."""
    policy = "# Evidence Policy\n\nMark a gate mandatory only when its risk applies.\n"
    lenses = "# Risk Lenses\n\nCheck auth, data loss, and concurrency.\n"
    validator = "#!/usr/bin/env python3\nprint('VALID')\n"
    capture = "#!/usr/bin/env python3\nprint('{}')\n"
    scaffold = "#!/usr/bin/env python3\nprint('SCAFFOLD')\n"
    with tempfile.TemporaryDirectory(prefix="sam-skill-groups-") as temporary:
        root = Path(temporary)
        for name in ("sam-create-feature", "sam-fix-bug", "sam-simplify-task"):
            write_routed_skill(
                root,
                name,
                {
                    "references/evidence-policy.md": policy,
                    "references/risk-lenses.md": lenses,
                    "scripts/validate_report.py": validator,
                    "scripts/capture_scope.py": capture,
                },
            )
        write_routed_skill(
            root,
            "sam-refine-task",
            {
                "references/evidence-policy.md": policy,
                "references/risk-lenses.md": lenses,
                "scripts/validate_report.py": validator.replace("VALID", "REFINED"),
                "scripts/capture_scope.py": capture,
            },
        )
        write_routed_skill(
            root, "sam-perceived-performance", {"scripts/capture_scope.py": capture}
        )
        for name in (
            "sam-orchestrate",
            "sam-orchestrate-claude-grok",
            "sam-orchestrate-codex-glmflash",
            "sam-orchestrate-codex-grok",
        ):
            write_routed_skill(root, name, {"scripts/scaffold_report.py": scaffold})
        write_routed_skill(
            root,
            "sam-create-test-coverage",
            {"scripts/scaffold_report.py": scaffold.replace("SCAFFOLD", "COVERAGE")},
        )
        write_routed_skill(
            root,
            "sam-plan",
            {
                "references/evidence-policy.md": policy + "Plan only.\n",
                "scripts/capture_scope.py": capture + "# plan only\n",
            },
        )
        write_routed_skill(
            root, "sam-review", {"references/risk-lenses.md": lenses + "Review only.\n"}
        )
        expect_valid(module, root, "differing copies outside the declared sets rejected")

        def expect_drift(relative: str, label: str, body: str) -> None:
            path = root / relative
            original = path.read_text(encoding="utf-8")
            path.write_text(body, encoding="utf-8")
            errors = module.validate_root(root)
            if not any(
                f"{label} has diverged between skills" in error and relative in error
                for error in errors
            ):
                raise RuntimeError(f"drift in {relative} not named: {errors}")
            path.write_text(original, encoding="utf-8")

        expect_drift(
            "sam-refine-task/references/evidence-policy.md",
            "shared file references/evidence-policy.md",
            policy.replace("only when", "whenever"),
        )
        # Byte identity, not semantic similarity: one trailing newline is drift.
        expect_drift(
            "sam-simplify-task/references/risk-lenses.md",
            "shared file references/risk-lenses.md",
            lenses + "\n",
        )
        expect_drift(
            "sam-create-feature/scripts/validate_report.py",
            "shared file scripts/validate_report.py",
            validator.replace("VALID", "PASS"),
        )
        expect_drift(
            "sam-perceived-performance/scripts/capture_scope.py",
            "shared file scripts/capture_scope.py",
            capture + "# drift\n",
        )
        expect_drift(
            "sam-orchestrate-codex-glmflash/scripts/scaffold_report.py",
            "shared file scripts/scaffold_report.py",
            scaffold + "# drift\n",
        )
        expect_valid(module, root, "restored copies rejected")

        # A merged or deleted copy is tolerated, but the rest stay bound.
        (root / "sam-fix-bug/references/evidence-policy.md").unlink()
        expect_valid(module, root, "missing group copy rejected")
        expect_drift(
            "sam-refine-task/references/evidence-policy.md",
            "shared file references/evidence-policy.md",
            policy + "extra\n",
        )
        (root / "sam-create-feature/references/evidence-policy.md").unlink()
        (root / "sam-simplify-task/references/evidence-policy.md").unlink()
        expect_valid(module, root, "single remaining copy rejected")


def check_run_checked_output() -> None:
    """run_checked stdout is one JSON line that is enough to cite the command in
    a report; a failure adds a capped, redacted log tail on stderr while the
    receipt and log on disk stay complete and verifiable."""
    copies = sorted(REPO.glob("sam-*/scripts/run_checked.py"))
    if not copies:
        raise RuntimeError("no run_checked.py copy found")
    script = copies[0]
    verifier = load_module(script.with_name("verify_receipts.py"), "verify_receipts")
    sentinel = "R3ALCRED9f71c6aa83d24bc7e158cc31"
    upper_sentinel = sentinel.upper()[:16]
    keys = {"receipt", "id", "status", "determinism", "exit_codes", "command"}

    with tempfile.TemporaryDirectory(prefix="sam-run-checked-") as temporary:
        receipts = Path(temporary)

        def run_checked(
            command_id: str, shell: str, *extra: str
        ) -> tuple[subprocess.CompletedProcess[str], dict, list[str]]:
            argv = ["/bin/sh", "-c", shell]
            result = subprocess.run(
                [sys.executable, "-B", str(script), "--id", command_id,
                 "--receipts-dir", str(receipts), "--classification", "TARGET",
                 *extra, "--", *argv],
                capture_output=True, text=True, check=False,
            )
            lines = result.stdout.splitlines()
            if len(lines) != 1:
                raise RuntimeError(f"stdout must be one JSON line: {result.stdout!r}")
            summary = json.loads(lines[0])
            if set(summary) != keys:
                raise RuntimeError(f"stdout keys drifted: {sorted(summary)}")
            if summary["command"] != " ".join(argv):
                raise RuntimeError("stdout command is not the exact argv text")
            raw = Path(summary["receipt"]).read_text(encoding="utf-8")
            receipt = json.loads(raw)
            # Receipts on disk stay human-diffable: indent=2, sorted keys, newline.
            if raw != json.dumps(receipt, indent=2, sort_keys=True) + os.linesep:
                raise RuntimeError("on-disk receipt format changed from indent=2 JSON")
            body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
            canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
            if receipt.get("receipt_sha256") != hashlib.sha256(
                canonical.encode("utf-8")
            ).hexdigest() or not receipt.get("runs"):
                raise RuntimeError("on-disk receipt is no longer the full receipt")
            errors: list[str] = []
            verifier.verify_commands(
                [{"id": summary["id"], "status": summary["status"],
                  "classification": "TARGET", "command": summary["command"],
                  "receipt": summary["receipt"]}],
                errors,
            )
            return result, summary, errors

        passed, summary, errors = run_checked("CMD-001", "echo ok", "--repeat", "2")
        if errors or passed.returncode != 0:
            raise RuntimeError(f"PASS line cannot be cited in a report: {errors}")
        if summary["status"] != "PASS" or summary["exit_codes"] != [0, 0]:
            raise RuntimeError(f"PASS summary is wrong: {summary}")
        if summary["determinism"] != "STABLE" or passed.stderr:
            raise RuntimeError("PASS must be STABLE with no stderr tail")
        # PASS stdout carries no log path, so the documented naming convention
        # is the only way to find a PASS log; it must match the receipt.
        usage = subprocess.run(
            [sys.executable, "-B", str(script), "--help"],
            capture_output=True, text=True, check=True,
        ).stdout
        receipt = json.loads(Path(summary["receipt"]).read_text(encoding="utf-8"))
        expected = [str(receipts.resolve() / f"CMD-001.run{n}.log") for n in (1, 2)]
        if "<receipts-dir>/<id>.run<N>.log" not in usage or expected != [
            run["log_path"] for run in receipt["runs"]
        ]:
            raise RuntimeError("PASS log path does not follow the documented name")
        if "best-effort" not in usage:
            raise RuntimeError("--help must say redaction is best-effort")

        # Each line holds the sentinel in a form only one rule catches, so a
        # dropped rule or alternative leaks its own line. Only the last 12 chars
        # are searched, so a value redacted only in part still counts as a leak.
        leak_marks = (sentinel[-12:], upper_sentinel[-12:])
        secrets = [
            f"api_key={sentinel}",
            f"Authorization: Basic {sentinel}",
            f"retry with bearer {sentinel}",
            f"https://user:{sentinel}@host.invalid/x",
            f"postgres://app:{sentinel}@db.invalid/x",
            f"redis://:{sentinel}@cache.invalid",
            f"Cookie: session={sentinel}",
            f"set-cookie: sid={sentinel}; Path=/",
            f"curl -u admin:{sentinel} https://x.invalid",
            f"--password {sentinel}",
            f"key sk_live_{sentinel}",
            f"glpat-{sentinel}",
            f"npm_{sentinel}",
            f"AIza{sentinel}",
            f"password=abc,{sentinel}",
            f'{{"password": "{sentinel}"}}',
            f'{{"password": "ab\\"{sentinel}"}}',
            f"ghp_{sentinel}",
            f"github_pat_{sentinel}",
            f"xoxb-{sentinel}",
            f"AKIA{upper_sentinel}",
            f"sk-{sentinel}",
            f"eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.{sentinel}",
            f"hooks.slack.com/services/T0/B0/{sentinel}",
            f"--user admin:{sentinel}",
            f"private_key={sentinel}",
            f'"token" => "{sentinel}"',
            f"https://{sentinel}@git.invalid/org/repo.git",
            f"mysql -uroot -p{sentinel} app",
            f"DB_PASS={sentinel}",
            f"pwd={sentinel}",
            f"pass = {sentinel}",
            f"credentials: {sentinel}",
            f"session_id={sentinel}",
            f"-----BEGIN RSA PRIVATE KEY-----\n{sentinel}\n-----END RSA PRIVATE KEY-----",
            f"-----BEGIN PGP PRIVATE KEY BLOCK-----\n{sentinel}\n"
            "-----END PGP PRIVATE KEY BLOCK-----",
            f"mariadb -h db -p{sentinel} app",
            f"--pass {sentinel}",
            f"--passphrase {sentinel}",
            f"passphrase: {sentinel}",
            f"    client-key-data: {sentinel}",
            f"password: correct horse {sentinel}",
            f'{{"password": "correct horse {sentinel}", "user": "kept-double"}}',
            f"secret: 'correct horse {sentinel}' kept-single",
            f"ASIA{upper_sentinel}",
            f"xapp-1-{sentinel}",
            f"whsec_{sentinel}",
            f"hf_{sentinel}",
            f"pypi-AgEIcHlwaS5vcmc{sentinel}",
            f"url?jwt=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.{sentinel}",
        ]
        # Batches keep every secret line inside the 40-line tail.
        tails = ""
        for start in range(0, len(secrets), 20):
            batch = secrets[start:start + 20]
            command_id = f"CMD-1{start:02d}"
            noisy = (
                "i=1; while [ $i -le 100 ]; do echo line-$i; i=$((i+1)); done; "
                + "".join(f"printf '%s\\n' {shlex.quote(line)}; " for line in batch)
                + "echo 'PASS: 25 harnesses'; echo last-line; exit 3"
            )
            failed, summary, errors = run_checked(
                command_id, noisy, "--repeat", "2", "--expect-pass"
            )
            if errors or failed.returncode != 1 or summary["exit_codes"] != [3, 3]:
                raise RuntimeError(f"FAIL summary is wrong: {summary} {errors}")
            tail = failed.stderr.splitlines()
            if not tail or f"{command_id}.run1.log" not in tail[0]:
                raise RuntimeError(f"FAIL tail must name the log: {failed.stderr!r}")
            leaked = [line for line in tail if any(mark in line for mark in leak_marks)]
            if leaked or failed.stderr.count("[REDACTED]") < len(batch):
                raise RuntimeError(f"FAIL tail leaked a secret: {leaked or tail}")
            # The header must not present the tail as safe to quote.
            if "best-effort redacted tail" not in tail[0] or "verify before quoting" not in tail[0]:
                raise RuntimeError(f"FAIL header must warn the redaction is best-effort: {tail[0]!r}")
            if "PASS: 25 harnesses" not in tail:
                raise RuntimeError("a harness PASS summary line must not be redacted")
            if len(tail) - 1 > 40 or "last-line" not in tail or "line-1" in tail:
                raise RuntimeError(f"FAIL tail is not the capped end: {tail}")
            log = (receipts / f"{command_id}.run1.log").read_text(encoding="utf-8")
            if sentinel not in log or "line-1\n" not in log:
                raise RuntimeError("captured log must stay complete and unredacted")
            tails += failed.stderr
        # A quoted value ends at its closing quote, so the rest stays readable.
        if "kept-double" not in tails or "kept-single" not in tails:
            raise RuntimeError(f"quoted-value redaction ran past its quote: {tails!r}")

        wide, _, _ = run_checked(
            "CMD-003", "i=0; while [ $i -lt 40 ]; do printf '%0500d\\n' 0; "
            "i=$((i+1)); done; exit 1",
        )
        if len(wide.stderr.split("\n", 1)[1]) > 4096 + 1:
            raise RuntimeError("FAIL tail exceeds the 4096-char cap")

        # A line cut by the read window may hide its key, so it is never shown.
        cut, _, _ = run_checked(
            "CMD-004",
            f"printf 'token=%070000d' 0; printf '{sentinel}\\nafter-cut\\n'; exit 1",
        )
        if sentinel[-12:] in cut.stderr or "after-cut" not in cut.stderr:
            raise RuntimeError(f"window-cut line leaked: {cut.stderr[-300:]!r}")

        def run_file(command_id: str, payload: str) -> subprocess.CompletedProcess[str]:
            source = receipts / f"{command_id}.payload"
            source.write_text(payload, encoding="utf-8")
            result, _, _ = run_checked(command_id, f"cat '{source}'; exit 1")
            return result

        # A window that starts inside a PEM body still hides the body up to END.
        body = "".join(f"{'A' * 63}{index % 10}\n" for index in range(1200))
        for command_id, kind in (
            ("CMD-007", "PRIVATE KEY"), ("CMD-010", "PGP PRIVATE KEY BLOCK")
        ):
            pem = run_file(
                command_id,
                f"-----BEGIN {kind}-----\n" + body + sentinel
                + f"\n-----END {kind}-----\nafter-end\n",
            )
            if sentinel[-12:] in pem.stderr or "after-end" not in pem.stderr:
                raise RuntimeError(f"{kind} body cut by the window leaked: {pem.stderr[-300:]!r}")

        # A BEGIN with no END (output stopped mid-key) hides everything after it.
        unterminated = run_file(
            "CMD-011",
            "before-key\n-----BEGIN OPENSSH PRIVATE KEY-----\n"
            f"b3BlbnNzaC1rZXktdjEAAAAA\n{sentinel}\n",
        )
        if sentinel[-12:] in unterminated.stderr or "before-key" not in unterminated.stderr:
            raise RuntimeError(f"PEM without END leaked: {unterminated.stderr[-300:]!r}")

        # Redaction runs before the char cap: a cut between a key and its value
        # would otherwise leave the value without the key that marks it secret.
        first = f"config api_key={sentinel}"
        filler = ["f" * 103] * 38 + ["g" * 106]
        text = "\n".join([first, *filler])
        if len(text) - 4096 != len("config api"):
            raise RuntimeError("cap-order fixture no longer cuts inside the key")
        ordered = run_file("CMD-008", "prefix\n" + text + "\n")
        if sentinel[-12:] in ordered.stderr:
            raise RuntimeError(f"char cap ran before redaction: {ordered.stderr[:300]!r}")

        # Output past the 4 MiB log cap is flagged in the header.
        capped, _, _ = run_checked(
            "CMD-009", "yes 0123456789abcdef0123456789abcdef | head -c 4300000; exit 1"
        )
        if "capture truncated at the log cap" not in capped.stderr.split("\n", 1)[0]:
            raise RuntimeError(f"log-cap truncation is not reported: {capped.stderr[:300]!r}")

        # Bounded repeats keep one long line from making redaction quadratic.
        checker = load_module(script, "run_checked")
        started = time.monotonic()
        checker.redact("a://:" * 12000)
        if time.monotonic() - started > 1.0:
            raise RuntimeError("URL password rule is no longer bounded")

        # Every new or changed rule stays linear on a 64 KiB adversarial line;
        # the unbounded mysql, JWT (no lookbehind) and -u forms took seconds.
        def best_seconds(text: str) -> float:
            best = float("inf")
            for _ in range(3):
                started = time.perf_counter()
                checker.redact(text)
                best = min(best, time.perf_counter() - started)
                if best < 0.1:
                    break
            return best

        for rule, prefix, unit in (
            ("mysql", "", "mysql "),
            ("mariadb", "", "mariadb "),
            ("JWT lookbehind", "", "eyJ-"),
            ("URL", "", "x"),
            ("-u", " -u", "="),
            ("PEM BEGIN", "-----BEGIN ", "A "),
            ("PEM END", "-----END ", "A "),
            ("AWS", "", "ASIA"),
            ("xapp", "", "xapp-"),
            ("whsec", "", "whsec_"),
            ("hf", "", "hf_"),
            ("pypi", "", "pypi-"),
            ("passphrase", "", "passphrase"),
            ("key-data", "", "key-data"),
            ("--pass", "", "--pass"),
            ("unquoted value", "password: ", "x "),
        ):
            elapsed = best_seconds((prefix + unit * 65536)[:65536])
            if elapsed >= 0.1:
                raise RuntimeError(f"{rule} rule took {elapsed:.2f}s on a 64 KiB line")

        # FLAKY is FAIL too: the tail must come from the run that failed.
        counter = receipts / "flaky.count"
        flaky, summary, errors = run_checked(
            "CMD-005",
            f"if [ -f '{counter}' ]; then echo run-two-failed; exit 4; fi; "
            f": > '{counter}'; echo run-one-ok",
            "--repeat", "2",
        )
        if errors or summary["determinism"] != "FLAKY" or summary["exit_codes"] != [0, 4]:
            raise RuntimeError(f"FLAKY summary is wrong: {summary} {errors}")
        header = flaky.stderr.split("\n", 1)[0]
        if "FAIL run 2 exit 4" not in header or "CMD-005.run2.log" not in header:
            raise RuntimeError(f"FLAKY tail must name the failing run: {flaky.stderr!r}")
        if "run-two-failed" not in flaky.stderr or "run-one-ok" in flaky.stderr:
            raise RuntimeError(f"FLAKY tail is not the failing run's log: {flaky.stderr!r}")

        # An empty log is reported as empty, not as a truncated window.
        empty, _, _ = run_checked("CMD-006", "exit 1")
        if empty.stderr.splitlines()[1:] != ["(log is empty)"]:
            raise RuntimeError(f"empty FAIL log is misreported: {empty.stderr!r}")
        # Blank lines are not a cut window, and a cut window is not blank lines.
        blank, _, _ = run_checked("CMD-012", "printf '\\n\\n'; exit 1")
        if blank.stderr.splitlines()[1:] != ["(only blank lines in the tail)"]:
            raise RuntimeError(f"blank FAIL log is misreported: {blank.stderr!r}")
        partial, _, _ = run_checked("CMD-013", "printf '%070000d' 0; exit 1")
        if partial.stderr.splitlines()[1:] != ["(no complete line in the tail window)"]:
            raise RuntimeError(f"cut-only FAIL window is misreported: {partial.stderr!r}")

        # A reader that leaves early (`2>&1 | head -1`) must not change the exit
        # status: the receipt is already written.
        for extra, expected in (((), 0), (("--expect-pass",), 1)):
            read_end, write_end = os.pipe()
            os.close(read_end)
            try:
                broken = subprocess.run(
                    [sys.executable, "-B", str(script), "--id", "CMD-014",
                     "--receipts-dir", str(receipts), "--classification", "TARGET",
                     *extra, "--", "/bin/sh", "-c", "echo boom; exit 1"],
                    stdout=subprocess.PIPE, stderr=write_end, text=True, check=False,
                )
            finally:
                os.close(write_end)
            if broken.returncode != expected or json.loads(broken.stdout)["status"] != "FAIL":
                raise RuntimeError(
                    f"closed stderr changed exit {expected} to {broken.returncode}"
                )


def check_harness_runner_output() -> None:
    """By default the runner prints only FAIL lines plus one summary, so a
    passing suite costs one line of context; --verbose adds the PASS lines."""
    runner = Path(__file__).with_name("run_skill_harnesses.py")
    with tempfile.TemporaryDirectory(prefix="sam-harness-runner-") as temporary:
        root = Path(temporary)
        good = root / "sam-good/scripts/test_good_harness.py"
        bad = root / "sam-bad/scripts/test_harness.py"
        for path, body in (
            (good, "print('noise')\nprint('good summary')\n"),
            (bad, "import sys\nprint('bad stdout')\nsys.exit('bad detail')\n"),
        ):
            path.parent.mkdir(parents=True)
            path.write_text(body, encoding="utf-8")

        def run(*extra: str) -> tuple[int, list[str]]:
            result = subprocess.run(
                [sys.executable, "-B", str(runner), "--root", str(root), *extra],
                capture_output=True, text=True, check=False,
            )
            return result.returncode, result.stdout.splitlines()

        fail = "FAIL sam-bad/scripts/test_harness.py: bad detail"
        passed = "PASS sam-good/scripts/test_good_harness.py: good summary"
        for extra, expected in (
            ((), (1, [fail, "FAILED: 1/2 harnesses"])),
            (("--verbose",), (1, [fail, passed, "FAILED: 1/2 harnesses"])),
        ):
            if (actual := run(*extra)) != expected:
                raise RuntimeError(f"runner output {extra} drifted: {actual}")
        bad.unlink()
        if (actual := run()) != (0, ["PASS: 1 harnesses"]):
            raise RuntimeError(f"passing runner output is not one line: {actual}")


def main() -> int:
    module = load_validator()
    with tempfile.TemporaryDirectory(prefix="sam-skill-suite-") as temporary:
        root = Path(temporary)
        skill = write_valid_skill(root)
        errors = module.validate_root(root)
        if errors:
            raise RuntimeError(f"valid fixture rejected: {errors}")

        agent = skill / "agents/openai.yaml"
        original_agent = agent.read_text(encoding="utf-8")
        agent.write_text(
            original_agent.replace(
                "Validate an evidence-backed example workflow", "Too short"
            ),
            encoding="utf-8",
        )
        expect_error(module, root, "short_description length")
        agent.write_text(original_agent, encoding="utf-8")

        skill_md = skill / "SKILL.md"
        original_skill = skill_md.read_text(encoding="utf-8")
        skill_md.write_text(
            original_skill.replace("evidence-backed", "GPT-9-backed", 1),
            encoding="utf-8",
        )
        expect_error(module, root, "named GPT model")
        skill_md.write_text(original_skill, encoding="utf-8")

        readme = root / "README.md"
        readme.write_text(
            "# Skills\n\n- sam-example uses a GPT-9 execution route.\n",
            encoding="utf-8",
        )
        expect_error(module, root, "README.md: forbidden named GPT model")
        readme.unlink()

        reference = skill / "references/policy.md"
        reference.write_text("# Policy\n" + "detail\n" * 101, encoding="utf-8")
        expect_error(module, root, "exceeds 100 lines without contents")
        reference.write_text("# Policy\n\nRequire evidence.\n", encoding="utf-8")

        script = skill / "scripts/validate_report.py"
        script.chmod(0o644)
        expect_error(module, root, "not executable")
        script.chmod(0o755)

        advisor = root / "sam-codex-advisor"
        (advisor / "agents").mkdir(parents=True)
        (advisor / "SKILL.md").write_text(
            """---
name: sam-codex-advisor
description: "Consult Codex on gpt-5.6-sol as an advisor. Use when a fixed provider-specific second opinion is requested."
---

# Sam Codex Advisor

## Non-Negotiable Contract

- Keep the advisor read-only.

## Output

Return the recommendation and model used.
""",
            encoding="utf-8",
        )
        (advisor / "agents/openai.yaml").write_text(
            """interface:
  display_name: "Sam Codex Advisor"
  short_description: "Consult a fixed provider-specific advisor"
  default_prompt: "Use $sam-codex-advisor for a second opinion."
""",
            encoding="utf-8",
        )
        advisor_errors = module.validate_root(root)
        if advisor_errors:
            raise RuntimeError(
                f"provider-specific advisor fixture rejected: {advisor_errors}"
            )
        advisor_skill = advisor / "SKILL.md"
        original_advisor = advisor_skill.read_text(encoding="utf-8")
        advisor_skill.write_text(
            original_advisor.replace("gpt-5.6-sol", "GPT-9"), encoding="utf-8"
        )
        expect_error(module, root, "named GPT model")
        advisor_skill.write_text(original_advisor, encoding="utf-8")

        skill_md.write_text(
            original_skill.replace(
                "](references/policy.md)", "](references/missing.md)"
            ),
            encoding="utf-8",
        )
        expect_error(module, root, "broken relative link")
        skill_md.write_text(original_skill, encoding="utf-8")

        # Shared scripts are duplicated because skills install standalone; the
        # only thing making that safe is that no copy may drift, so none may be
        # dropped from the checked set.
        expected_shared = ("run_checked.py", "verify_receipts.py", "audit_test_diff.py")
        if module.SHARED_SCRIPTS != expected_shared:
            raise RuntimeError(f"SHARED_SCRIPTS drifted: {module.SHARED_SCRIPTS}")
        shared_name = module.SHARED_SCRIPTS[0]
        for owner, body in ((skill, "print('one')\n"), (advisor, "print('two')\n")):
            shared = owner / "scripts" / shared_name
            shared.parent.mkdir(parents=True, exist_ok=True)
            shared.write_text(f"#!/usr/bin/env python3\n{body}", encoding="utf-8")
            shared.chmod(0o755)
            routed = owner / "SKILL.md"
            routed.write_text(
                routed.read_text(encoding="utf-8")
                + f"\nAlso run `scripts/{shared_name}`.\n",
                encoding="utf-8",
            )
        expect_error(module, root, "has diverged between skills")

        (advisor / "scripts" / shared_name).write_text(
            "#!/usr/bin/env python3\nprint('one')\n", encoding="utf-8"
        )
        (advisor / "scripts" / shared_name).chmod(0o755)
        identical_errors = module.validate_root(root)
        if identical_errors:
            raise RuntimeError(
                f"byte-identical shared scripts rejected: {identical_errors}"
            )

    check_shared_file_groups(module)
    check_run_checked_output()
    check_harness_runner_output()
    print(
        "PASS: valid packages, provider-specific advisor, shared-script drift, "
        "shared-file group drift, run_checked line/tail/redaction contract, "
        "harness runner output, and adversarial regressions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
