# Portable Runtime and Provider Matrix

## Contents

- [Principle](#principle)
- [Topology](#topology)
- [Runtime discovery](#runtime-discovery)
- [Effort policy](#effort-policy)
- [Scheduling](#scheduling)
- [Multi-provider confrontation](#multi-provider-confrontation)
- [Fallbacks](#fallbacks)

## Principle

The council targets capabilities, not brands. A provider is any independent
agent runtime that can receive a frozen packet, remain read-only, and return the
response contract. Provider keys are runtime-supplied lowercase slugs such as
`codex`, `claude-code`, `grok`, `local-agent`, or `vendor-x`.

Never require a particular model name, CLI, API, tool schema, or reasoning-tier
vocabulary. Host examples document compatibility; they do not form an
allowlist.

## Topology

- `single-host`: one controller uses distinct workers offered by the active
  runtime. This is always the default.
- `multi-provider`: two or more explicitly requested providers each run the
  full blind panel against the same packet. It always uses profile `full`.

Do not activate multi-provider from “be thorough,” “get another opinion,” an
incidental model name, or the controller's host. Clear examples include “run
the council on Codex and Grok” or “use Claude Code, Grok, and Codex panels.”

## Runtime discovery

Before dispatch, record for every provider:

```json
{
  "adapter": "host-native-workers",
  "model": "host-reported-model-or-host-default",
  "reviewer_effort": "medium",
  "arbiter_effort": "high",
  "max_parallel_workers": 6
}
```

Use the provider's reported model label. Normalize the selected effort to
`medium` for reviewers and `high` for arbiters. If the host does not expose an
effort control, record `host-default`. `max_parallel_workers` is the safe number
of independent worker calls that may run concurrently, excluding the
controller when the host makes that distinction.

## Effort policy

- Blind and conditional reviewers: closest supported equivalent of `medium`.
- Closure and system verifiers: closest supported equivalent of `medium`.
- Triage arbiter, arbiter, or meta-arbiter: closest supported equivalent of
  `high`.
- Do not escalate other seats merely to appear thorough. If a host cannot map
  these tiers, use its default and record the actual value.

The report records the portable normalized tier. A runtime may call these
controls “reasoning,” “thinking,” “effort,” or expose none; map its closest
setting to the normalized tier without exposing a vendor-specific requirement.

## Scheduling

Build all independent seat calls before dispatch. Set batch size to the largest
safe capacity reported by the host. Dispatch each batch concurrently and wait
only at blindness barriers:

1. all blind reviewers terminal;
2. author synthesis/revision complete;
3. all fresh verifiers terminal.

With enough capacity, a single-host full round has two worker waves: one blind
wave and one verifier wave. With lower capacity, use the mathematical minimum
number of batches. Never merge seats to fit capacity and never serialize calls
that the host can safely run concurrently.

## Multi-provider confrontation

Run every provider's full required panel with `{provider}/{seat}` IDs. Keep
blindness across seats and providers. Conditional seats run per provider.

After blind synthesis:

1. Build one evidence-backed position per provider.
2. Give each provider only peers' material claims.
3. Require `ACCEPT`, `REBUT`, or `CONCEDE` with evidence IDs.
4. Preserve supported minority blockers.
5. Use a fresh `meta-arbiter`; never decide by provider majority.

## Fallbacks

- If a named provider is unavailable, report the exact failure. Continue only
  when the user's requested minimum provider count remains available.
- If fewer than two providers remain and multi-provider was optional, downgrade
  to `single-host`; if it was mandatory, return `BLOCKED`.
- If distinct workers are unavailable, return `BLOCKED`.
- If effort controls or model labels are unavailable, use `host-default`; this
  alone does not block execution.
- Never simulate an unavailable provider inside the controller context.
