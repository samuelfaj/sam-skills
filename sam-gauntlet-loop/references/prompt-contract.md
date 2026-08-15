# Prompt Contract

The compiled prompt is the only instruction a later session follows after the
user pastes it. This skill compiles it and stops. Keep it short. The compiler
fills brackets. The agent does not add architecture, file layout, stack, or a
round cap unless the user demanded it.

## Shape

About 120 to 180 words. Plain sentences. No headings or bullets inside the
prompt. It should read like someone naming perfect and refusing less.

Required semantic fields:

1. Build `[GOAL]`.
2. The bar is `[BAR]`. Fetch the real thing first. Compare against it, not a
   description of it.
3. Break the work into the smallest pieces that can be judged alone.
4. For each piece, run a builder and a separate critic with fresh context.
5. The critic inspects actual output, compares blind with labels stripped,
   picks one, and names the single biggest remaining gap.
6. Harsh critic. Praise is not useful. If ours does not win, keep going.
7. Host-safe close (see below).
8. Budget line only when the user named a ceiling.

## Host close

`scripts/compile_prompt.py` appends exactly one close. Do not rewrite it.

- `claude-code`: `/loop` on each piece until the critic picks ours blind.
  Fan out subagents and `ultracode`. Keep a live progress page.
- `codex`: keep looping in the lead until the critic picks ours. Spawn
  builders and critics as distinct agents with fresh context. The lead owns
  the loop. Do not emit foreign orchestration tokens.
- `grok`: keep looping until the critic picks ours. Orchestrate with a
  workflow (`agent` + `parallel`) or top-level subagents. Never resume the
  critic from the builder. Watch `/workflows`. Do not emit foreign
  orchestration tokens.

## What stays out

No decomposition of files, no stack choice, no "stop after N rounds", no
default cost cap, no tool names unless the goal needs a specific generator or
browser. Extra instructions steal decisions the lead should make while looking
at the work.
