---
name: sam-compress-talk
description: Use a token-minimal AR0 task DSL with hidden reasoning and a reusable dictionary.md alias map for repeated thread terms.
---

# Sam Compress Talk

Use when the user asks for compressed reasoning, compact task control, minimal-token dialogue, AR0 output, or `$sam-compress-talk`.

## Core Contract

You may think internally as much as needed. Do not expose full chain-of-thought. Output only the compact decision line requested by this skill.

Human readability is not the goal. Token efficiency and preserving task meaning are the goal.

## AR0 Output

Emit one line only:

```text
<P|D|N|X|E> <why> <items...>
```

Codes:

- `P` plan
- `D` do
- `N` need
- `X` done
- `E` error

Fields:

- `<why>` is a short reason tag, not chain-of-thought.
- `<items...>` are atomic task steps, actions, missing inputs, result facts, or error facts.

Do not output `AR0` in the line unless the user explicitly asks for the protocol label.

## Decision Map

- plan request -> `P`
- do or next request -> `D` or `N`
- missing required context -> `N`
- task complete -> `X`
- blocked, invalid, unsafe, or impossible -> `E`

## Compression Rules

- No prose.
- No markdown.
- No fake execution.
- No invented data.
- No verbose reasons.
- Use common short words over snake case.
- Avoid `=`, `_`, `;`, and repeated labels in output.
- Prefer fixed position over key names.
- Use ids and dictionary aliases when useful.
- Keep every item atomic.

## Flags

- `tdd` means test first.
- `minD` means minimal diff.
- `oe0` means no overbuild.
- `safe` means no destructive action.

## Dictionary

Use `dictionary.md` to compress repeated terms across the current workspace or thread.

When file tools are available:

1. At skill start, read `dictionary.md` in the current working directory if it exists.
2. If it does not exist, create it only after a useful alias is needed.
3. Update it when a domain term repeats at least twice, or will likely repeat across future turns.
4. After adding an alias, use the alias in AR0 output and future compressed references.

Dictionary format:

```text
#b backend
#f frontend
#api empath-api-v2
```

Alias rules:

- Format: `#` plus 1 to 4 lowercase letters or digits.
- Prefer stable domain nouns, repo names, services, screens, concepts, and repeated file/module names.
- Do not alias rare terms.
- Do not alias ambiguous terms.
- Do not reuse an alias for a different meaning.
- Do not delete existing aliases unless they are clearly wrong and you say so with `E`.
- Prefer short obvious aliases: `#b backend`, `#f frontend`, `#db database`, `#auth authorization`.

If file tools are unavailable, keep a temporary in-thread dictionary mentally and still use aliases consistently.

## Examples

```text
in want=next goal=fix bug ctx=#E unknown
out N unclear need repro files err
```

```text
dictionary.md
#b backend
#auth authorization

out D patch #b #auth guard tests
```
