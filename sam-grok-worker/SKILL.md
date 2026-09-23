---
name: sam-grok-worker
description: "Delegate a bounded coding task to the Grok worker (grok-4.6, workspace sandbox, default effort high). Use when a host agent or user needs Grok to implement, fix, or verify scoped work."
---

# Sam Grok Worker

## Non-Negotiable Contract

- Model `grok-4.6` exactly. Effort `high` unless the user explicitly supplies
  `low`, `medium`, `high`, `xhigh`, or `max`; then use it exactly. Words like
  "deep", "quick", or "careful" are not effort values. Never lower effort for
  urgency, simplicity, cost, or latency.
- Headless, `workspace` sandbox, always-approve; memory, subagents, and
  auto-update disabled. Never rewrite the resolver's model, effort, sandbox,
  or approval flags.
- The task goes only through `--prompt-file`; never `-p` or stdin.
- One bounded task; never hand over the whole multi-phase workflow or publish
  authority. Minimum context, no secrets or credentials: cite repository files
  by path and line range.
- Do not silently fall back when the CLI, model, effort, sandbox, or
  authentication is unavailable, and never retry with another model or effort;
  return the exact blocker.
- Worker output is candidate work, not proof. Never claim the worker ran
  unless the invocation succeeded.
- **Token Saver:** Pass the host's content-free
  `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1` and its capability/lane environment
  unchanged to every controlled child (nested spawns, retries, resumes,
  recovery); never reconstruct or widen admission. A missing, malformed,
  denied, cross-user, or provider-mismatched receipt is raw fail-open input.
  Never put skills, exact-output commands, prompts, transcripts, secrets, or
  full responses in it. Skills and exact-output evidence stay lossless; claim
  no billing or quota savings. Never prepend an unmanaged wrapper path.
- **Telemetry (lifetime only):** With
  `T="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"`, bracket each
  controlled child: `run=$("$T" subagent begin --node <stable-id> </dev/null)`
  … `"$T" subagent end --run-id "$run" --status completed|failed|cancelled </dev/null`;
  keep the run id across retries. If the run's first `begin` fails, record one
  Subagents proof gap and skip brackets for the rest of the run. Telemetry
  never invents a Done row or receives skill bodies or exact output. Bracket
  the worker only when it is a controlled nested task.

## Procedure

1. Write the prompt to a caller-owned absolute temporary path: goal and
   acceptance criteria; in-scope paths, commands, and surfaces; out-of-scope
   and no-go surfaces (publish, push, remote comments, secrets); known facts,
   files, and evidence; and:
   - Act only as a worker for this bounded task; stay inside the frozen scope
     and no-go list.
   - Do not publish, push, open remote proposals, send messages, or perform
     other external writes unless the frozen request explicitly authorizes it.
   - Make the smallest safe change that meets the acceptance criteria.
   - Report in at most 250 words: files changed, commands run with pass/fail,
     residual risks, and blockers; separate completed work from unverified
     claims; no code excerpts.
2. Run `python3 -B <abs skill dir>/scripts/resolve_worker.py --prompt-file <abs prompt path> [--effort <user value>] --run`.
   It runs the fixed argv without a shell and prints one status line plus only
   the `text` report; a nonzero exit is the blocker. Without `--run` it prints
   only the argv: run it without a shell and read only the JSON `text`. Delete
   a remaining prompt file when safe.
3. Reconcile before accepting or publishing: inspect the working tree with
   `git status --short` (includes untracked files) and `git diff --stat`, then
   targeted diffs and any verification the worker claims. Reject unsupported
   claims, scope expansion, invented evidence, and unauthorized external
   writes. Settle disagreement with direct proof or present the tradeoff to
   the user; never defer blindly.

## Output

Return `Worker` (Grok `grok-4.6`), `Effort` (value; defaulted or
user-specified), `Summary`, `Changes` (files, behaviors), `Verification`
(proofs and results), `Risks` (residual risks, hard assumptions, blockers),
and `Caller decision` (accepted, rejected, or unresolved, with reason).
