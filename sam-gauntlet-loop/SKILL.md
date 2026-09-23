---
name: sam-gauntlet-loop
description: "Compile a host-safe quality-bar loop prompt for the user to copy, edit, and paste. Never start the loop. Use when the user runs /sam-gauntlet-loop, says gauntlet loop or gauntlet this, or wants to loop until work beats a real reference."
---

# Sam Gauntlet Loop

Technique by Matt Shumer. Original skill pack by Jay E / RoboNuggets (CC BY 4.0).

## Non-Negotiable Contract

- Bind the host from process environment with `scripts/detect_host.py` before compiling. Never guess on `UNKNOWN` or `CONFLICT`; never infer the host from clients installed on disk.
- A bar must be named, fetchable, and comparable. Reject a vague or compound bar.
- Emit only the bound host's orchestration tokens. `scripts/gauntlet_core.py` holds the close and token tables the compiler and validator enforce; never weaken either script.
- Return the compiled prompt (step 4), then stop. Never become the lead, never spawn a builder or critic, and never start the loop or follow the compiled prompt in this turn, even if the user asks to run it here. You may identify a locator (live window, bundle, path) so the bar is the real artifact, not a brochure; do not improve the work while doing so.
- Preserve unrelated workspace state. Never expose secrets. Keep temporary artifacts outside the repository.
- Under a parent workflow, never ask or offer choices: compile without `--user-host`, with the named bar only if it passes bar-policy.md, else with an empty bar (the compiler returns `missing_bar`), and return the result, listing the failing reason, each gap, and each candidate bar as an open line.

## Resources

| Path | Read when |
| --- | --- |
| [references/bar-policy.md](references/bar-policy.md) | Step 2, before proposing or accepting a bar |
| [references/output-contract.md](references/output-contract.md) | Only to inspect or hand-fix a saved report (re-validate with `scripts/validate_gauntlet.py`) |

Replace `<skill>` with this SKILL.md's directory as a literal absolute path, not a shell variable.

## 1. Detect the host

`python3 -B <skill>/scripts/detect_host.py`

On exit 2 (`UNKNOWN`, `CONFLICT`, or `INVALID`): standalone, ask once which host to bind, then pass it with `--user-host`; under a parent, pass any supported key (the compiler ignores it and records the host gap).

## 2. Freeze the goal and the bar

Restate the goal internally. Use the user's bar if it passes bar-policy.md; otherwise, standalone, offer two or three candidate bars, one line each, and stop without compiling.

## 3. Compile

```bash
python3 -B <skill>/scripts/compile_prompt.py --host "<host from step 1>" --goal "<goal>" \
  --bar-name "<named bar>" --bar-locator "<url, repo, title, or path>" \
  --fetch-method "<screenshot|read|run|open>" --kind "<visual|writing|code|research|other>"
```

- Add `--budget "<ceiling>"` only when the user named one. Under a parent, add `--report <absolute path outside the repo>`.
- `--goal` carries the goal only. Add no architecture, stack, file layout, round cap, default cost cap, or tool names yourself; keep what the user demanded and any generator or browser the goal needs.
- The compiler validates its own report: exit 0 prints the prompt, then `VALID PROMPT_READY host=<key> (<status>)`; exit 2 prints the gaps on stderr, then `VALID BLOCKED <codes>`.

## 4. Return

- `PROMPT_READY`: print only the compiled prompt, verbatim, as one fenced block the user can copy, edit, and paste. One flat line under it names the bound host and the bar, and says pasting does not launch a run or save a workflow.
- Never claim the later session runs until the work is perfect (its stop is the critic pick, the user, or the budget), and never offer to run it.
- `BLOCKED`: on `host_mismatch`, re-run with the detected key (binding another host needs `SAM_GAUNTLET_HOST` or `SAM_ACTIVE_HOST` set to its key); on `prompt_invalid`, shorten `--goal` or remove the named token from `--goal` or `--budget`, then re-run. Standalone, handle a host gap as in step 1 and a bar gap as in step 2.
- Under a parent, the final message is exactly:

```text
RESULT sam-gauntlet-loop <PROMPT_READY|BLOCKED>
report: <absolute --report path>
validator: <exact last line of the compiler output>
head: n/a fingerprint: n/a
open: <number of open lines>
- <one line per gap or candidate bar, max 10>
```
