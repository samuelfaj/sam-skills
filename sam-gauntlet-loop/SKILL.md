---
name: sam-gauntlet-loop
description: "Turn any goal into a named, fetchable quality-bar loop with isolated builder and critic pairs and host-detected orchestration. Use when the user runs /sam-gauntlet-loop, says gauntlet loop, gauntlet this, or asks to loop until the work beats a real reference."
---

# Sam Gauntlet Loop

Turn a goal into one short host-safe prompt, then optionally run it. The loop
beats a real reference. It does not grade itself against a rubric.

Technique by Matt Shumer. Original skill pack by Jay E / RoboNuggets (CC BY 4.0).

## Non-Negotiable Contract

- Detect the active host with `scripts/detect_host.py` before compiling or
  running. Never guess on `UNKNOWN` or `CONFLICT`. Never infer the host from
  files in a home directory — this machine may have every client installed.
- A bar must be named, fetchable, and comparable. Reject a vague bar.
- The critic is a separate agent with fresh context. Never let the builder
  judge its own work. Never resume the critic from the builder.
- The critic returns a binary pick (`ours` or `bar`) and one remaining gap.
  Scores are forbidden. Praise is not useful.
- Exit only when the critic picks `ours` blind, or the user stops the run.
  Never stop after a fixed round count.
- Emit only the orchestration tokens allowed for the detected host. A token
  that is valid on one host is harmful on another.
- Fetch the real bar before the first comparison. If the bar cannot be
  obtained, return `BLOCKED` (`bar_unfetched`). Do not invent the comparison.
- Preserve unrelated workspace state. Never expose secrets.
- Under a parent workflow, do not ask; return `BLOCKED` with the exact gap.

## Resource Routing

- Run `scripts/detect_host.py` before any compile or run.
- Read [references/bar-policy.md](references/bar-policy.md) before proposing or
  accepting a bar.
- Read [references/host-runtime.md](references/host-runtime.md) before running.
- Read [references/prompt-contract.md](references/prompt-contract.md) before
  compiling.
- Read [references/output-contract.md](references/output-contract.md) before
  writing the report.
- Shared host and token tables live in `scripts/gauntlet_core.py`.
- Run `scripts/compile_prompt.py` to emit the host-safe prompt.
- Run `scripts/validate_gauntlet.py` before returning.

## 1. Detect the host

```bash
SAM_GAUNTLET_DIR="<absolute directory containing this SKILL.md>"
python3 "$SAM_GAUNTLET_DIR/scripts/detect_host.py"
```

Honor `SAM_GAUNTLET_HOST` or `SAM_ACTIVE_HOST` when set to a supported key.
On `UNKNOWN` or `CONFLICT`, standalone: ask once which host to bind. Parent
workflow: `BLOCKED`.

## 2. Freeze the goal and the bar

Restate the goal internally. If the user already named a bar that passes
[references/bar-policy.md](references/bar-policy.md), use it. Otherwise offer
two or three candidate bars, one line each, and stop. Do not compile yet.

Prefer the hardest bar the critic can actually fetch. If the goal has a
measurable half (benchmark, pass rate, load time, length), name it beside the
reference.

## 3. Compile the prompt

```bash
python3 "$SAM_GAUNTLET_DIR/scripts/compile_prompt.py" \
  --host "<detected-host>" \
  --goal "<goal>" \
  --bar-name "<named bar>" \
  --bar-locator "<url, repo, title, or path>" \
  --fetch-method "<screenshot|read|run|open>" \
  --kind "<visual|writing|code|research|other>"
```

Add `--budget "<ceiling>"` only when the user named one. Print the compiled
prompt as a single paste-ready block. One flat line under it: "I can run this
here."

## 4. Run only when asked

If the user does not ask to run, stop after the prompt (`PROMPT_ONLY` /
`PROMPT_READY`).

If they ask to run, become the lead and follow the compiled prompt using only
the primitives in [references/host-runtime.md](references/host-runtime.md) for
the detected host.

For each piece: spawn a builder and a separate critic in parallel. Give the
critic the bar locator, the fetch method, and the output paths — not the
builder's transcript, effort, or self-assessment. If the critic picks `bar`,
feed only the named gap back to the builder. If two consecutive rounds produce
the same gap fingerprint, stop as `STALLED` and report the stuck gap.

Keep a short live progress note the user can watch. Do not write a decorative
site unless the goal is itself a site.

When the host provides `RC_TOKEN_SAVER_EXECUTION_RECEIPT_V1`, inherit that
receipt unchanged on every child. Bracket each spawned lifetime with:

```bash
telemetry_command="${REMOTE_CODE_SUBAGENT_TELEMETRY_COMMAND:-distill}"
child_run="$("$telemetry_command" subagent begin --node '<stable-id>')"
# run the builder or critic
"$telemetry_command" subagent end --run-id "$child_run" --status completed
```

Use `failed` or `cancelled` on the matching terminal path. Bridge unavailability
is a proof gap, not a license to invent a Done row.

## 5. Validate and return

Write the temporary report, then:

```bash
python3 "$SAM_GAUNTLET_DIR/scripts/validate_gauntlet.py" \
  "$GAUNTLET_TMP/report.json"
```

Do not weaken the validator. Remove temporary artifacts after capturing the
decision. Follow [references/output-contract.md](references/output-contract.md).
