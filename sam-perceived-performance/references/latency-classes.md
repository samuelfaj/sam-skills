# Latency Classes and Budgets

`scripts/classify_latency.py` owns this table. Read it to choose affordances;
never restate the numbers from memory in a report.

## The Four Measured Primitives

All four are measured from the same input event, in milliseconds.

- `feedback_ms` — first user-perceptible change caused by the input. This is the
  number that decides whether a system feels instantaneous.
- `meaningful_ms` — the affected region shows real, non-placeholder content for
  its primary element.
- `settled_ms` — the real work finished and the UI is final and consistent. This
  is real latency. Perceived-performance work must not increase it.
- `dead_time_ms` — total pending time where the UI shows neither an acknowledged
  state nor a progress signal. This is the number users experience as "broken".

Ordering is physical: `feedback_ms <= meaningful_ms <= settled_ms`, and
`dead_time_ms <= settled_ms`. A report that violates it is rejected before its
budget is considered.

## Classes

The class comes from `settled_ms` — the work you cannot make disappear. It sets
the minimum affordance, not the maximum.

| Class | `settled_ms` | Max `feedback_ms` | Max `dead_time_ms` |
| --- | --- | --- | --- |
| `INSTANT` | 0–100 | 100 | 100 |
| `RESPONSIVE` | 101–300 | 100 | 200 |
| `NOTICEABLE` | 301–1000 | 100 | 300 |
| `SLOW` | 1001–5000 | 100 | 300 |
| `TEDIOUS` | 5001–10000 | 100 | 500 |
| `BACKGROUND` | >10000 | 100 | 500 |

The feedback budget is 100 ms in every class. Below roughly 100 ms a person reads
the response as caused by their own action; past it, the system becomes something
they are waiting on. No amount of real work justifies a later acknowledgement.

## Required and Forbidden by Class

- `INSTANT` — nothing required beyond the state change itself. Forbids spinner,
  skeleton, progress bar, and any artificial delay: adding a loading affordance
  to an already-instant interaction makes it feel slower, not more polished.
- `RESPONSIVE` — requires immediate acknowledgement. Forbids spinners and
  blocking overlays; a spinner that appears and vanishes inside 300 ms registers
  as a flash of instability.
- `NOTICEABLE` — requires immediate acknowledgement plus an in-place placeholder
  or streamed content. Forbids full-page spinners and any placeholder whose
  geometry differs from the final content, because the correcting reflow costs
  more perceived speed than the placeholder bought.
- `SLOW` — requires acknowledgement, a layout-stable skeleton or streamed
  content, and an optimistic or deferred commit when the action is reversible.
  Forbids fake progress and blocking modal spinners.
- `TEDIOUS` — requires determinate progress driven by a real signal plus a cancel
  or background affordance. Forbids indeterminate-only progress: past five
  seconds a person needs to know whether waiting is worth it.
- `BACKGROUND` — requires a backgrounded job, a durable status surface, a
  completion notification, and safe navigation away mid-flight. Forbids blocking
  a route on completion. Above ten seconds attention is gone; the only honest
  design lets the user leave and come back.

## Budget Checks

```bash
python3 "$SAM_PERCEIVED_DIR/scripts/classify_latency.py" \
  --label I-001 --settled-ms 1830 --feedback-ms 40 --meaningful-ms 120 \
  --dead-time-ms 0 --baseline-settled-ms 1840
```

Exit 0 means every budget holds; exit 1 prints each violation. Run it through
`scripts/run_checked.py` so the verdict carries a receipt.

`feels_instantaneous` in the output is true only when `feedback_ms <= 100` and
`dead_time_ms == 0`. That pair, not a lower `settled_ms`, is the goal of this
workflow.

## Real-Latency Regression Budget

An increase in `settled_ms` is allowed only up to `max(25ms, 5% of baseline)`,
which is measurement noise rather than permission. Prefetching that saturates the
network, a heavier client bundle, or extra render passes all show up here. A
change that makes the real interaction slower to make it feel faster is reverted.
