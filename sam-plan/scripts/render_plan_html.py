#!/usr/bin/env python3
"""Render a validated-style plan-report.json into a light-theme multi-page HTML plan pack."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]
SCRIPT_RE = re.compile(r"<\s*script\b", re.IGNORECASE)
EVENT_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)


CSS = """
:root {
  color-scheme: light;
  --brand: #0f6b5c;
  --brand-strong: #0b5247;
  --lime: #c6f06c;
  --ink: #14201f;
  --muted: #5f6f6c;
  --line: #d9e4e1;
  --bg: #f5f7f6;
  --card: #ffffff;
  --warn: #9c6a00;
  --danger: #a5272f;
  --ok: #107c41;
  --info: #1a6ca8;
}
* { box-sizing: border-box; }
html { color-scheme: light; background: var(--bg); }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.52;
  color: var(--ink);
  background: var(--bg);
}
header {
  background: linear-gradient(135deg, #ffffff 0%, #eef7f4 100%);
  border-bottom: 1px solid var(--line);
  padding: 32px 5vw 20px;
}
header h1 { margin: 0; font-size: clamp(28px, 4vw, 48px); }
header p { margin: 10px 0 0; color: var(--muted); max-width: 980px; font-size: 17px; }
.meta { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
nav {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 12px 5vw;
  background: #ffffff;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 5;
}
nav a {
  flex: 0 0 auto;
  color: var(--brand);
  text-decoration: none;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 12px;
  background: #fff;
}
nav a[aria-current="page"] {
  background: #e7f6f1;
  border-color: #b9dcd3;
  font-weight: 600;
}
main { padding: 24px 5vw 64px; max-width: 1440px; margin: 0 auto; }
section {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 22px;
  margin: 0 0 18px;
}
h2 { margin: 0 0 14px; font-size: 24px; }
h3 { margin: 18px 0 8px; font-size: 17px; }
p { margin: 8px 0; }
ul, ol { margin: 8px 0 8px 22px; padding: 0; }
li { margin: 6px 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  background: #fff;
  font-size: 14px;
}
th, td {
  border: 1px solid var(--line);
  padding: 10px;
  vertical-align: top;
  text-align: left;
}
th { background: #eef8f5; color: #143c38; }
code, pre {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #f2f6f5;
  border: 1px solid #dce7e5;
  border-radius: 8px;
}
code { padding: 1px 5px; }
pre { padding: 14px; overflow: auto; white-space: pre-wrap; }
.callout {
  border-left: 4px solid var(--brand);
  background: #f3fbf9;
  padding: 12px 14px;
  border-radius: 8px;
  margin: 10px 0;
}
.callout.danger { border-left-color: var(--danger); background: #fff4f4; }
.callout.warn { border-left-color: var(--warn); background: #fff9ec; }
.callout.ok { border-left-color: var(--ok); background: #f0fff5; }
.callout.decision { border-left-color: #7aa312; background: #fbfff3; }
.tag {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 2px 8px;
  margin: 2px;
  background: #fff;
  font-size: 12px;
  color: var(--muted);
}
.tag.strong { color: var(--brand-strong); border-color: #b9dcd3; background: #eef8f5; }
.small { color: var(--muted); font-size: 13px; }
@media (max-width: 760px) {
  header { padding: 24px 18px 16px; }
  nav { padding: 10px 18px; }
  main { padding: 18px; }
  section { padding: 16px; }
}
""".strip()


def load_json(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("report must be a JSON object")
    return value


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def safe_text(value: str) -> str:
    text = value or ""
    if SCRIPT_RE.search(text) or EVENT_RE.search(text):
        return esc(text)
    # Allow a tiny HTML subset already escaped by planner; still escape by default.
    # If content contains tags, keep as escaped plain text for safety.
    if "<" in text and ">" in text:
        return esc(text)
    return esc(text)


def render_list(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    body = "".join(f"<li>{safe_text(item)}</li>" for item in items)
    return f"<{tag}>{body}</{tag}>"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(cell)}</th>" for cell in headers)
    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>" + "".join(f"<td>{safe_text(cell)}</td>" for cell in row) + "</tr>"
        )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_block(block: JsonObject) -> str:
    block_type = block.get("type")
    if block_type == "paragraph":
        return f"<p>{safe_text(block.get('text', ''))}</p>"
    if block_type == "code":
        return f"<pre><code>{esc(block.get('text', ''))}</code></pre>"
    if block_type == "list":
        items = block.get("items") or []
        ordered = bool(block.get("ordered"))
        return render_list([str(item) for item in items], ordered=ordered)
    if block_type == "callout":
        tone = block.get("tone") or "info"
        klass = "callout"
        if tone in {"ok", "warn", "danger", "decision"}:
            klass += f" {tone}"
        return f'<div class="{klass}"><p>{safe_text(block.get("text", ""))}</p></div>'
    if block_type == "table":
        headers = [str(item) for item in block.get("headers") or []]
        rows = [[str(cell) for cell in row] for row in block.get("rows") or []]
        return render_table(headers, rows)
    return f"<p>{safe_text(block.get('text', ''))}</p>"


def chapter_filename(chapter: JsonObject) -> str:
    return f"{chapter['id']}-{chapter['slug']}.html"


def render_nav(chapters: list[JsonObject], current: str) -> str:
    links = []
    for chapter in chapters:
        name = chapter_filename(chapter)
        label = f"{chapter['id']}-{chapter['slug']}"
        current_attr = ' aria-current="page"' if name == current else ""
        links.append(f'<a href="./{esc(name)}"{current_attr}>{esc(label)}</a>')
    return f'<nav aria-label="Plan files">{"".join(links)}</nav>'


def render_page(
    *,
    title: str,
    subtitle: str,
    chapters: list[JsonObject],
    filename: str,
    body: str,
    meta_tags: list[str],
) -> str:
    tags = "".join(f'<span class="tag strong">{esc(tag)}</span>' for tag in meta_tags)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#f5f7f6">
  <title>{esc(title)}</title>
  <style>
{CSS}
  </style>
</head>
<body>
  <header>
    <h1>{esc(title)}</h1>
    <p>{esc(subtitle)}</p>
    <div class="meta">{tags}</div>
  </header>
  {render_nav(chapters, filename)}
  <main>
{body}
  </main>
</body>
</html>
"""


def render_chapter_body(chapter: JsonObject) -> str:
    parts = [f"<section><h2>{esc(chapter.get('title', ''))}</h2>"]
    summary = chapter.get("summary")
    if summary:
        parts.append(f'<p class="small">{esc(summary)}</p>')
    for section in chapter.get("sections") or []:
        parts.append(f"<h3>{esc(section.get('heading', ''))}</h3>")
        for block in section.get("blocks") or []:
            if isinstance(block, dict):
                parts.append(render_block(block))
    parts.append("</section>")
    return "\n".join(parts)


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _join_bullets(items: list[str], *, empty: str = "—") -> str:
    cleaned = [item.strip() for item in items if item and str(item).strip()]
    if not cleaned:
        return empty
    return " • ".join(cleaned)


def synthesize_compact_chapter(report: JsonObject) -> JsonObject:
    """Build a single pack page from freeze fields when chapters are omitted.

    Rich default projection for humans: status, scope, thesis, executable steps
    (why/how/surfaces/deps/DoD/proofs), acceptance map, risks, residuals,
    evidence, and simplicity cuts — not just goal + titles.
    """
    frozen = report.get("frozen") if isinstance(report.get("frozen"), dict) else {}
    thesis = report.get("thesis") if isinstance(report.get("thesis"), dict) else {}
    study = report.get("study") if isinstance(report.get("study"), dict) else {}
    council = report.get("council") if isinstance(report.get("council"), dict) else {}
    simplicity = (
        report.get("simplicity") if isinstance(report.get("simplicity"), dict) else {}
    )
    steps = report.get("steps") if isinstance(report.get("steps"), list) else []
    evidence = report.get("evidence") if isinstance(report.get("evidence"), list) else []
    risks = report.get("risks") if isinstance(report.get("risks"), list) else []
    residuals = _as_str_list(report.get("residuals"))
    blockers = _as_str_list(report.get("blockers"))
    risk_flags = _as_str_list(report.get("risk_flags"))
    acceptance = (
        report.get("acceptance_trace")
        if isinstance(report.get("acceptance_trace"), list)
        else []
    )
    verifications = (
        report.get("verifications")
        if isinstance(report.get("verifications"), list)
        else []
    )
    proof_by_id = {
        str(item.get("id")): item
        for item in verifications
        if isinstance(item, dict) and item.get("id")
    }

    status = str(report.get("status") or "")
    depth = str(report.get("depth") or "")
    case_type = str(report.get("case_type") or "")
    status_tone = "ok"
    if status in {"BLOCKED", "NOT_CONFIDENT"}:
        status_tone = "danger" if status == "BLOCKED" else "warn"
    elif status != "READY_TO_EXECUTE":
        status_tone = "warn"

    status_bits = [
        f"Status: {status or 'unknown'}",
        f"Depth: {depth or '—'}",
        f"Case: {case_type or '—'}",
    ]
    if risk_flags:
        status_bits.append("Risk flags: " + ", ".join(risk_flags))
    if council.get("required") is True:
        runs = council.get("runs") if isinstance(council.get("runs"), list) else []
        run_statuses = [
            str(run.get("status"))
            for run in runs
            if isinstance(run, dict) and run.get("status")
        ]
        status_bits.append(
            "Council: required"
            + (f" ({', '.join(run_statuses)})" if run_statuses else "")
        )
    elif council.get("skip_reason"):
        status_bits.append(f"Council skipped: {council.get('skip_reason')}")
    if blockers:
        status_bits.append("Blockers: " + "; ".join(blockers))
    if residuals:
        status_bits.append("Residuals: " + "; ".join(residuals))

    success = _as_str_list(frozen.get("success_criteria"))
    non_goals = _as_str_list(frozen.get("non_goals"))
    invariants = _as_str_list(frozen.get("invariants"))
    constraints = _as_str_list(frozen.get("constraints"))
    no_go = _as_str_list(frozen.get("no_go"))

    step_rows: list[list[str]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        how = _as_str_list(step.get("how"))
        dod = _as_str_list(step.get("dod"))
        surfaces = _as_str_list(step.get("surfaces"))
        depends = _as_str_list(step.get("depends_on"))
        proofs = _as_str_list(step.get("proof_ids"))
        preconditions = _as_str_list(step.get("preconditions"))
        how_text = _join_bullets(how, empty="(how not recorded)")
        if preconditions:
            how_text = f"Pre: {_join_bullets(preconditions)} | How: {how_text}"
        step_rows.append(
            [
                str(step.get("id", "")),
                str(step.get("title", "")),
                str(step.get("why", "")),
                how_text,
                _join_bullets(surfaces),
                _join_bullets(depends, empty="—"),
                _join_bullets(dod),
                _join_bullets(proofs),
            ]
        )

    acceptance_rows: list[list[str]] = []
    for item in acceptance:
        if not isinstance(item, dict):
            continue
        proof_ids = _as_str_list(item.get("proof_ids"))
        proof_labels = []
        for pid in proof_ids:
            proof = proof_by_id.get(pid)
            if isinstance(proof, dict):
                proof_labels.append(
                    f"{pid}: {proof.get('proof', '')} [{proof.get('status', '')}]"
                )
            else:
                proof_labels.append(pid)
        acceptance_rows.append(
            [
                str(item.get("criterion", "")),
                _join_bullets(_as_str_list(item.get("step_ids"))),
                _join_bullets(proof_labels),
            ]
        )

    risk_rows: list[list[str]] = []
    for item in risks:
        if not isinstance(item, dict):
            continue
        risk_rows.append(
            [
                str(item.get("id", "")),
                str(item.get("severity", "")),
                str(item.get("status", "")),
                str(item.get("claim", "")),
                str(item.get("mitigation", "")),
            ]
        )

    evidence_items = []
    for item in evidence:
        if isinstance(item, dict):
            evidence_items.append(
                f"{item.get('id', '')} [{item.get('classification', '')}]: "
                f"{item.get('claim', '')} ({item.get('locator', '')})"
            )

    rejected = thesis.get("rejected_alternatives") or []
    if not isinstance(rejected, list):
        rejected = []

    surfaces_mapped = _as_str_list(study.get("surfaces_mapped"))
    tools_used = _as_str_list(study.get("tools_used"))
    cuts = _as_str_list(simplicity.get("cuts"))
    retained = _as_str_list(simplicity.get("retained_complexity_justifications"))

    sections: list[JsonObject] = [
        {
            "heading": "Status",
            "blocks": [
                {
                    "type": "callout",
                    "tone": status_tone,
                    "text": " | ".join(status_bits),
                }
            ],
        },
        {
            "heading": "Goal & scope",
            "blocks": [
                {"type": "paragraph", "text": str(frozen.get("goal", ""))},
                {
                    "type": "table",
                    "headers": ["Lens", "Items"],
                    "rows": [
                        ["Success criteria", _join_bullets(success, empty="(none)")],
                        ["Non-goals", _join_bullets(non_goals, empty="(none)")],
                        ["Invariants", _join_bullets(invariants, empty="(none)")],
                        ["Constraints", _join_bullets(constraints, empty="(none)")],
                        ["No-go", _join_bullets(no_go, empty="(none)")],
                    ],
                },
            ],
        },
        {
            "heading": "Thesis",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": str(thesis.get("approach") or thesis.get("summary") or ""),
                },
                {
                    "type": "list",
                    "items": [f"Rejected: {item}" for item in rejected]
                    or ["(no rejected alternatives recorded)"],
                },
            ],
        },
        {
            "heading": "Steps (what / how / where / done)",
            "blocks": [
                {
                    "type": "table",
                    "headers": [
                        "ID",
                        "Step",
                        "Why",
                        "How",
                        "Surfaces",
                        "Deps",
                        "DoD",
                        "Proofs",
                    ],
                    "rows": step_rows or [["", "No steps", "", "", "", "", "", ""]],
                }
            ],
        },
        {
            "heading": "Acceptance map",
            "blocks": [
                {
                    "type": "table",
                    "headers": ["Success criterion", "Steps", "Proofs"],
                    "rows": acceptance_rows
                    or [["(no acceptance_trace)", "", ""]],
                }
            ],
        },
    ]

    if risk_rows or risk_flags:
        risk_blocks: list[JsonObject] = []
        if risk_flags:
            risk_blocks.append(
                {
                    "type": "callout",
                    "tone": "warn",
                    "text": "Risk flags: " + ", ".join(risk_flags),
                }
            )
        risk_blocks.append(
            {
                "type": "table",
                "headers": ["ID", "Severity", "Status", "Claim", "Mitigation"],
                "rows": risk_rows or [["", "", "", "(no structured risks)", ""]],
            }
        )
        sections.append({"heading": "Risks", "blocks": risk_blocks})

    if blockers or residuals:
        open_items = []
        if blockers:
            open_items.extend([f"BLOCKER: {item}" for item in blockers])
        if residuals:
            open_items.extend([f"Residual: {item}" for item in residuals])
        sections.append(
            {
                "heading": "Open items",
                "blocks": [
                    {
                        "type": "callout",
                        "tone": "danger" if blockers else "warn",
                        "text": " | ".join(open_items),
                    }
                ],
            }
        )

    if evidence_items:
        sections.append(
            {
                "heading": "Evidence",
                "blocks": [{"type": "list", "items": evidence_items}],
            }
        )

    study_items = []
    if surfaces_mapped:
        study_items.append("Surfaces: " + ", ".join(surfaces_mapped))
    if tools_used:
        study_items.append("Tools: " + ", ".join(tools_used))
    if study_items:
        sections.append(
            {
                "heading": "Study receipts",
                "blocks": [{"type": "list", "items": study_items}],
            }
        )

    if cuts or retained:
        simple_blocks: list[JsonObject] = []
        if cuts:
            simple_blocks.append(
                {
                    "type": "list",
                    "items": [f"Cut: {item}" for item in cuts],
                }
            )
        if retained:
            simple_blocks.append(
                {
                    "type": "callout",
                    "tone": "warn",
                    "text": "Retained complexity: " + " | ".join(retained),
                }
            )
        sections.append({"heading": "Simplicity", "blocks": simple_blocks})

    return {
        "id": "00",
        "slug": "plano",
        "title": "Plano",
        "summary": str(frozen.get("prompt_summary") or frozen.get("goal") or "Plan"),
        "sections": sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to plan-report.json")
    parser.add_argument(
        "--out",
        required=True,
        help="Plan output directory (created if missing)",
    )
    args = parser.parse_args()

    try:
        report = load_json(args.report)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: failed to load report: {error}", file=sys.stderr)
        return 2

    chapters = report.get("chapters")
    if not isinstance(chapters, list):
        chapters = []
    if not chapters:
        chapters = [synthesize_compact_chapter(report)]
        report["chapters"] = chapters

    out_dir = Path(args.out).expanduser()
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    else:
        out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "assets").mkdir(exist_ok=True)

    # Keep output.plan_dir and html_files aligned with render target.
    html_files = [chapter_filename(chapter) for chapter in chapters if isinstance(chapter, dict)]
    output = report.get("output") if isinstance(report.get("output"), dict) else {}
    output = dict(output)
    output["plan_dir"] = str(out_dir)
    output["html_files"] = html_files
    report["output"] = output

    meta = [
        f"status:{report.get('status', '')}",
        f"depth:{report.get('depth', '')}",
        f"case:{report.get('case_type', '')}",
    ]

    for chapter in chapters:
        if not isinstance(chapter, dict):
            print("error: chapter entries must be objects", file=sys.stderr)
            return 2
        filename = chapter_filename(chapter)
        body = render_chapter_body(chapter)
        page = render_page(
            title=str(chapter.get("title") or filename),
            subtitle=str(chapter.get("summary") or report.get("frozen", {}).get("goal", "")),
            chapters=chapters,
            filename=filename,
            body=body,
            meta_tags=meta,
        )
        (out_dir / filename).write_text(page, encoding="utf-8")

    report_path = out_dir / "plan-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(str(out_dir))
    for name in html_files:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
