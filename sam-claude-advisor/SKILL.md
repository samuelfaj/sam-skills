---
name: sam-claude-advisor
description: "Consult Claude as a read-only advisor for a focused assumption, tradeoff, architecture question, security concern, difficult diagnosis, or high-risk decision. The calling agent binds model and reasoning effort from the sam-orchestrate host-runtime-matrix advisor row (or the user's exact override). Use when the user requests a Claude second opinion or when another AI agent needs a bounded independent advisory pass."
---

# Sam Claude Advisor

Obtain one independent advisory answer. Keep the calling agent responsible for
the final decision, implementation, and proof.

## Non-Negotiable Contract

- Bind `model` and `effort` in the calling agent. Prefer the **advisor** row for
  the Claude Code host in
  [../sam-orchestrate/references/host-runtime-matrix.md](../sam-orchestrate/references/host-runtime-matrix.md).
  Do not hardcode a model or invent one outside that matrix and an explicit
  user override.
- If the user supplies an effort (`low`, `medium`, `high`, `xhigh`, or `max`),
  use that value exactly. Otherwise use the matrix advisor effort for Claude Code.
- Do not infer a lower effort from urgency, simplicity, cost, or latency.
- Run the advisor read-only with plan permissions and no session persistence.
- Permit only `Read`, `Glob`, and `Grep` tools. Do not let it edit files, run
  shell commands, spawn subagents, publish, commit, push, or perform external writes.
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
- Selected `model` and `effort` (matrix advisor binding, or user override) and
  whether effort was user-specified.

## 2. Resolve the Invocation

Run the deterministic resolver before invoking the advisor. Both flags are
required:

```bash
SAM_CLAUDE_ADVISOR_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_CLAUDE_ADVISOR_DIR/scripts/resolve_advisor.py" \
  --model "<caller-selected-model>" \
  --effort "<caller-selected-effort>"
```

The resolver returns an argv array fixed to Claude, the selected model and
effort, plan permission mode, read-only tools, JSON output, and disabled session
persistence. It does not invent defaults.

## 3. Invoke Safely

Execute the returned argv directly without a shell. Send the advisory request
through stdin because `claude --print` reads piped text when no prompt argument
is supplied. Do not interpolate the question into a command string or expose it
in process arguments.

Require the advisor prompt to say:

- Act only as an advisor.
- Do not edit files, run shell commands, or spawn subagents.
- Answer the focused question.
- Return a recommendation, key risks, hard assumptions, and verification path.
- Separate confirmed evidence from inference.

Wait for completion and parse the JSON `result`. If invocation fails, return the
exact blocker and do not retry with another model or effort.

## 4. Reconcile

Check the response against supplied evidence. Reject unsupported claims,
scope expansion, invented facts, and implementation work. Resolve disagreement
using direct evidence or present the tradeoff to the user; do not defer blindly.

## Output

Return:

- `Advisor`: Claude with the selected model.
- `Effort`: selected effort and whether it was matrix-default or user-specified.
- `Recommendation`: concise advisory conclusion.
- `Risks`: material risks and hard assumptions.
- `Verification`: strongest next proof.
- `Caller decision`: accepted, rejected, or unresolved, with reason.

Do not claim the advisor ran unless the invocation completed successfully.
