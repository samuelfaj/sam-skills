#!/usr/bin/env python3
"""Regression tests for the repository skill-suite validator."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType


def load_validator() -> ModuleType:
    path = Path(__file__).with_name("validate_skill_suite.py")
    spec = importlib.util.spec_from_file_location("validate_skill_suite", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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

    print("PASS: valid packages, provider-specific advisor, and seven adversarial regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
