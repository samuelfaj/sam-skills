---
name: sam-plan
description: "Study a task and produce a validated plan freeze, a descriptive human-first HTML plan, and an executable agent-plan.md handoff; council only on risk triggers. Use when the user runs /sam-plan, asks for an implementation plan, or needs pre-implementation planning before sam-task/sam-work."
---

# Sam Plan

Turn one planning prompt into a conducted inquiry and decision freeze with three complementary artifacts: `plan-report.json` as the validated source of truth, a descriptive, human-first HTML plan, and `agent-plan.md` as a concise, executable handoff for coding agents. The HTML and Markdown must communicate the same decisions and scope; neither replaces the JSON gate.

## Non-Negotiable Contract

- Plan only: no production code edits, commits, PRs, deploys, or external
  writes beyond the plan directory and local scratch.
- Separate `FACT`, `ASSUMPTION`, and `UNKNOWN`. Never invent locators, promote
  guesses to facts, or raise confidence by repetition; prefer `UNKNOWN`.
  Absent external systems, guessed production state, and imagined APIs are
  not facts.
- Every terminal plan has a validated `plan-report.json`, a human-first HTML
  plan rendered only by `scripts/render_plan_html.py`, and `agent-plan.md` in the
  plan directory. Keep the HTML descriptive and decision-oriented: explain the
  context, user problem, intended outcome, proposed experience, approach,
  staged delivery, trade-offs, risks, open decisions, and how success will be
  recognized. Use authored `chapters[]` to shape the narrative whenever the
  plan has more than one meaningful topic; do not force a long-form pack for a
  genuinely small fix. Never write HTML or CSS yourself; wireframes stay
  textual unless the user provides or requests images.
- `agent-plan.md` is a Markdown execution handoff, not a copy of the human
  narrative or the JSON. Include goal and non-goals, decisions and constraints,
  ordered implementation steps with relevant paths, dependencies, definition
  of done and proof, plus risks, unresolved items, and explicit stop conditions.
  Keep its scope and decisions consistent with the validated report and HTML.
  Write it from the final report after HTML rendering, then validate that it
  exists and is non-empty before declaring the plan complete.
- Fail closed: `NOT_CONFIDENT` (useful plan, but material unknowns,
  unaccepted assumptions, or `NOT_RUN` proofs remain) or `BLOCKED` (missing
  access, owner decision, unsafe scope, or council/runtime capability prevents
  a defensible plan) beats a false `READY_TO_EXECUTE`. Never claim a finished
  plan without `VALID` from the `--require-html` run.
- Council only on risk triggers or explicit user request, never on depth
  labels. One council run per freeze; an author-revised thesis is not another
  round.
- Redact secrets, credentials, tokens, and private customer data from all plan
  artifacts.

## Resources

| Read | When |
| --- | --- |
| `references/output-contract.md` | Workflow step 3, when drafting the freeze (holds the risk-flag catalog) |
| `references/complexity-routing.md` | Before choosing `simple`, or when depth is ambiguous |
| `references/council-integration.md`; then `../sam-council/SKILL.md` (full; never emulate) only if you run council yourself (standalone or inline in the controller) | Workflow step 4: a risk flag fires or the user requests council |
| `references/chapter-taxonomy.md` | Only when authoring `chapters[]` |

Re-read a file only after compaction or when you cannot quote the section you
need.

## Study Loop

Workflow step 2. Investigate with tools first; ask the user only when
standalone and a material unknown blocks planning.

1. **Freeze intent**: goal, non-goals, success criteria, invariants,
   constraints, and no-go from the prompt and explicit owner decisions.
2. **Revalidate durable context**: repository instructions and user-approved
   host context are leads, not proof; a `FACT` needs a current locator.
3. **Map surfaces**: inspect only what planning needs (repo files, tests,
   schemas, issue text, safe local runtime observations, user constraints);
   record `study.surfaces_mapped` and `study.tools_used`. A host code graph is
   advisory: if used, record callers/dependents as evidence (e.g. kind
   `graph-impact`) and cite the query in `tools_used`; if unavailable, record
   a residual or a non-material `UNKNOWN` with a probe. Never fabricate graph
   use or gate on it.
4. **Ledger**: give each material claim a stable ID and link dependent steps
   and risks to it. A claim is material when a wrong answer would change
   steps, risk, scope, or verification; non-material color needs no ID.
   `FACT`: code, tests, logs, config, authoritative docs, or a recorded user
   decision, with a locator (`path[:line[:col]]`, `symbol @ path:line`,
   `user decision: …`, `decision: …`, or `command: …`). `ASSUMPTION`:
   plausible, unverified. `UNKNOWN`: missing or contradictory evidence. Mark
   an assumption or risk `ACCEPTED` only on explicit owner acceptance.
