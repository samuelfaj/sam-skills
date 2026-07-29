# Honesty Policy

Perceived performance is a promise about state, made before the state is
confirmed. The promise is honest only when the system can keep it or visibly take
it back. Read this before applying any optimistic or progress affordance.

## The Line

Feeling instantaneous means feedback arrives inside 100 ms and no pending moment
goes unacknowledged. It never means the user is told something happened that did
not happen. If the only way to make an interaction feel fast is to misreport its
outcome, the honest result is a partial improvement, not a faster-looking lie.

## Never Fake

- **Progress that is not measured.** A determinate bar or percentage must be
  derived from a real signal — bytes transferred, items processed, steps
  completed. If no real signal exists, use an indeterminate affordance and say
  what is happening. `progress_presentation: DETERMINATE` with
  `progress_signal: SYNTHETIC` is rejected.
- **Success that is not reversible.** An optimistic outcome requires that the
  displayed state can be corrected with no user-visible loss and no irreversible
  side effect already implied. Set `irreversible_effect: true` and reject the
  optimistic path for a captured payment, a sent message, a published record, a
  destructive delete, or any external commit you cannot retract.
- **Absence of failure.** A rollback that silently restores prior state teaches
  the user their action worked. Every rollback needs a visible failure surface at
  the point of the action.
- **Freshness.** Cache-first rendering may not present stale data as current when
  the user is about to act on it — balances, inventory, permissions, prices.

## Optimistic Update Checklist

Every field is required and mechanically enforced for an `APPLIED` optimistic
technique.

- `failure_mode` — the concrete way the real work fails.
- `reversible: true` — the displayed state is correctable.
- `irreversible_effect: false` — no unretractable side effect is implied.
- `rollback` — exactly what is restored, including derived and adjacent state.
- `on_failure_ui` — what the user sees and can do next, at the point of action.
- `failure_path_evidence_ids` — a passing test that drives the failure and asserts
  the rollback plus the failure surface. The happy path is not proof.

An optimistic update whose failure path is untested is an unproven claim about the
most important moment in the interaction.

## Concurrency and Reconciliation

State the reconciliation rule before applying an optimistic or cached technique:

- What wins when the server result differs from the optimistic state.
- What happens to a second action taken while the first is pending.
- What happens if responses arrive out of order.
- What happens if the user navigates away or the tab closes mid-flight.

"The server is authoritative" is a rule. "It usually resolves" is not.

## Accessibility

An asynchronous change that is only visual is invisible to part of the audience,
and a change announced badly is worse than a silent one.

- Announce pending, settled, and failed states through a polite live region.
  Reserve assertive announcements for failures that block the user.
- Never announce a placeholder as content. A skeleton is decorative; the loading
  state is what gets announced.
- Keep focus stable. Content arriving asynchronously must not move focus out from
  under a keyboard or screen-reader user.
- Respect reduced-motion preferences: transitions that mask latency must degrade
  to an instant state change, not disappear into an unacknowledged wait.
- The `accessibility-announcement` gate requires a passing test for any applied
  technique. Manual observation is not evidence.

## What the Validator Cannot See

`scripts/validate_perceived_report.py` checks the declared shape of a change. It
cannot see a report that declares `optimistic: false` for code that does show an
unconfirmed outcome, or `progress_signal: REAL` for a number computed from a
timer. Those are lies about the input, and the honest handling is to classify by
what the code actually renders. State the technique as what a user would call it,
not as whichever field combination validates.
