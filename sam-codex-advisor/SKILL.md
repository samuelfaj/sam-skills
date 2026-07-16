---
name: sam-codex-advisor
description: "Consult Codex on gpt-5.6-sol as a read-only advisor for a focused assumption, tradeoff, architecture question, security concern, difficult diagnosis, or high-risk decision. Use when the user requests a Codex second opinion or when another AI agent needs a bounded independent advisory pass; default reasoning effort to high unless the user explicitly supplies an effort."
---

# Sam Codex Advisor

Obtain one independent advisory answer. Keep the calling agent responsible for
the final decision, implementation, and proof.

## Non-Negotiable Contract

- Use `gpt-5.6-sol` exactly. Do not substitute another model.
- Use reasoning effort `high` unless the user explicitly supplies `low`,
  `medium`, `high`, `xhigh`, or `max`; use the supplied value exactly.
- Do not infer a lower effort from urgency, simplicity, cost, or latency.
- Run the advisor read-only and ephemerally. Do not let it edit files, spawn
  subagents, publish, commit, push, or perform external writes.
- Ask one focused question. Do not delegate the whole task or request implementation.
- Pass only the minimum context required and exclude secrets or credentials.
- Do not silently fall back when the CLI, model, effort, or authentication is unavailable.
- Treat the advisor response as analysis, not proof. Verify material claims before acting.

## 1. Freeze the Advisory Request

Record:

- Focused question or decision.
- Relevant facts and evidence.
- Constraints and no-go surfaces.
- Current hypothesis, if any.
- Desired output: recommendation, risks, and strongest verification path.

If the request contains an explicit effort, preserve it. Otherwise select `high`.
Do not treat words such as “deep”, “quick”, or “careful” as effort values.

## 2. Resolve the Invocation

Run the deterministic resolver before invoking the advisor:

```bash
SAM_CODEX_ADVISOR_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_CODEX_ADVISOR_DIR/scripts/resolve_advisor.py"
python3 "$SAM_CODEX_ADVISOR_DIR/scripts/resolve_advisor.py" --effort high
```

Use the first form when effort is absent. Use the second form with the user's
exact effort when supplied. The resolver returns an argv array fixed to Codex,
`gpt-5.6-sol`, the selected effort, ephemeral execution, and read-only sandboxing.

## 3. Invoke Safely

Execute the returned argv directly without a shell. Send the advisory request
through stdin because the final `-` tells `codex exec` to read the prompt there.
Do not interpolate the question into a command string or expose it in process arguments.

Require the advisor prompt to say:

- Act only as an advisor.
- Do not edit files or spawn subagents.
- Answer the focused question.
- Return a recommendation, key risks, hard assumptions, and verification path.
- Separate confirmed evidence from inference.

Wait for completion. If invocation fails, return the exact blocker and do not
retry with another model or effort.

## 4. Reconcile

Check the response against supplied evidence. Reject unsupported claims,
scope expansion, invented facts, and implementation work. Resolve disagreement
using direct evidence or present the tradeoff to the user; do not defer blindly.

## Output

Return:

- `Advisor`: Codex `gpt-5.6-sol`.
- `Effort`: selected effort and whether it was defaulted or user-specified.
- `Recommendation`: concise advisory conclusion.
- `Risks`: material risks and hard assumptions.
- `Verification`: strongest next proof.
- `Caller decision`: accepted, rejected, or unresolved, with reason.

Do not claim the advisor ran unless the invocation completed successfully.
