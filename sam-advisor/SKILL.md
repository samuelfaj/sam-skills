---
name: sam-advisor
description: "Read-only second opinion from a chosen advisor runtime (codex or claude) on a focused assumption, tradeoff, architecture, security, diagnosis, or high-risk decision. Use when a bounded independent advisory pass is needed; not for implementation or delegating the whole task."
---

# Sam Advisor

## Non-Negotiable Contract

- Bind `advisor`, `model`, and `effort` in the calling agent. The user passes
  the advisor (`codex` or `claude`) and optionally the model and effort, e.g.
  `/sam-advisor claude opus high` or `$sam-advisor --advisor codex --effort xhigh`.
  If the advisor is missing, ask the user; never guess it.
- `model` and `effort`: the user's exact override, else the matching advisor
  row (`codex` for codex, `claude-code` for claude) of
  `<abs skill dir>/../sam-orchestrate/references/host-runtime-matrix.md`. Read
  only that section (`sed -n '/^## Advisor/,$p' <abs matrix path>`; the whole
  file only if that prints nothing). Never hardcode or invent a model.
  Use a user-supplied effort (`low`, `medium`, `high`, `xhigh`, `max`)
  exactly; never lower effort for urgency, simplicity, cost, or latency.
- Read-only, ephemeral; no edits, subagents, publishing, commits, pushes, or
  external writes. Per-advisor restrictions are below.
- One focused question; never delegate the whole task or request
  implementation. Minimum context, no secrets or credentials: cite repository
  files by path and line range; paste only facts the advisor cannot read.
- The prompt reaches the CLI only through stdin, never argv or a command string.
- Do not silently fall back when the CLI, advisor, model, effort, or
  authentication is unavailable, and never retry with another advisor, model,
  or effort; return the exact blocker.
- The answer is analysis, not proof; the caller keeps the decision,
  implementation, and proof. Never claim the advisor ran unless the invocation
  succeeded.
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
  never invents a Done row or receives skill bodies or exact output. Bracket
  the consult only when it is a controlled nested lifetime.

## Advisors

### codex

- Matrix row: `codex`.
- Sandbox: read-only, ephemeral, strict config, user config ignored.
- Without `--run` (keep `--prompt-file`) the resolver prints only the argv:
  run it without a shell and read only the `--output-last-message` file.

### claude

- Matrix row: `claude-code`.
- Plan permission mode, only `Read`, `Glob`, `Grep`, no session persistence;
  no shell.
- Without `--run` the resolver prints only the argv: run it without a shell,
  prompt on stdin, and read only the JSON `result`.

## Subordinate mode

When a parent skill invoked this consult: if it supplied `advisor`, `model`,
and `effort`, use them exactly without opening the matrix; return the Output
fields inline as a consult record; emit no workflow report, close no parent
phase, and never alter the parent's response format, phases, gates, or
evidence rules; never ask the user; on failure, hand the exact blocker back as
a residual and let the parent decide.

## Procedure

1. Write the prompt to an absolute scratch path: the question, relevant facts
   and evidence, constraints and no-go surfaces, any current hypothesis, and:
   - Act only as an advisor. Do not edit files, run shell commands, or spawn
     subagents.
   - Answer the focused question in at most 400 words under Recommendation,
     Risks, Assumptions, and Verification.
   - Separate confirmed evidence from inference.
2. Run `python3 -B <abs skill dir>/scripts/resolve_advisor.py --advisor <codex|claude> --model <model> --effort <effort> --run --prompt-file <abs prompt path>`.
   It runs the fixed argv without a shell and prints one status line plus only
   the answer; a nonzero exit is the blocker.
3. Reconcile before acting: check the answer against the evidence and verify
   material claims; reject unsupported claims, scope expansion, invented
   facts, and implementation work. Settle disagreement with direct evidence or
   present the tradeoff to the user; never defer blindly.

## Output

Return `Advisor` (runtime, selected model), `Effort` (value; matrix-default or
user-specified), `Recommendation`, `Risks` (with hard assumptions),
`Verification` (strongest next proof), and `Caller decision` (accepted,
rejected, or unresolved, with reason).
