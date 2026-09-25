#!/usr/bin/env python3
"""Render a validated-style plan-report.json into a light-theme multi-page HTML plan pack.

Visual contract (maintainers): light theme only (`color-scheme: light`), self-contained
CSS, sticky nav linking every page in order, callout tones info|ok|warn|danger|decision.
All planner text is HTML-escaped. An empty `chapters` list renders one compact page
synthesized from the freeze; the synthesized chapter is never written back.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]
PORTUGUESE_WORDS = {"a", "ao", "as", "com", "como", "da", "das", "de", "do", "dos", "e", "em", "melhorar", "não", "no", "na", "o", "os", "para", "por", "que", "se", "sem", "sobre", "um", "uma", "usuário", "usuários", "aplicativo", "desempenho", "corrigir", "implementar", "adicionar", "criar", "página", "sistema"}
ENGLISH_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "how", "improve", "implement", "in", "into", "is", "of", "on", "or", "the", "to", "user", "users", "with", "without", "fix", "create", "add", "page", "system", "app", "performance"}
SCRIPT_RE = re.compile(r"<\s*script\b", re.IGNORECASE)
EVENT_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)


CSS = """
:root{color-scheme:light;--brand:#136b55;--brand-dark:#10483e;--ink:#183337;--muted:#5e7274;--line:#dce8e3;--paper:#f5f8f4;--white:#fff;--mint:#e1f4e9;--blue:#e8f0ff;--amber:#fff0cf;--rose:#ffe9e5;--shadow:0 18px 55px rgba(22,58,49,.09);--warn:#865900;--danger:#a5272f;--ok:#107c41}
*{box-sizing:border-box}html{scroll-behavior:smooth;background:var(--paper)}body{margin:0;color:var(--ink);background:var(--paper);font:16px/1.65 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--brand)}a:hover{text-decoration-thickness:2px}
header{padding:clamp(42px,8vw,100px) max(24px,calc((100vw - 1180px)/2));background:radial-gradient(circle at 82% 18%,#d9f4e6 0,transparent 30%),linear-gradient(135deg,#fbfdf9,#eef7f2);border-bottom:1px solid var(--line)}.eyebrow{display:block;margin-bottom:18px;color:var(--brand);font-size:12px;font-weight:850;letter-spacing:.14em;text-transform:uppercase}header h1{max-width:1000px;margin:0;font-size:clamp(38px,6.2vw,76px);line-height:1.04;letter-spacing:-.055em}header p{max-width:850px;margin:18px 0 0;color:#426166;font-size:clamp(18px,2vw,24px);line-height:1.5}.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}
nav{position:sticky;top:0;z-index:5;display:flex;gap:8px;overflow:auto;padding:12px max(20px,calc((100vw - 1180px)/2));border-bottom:1px solid var(--line);background:rgba(255,255,255,.94);backdrop-filter:blur(14px);white-space:nowrap}nav a{flex:0 0 auto;padding:7px 12px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--brand-dark);font-size:12px;font-weight:700;text-decoration:none}nav a[aria-current="page"]{border-color:#b9e6ce;background:var(--mint)}
main{max-width:1240px;margin:0 auto;padding:38px 28px 90px}.chapter-lead{max-width:850px;margin:0 auto 24px;padding:0 8px 22px;color:var(--muted);font-size:18px}.chapter-sections{display:grid;gap:18px}.plan-section{scroll-margin-top:84px;margin:0;padding:clamp(22px,3.4vw,38px);border:1px solid var(--line);border-radius:22px;background:var(--white);box-shadow:0 4px 20px rgba(29,62,51,.035)}.plan-section h2{margin:0 0 15px;font-size:clamp(23px,3vw,34px);line-height:1.17;letter-spacing:-.035em}.plan-section h3{margin:20px 0 8px;font-size:19px;line-height:1.3}.plan-section p{max-width:850px;margin:9px 0}.plan-section.step-card{border-left:5px solid var(--brand);background:linear-gradient(105deg,#f7fbf8 0,#fff 42%)}.plan-section.decision-card{border-left:5px solid #d4a53b;background:linear-gradient(105deg,#fffaf0 0,#fff 48%)}.plan-section.risk-card{border-left:5px solid #cf7168;background:linear-gradient(105deg,#fff7f5 0,#fff 48%)}.section-number{display:block;margin-bottom:9px;color:var(--brand);font-size:12px;font-weight:850;letter-spacing:.12em;text-transform:uppercase}.section-nav{position:static;z-index:auto;display:flex;gap:8px;overflow:auto;margin:0 auto 22px;padding:4px 8px 12px;border:0;background:transparent;backdrop-filter:none}.section-nav a{font-size:12px}.callout{margin:16px 0;padding:15px 18px;border:1px solid #b9e6ce;border-left:5px solid var(--brand);border-radius:14px;background:var(--mint)}.callout.danger{border-color:#f0cfc8;border-left-color:var(--danger);background:var(--rose)}.callout.warn{border-color:#f1d99c;border-left-color:#d4a53b;background:var(--amber)}.callout.ok{border-color:#b9e6ce;border-left-color:var(--ok);background:#f0fff5}.callout.decision{border-color:#d4e6b1;border-left-color:#7aa312;background:#fbfff3}ul,ol{margin:10px 0 10px 22px;padding:0}li{margin:8px 0}.tag{display:inline-block;padding:5px 11px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--muted);font-size:12px;font-weight:700}.tag.strong{border-color:#b9dcd3;background:#eef8f5;color:var(--brand-dark)}.small{color:var(--muted);font-size:14px}code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:#f2f6f5;border:1px solid #dce7e5;border-radius:8px}code{padding:2px 5px}pre{padding:14px;overflow:auto;white-space:pre-wrap}table{width:100%;border-collapse:collapse;margin:14px 0;background:#fff;font-size:14px}th,td{padding:10px;border:1px solid var(--line);text-align:left;vertical-align:top}th{background:#eef8f5;color:#143c38} .callout p:last-child{margin-bottom:0}
@media(max-width:700px){header{padding:52px 20px 42px}.eyebrow{font-size:10px}nav{padding:10px 14px}main{padding:22px 14px 60px}.chapter-lead{padding:0 4px 14px;font-size:16px}.plan-section{padding:22px 19px;border-radius:17px}.plan-section.step-card,.plan-section.decision-card,.plan-section.risk-card{border-left-width:4px}.section-nav{margin:0 -3px 15px;padding-inline:3px}table{display:block;overflow-x:auto;white-space:normal}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
""".strip()


def load_json(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("report must be a JSON object")
    return value


def detect_language(text: str) -> str:
    words = set(re.findall(r"[^\W_]+", text.casefold(), re.UNICODE))
    return "pt" if len(words & PORTUGUESE_WORDS) > len(words & ENGLISH_WORDS) else "en"


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
    html_language = detect_language(f"{title} {subtitle}")
    return f"""<!doctype html>
<html lang="{html_language}">
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
    <div class="eyebrow">{"PLANO / VISÃO PARA PESSOAS" if html_language == "pt" else "PLAN / HUMAN-READABLE BRIEF"}</div>
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
    sections = chapter.get("sections") or []
    parts = ['<div class="chapter-sections">']
    for index, section in enumerate(sections, start=1):
        heading = str(section.get("heading", ""))
        normalized = heading.casefold()
        card_class = "plan-section"
        if re.match(r"^\d+[.)]", heading):
            card_class += " step-card"
        elif any(token in normalized for token in ("decision", "decis", "architecture", "arquitetura")):
            card_class += " decision-card"
        elif any(token in normalized for token in ("risk", "risco", "block", "bloqueio", "open", "pendência", "questão")):
            card_class += " risk-card"
        parts.append(f'<section class="{card_class}" id="section-{index}">')
        step = re.match(r"^(\d+)[.)]", heading)
        if step:
            label = "ETAPA" if detect_language(str(chapter.get("summary", ""))) == "pt" else "STEP"
            parts.append(f'<span class="section-number">{label} {int(step.group(1)):02d}</span>')
        parts.append(f"<h2>{esc(heading)}</h2>")
        for block in section.get("blocks") or []:
            if isinstance(block, dict):
                parts.append(render_block(block))
        parts.append("</section>")
    parts.append("</div>")
    if sections:
        label = "Navegue por esta página" if detect_language(str(chapter.get("summary", ""))) == "pt" else "On this page"
        links = "".join(f'<a href="#section-{index}">{esc(section.get("heading", ""))}</a>' for index, section in enumerate(sections, start=1))
        parts.insert(0, f'<nav class="section-nav" aria-label="{esc(label)}">{links}</nav>')
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

    portuguese = detect_language(f"{frozen.get('prompt_summary', '')} {frozen.get('goal', '')}") == "pt"
    status_labels = {
        "Status: ": "Situação: " if portuguese else "Status: ",
        "Depth: ": "Detalhamento: " if portuguese else "Plan size: ",
        "Case: ": "Tipo: " if portuguese else "Plan type: ",
        "Risk flags: ": "Riscos: " if portuguese else "Risk areas: ",
        "Council: required": "Revisão independente necessária" if portuguese else "Independent review required",
        "Council skipped: ": "Revisão independente dispensada: " if portuguese else "Independent review skipped: ",
        "Blockers: ": "Bloqueios: " if portuguese else "Blocked by: ",
        "Residuals: ": "Pendências: " if portuguese else "Remaining questions: ",
    }
    status_bits = [next((translated + text[len(source):] for source, translated in status_labels.items() if text.startswith(source)), text) for text in status_bits]
    if portuguese:
        status_bits = [bit.replace("READY_TO_EXECUTE", "Pronto para executar").replace("NOT_CONFIDENT", "Ainda falta confirmação").replace("BLOCKED", "Bloqueado").replace("simple", "enxuto").replace("standard", "padrão").replace("deep", "detalhado").replace("BUG", "Correção").replace("FEATURE", "Funcionalidade").replace("PRODUCT", "Produto").replace("MIGRATION", "Migração").replace("OPS", "Operação").replace("SPIKE", "Investigação") for bit in status_bits]

    success = _as_str_list(frozen.get("success_criteria"))
    non_goals = _as_str_list(frozen.get("non_goals"))
    invariants = _as_str_list(frozen.get("invariants"))
    constraints = _as_str_list(frozen.get("constraints"))
    no_go = _as_str_list(frozen.get("no_go"))

    evidence_items = []
    for item in evidence:
        if isinstance(item, dict):
            evidence_items.append(
                f"{item.get('classification', '')}: {item.get('claim', '')}"
            )

    rejected = thesis.get("rejected_alternatives") or []
    if not isinstance(rejected, list):
        rejected = []

    cuts = _as_str_list(simplicity.get("cuts"))
    retained = _as_str_list(simplicity.get("retained_complexity_justifications"))

    sections: list[JsonObject] = [
        {
            "heading": "The situation",
            "blocks": [
                {"type": "paragraph", "text": str(frozen.get("goal", ""))},
                {"type": "paragraph", "text": str(thesis.get("summary", ""))},
                {"type": "callout", "tone": status_tone, "text": " | ".join(status_bits)},
            ],
        },
        {
            "heading": "What success looks like",
            "blocks": [
                {"type": "list", "items": success or ["Success criteria are not recorded."]},
                {"type": "paragraph", "text": "What this plan leaves out: " + _join_bullets(non_goals, empty="Nothing explicitly excluded.")},
                {"type": "paragraph", "text": "Constraints and invariants: " + _join_bullets(invariants + constraints + no_go, empty="No additional constraints recorded.")},
            ],
        },
        {
            "heading": "The proposed direction",
            "blocks": [
                {"type": "paragraph", "text": str(thesis.get("approach") or thesis.get("summary") or "")},
                {"type": "paragraph", "text": "Why this direction: " + str(steps[0].get("why", "")) if steps and isinstance(steps[0], dict) else ""},
                {"type": "list", "items": [f"Considered and set aside: {item}" for item in rejected] or ["No alternative approach was recorded."]},
            ],
        },
    ]

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        sequence_blocks: list[JsonObject] = [
            {"type": "paragraph", "text": str(step.get("why", ""))},
            {"type": "paragraph", "text": "What happens: " + _join_bullets(_as_str_list(step.get("how")))},
        ]
        step_titles = {str(item.get("id")): str(item.get("title", "")) for item in steps if isinstance(item, dict)}
        dependencies = [step_titles.get(dep, dep) for dep in _as_str_list(step.get("depends_on"))]
        surfaces = _as_str_list(step.get("surfaces"))
        if dependencies:
            sequence_blocks.append({"type": "paragraph", "text": "Depends on: " + ", ".join(dependencies)})
        if surfaces:
            sequence_blocks.append({"type": "paragraph", "text": "Areas involved: " + ", ".join(surfaces)})
        sequence_blocks.append({"type": "callout", "tone": "ok", "text": "Done when: " + _join_bullets(_as_str_list(step.get("dod")))})
        proof_ids = _as_str_list(step.get("proof_ids"))
        proof_text = [str(proof_by_id.get(pid, {}).get("proof", pid)) for pid in proof_ids]
        if proof_text:
            sequence_blocks.append({"type": "paragraph", "text": "How we will check: " + _join_bullets(proof_text)})
        sections.append({"heading": f"{index}. {step.get('title', 'Delivery step')}", "blocks": sequence_blocks})

    if acceptance:
        acceptance_items = []
        for item in acceptance:
            if not isinstance(item, dict):
                continue
            proof_labels = [str(proof_by_id.get(pid, {}).get("proof", pid)) for pid in _as_str_list(item.get("proof_ids"))]
            acceptance_items.append(str(item.get("criterion", "")) + (" — checked by: " + _join_bullets(proof_labels) if proof_labels else ""))
        sections.append({"heading": "How we will know it worked", "blocks": [{"type": "list", "items": acceptance_items}]})

    if risks or risk_flags:
        risk_items = [f"{item.get('severity', 'unspecified')} risk ({item.get('status', 'unresolved')}): {item.get('claim', '')} — mitigation: {item.get('mitigation', 'not recorded')}" for item in risks if isinstance(item, dict)]
        if risk_flags and not risk_items:
            risk_items = [f"Risk area to address: {flag.replace('_', ' ')}" for flag in risk_flags]
        risk_blocks = [{"type": "paragraph", "text": "Risks that shape this plan: " + _join_bullets(risk_items, empty="No additional risks recorded.")}]
        if risk_flags:
            risk_blocks.append({"type": "callout", "tone": "warn", "text": "Risk categories: " + ", ".join(flag.replace("_", " ") for flag in risk_flags)})
        sections.append({"heading": "Trade-offs and risks", "blocks": risk_blocks})

    open_items = [f"Decision needed: {item.get('claim', '')} — next probe: {item.get('probe', '')}" for item in report.get("unknowns", []) if isinstance(item, dict) and item.get("material")]
    open_items.extend(f"Blocker: {item}" for item in blockers)
    open_items.extend(f"Still to resolve: {item}" for item in residuals)
    if open_items:
        sections.append({"heading": "Questions still open", "blocks": [{"type": "list", "items": open_items}]})

    if evidence_items:
        sections.append({"heading": "What this plan is based on", "blocks": [{"type": "list", "items": evidence_items}]})

    if cuts or retained:
        simplicity_items = [f"Deferred: {item}" for item in cuts] + [f"Kept despite added complexity: {item}" for item in retained]
        sections.append({"heading": "Why the plan stays this small", "blocks": [{"type": "list", "items": simplicity_items}]})

    chapter = {
        "id": "00",
        "slug": "plano",
        "title": str(frozen.get("prompt_summary") or frozen.get("goal") or "Plan"),
        "summary": str(frozen.get("goal") or frozen.get("prompt_summary") or "Plan"),
        "sections": sections,
    }
    language_text = f"{frozen.get('prompt_summary', '')} {frozen.get('goal', '')}"
    if detect_language(language_text) == "pt":
        headings = {
            "The situation": "Contexto e problema",
            "What success looks like": "Como será o sucesso",
            "The proposed direction": "Abordagem proposta",
            "Trade-offs and risks": "Trade-offs e riscos",
            "Questions still open": "Questões em aberto",
            "What this plan is based on": "O que sustenta este plano",
            "Why the plan stays this small": "Por que o plano mantém este escopo",
            "How we will know it worked": "Como vamos confirmar o resultado",
        }
        phrases = {
            "What this plan leaves out: ": "Fora do escopo: ",
            "Constraints and invariants: ": "Restrições e invariantes: ",
            "Why this direction: ": "Por que esta abordagem: ",
            "Considered and set aside: ": "Alternativa considerada e descartada: ",
            "What happens: ": "O que será feito: ",
            "Depends on: ": "Depende de: ",
            "Areas involved: ": "Áreas envolvidas: ",
            "Done when: ": "Concluído quando: ",
            "How we will check: ": "Como verificar: ",
            "Risks that shape this plan: ": "Riscos considerados neste plano: ",
            "Risk categories: ": "Categorias de risco: ",
            "Decision needed: ": "Decisão necessária: ",
            " — next probe: ": " — próxima verificação: ",
            "Blocker: ": "Bloqueio: ",
            "Still to resolve: ": "Ainda precisa ser resolvido: ",
            "Success criteria are not recorded.": "Os critérios de sucesso não foram registrados.",
            "Nothing explicitly excluded.": "Nada foi explicitamente excluído.",
            "No additional constraints recorded.": "Nenhuma restrição adicional registrada.",
            "No alternative approach was recorded.": "Nenhuma abordagem alternativa foi registrada.",
            "No additional risks recorded.": "Nenhum risco adicional foi registrado.",
        }
        for section in chapter["sections"]:
            section["heading"] = headings.get(section["heading"], section["heading"])
            for block in section.get("blocks", []):
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    text = block["text"]
                    for source, translated in phrases.items():
                        text = text.replace(source, translated)
                    block["text"] = text
                if isinstance(block, dict) and isinstance(block.get("items"), list):
                    block["items"] = [next((value + item[len(key):] for key, value in phrases.items() if item.startswith(key)), phrases.get(item, item)) for item in block["items"]]
    return chapter


def render_report_status(report: JsonObject) -> str:
    portuguese = detect_language(" ".join(str(report.get("frozen", {}).get(key, "")) for key in ("prompt_summary", "goal"))) == "pt"
    risks = [item for item in report.get("risks", []) if isinstance(item, dict)]
    unknowns = [item for item in report.get("unknowns", []) if isinstance(item, dict) and item.get("material")]
    open_items = [str(item.get("claim", "")) for item in unknowns]
    open_items.extend(_as_str_list(report.get("blockers")))
    open_items.extend(_as_str_list(report.get("residuals")))
    risk_text = [f"{item.get('severity', 'unspecified')} / {item.get('status', 'unresolved')}: {item.get('claim', '')} — {item.get('mitigation', 'No mitigation recorded.') if not portuguese else item.get('mitigation', 'Mitigação não registrada.')}" for item in risks]
    if report.get("risk_flags") and not risk_text:
        risk_text = [str(flag).replace("_", " ") for flag in report["risk_flags"]]
    if not risk_text and not open_items:
        return ""
    heading = "Riscos e questões em aberto" if portuguese else "Risks and open questions"
    risk_heading = "Riscos e mitigações" if portuguese else "Risks and mitigations"
    open_heading = "Decisões e pendências" if portuguese else "Decisions and unresolved items"
    parts = [f'<section class="plan-section risk-card" id="report-status"><h2>{esc(heading)}</h2>']
    if risk_text:
        parts.append(f"<h3>{esc(risk_heading)}</h3>{render_list(risk_text)}")
    if open_items:
        parts.append(f"<h3>{esc(open_heading)}</h3>{render_list(open_items)}")
    parts.append("</section>")
    return "\n".join(parts)


def chapter_source_text(chapters: list[JsonObject]) -> str:
    fragments: list[str] = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        fragments.extend([str(chapter.get("title", "")), str(chapter.get("summary", ""))])
        for section in chapter.get("sections", []):
            if not isinstance(section, dict):
                continue
            fragments.append(str(section.get("heading", "")))
            for block in section.get("blocks", []):
                if not isinstance(block, dict):
                    continue
                fragments.append(str(block.get("text", "")))
                fragments.extend(str(item) for item in block.get("items", []))
                fragments.extend(str(cell) for row in block.get("rows", []) for cell in row)
    return " ".join(fragments).casefold()


def render_report_delivery_summary(report: JsonObject, chapters: list[JsonObject]) -> tuple[str, list[tuple[str, str]]]:
    frozen = report.get("frozen") if isinstance(report.get("frozen"), dict) else {}
    source_text = chapter_source_text(chapters)
    portuguese = detect_language(f"{frozen.get('prompt_summary', '')} {frozen.get('goal', '')}") == "pt"
    sections: list[str] = []
    links: list[tuple[str, str]] = []
    success = _as_str_list(frozen.get("success_criteria"))
    missing_success = [criterion for criterion in success if criterion.casefold() not in source_text]
    if missing_success:
        section_id = "report-success"
        title = "Critérios de sucesso ainda não detalhados" if portuguese else "Success criteria not covered elsewhere"
        sections.append(f'<section class="plan-section" id="{section_id}"><h2>{esc(title)}</h2>{render_list(missing_success)}</section>')
        links.append((section_id, "Critérios de sucesso" if portuguese else "Success criteria"))

    steps = [step for step in report.get("steps", []) if isinstance(step, dict)]
    step_titles = {str(step.get("id")): str(step.get("title", "")) for step in steps}
    verifications = {str(item.get("id")): item for item in report.get("verifications", []) if isinstance(item, dict)}
    for index, step in enumerate(steps, start=1):
        details = [str(step.get("title", "")), str(step.get("why", "")), *_as_str_list(step.get("how")), *_as_str_list(step.get("dod")), *_as_str_list(step.get("surfaces"))]
        details.extend(step_titles.get(dep, dep) for dep in _as_str_list(step.get("depends_on")))
        details.extend(str(verifications.get(pid, {}).get("proof", pid)) for pid in _as_str_list(step.get("proof_ids")))
        if all(detail and detail.casefold() in source_text for detail in details):
            continue
        section_id = f"report-step-{index}"
        title = str(step.get("title", "Etapa de entrega" if portuguese else "Delivery step"))
        label = "ETAPA" if portuguese else "STEP"
        content = [f'<span class="section-number">{label} {index:02d}</span>', f"<h2>{esc(title)}</h2>"]
        if step.get("why"):
            content.append(f"<p>{safe_text(str(step['why']))}</p>")
        how = _as_str_list(step.get("how"))
        if how:
            content.append(f"<h3>{'O que será feito' if portuguese else 'What will happen'}</h3>{render_list(how)}")
        dependencies = [step_titles.get(dep, dep) for dep in _as_str_list(step.get("depends_on"))]
        if dependencies:
            content.append(f"<p><strong>{'Depende de' if portuguese else 'Depends on'}:</strong> {safe_text(', '.join(dependencies))}</p>")
        surfaces = _as_str_list(step.get("surfaces"))
        if surfaces:
            content.append(f"<p><strong>{'Áreas envolvidas' if portuguese else 'Areas involved'}:</strong> {safe_text(', '.join(surfaces))}</p>")
        dod = _as_str_list(step.get("dod"))
        if dod:
            content.append(f"<div class=\"callout ok\"><strong>{'Concluído quando' if portuguese else 'Done when'}:</strong>{render_list(dod)}</div>")
        proof_labels = [str(verifications.get(pid, {}).get("proof", pid)) for pid in _as_str_list(step.get("proof_ids"))]
        if proof_labels:
            content.append(f"<p><strong>{'Como verificar' if portuguese else 'How to verify'}:</strong> {safe_text(_join_bullets(proof_labels))}</p>")
        sections.append(f'<section class="plan-section step-card" id="{section_id}">{"".join(content)}</section>')
        links.append((section_id, title))

    acceptance = [item for item in report.get("acceptance_trace", []) if isinstance(item, dict)]
    success_set = {criterion.casefold() for criterion in success}
    missing_acceptance = []
    for item in acceptance:
        criterion = str(item.get("criterion", ""))
        proofs = [str(verifications.get(pid, {}).get("proof", pid)) for pid in _as_str_list(item.get("proof_ids"))]
        missing_proofs = [proof for proof in proofs if proof.casefold() not in source_text]
        criterion_missing = criterion.casefold() not in source_text and criterion.casefold() not in success_set
        if criterion_missing or missing_proofs:
            missing_acceptance.append((item, criterion_missing, missing_proofs))
    if missing_acceptance:
        section_id = "report-acceptance"
        title = "Como vamos confirmar o resultado" if portuguese else "How we will confirm the outcome"
        rows = []
        for item, criterion_missing, missing_proofs in missing_acceptance:
            criterion = str(item.get("criterion", ""))
            if criterion_missing:
                proofs = [str(verifications.get(pid, {}).get("proof", pid)) for pid in _as_str_list(item.get("proof_ids"))]
                rows.append(criterion + (" — " + _join_bullets(proofs) if proofs else ""))
            else:
                label = "Verificar" if portuguese else "Verify"
                rows.append(f"{label} {criterion}: " + _join_bullets(missing_proofs))
        sections.append(f'<section class="plan-section" id="{section_id}"><h2>{esc(title)}</h2>{render_list(rows)}</section>')
        links.append((section_id, "Aceitação" if portuguese else "Acceptance"))
    return "\n".join(sections), links


def md_escape(value: Any) -> str:
    text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>-])", lambda match: "\\" + match.group(1), text)


def render_agent_markdown(report: JsonObject) -> str:
    frozen = report.get("frozen") if isinstance(report.get("frozen"), dict) else {}
    thesis = report.get("thesis") if isinstance(report.get("thesis"), dict) else {}
    probe = " ".join([str(frozen.get("prompt_summary", "")), str(frozen.get("goal", ""))])
    portuguese = detect_language(probe) == "pt"
    labels = {
        "title": "Plano de implementação" if portuguese else "Implementation plan",
        "goal": "Objetivo" if portuguese else "Goal",
        "scope": "Limites do escopo" if portuguese else "Scope boundaries",
        "success": "Critérios de sucesso" if portuguese else "Included success criteria",
        "nong": "Fora do escopo" if portuguese else "Non-goals",
        "decisions": "Decisões e restrições" if portuguese else "Decisions and constraints",
        "steps": "Etapas ordenadas de implementação" if portuguese else "Ordered implementation steps",
        "risks": "Riscos" if portuguese else "Risks",
        "open": "Pendências e condições para interromper" if portuguese else "Open items and stop conditions",
        "acceptance": "Verificações de aceitação" if portuguese else "Acceptance checks",
        "implementation": "Implementação" if portuguese else "Implementation",
        "paths": "Caminhos relevantes" if portuguese else "Relevant paths",
        "dependencies": "Dependências" if portuguese else "Dependencies",
        "dod": "Definição de pronto" if portuguese else "Definition of done",
        "proof": "Como verificar" if portuguese else "Proof",
    }
    escape = md_escape
    title = frozen.get("prompt_summary") or frozen.get("goal", "Plan")
    steps = [item for item in report.get("steps", []) if isinstance(item, dict)]
    step_titles = {str(item.get("id")): str(item.get("title", "")) for item in steps}
    verifications = {str(item.get("id")): item for item in report.get("verifications", []) if isinstance(item, dict)}
    lines = [f"# {labels['title']}: {escape(title)}", "", f"Status: **{escape(report.get('status', 'UNKNOWN'))}** · Depth: **{escape(report.get('depth', 'unknown'))}**", "", f"## {labels['goal']}", escape(frozen.get("goal", "")), "", f"## {labels['scope']}", f"### {labels['success']}"]
    lines.extend(f"- {escape(item)}" for item in _as_str_list(frozen.get("success_criteria")))
    lines.extend(["", f"### {labels['nong']}"])
    lines.extend(f"- {escape(item)}" for item in _as_str_list(frozen.get("non_goals")))
    lines.extend(["", f"## {labels['decisions']}", escape(thesis.get("approach") or thesis.get("summary") or "")])
    for heading, key in (("Invariants" if not portuguese else "Invariantes", "invariants"), ("Constraints" if not portuguese else "Restrições", "constraints"), ("Do not do" if not portuguese else "Não fazer", "no_go")):
        items = _as_str_list(frozen.get(key))
        if items:
            lines.extend(["", f"### {heading}"])
            lines.extend(f"- {escape(item)}" for item in items)
    lines.extend(["", f"## {labels['steps']}"])
    for index, step in enumerate(steps, start=1):
        lines.extend(["", f"### {index}. {escape(step.get('title', ''))}", escape(step.get("why", ""))])
        for label, key in ((labels["implementation"], "how"), (labels["paths"], "surfaces"), (labels["dependencies"], "depends_on"), (labels["dod"], "dod")):
            items = _as_str_list(step.get(key))
            if key == "depends_on":
                items = [step_titles.get(value, value) for value in items]
            if items:
                lines.extend(["", f"**{label}**"])
                lines.extend(f"- {escape(item)}" for item in items)
        proof_items = []
        for proof_id in _as_str_list(step.get("proof_ids")):
            proof = verifications.get(proof_id, {})
            text = str(proof.get("proof", proof_id))
            if proof.get("reason"):
                text += f" — {proof['reason']}"
            proof_items.append(text)
        if proof_items:
            lines.extend(["", f"**{labels['proof']}**"])
            lines.extend(f"- {escape(item)}" for item in proof_items)
    lines.extend(["", f"## {labels['risks']}"])
    risk_items = [item for item in report.get("risks", []) if isinstance(item, dict)]
    if risk_items:
        for item in risk_items:
            lines.append(f"- {escape(item.get('severity', 'unknown'))} / {escape(item.get('status', 'unknown'))}: {escape(item.get('claim', ''))} Mitigation: {escape(item.get('mitigation', ''))}")
    elif _as_str_list(report.get("risk_flags")):
        lines.extend(f"- {escape(flag.replace('_', ' '))}" for flag in _as_str_list(report.get("risk_flags")))
    else:
        lines.append("- No additional risks recorded." if not portuguese else "- Nenhum risco adicional registrado.")
    open_items = [str(item.get("claim", "")) for item in report.get("unknowns", []) if isinstance(item, dict) and item.get("material")]
    open_items.extend(_as_str_list(report.get("blockers")))
    open_items.extend(_as_str_list(report.get("residuals")))
    lines.extend(["", f"## {labels['open']}"])
    lines.extend(f"- {escape(item)}" for item in open_items)
    if not open_items:
        lines.append("- No material open items recorded. Stop and reassess if implementation contradicts a frozen decision or verification fails." if not portuguese else "- Nenhuma pendência material registrada. Pare e reavalie se a implementação contrariar uma decisão congelada ou uma verificação falhar.")
    lines.extend(["", f"## {labels['acceptance']}"])
    for item in report.get("acceptance_trace", []):
        if isinstance(item, dict):
            proof_text = [str(verifications.get(pid, {}).get("proof", pid)) for pid in _as_str_list(item.get("proof_ids"))]
            lines.append(f"- {escape(item.get('criterion', ''))}" + (" — " + "; ".join(escape(value) for value in proof_text) if proof_text else ""))
    return "\n".join(lines).rstrip() + "\n"


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
        # In memory only: persisting it would make later renders reuse a stale page.
        chapters = [synthesize_compact_chapter(report)]

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
    output["agent_file"] = "agent-plan.md"
    report["output"] = output

    meta = [
        f"status:{report.get('status', '')}",
        f"depth:{report.get('depth', '')}",
        f"case:{report.get('case_type', '')}",
    ]

    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            print("error: chapter entries must be objects", file=sys.stderr)
            return 2
        filename = chapter_filename(chapter)
        body = render_chapter_body(chapter)
        if index == 0 and report.get("chapters"):
            delivery_summary, delivery_links = render_report_delivery_summary(report, chapters)
            status_panel = render_report_status(report)
            portuguese = detect_language(str(chapter.get("summary", ""))) == "pt"
            supplement_links = "".join(f'<a href="#{esc(section_id)}">{esc(label)}</a>' for section_id, label in delivery_links)
            if status_panel:
                nav_label = "Riscos e pendências" if portuguese else "Risks and open questions"
                supplement_links += f'<a href="#report-status">{esc(nav_label)}</a>'
            if supplement_links:
                body = body.replace("</nav>", supplement_links + "</nav>", 1)
            body += delivery_summary + status_panel
        page = render_page(
            title=str(chapter.get("title") or filename),
            subtitle=str(chapter.get("summary") or report.get("frozen", {}).get("goal", "")),
            chapters=chapters,
            filename=filename,
            body=body,
            meta_tags=meta,
        )
        (out_dir / filename).write_text(page, encoding="utf-8")

    agent_path = out_dir / "agent-plan.md"
    agent_path.write_text(render_agent_markdown(report), encoding="utf-8")
    artifact_names = [*html_files, "agent-plan.md"]
    output["artifact_sha256"] = {
        name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
        for name in artifact_names
    }
    hash_report = json.loads(json.dumps(report))
    hash_output = hash_report["output"]
    hash_output.pop("artifact_sha256", None)
    hash_output.pop("rendered_report_sha256", None)
    canonical = json.dumps(hash_report, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    output["rendered_report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    report_path = out_dir / "plan-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(str(out_dir))
    for name in html_files:
        print(name)
    print("agent-plan.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
