# Honesty Policy

Applies to every optimistic, cached, or progress technique. If the only way to feel fast is to misreport an outcome, the honest result is a partial improvement.

## Never Fake

- **Progress.** A determinate bar or percentage derives from a real signal: bytes transferred, items processed, steps completed. Without one, use an indeterminate affordance and say what is happening.
- **Success.** Set `irreversible_effect: true` and reject the optimistic path for a captured payment, a sent message, a published record, a destructive delete, or any external commit you cannot retract.
- **Absence of failure.** A silent rollback teaches the user the action worked. Every rollback shows a visible failure surface at the point of action, with what the user can do next. The happy path is not failure-path proof.
- **Freshness.** Cache-first rendering never presents stale data as current when the user is about to act on it: balances, inventory, permissions, prices.

## Decide Reversibility Before Code

For each optimistic or cached candidate, state the failure mode, what rollback restores (including derived and adjacent state), what the user sees and can do on failure, and the reconciliation rule. An irreversible effect rejects the optimistic path: use acknowledgement plus real progress.

## Reconciliation Rule

State it before applying an optimistic or cached technique: what wins when the server result differs, what happens to a second action taken while the first is pending, how out-of-order responses resolve, and what happens on navigation away or tab close mid-flight. "The server is authoritative" is a rule; "it usually resolves" is not.

## Classify by What Renders

The validator checks the declared shape, not the code. Declaring `optimistic: false` for code that shows an unconfirmed outcome, or `progress_signal: REAL` for a timer-derived number, lies about the input. Classify by what the code actually renders, and name the technique as a user would, not by whichever field combination validates.
