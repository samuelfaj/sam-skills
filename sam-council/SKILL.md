---
name: sam-council
description: "Blind specialist council that triages or falsifies consequential software plans via rebuttal and evidence-weighted decisions. Use for architecture, features, migrations, incidents, releases, security, costly, uncertain, or hard-to-reverse decisions; multi-provider only on explicit request."
---

# Sam Council

## Non-Negotiable Contract

- Stay read-only in the target system. Never invent an unavailable worker or
  provider, or simulate one in the controller context.
- One distinct worker per seat. Blind first pass: no seat sees peer output
  until every seat in the pass is terminal; seats return responses only in
  their subagent result, never a file.
- Answer every objection. Decide by evidence and risk, never by vote or
  provider count; one supported blocker outweighs any number of passes.
- Never report approval while a supported blocker, untreated high, unverified
  critical assumption, or unvalidated correction remains, or call a blocked or
  invalid result approved. `TRIAGE_PASS` is never approval and
  `ESCALATE_TO_FULL` never implies it. Never accept a blocker as residual
  risk, or a high on the user's behalf.
- Keep every raw response (step 6) until the report validates. Only validator
  `VALID` is machine proof.
- **Token Saver:** Pass the host's content-free
  `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` and its capability/lane environment
  unchanged to every controlled child (nested spawns, retries, resumes,
  recovery); never reconstruct or widen admission. A missing, malformed,
  denied, cross-user, or provider-mismatched receipt is raw fail-open input.
  Never put skills, exact-output commands, prompts, transcripts, secrets, or
  full responses in it. Skills and exact-output evidence stay lossless; claim
  no billing or quota savings.
- **Telemetry (lifetime only):** With
  `T="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"`, bracket each
  controlled child: `run=$("$T" subagent begin --node <stable-id> </dev/null)`
  … `"$T" subagent end --run-id "$run" --status completed|failed|cancelled </dev/null`;
  keep the run id across retries. If the run's first `begin` fails, record one
  Subagents proof gap and skip brackets for the rest of the run. Telemetry
  never invents a Done row or receives skill bodies or exact output. Begin a
  wave's seats in one shell call, printing each run id; end them in one call
  at the barrier, passing each run id literally.

## Resources

Substitute real absolute paths: `<skill>` (this directory), `<run>`
(`<scratch>/council/<run-id>`: report and raw responses, never given to a
worker), and `<pkt>` (`<scratch>/council-packets/<run-id>`: the only files
workers get). Do not re-read a file already read in this context unless
context was compacted since or you cannot quote the section.

| Reference | Read when |
| --- | --- |
| `references/reviewer-lenses.md` | Step 1 |
| `references/prompt-contract.md` | Steps 3-9 |
| `references/output-contract.md` | Step 11 |
| `references/provider-matrix.md` | Explicit multi-provider runs only |

## Profile and topology

| Profile | Use when | Blind seats | Verifiers | Rounds |
| --- | --- | --- | --- | --- |
| `fast` | Reversible, bounded work, no full trigger | 3 fast seats (reviewer-lenses.md) | Fresh `triage-arbiter` | 1 |
| `full` | Explicit request for `full`; costly, irreversible, production-critical, security/privacy, migration, compliance, or multi-provider work; a specialist applies | 6 required + every applicable specialist | Fresh `closure-verifier`, `system-verifier`, `arbiter` | 1, max 3 |

- Pick the smallest valid profile before forming the thesis; a plain
  `sam-council` request gets `fast` only when every full trigger is absent.
  When uncertain, pick `full`; never dispatch `fast` only to escalate.
