---
name: sam-gauntlet-loop
description: "Compile a host-safe quality-bar loop prompt and return it for the user to copy, edit, and paste. Never start the loop. Use when the user runs /sam-gauntlet-loop, says gauntlet loop, gauntlet this, or asks to loop until the work beats a real reference."
---

# Sam Gauntlet Loop

Compile one short host-safe gauntlet prompt and return it. Do not start the
loop. The user copies, edits, and pastes the prompt themselves.

Technique by Matt Shumer. Original skill pack by Jay E / RoboNuggets (CC BY 4.0).

## Non-Negotiable Contract

- Detect the active host with `scripts/detect_host.py` before compiling. Never
  guess on `UNKNOWN` or `CONFLICT`. Never infer the host from files in a home
  directory — this machine may have every client installed.
- A bar must be named, fetchable, and comparable. Reject a vague bar.
- Emit only the orchestration tokens allowed for the detected host. A token
  that is valid on one host is harmful on another.
- Return the compiled prompt as a single paste-ready block, then stop. Never
  become the lead, never spawn a builder or critic, never fetch the bar, and
  never start the loop — even if the user asks to run it here.
- Preserve unrelated workspace state. Never expose secrets.
- Under a parent workflow, do not ask; return `BLOCKED` with the exact gap.

## Resource Routing

- Run `scripts/detect_host.py` before any compile.
- Read [references/bar-policy.md](references/bar-policy.md) before proposing or
  accepting a bar.
- Read [references/host-runtime.md](references/host-runtime.md) before
  compiling.
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

Add `--budget "<ceiling>"` only when the user named one. Print only the
compiled `prompt` string as one fenced block the user can copy, edit, and
paste. One flat line under it names the bound host and the bar. Do not offer
to run it. Do not start it.

## 4. Validate and return

Write the temporary `PROMPT_ONLY` report, then:

```bash
python3 "$SAM_GAUNTLET_DIR/scripts/validate_gauntlet.py" \
  "$GAUNTLET_TMP/report.json"
```

Do not weaken the validator. Remove temporary artifacts after capturing the
decision. Follow [references/output-contract.md](references/output-contract.md).
Never follow the compiled prompt in this turn.