5. **Thesis**: a falsifiable approach plus at least one simpler path rejected
   with a reason.
6. **Steps**: ordered, each with why, imperative `how[]` (2-7 concrete bullets
   naming files, behaviors, and what not to touch), surfaces (repo paths), an
   observable DoD, and proof IDs, so a READY step is implementable without
   re-deriving the procedure.
7. **Gates**: risks (accepted or mitigated), open material unknowns,
   `acceptance_trace`, and residuals (risk flags and council: Workflow steps
   3-4).

**Simplicity** (before READY): prefer the smallest plan that still makes
implementation decisions explicit. Drop a step if the goal holds without it or
another step has the same DoD; prefer existing modules, paths, patterns, and
repo standards over new abstractions or re-planning; plan one happy path plus
material failure modes; reject alternatives or layers that only add unproven
flexibility (speculative flags, adapters, "future-proof" layers). Record
`simplicity.cuts` (deferred work, with reason) and
`retained_complexity_justifications` (only when a simpler option failed for a
falsifiable reason: compatibility, safety, measured constraint), including any
complex path kept against a council simplification objection. HTML and
chapters are never proof of study.

## Depth and Risk Flags

Depth (`simple|standard|deep`) is a signal only; it never forces chapters or
council. Default `standard` when uncertain; prefer `simple` over ceremony (no
large templates for tiny bugs).

Set every risk flag that applies (catalog: output contract). Any flag means
council. With none, record a concrete `council.skip_reason`: a self-critical
pass is enough, but if it surfaces a material failure mode, add the flag and
run council. Do not under-flag to skip council; dismiss a validator flag
suggestion only as a keyword false positive, per the output contract.

## Workflow

Invoke the scripts; never reimplement them. Write every command with literal
absolute paths (`<skill-dir>` is this SKILL.md's absolute directory). Run
`scripts/test_plan_harness.py` only when changing this skill.

1. **Scaffold** (`PLAN_DIR` defaults to `<cwd>/plan`; a parent may set it):

   ```bash
   python3 -B <skill-dir>/scripts/scaffold_plan_dir.py --out <PLAN_DIR> \
     --prompt-file <file with the exact prompt> --repo-root <REPO_ROOT>
   ```

   Under a parent, pass `--prompt-hash <parent prompt sha256>` instead of
   `--prompt-file`. It writes a fail-closed skeleton `plan-report.json`, or
   reuses the existing freeze of the same prompt; on reuse, delete a
   `00`/`plano` chapter you did not author (an old renderer persisted it).
2. **Study** (loop above); set depth.
3. **Draft** the freeze in place per the output contract, with risk flags.
4. **Council** when flagged (Resources row).
5. **Render both audience-specific plans and validate** after the report is
   complete. The renderer writes the human-facing HTML and the agent handoff
   from that same final report; it also updates the freeze's artifact list.

   ```bash
   python3 -B <skill-dir>/scripts/render_plan_html.py <PLAN_DIR>/plan-report.json --out <PLAN_DIR> \
     && python3 -B <skill-dir>/scripts/validate_plan_report.py <PLAN_DIR>/plan-report.json \
       --repo-root <REPO_ROOT> --require-html
   ```

   Omit `--repo-root` only when the target tree is unavailable; then prefer
   `BLOCKED` or `NOT_CONFIDENT` over fake paths. Fix from the validator's error
   lines and patch the report in place; do not read validator source or rewrite
   the whole report. Do not read the rendered HTML back. If the report changes,
   rerun the renderer so both audience-specific artifacts match the final report
   before validating again.

Match the user's language for prose and the HTML body when practical. Remove
scratch outside the plan directory when done.

## Return

Child mode (a parent or phase worker invoked this skill): never ask the user;
the final message is exactly this block.

```
RESULT sam-plan <READY_TO_EXECUTE|NOT_CONFIDENT|BLOCKED|COUNCIL_REQUIRED>
report: <absolute PLAN_DIR>/plan-report.json
human_plan: <absolute PLAN_DIR>/<primary .html>
agent_plan: <absolute PLAN_DIR>/agent-plan.md
validator: <exact last line of the validator output>
head: <target repo HEAD sha|n/a> fingerprint: n/a
open: <n>
- <one line per open required item, max 10>
```

`COUNCIL_REQUIRED` is the phase-worker handoff in council-integration.md.

Standalone: at most 15 lines (status, depth and its rationale, one-line
thesis and step count, council skip reason or result, residuals, blockers,
risk flags, validator line, absolute `PLAN_DIR`, primary HTML path,
`agent-plan.md` path, and report path). Never paste the JSON.