- Topology: `single-host` (default; the active host's distinct workers) or
  `multi-provider`, only when the user explicitly names at least two
  independent providers, never from "be thorough", "another opinion", an
  incidental model name, or the controller's host; it forces `full`. One
  named provider: `single-host` on it. Provider IDs are runtime-supplied
  lowercase slugs, not an allowlist.

## Execution policy

- Never require a named model, CLI, API, tool schema, or effort vocabulary. A
  host limitation never justifies fabricated compliance: use the nearest
  supported capability and record the deviation. A missing effort control or
  model label alone does not block.
- Effort: closest `medium` for every seat except arbiters (closest `high`);
  `host-default`, recorded, when not configurable. Never raise other seats to
  look thorough.
- Build all seat calls first; dispatch at maximum safe capacity in the minimum
  number of batches; wait only at barriers (blind seats terminal, author
  revision done, verifiers terminal). Never merge seats to fit capacity or
  serialize seats the host can run together. Never run the validator or
  harness in seat workers.

## Workflow

1. Freeze objective, decision, scope, invariants, constraints, no-go surfaces,
   owner, evidence, assumptions, profile/topology, execution policy, runtime
   capability, seats (with every conditional seat), and batch plan.
2. Write `T-001`, a concise falsifiable thesis: approach, interfaces,
   state/failure boundaries, steps, alternatives, tests, rollout/recovery,
   observability, risks, measurable success, recheck triggers. IDs: evidence
   `E-###`, assumptions `A-###`, theses `T-###`, objections `O-R<round>-###`.
   Classify evidence `VERIFIED`, `OBSERVED`, `INFERRED`, `ASSUMED`, or
   `UNKNOWN`; repetition never upgrades it.
3. Write the frozen packet once (prompt-contract.md), or a delta packet
   (below).
4. Run `python3 -B <skill>/scripts/scaffold_council_report.py init --out <run>/council-report.json --packet <pkt>/packet.md --profile <p> --provider <slug> --max-parallel <n> --model <label|host-default> [--adapter <label>] --reviewer-effort <medium|host-default> --arbiter-effort <high|host-default> --repo <target repo> --reuse-dir <scratch>/council [--select <specialist>]... [--base-report <prior>]`;
   `--max-parallel` is the safe number of concurrent worker calls, excluding
   the controller where the host distinguishes it. On
   `REUSE <path> … validator: <line>`, dispatch nothing and return that report
   (Output).
5. Dispatch blind seats with only the seat ID, its lens, and the packet path
   (paste the packet only if the worker cannot read files).
6. After the barrier, keep each raw response as a locator (a path or ID from
   which the host can re-open that exact response) or, if none exists, as
   `<run>/raw/<seat>.md`. Normalize without voting; deduplicate by
   failure mechanism, keeping all `supporting_reviewer_ids`; keep unsupported
   claims as `UNSUPPORTED`. Multi-provider: confront per provider-matrix.md.
7. Zero-objection fast pass (every seat `NO_MATERIAL_OBJECTION`, no `ESCALATE`
   seat, no `UNRESOLVED` assumption): skip steps 8-10 and delete init's
   triage-arbiter entry; the report records `TRIAGE_PASS` with no verification.
8. Cross-examine the author (prompt-contract.md). Publish the revised thesis,
   mapping every objection to response, change, validation, and status.
9. Run the fresh verification panel.
10. Stop after round one and return a terminal result; never start another
    round automatically. Run round two or three only when the user explicitly
    asks this turn to validate a revised thesis, and only then set
    `continuation_authorized` true; an author bumping `T-001` to `T-00N`, a
    `REVISE` result, or a verifier `REJECT` is not authorization. Max three
    rounds; stop after two without material progress.
11. Fill the report. After every edit run
    `python3 -B <skill>/scripts/scaffold_council_report.py finalize <run>/council-report.json --repo <target repo>`
    (derives mechanical fields, then runs `scripts/validate_council_report.py`).
    Fix from the validator's error lines and patch the report in place; do not
    read validator source or rewrite the whole report. Run
    `python3 -B <skill>/scripts/test_council_harness.py` only when changing
    this skill.

**Delta packet.** When a parent re-runs council on a new commit after a fix
and the prior report on the same thesis is VALID and passing, the packet keeps
the charter, profile, topology, and verbatim seat mission but replaces the
thesis, evidence, and excerpts with the prior final thesis, every prior
objection with status, `git diff <prior packet_head> <new head>`, and fresh
receipts; pass `--base-report <prior>` and run every seat. Use a full packet
to change profile, or when the delta touches public contracts/APIs/schemas,
auth/security/permissions, persistence/migrations, shared modules used
outside the change, or risk-tagged paths, or exceeds the original change.

## Decision rules

| Status | Only when |
| --- | --- |
| `TRIAGE_PASS` (fast) | No supported blocker/high, critical unknown, specialist trigger, or material displaced risk |
| `ESCALATE_TO_FULL` (fast) | Any blocker/high, critical unknown, applicable specialist, multi-provider need, or displaced/new material risk |
| `APPROVED` (full) | No supported blocker/high; critical assumptions and corrections verified |
| `APPROVED_WITH_CONDITIONS` (full) | No blocker; every high mitigated or explicitly accepted by the decision owner, with owned gated conditions |
| `REVISE` (full) | An actionable material objection or unknown remains after the authorized round |
| `BLOCKED` | Distinct workers, required evidence, authority, provider, or runtime capability unavailable |

Each profile returns only the statuses tagged with it, or `BLOCKED`.

## Output

- Child mode (invoked by a parent skill or phase worker): the final message is
  exactly this block; never restate the report.
  ```
  RESULT sam-council <STATUS>
  report: <absolute path>
  validator: <exact last line of the validator output>
  head: <sha|none> fingerprint: <packet_fingerprint|n/a>
  open: <n>
  - <one line per open blocker, high, or condition, max 10>
  ```
  On `REUSE`, `report:` is the reused report and the next line is
  `reused_from: <that path>`.
- Standalone: at most 15 lines (status, confidence, profile, topology, material
  objections and conditions, residual uncertainty, validator line, any
  `reused_from`) plus the report path; never the JSON.
