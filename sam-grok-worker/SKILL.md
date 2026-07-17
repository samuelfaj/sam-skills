---
name: sam-grok-worker
description: "Delegate a bounded implementation task to the fixed Grok worker (grok-4.5) under workspace sandbox and headless execution. Use when a host agent or user needs Grok to implement, fix, or verify a scoped coding task; default effort high unless explicitly supplied."
---

# Sam Grok Worker

Delegate one bounded task to Grok. Keep the calling agent responsible for scope,
final decision, publication, and proof.

## Non-Negotiable Contract

- Use model `grok-4.5` exactly. Do not substitute another model.
- Use effort `high` unless the user explicitly supplies `low`, `medium`, `high`,
  `xhigh`, or `max`; use the supplied value exactly.
- Do not infer a lower effort from urgency, simplicity, cost, or latency.
- Invoke headless Grok with workspace sandbox and always-approve so the worker
  can edit inside the working tree without interactive prompts.
- Disable memory, subagents, and auto-update for the worker session.
- Transport the task only through `--prompt-file`. Headless Grok does not read
  piped stdin as the prompt.
- Ask for one bounded task. Do not hand over the entire multi-phase workflow or
  authorization to publish.
- Pass only the minimum context required and exclude secrets or credentials.
- Do not silently fall back when the CLI, model, effort, sandbox, or
  authentication is unavailable.
- Treat worker output as candidate work, not proof. Verify material claims and
  diffs before accepting or publishing.

## 1. Freeze the Worker Request

Record:

- Exact task goal and acceptance criteria.
- In-scope paths, commands, and surfaces.
- Out-of-scope and no-go surfaces (publish, push, remote comments, secrets).
- Relevant facts, files, and evidence already known.
- Desired return: summary of changes, verification run, residual risks.

If the request contains an explicit effort, preserve it. Otherwise select `high`.
Do not treat words such as “deep”, “quick”, or “careful” as effort values.

## 2. Materialize the Prompt File

Write the full worker prompt to a temporary absolute path owned by the caller.
Do not put the prompt in process argv via `-p`.

Require the prompt to say:

- Act only as a worker for this bounded task.
- Stay inside the frozen scope and no-go list.
- Do not publish, push, open remote proposals, send messages, or perform other
  external writes unless the frozen request explicitly authorizes that action.
- Prefer the smallest safe change that satisfies acceptance criteria.
- Return: what changed, how it was verified, residual risks, and blockers.
- Separate completed work from unverified claims.

## 3. Resolve the Invocation

Run the deterministic resolver before invoking the worker:

```bash
SAM_GROK_WORKER_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_GROK_WORKER_DIR/scripts/resolve_worker.py" --prompt-file /abs/path/prompt.txt
python3 "$SAM_GROK_WORKER_DIR/scripts/resolve_worker.py" --prompt-file /abs/path/prompt.txt --effort high
```

Use the first form when effort is absent. Use the second form with the user's
exact effort when supplied. The resolver returns an argv array fixed to Grok,
`grok-4.5`, the selected effort, workspace sandbox, always-approve, no-memory,
no-subagents, JSON output, and the absolute prompt file.

## 4. Invoke Safely

Execute the returned argv directly without a shell. Do not rewrite model,
effort, sandbox, or approval flags. Do not swap `--prompt-file` for `-p` or
stdin.

Wait for completion and parse the JSON `text` field as the worker report. If
invocation fails, return the exact blocker and do not retry with another model
or effort. Delete the temporary prompt file after the run when it is safe to do
so.

## 5. Reconcile

Inspect the working tree and any verification the worker claims. Reject
unsupported claims, scope expansion, invented evidence, and unauthorized
external writes. Resolve disagreement with direct proof or present the tradeoff
to the user; do not defer blindly.

## Output

Return:

- `Worker`: Grok `grok-4.5`.
- `Effort`: selected effort and whether it was defaulted or user-specified.
- `Summary`: concise report of work performed.
- `Changes`: files or behaviors touched, if any.
- `Verification`: proofs run and their results.
- `Risks`: residual risks, hard assumptions, and blockers.
- `Caller decision`: accepted, rejected, or unresolved, with reason.

Do not claim the worker ran unless the invocation completed successfully.
