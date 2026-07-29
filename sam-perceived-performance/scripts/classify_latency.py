#!/usr/bin/env python3
"""Classify a measured interaction into a perception class and check its budget.

Single source of truth for the perception thresholds. The report validator
imports `classify` and `budget_errors` from this module so a report cannot be
graded against a different table than the one the gate executed.

Inputs are measured milliseconds for one interaction:

- settled: input event -> real work finished and the UI is final and consistent.
- feedback: input event -> first user-perceptible change caused by that input.
- meaningful: input event -> the affected region shows real, non-placeholder
  content for its primary element (optional; defaults to settled).
- dead time: total time the interaction is pending while the UI shows neither an
  acknowledged state nor a progress signal.

Exit status: 0 when every budget holds, 1 when a budget is violated, 2 on bad
input. Run it through run_checked.py so the budget verdict carries a receipt.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# Perception classes ordered by the real settled latency they describe. The
# ceilings come from interaction-response research: ~100 ms reads as direct
# causation, ~1 s keeps flow, ~10 s loses attention entirely.
CLASSES: tuple[dict[str, Any], ...] = (
    {
        "name": "INSTANT",
        "max_settled_ms": 100,
        "max_feedback_ms": 100,
        "max_dead_time_ms": 100,
        "required": (),
        "forbidden": ("spinner", "skeleton", "artificial-delay", "progress-bar"),
    },
    {
        "name": "RESPONSIVE",
        "max_settled_ms": 300,
        "max_feedback_ms": 100,
        "max_dead_time_ms": 200,
        "required": ("immediate-acknowledgement",),
        "forbidden": ("spinner", "blocking-overlay", "fake-progress"),
    },
    {
        "name": "NOTICEABLE",
        "max_settled_ms": 1000,
        "max_feedback_ms": 100,
        "max_dead_time_ms": 300,
        "required": ("immediate-acknowledgement", "in-place-placeholder-or-stream"),
        "forbidden": ("full-page-spinner", "layout-shifting-placeholder", "fake-progress"),
    },
    {
        "name": "SLOW",
        "max_settled_ms": 5000,
        "max_feedback_ms": 100,
        "max_dead_time_ms": 300,
        "required": (
            "immediate-acknowledgement",
            "layout-stable-skeleton-or-stream",
            "optimistic-or-deferred-commit-when-reversible",
        ),
        "forbidden": ("fake-progress", "blocking-modal-spinner"),
    },
    {
        "name": "TEDIOUS",
        "max_settled_ms": 10000,
        "max_feedback_ms": 100,
        "max_dead_time_ms": 500,
        "required": (
            "immediate-acknowledgement",
            "real-determinate-progress",
            "cancel-or-background-affordance",
        ),
        "forbidden": ("fake-progress", "indeterminate-only-progress"),
    },
    {
        "name": "BACKGROUND",
        "max_settled_ms": None,
        "max_feedback_ms": 100,
        "max_dead_time_ms": 500,
        "required": (
            "immediate-acknowledgement",
            "backgrounded-job",
            "durable-status-surface",
            "completion-notification",
            "navigation-safe",
        ),
        "forbidden": ("fake-progress", "route-blocking-wait"),
    },
)

# A change may not make the real interaction slower in the name of feeling
# faster. Absolute floor absorbs measurement noise on fast interactions.
REGRESSION_FLOOR_MS = 25
REGRESSION_FRACTION = 0.05
# Anti-flicker floors are legitimate; masking real latency with sleep is not.
MAX_ADDED_DELAY_MS = 200
# Wall-clock timing is noisy. Fewer samples cannot support a timing claim.
MIN_SAMPLES = 5
# "Feels instantaneous" is not a vibe: first feedback within one perception
# quantum and no unacknowledged pending time anywhere in the interaction.
INSTANT_FEEDBACK_MS = 100


def classify(settled_ms: int) -> dict[str, Any]:
    """Return the perception class and budgets for a measured settled latency."""
    for entry in CLASSES:
        ceiling = entry["max_settled_ms"]
        if ceiling is None or settled_ms <= ceiling:
            return dict(entry)
    return dict(CLASSES[-1])


def regression_budget_ms(baseline_settled_ms: int) -> int:
    """Largest real-latency increase that measurement noise can still explain."""
    return max(REGRESSION_FLOOR_MS, int(baseline_settled_ms * REGRESSION_FRACTION))


def budget_errors(
    label: str,
    settled_ms: int,
    feedback_ms: int,
    dead_time_ms: int,
    meaningful_ms: int | None = None,
    *,
    enforce_budget: bool = True,
) -> list[str]:
    """Check one measured interaction against its class budget.

    Ordering is part of the contract: feedback cannot follow meaningful content,
    meaningful content cannot follow settlement, and dead time is a slice of the
    interaction, so a report with impossible timings fails before its budget is
    ever considered.

    Pass `enforce_budget=False` for a pre-change baseline: an interaction that
    already met its budget would not need this workflow, so grading the baseline
    against the budget would reject exactly the reports worth writing. Ordering
    is still checked, because impossible baseline timings are still impossible.
    """
    errors: list[str] = []
    resolved_meaningful = settled_ms if meaningful_ms is None else meaningful_ms
    for name, value in (
        ("settled", settled_ms),
        ("feedback", feedback_ms),
        ("meaningful", resolved_meaningful),
        ("dead_time", dead_time_ms),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{label} {name} must be a non-negative integer of milliseconds")
    if errors:
        return errors
    if feedback_ms > resolved_meaningful:
        errors.append(f"{label} first feedback cannot arrive after meaningful content")
    if resolved_meaningful > settled_ms:
        errors.append(f"{label} meaningful content cannot arrive after settlement")
    if dead_time_ms > settled_ms:
        errors.append(f"{label} dead time cannot exceed the settled interaction")
    if not enforce_budget:
        return errors
    entry = classify(settled_ms)
    if feedback_ms > entry["max_feedback_ms"]:
        errors.append(
            f"{label} class {entry['name']} allows first feedback within "
            f"{entry['max_feedback_ms']}ms; measured {feedback_ms}ms"
        )
    if dead_time_ms > entry["max_dead_time_ms"]:
        errors.append(
            f"{label} class {entry['name']} allows {entry['max_dead_time_ms']}ms of "
            f"unacknowledged pending time; measured {dead_time_ms}ms"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="interaction")
    parser.add_argument("--settled-ms", required=True, type=int)
    parser.add_argument("--feedback-ms", required=True, type=int)
    parser.add_argument("--dead-time-ms", required=True, type=int)
    parser.add_argument("--meaningful-ms", type=int, default=None)
    parser.add_argument(
        "--baseline-settled-ms",
        type=int,
        default=None,
        help="Baseline settled latency; enables the real-latency regression check.",
    )
    args = parser.parse_args()

    entry = classify(args.settled_ms)
    errors = budget_errors(
        args.label,
        args.settled_ms,
        args.feedback_ms,
        args.dead_time_ms,
        args.meaningful_ms,
    )
    allowed_regression = None
    if args.baseline_settled_ms is not None:
        if args.baseline_settled_ms < 0:
            errors.append(f"{args.label} baseline settled latency must not be negative")
        else:
            allowed_regression = regression_budget_ms(args.baseline_settled_ms)
            increase = args.settled_ms - args.baseline_settled_ms
            if increase > allowed_regression:
                errors.append(
                    f"{args.label} real latency regressed by {increase}ms; budget is "
                    f"{allowed_regression}ms"
                )
    verdict = {
        "label": args.label,
        "class": entry["name"],
        "settled_ms": args.settled_ms,
        "feedback_ms": args.feedback_ms,
        "meaningful_ms": args.meaningful_ms,
        "dead_time_ms": args.dead_time_ms,
        "max_feedback_ms": entry["max_feedback_ms"],
        "max_dead_time_ms": entry["max_dead_time_ms"],
        "required_affordances": list(entry["required"]),
        "forbidden_affordances": list(entry["forbidden"]),
        "allowed_real_latency_increase_ms": allowed_regression,
        "feels_instantaneous": not errors
        and args.feedback_ms <= INSTANT_FEEDBACK_MS
        and args.dead_time_ms == 0,
        "status": "WITHIN_BUDGET" if not errors else "OUT_OF_BUDGET",
        "violations": errors,
    }
    json.dump(verdict, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
