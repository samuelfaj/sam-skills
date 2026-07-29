# Technique Catalog

## Contents

- [How to Choose](#how-to-choose)
- [Acknowledgement Techniques](#acknowledgement-techniques)
- [Placeholder and Streaming Techniques](#placeholder-and-streaming-techniques)
- [Anticipation Techniques](#anticipation-techniques)
- [Commit Techniques](#commit-techniques)
- [Offloading Techniques](#offloading-techniques)
- [Rejected Patterns](#rejected-patterns)

## How to Choose

Work from the measurement, not the catalog. The class of `settled_ms` sets the
floor; reversibility decides whether an optimistic commit is available; the cost
column decides whether the technique is worth its complexity.

Prefer the cheapest technique that closes the measured gap. One acknowledgement
that lands in 40 ms beats a skeleton, a spinner, and a progress bar stacked on an
interaction nobody profiled.

## Acknowledgement Techniques

**Immediate local state change** — apply the pressed, selected, checked, or
submitted state from the input handler before any request starts. Cost: near
zero. Failure mode: the state disagrees with the server result, so it needs the
same rollback discipline as an optimistic commit whenever it implies an outcome.
Proof: a test asserting the state changes without awaiting the request.

**Input echo** — render typed characters, dragged positions, and toggles from
local state, never from a server round trip. Cost: local state to reconcile.
Failure mode: server normalization surprises the user mid-edit; reconcile on
settle, not on every keystroke. Proof: a test typing while the request is pending.

**Disabled-with-reason instead of blocked** — keep the surface interactive and
name why an action is unavailable rather than freezing the view. Cost: copy.
Failure mode: stale reasons after the condition clears.

## Placeholder and Streaming Techniques

**Layout-stable skeleton** — reserve the final geometry and show a neutral
placeholder. Cost: a second layout to maintain. Failure mode: geometry drift
between skeleton and content, which produces a shift that feels worse than the
wait. Proof: a test or measurement showing no layout shift on settle.

**Progressive rendering** — paint each region as its data arrives instead of
awaiting the slowest dependency. Cost: partial states multiply. Failure mode:
regions settling in a jarring order, or a late region shifting earlier ones.

**Streamed response** — send the first bytes before the full result exists so
`meaningful_ms` drops far below `settled_ms`. Cost: streaming-capable transport
and error handling after headers are sent. Failure mode: a mid-stream failure
that already looks like success — the surface must be able to retract.

**Chunked work with yields** — split long client work so the main thread stays
responsive. Cost: scheduling. Failure mode: total work grows; watch `settled_ms`.

## Anticipation Techniques

**Prefetch on intent** — fetch on hover, focus, viewport entry, or route
proximity. Cost: wasted requests. Failure mode: bandwidth contention that slows
the interaction actually in flight, which the regression budget catches. Never
prefetch anything with a side effect.

**Cache-first with revalidation** — render known-good data immediately, refresh
behind it. Cost: staleness. Failure mode: a stale value read as current — label
freshness whenever the difference is consequential, and never for balances,
inventory, or anything the user is about to act on irreversibly.

**Precomputation** — compute at write time or build time instead of read time.
Cost: storage and invalidation. Failure mode: silently stale derived data.

**Speculative execution** — start the likely request before the user commits.
Cost: wasted work and possible side effects. Only for idempotent reads.

## Commit Techniques

**Optimistic update** — show the outcome before confirmation. Only when the
effect is reversible and the failure surface is proven. Requires a stated failure
mode, rollback, failure UI, and a passing failure-path test. See
[honesty-policy.md](honesty-policy.md).

**Deferred commit with undo** — apply locally, expose a real undo window, then
commit. Cost: a queue and a window to reason about. Failure mode: the window
closes during navigation or a crash and the change is silently lost.

**Write-behind queue** — accept the input, persist the intent, retry in the
background. Cost: durable queue, ordering, conflicts. Failure mode: a queue that
drains after the user assumes the work is done, with no surface for failures.

## Offloading Techniques

**Backgrounded job with status surface** — required above ten seconds. The user
must be able to leave, come back, and find out what happened. Failure mode: a
status that exists only in the tab that started the job.

**Completion notification** — tell the user when a backgrounded job lands, with a
route straight to the result. Failure mode: notifying without a way to act.

## Rejected Patterns

These never ship. The validator rejects the first two mechanically.

- **Fake progress** — a determinate bar or percentage not derived from real work.
  It is a fabricated measurement rendered as UI.
- **Artificial delay beyond 200 ms** — an anti-flicker floor is legitimate;
  padding an interaction to look deliberate is masking latency with latency.
- **Fake success** — showing a completed outcome for work that can fail without a
  rollback path, or for any irreversible effect.
- **Spinner on a sub-300 ms interaction** — a flash that reads as instability.
- **Skeleton with the wrong geometry** — trades a wait for a layout shift.
- **Suppressed errors** — hiding a failure so the illusion survives. The illusion
  is not the product.
