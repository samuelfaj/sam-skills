# Technique Catalog

Choose the cheapest technique that closes the measured gap: one acknowledgement landing in 40 ms beats stacked loading affordances. Optimistic, cached, and progress techniques also follow honesty-policy.md; every applied technique owes the SKILL.md step 4 tests and the accessibility rules below.

| Technique | Use | Cost | Failure mode / guard | Proof |
| --- | --- | --- | --- | --- |
| Immediate local state change | apply pressed/selected/checked/submitted state in the input handler before any request | near zero | disagrees with the server; needs optimistic rollback discipline whenever it implies an outcome | test: state changes without awaiting the request |
| Input echo | render typed text, drag positions, toggles from local state, never a round trip | local state to reconcile | server normalization surprises mid-edit; reconcile on settle, not per keystroke | test typing while the request is pending |
| Disabled-with-reason | keep the surface interactive and name why an action is unavailable instead of freezing it | copy | stale reason after the condition clears | |
| Layout-stable skeleton | reserve the final geometry with a neutral placeholder | a second layout | geometry drift causes a shift worse than the wait | test or measurement: no layout shift on settle |
| Progressive rendering | paint each region as its data arrives, not after the slowest dependency | partial states multiply | jarring settle order; a late region shifts earlier ones | |
| Streamed response | send first bytes before the full result so `meaningful_ms` drops far below `settled_ms` | streaming transport; errors after headers | a mid-stream failure already looks like success; the surface must retract | |
| Chunked work with yields | split long client work so the main thread stays responsive | scheduling | total work grows; watch `settled_ms` | |
| Prefetch on intent | fetch on hover, focus, viewport entry, or route proximity | wasted requests | bandwidth contention slows the in-flight interaction (the regression budget catches it); never prefetch anything with a side effect | |
| Cache-first with revalidation | render known-good data, refresh behind it | staleness | a stale value read as current; label freshness when consequential; never for balances, inventory, or anything acted on irreversibly | |
| Precomputation | compute at write or build time instead of read time | storage, invalidation | silently stale derived data | |
| Speculative execution | start the likely request before the user commits; idempotent reads only | wasted work | side effects | |
| Optimistic update | show the outcome before confirmation; reversible effects only | rollback and failure UI | see honesty-policy.md | passing failure-path test |
| Deferred commit with undo | apply locally, expose a real undo window, then commit | a queue and a window | the window closes on navigation or crash and the change is silently lost | |
| Write-behind queue | accept input, persist the intent, retry in the background | durable queue, ordering, conflicts | drains after the user assumes it is done, with no failure surface | |
| Backgrounded job with status surface | required above 10 s: the user can leave, return, and find the outcome | job infrastructure | status exists only in the tab that started the job | |
| Completion notification | tell the user when a backgrounded job lands, with a route to the result | | notifying without a way to act | |

## Accessibility (every applied technique)

- Announce pending, settled, and failed states in a polite live region; use assertive only for failures that block the user.
- Announce the loading state, never a skeleton as content.
- Keep focus stable while content arrives.
- Reduced motion degrades to an instant state change, never an unacknowledged wait; state the behavior.
- Manual observation is not evidence.
