# Simplicity Rules

## Contents

1. Default posture
2. Mandatory checks
3. Cuts vs retention
4. Anti-patterns

## Default posture

Choose the smallest plan and smallest future implementation that still hits the
frozen goal. Ceremony is a defect when the prompt is simple.

## Mandatory checks

Before `READY_TO_EXECUTE`:

1. For every step: if removed, does the goal still hold? Drop if yes.
2. Prefer existing modules, paths, and patterns over new abstractions.
3. One happy path plus material failure modes—not a framework.
4. Delete chapters that do not change an implementation decision.
5. Reject alternatives that only add flexibility without a proven need.

## Cuts vs retention

Record:

- `cuts`: work deliberately out of scope or deferred with reason.
- `retained_complexity_justifications`: only when a simpler option was rejected
  for a falsifiable reason (compat, safety, measured constraint).

If the council simplification seat proposes a cut and the plan keeps the complex
path, the justification must appear in HTML as a warn callout.

## Anti-patterns

- Fixed large product templates for tiny bugs.
- Council rounds that restate the prompt without failure modes.
- Speculative config flags, adapters, or “future-proof” layers.
- Duplicate steps that restate the same DoD.
- Planning implementation details the repo already standardizes elsewhere.
