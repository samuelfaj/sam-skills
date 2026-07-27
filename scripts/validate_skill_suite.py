#!/usr/bin/env python3
"""Validate structural and portability contracts for every skill package."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^]]*]\(([^)]+)\)")
AGENT_FIELD_RE = re.compile(r"^  ([a-z_]+):\s*(.+?)\s*$")
FORBIDDEN_TEXT = (
    ("OpenClaw", re.compile(r"\bopenclaw\b", re.IGNORECASE)),
    ("named GPT model", re.compile(r"\bgpt(?:-[a-z0-9.]+)+\b", re.IGNORECASE)),
    ("Claude", re.compile(r"\bclaude\b", re.IGNORECASE)),
    ("OpenAI", re.compile(r"\bopenai\b", re.IGNORECASE)),
    ("Anthropic", re.compile(r"\banthropic\b", re.IGNORECASE)),
    ("Gemini", re.compile(r"\bgemini\b", re.IGNORECASE)),
    ("Llama", re.compile(r"\bllama\b", re.IGNORECASE)),
    ("Haiku", re.compile(r"\bhaiku\b", re.IGNORECASE)),
    ("Sonnet", re.compile(r"\bsonnet\b", re.IGNORECASE)),
    ("Opus", re.compile(r"\bopus\b", re.IGNORECASE)),
    ("Fable", re.compile(r"\bfable\b", re.IGNORECASE)),
    ("Codex host", re.compile(r"\bcodex\b", re.IGNORECASE)),
)
ALLOWED_SKILL_FILES = {"SKILL.md"}
ALLOWED_RESOURCE_DIRS = {"agents", "assets", "references", "scripts"}
# Shared implementations that must stay byte-identical across every skill that
# ships them. Skills install standalone and cannot import across packages.
SHARED_SCRIPTS = ("run_checked.py", "verify_receipts.py", "audit_test_diff.py")
PROVIDER_SPECIFIC_REPLACEMENTS = {
    "sam-codex-advisor": (
        (re.compile(r"\bcodex\b", re.IGNORECASE), "advisor-runtime"),
        (re.compile(r"\bgpt-5\.6-(?:luna|sol)\b", re.IGNORECASE), "approved-model"),
    ),
    "sam-claude-advisor": (
        (re.compile(r"\bclaude\b", re.IGNORECASE), "advisor-runtime"),
        (re.compile(r"\b(?:haiku|sonnet|opus|fable)\b", re.IGNORECASE), "approved-model"),
    ),

    "sam-orchestrate": (
        (re.compile(r"\bcodex\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bclaude(?:-code)?\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bgrok\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bgpt-5\.6-(?:luna|sol)\b", re.IGNORECASE), "approved-model"),
        (re.compile(r"\bgrok-4\.5\b", re.IGNORECASE), "approved-model"),
        (re.compile(r"\b(?:haiku|sonnet|opus|fable)\b", re.IGNORECASE), "approved-model"),
    ),
    "sam-orchestrate-codex-grok": (
        (re.compile(r"\bcodex\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bgrok\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bgpt-5\.6-(?:luna|sol)\b", re.IGNORECASE), "approved-model"),
        (re.compile(r"\bgrok-4\.5\b", re.IGNORECASE), "approved-model"),
    ),
    "sam-orchestrate-claude-grok": (
        (re.compile(r"\bclaude(?:-code)?\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bgrok\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\b(?:haiku|sonnet|opus|fable)\b", re.IGNORECASE), "approved-model"),
        (re.compile(r"\bgrok-4\.5\b", re.IGNORECASE), "approved-model"),
    ),
    "sam-council": (
        (re.compile(r"\bcodex\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bclaude(?:-code)?\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bgrok\b", re.IGNORECASE), "host-runtime"),
        (re.compile(r"\bgpt-5\.6-(?:luna|sol)\b", re.IGNORECASE), "approved-model"),
        (re.compile(r"\bgrok-4\.5\b", re.IGNORECASE), "approved-model"),
        (re.compile(r"\b(?:haiku|sonnet|opus|fable)\b", re.IGNORECASE), "approved-model"),
        (re.compile(r"\bopenai\b", re.IGNORECASE), "provider"),
        (re.compile(r"\bxai\b", re.IGNORECASE), "provider"),
    ),
}


@dataclass(frozen=True)
class Skill:
    root: Path
    name: str
    description: str
    body: str


def scalar(raw: str) -> str:
    value = raw.strip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid quoted scalar: {value}") from error
        if not isinstance(parsed, str):
            raise ValueError(f"expected string scalar: {value}")
        return parsed
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def load_skill(root: Path) -> Skill:
    path = root / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 4 or lines[0] != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("SKILL.md frontmatter is not closed") from error
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or ":" not in line:
            raise ValueError(f"unsupported frontmatter line: {line!r}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            raise ValueError(f"duplicate frontmatter key: {key}")
        metadata[key] = scalar(raw_value)
    if set(metadata) != {"name", "description"}:
        raise ValueError("frontmatter must contain only name and description")
    return Skill(
        root=root,
        name=metadata["name"],
        description=metadata["description"],
        body="\n".join(lines[end + 1 :]).strip(),
    )


def validate_frontmatter(skill: Skill, errors: list[str]) -> None:
    prefix = skill.root.name
    if skill.name != prefix:
        errors.append(f"{prefix}: frontmatter name must match directory")
    if len(skill.name) > 64 or not NAME_RE.fullmatch(skill.name):
        errors.append(f"{prefix}: invalid skill name")
    if not (40 <= len(skill.description) <= 500):
        errors.append(f"{prefix}: description must be 40-500 characters")
    if not re.search(
        r"\buse\b.{0,24}\b(?:when|for|after)\b", skill.description, re.IGNORECASE
    ):
        errors.append(f"{prefix}: description must include explicit trigger guidance")
    line_count = len((skill.root / "SKILL.md").read_text(encoding="utf-8").splitlines())
    if line_count > 500:
        errors.append(f"{prefix}: SKILL.md has {line_count} lines; maximum is 500")
    if "## Non-Negotiable Contract" not in skill.body:
        errors.append(f"{prefix}: missing Non-Negotiable Contract")
    has_output_contract = "references/output-contract.md" in skill.body
    has_output_heading = re.search(
        r"^## .*?(?:Output|Return)", skill.body, re.MULTILINE | re.IGNORECASE
    )
    if not (has_output_contract or has_output_heading):
        errors.append(f"{prefix}: missing explicit output/return section")


def validate_agent_metadata(skill: Skill, errors: list[str]) -> None:
    prefix = skill.root.name
    agents = skill.root / "agents"
    expected = agents / "openai.yaml"
    if not expected.is_file():
        errors.append(f"{prefix}: agents/openai.yaml is required")
        return
    yaml_files = sorted(path.name for path in agents.glob("*.yaml"))
    if yaml_files != ["openai.yaml"]:
        errors.append(f"{prefix}: unexpected agent metadata files: {yaml_files}")
    text = expected.read_text(encoding="utf-8")
    if not text.startswith("interface:\n"):
        errors.append(f"{prefix}: openai.yaml must start with interface")
    fields: dict[str, str] = {}
    raw_fields: dict[str, str] = {}
    for line in text.splitlines():
        match = AGENT_FIELD_RE.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        if key in {"display_name", "short_description", "default_prompt"}:
            raw_fields[key] = raw_value
            try:
                fields[key] = scalar(raw_value)
            except ValueError as error:
                errors.append(f"{prefix}: agents/openai.yaml {error}")
    required = {"display_name", "short_description", "default_prompt"}
    if set(fields) != required:
        errors.append(f"{prefix}: interface requires {sorted(required)}")
        return
    for key, raw_value in raw_fields.items():
        if not raw_value.startswith(('"', "'")):
            errors.append(f"{prefix}: interface.{key} must be quoted")
    short = fields["short_description"]
    if not 25 <= len(short) <= 64:
        errors.append(
            f"{prefix}: short_description length {len(short)} is outside 25-64"
        )
    if f"${skill.name}" not in fields["default_prompt"]:
        errors.append(f"{prefix}: default_prompt must mention ${skill.name}")


def validate_references(skill: Skill, errors: list[str]) -> None:
    prefix = skill.root.name
    references = skill.root / "references"
    if references.is_dir():
        for path in sorted(references.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix != ".md":
                errors.append(f"{prefix}: reference must be Markdown: {path.name}")
                continue
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            if len(lines) > 100:
                opening = "\n".join(lines[:40]).lower()
                if (
                    "## contents" not in opening
                    and "## table of contents" not in opening
                ):
                    errors.append(
                        f"{prefix}: {path.relative_to(skill.root)} exceeds 100 lines without contents"
                    )
            relative = path.relative_to(skill.root).as_posix()
            if relative not in skill.body:
                errors.append(
                    f"{prefix}: orphan reference not routed by SKILL.md: {relative}"
                )


def validate_scripts(skill: Skill, errors: list[str]) -> None:
    prefix = skill.root.name
    scripts = skill.root / "scripts"
    if not scripts.is_dir():
        return
    for path in sorted(scripts.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill.root).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            errors.append(
                f"{prefix}: generated Python cache must be removed: {relative}"
            )
            continue
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError) as error:
                errors.append(f"{prefix}: invalid Python script {relative}: {error}")
            if not path.stat().st_mode & stat.S_IXUSR:
                errors.append(f"{prefix}: Python script is not executable: {relative}")
        if path.name.startswith("test_") or path.name.endswith("_harness.py"):
            continue
        if relative not in skill.body:
            errors.append(
                f"{prefix}: runtime script not routed by SKILL.md: {relative}"
            )


def validate_links(skill: Skill, errors: list[str]) -> None:
    prefix = skill.root.name
    for raw_target in LINK_RE.findall(skill.body):
        target = raw_target.split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith(("#", "/")):
            continue
        resolved = (skill.root / target).resolve()
        if not resolved.exists():
            errors.append(f"{prefix}: broken relative link: {raw_target}")


def validate_portability(skill: Skill, errors: list[str]) -> None:
    prefix = skill.root.name
    paths = [skill.root / "SKILL.md"]
    for directory in ("agents", "references", "scripts"):
        root = skill.root / directory
        if root.is_dir():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = text.replace("openai.yaml", "agent-metadata.yaml")
        text = text.replace("anthropic.yaml", "obsolete-metadata.yaml")
        for pattern, replacement in PROVIDER_SPECIFIC_REPLACEMENTS.get(
            skill.name, ()
        ):
            text = pattern.sub(replacement, text)
        for label, pattern in FORBIDDEN_TEXT:
            match = pattern.search(text)
            if match:
                relative = path.relative_to(skill.root)
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{prefix}: forbidden {label} wording in {relative}:{line}"
                )
        if "/root/codex-automations" in text:
            errors.append(f"{prefix}: fixed host-specific temporary path is forbidden")


def validate_layout(skill: Skill, errors: list[str]) -> None:
    prefix = skill.root.name
    for child in skill.root.iterdir():
        if child.is_file() and child.name not in ALLOWED_SKILL_FILES:
            errors.append(f"{prefix}: extraneous top-level file: {child.name}")
        if child.is_dir() and child.name not in ALLOWED_RESOURCE_DIRS:
            errors.append(f"{prefix}: extraneous resource directory: {child.name}")


def validate_shared_scripts(root: Path, errors: list[str]) -> None:
    """Skills install standalone, so shared logic is duplicated by design.

    Duplication is only safe if it cannot drift: every copy must be byte-identical.
    """
    for name in SHARED_SCRIPTS:
        copies = sorted(root.glob(f"sam-*/scripts/{name}"))
        if len(copies) < 2:
            continue
        digests: dict[str, list[str]] = {}
        for path in copies:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            digests.setdefault(digest, []).append(
                path.relative_to(root).as_posix()
            )
        if len(digests) > 1:
            groups = " | ".join(
                ", ".join(paths) for paths in sorted(digests.values())
            )
            errors.append(
                f"shared script {name} has diverged between skills: {groups}"
            )


def validate_repository_docs(
    root: Path, skills: list[Skill], errors: list[str]
) -> None:
    readme = root / "README.md"
    if not readme.is_file():
        return
    try:
        raw_text = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        errors.append(f"README.md: cannot read UTF-8 text: {error}")
        return
    for skill in skills:
        if skill.name not in raw_text:
            errors.append(f"README.md: missing skill catalog entry for {skill.name}")
    inspected = raw_text
    # Longest skill names first so prefixes (e.g. sam-orchestrate) do not leave
    # residual forbidden tokens inside longer names (sam-orchestrate-codex-grok).
    for skill_name in sorted(PROVIDER_SPECIFIC_REPLACEMENTS, key=len, reverse=True):
        inspected = inspected.replace(skill_name, "provider-specific-advisor")
    for label, pattern in FORBIDDEN_TEXT:
        match = pattern.search(inspected)
        if match:
            line = inspected.count("\n", 0, match.start()) + 1
            errors.append(f"README.md: forbidden {label} wording at line {line}")


def validate_root(root: Path) -> list[str]:
    errors: list[str] = []
    skill_roots = sorted(
        path.parent for path in root.glob("sam-*/SKILL.md") if path.is_file()
    )
    if not skill_roots:
        return ["no sam-* skill packages found"]
    names: set[str] = set()
    skills: list[Skill] = []
    for skill_root in skill_roots:
        try:
            skill = load_skill(skill_root)
        except (OSError, ValueError, UnicodeDecodeError) as error:
            errors.append(f"{skill_root.name}: {error}")
            continue
        if skill.name in names:
            errors.append(f"duplicate skill name: {skill.name}")
        names.add(skill.name)
        skills.append(skill)
        validate_frontmatter(skill, errors)
        validate_layout(skill, errors)
        validate_agent_metadata(skill, errors)
        validate_references(skill, errors)
        validate_scripts(skill, errors)
        validate_links(skill, errors)
        validate_portability(skill, errors)
    validate_shared_scripts(root, errors)
    validate_repository_docs(root, skills, errors)
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Skill repository root")
    return parser.parse_args()


def main() -> int:
    root = Path(parse_args().root).resolve()
    errors = validate_root(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"INVALID: {len(errors)} error(s)", file=sys.stderr)
        return 1
    count = sum(1 for _ in root.glob("sam-*/SKILL.md"))
    print(f"VALID: {count} skill package(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
