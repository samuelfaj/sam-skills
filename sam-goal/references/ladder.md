# Ladder

Stop at the first rung that holds. Climb only after you have read the
task and traced the real flow.

1. Does this need to exist? Speculative need: skip it, say so in one line.
2. Already in this codebase? Reuse the helper, type, or pattern. Look first.
3. Standard library does it? Use it.
4. Native platform feature covers it? Prefer it: native date input over a
   picker package, CSS over script, a database constraint over app code.
5. An already-present dependency solves it? Use that. Do not add a new one
   for what a few lines can do.
6. Can it be one line? One line.
7. Only then: the minimum that works.

Two rungs work: take the higher one and move on. Two standard-library
options of the same size: take the one that is correct on edge cases.
Lazy means less code, not the flimsier algorithm.

The smallest change in the wrong place is a second bug. Understand first.

## Intensity

| Level | Rule |
| --- | --- |
| lite | Build what was asked. Name the lazier alternative in one line. |
| full | Ladder enforced. Shortest correct diff. Default. |
| ultra | Deletion first. Ship the one-liner and challenge leftover requirement. |

User names a package or insists on the full shape: build that, no re-arguing.
Record the named package in `authorized_dependencies`.

## Never skip

Input validation at trust boundaries, error handling that prevents data
loss, security, accessibility, calibration knobs real hardware needs, and
anything explicitly requested. Non-trivial logic (branch, loop, parser,
money or security path) leaves **one** runnable check: an assert self-check
or one small test file. No framework, no fixture pile. Trivial one-liners
need no test.

Mark a deliberate corner with a known ceiling using a `sam-goal:` comment
that names the ceiling and the upgrade path.

## Overbuild tags

One line per finding, then `net: -<N> lines possible.` Nothing to cut:
`Lean already. Ship.`

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` code or package doing what the platform already does. Name it.
- `yagni:` one-implementation interface, unset config, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

Out of scope: correctness, security, and performance bugs. Do not flag the
one required runnable check.
