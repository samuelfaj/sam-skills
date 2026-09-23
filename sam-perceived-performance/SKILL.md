---
name: sam-perceived-performance
description: "Make slow UI interactions feel instant: measured feedback, reversible optimistic updates, stable placeholders, streaming, prefetch; no fake progress, success, or freshness. Use when an action, screen, list, form, upload, search, or navigation feels slow, laggy, janky, or spinner-bound and latency is irreducible."
---

# Sam Perceived Performance

Make the named interactions feel instantaneous while the real work continues behind them. Stay stack-, provider-, host-, tool-, and model-neutral.

**Instant** = `feedback_ms <= 100` and `dead_time_ms == 0` (`feels_instantaneous` in classify_latency output), proven by receipted before/after measurements — never by a spinner's presence or a lower `settled_ms`.

## Non-Negotiable Contract

- Never expose secrets, credentials, private data, or sensitive paths in diffs, commands, reports, artifacts, or returned evidence.
- Never fake progress (a determinate bar or percentage needs a real signal), success (an optimistic outcome needs a reversible effect, a proven rollback, and a visible failure surface), or freshness.
- Never make the real interaction slower to feel faster: a `settled_ms` increase beyond `max(25ms, 5% of baseline)` is a regression to revert.
- Never suppress or delay an error. Artificial delay is capped at a 200 ms anti-flicker floor and needs a stated reason.
- No timing claim without receipted measurements of the same interaction in the same environment, before and after. An unmeasurable interaction is `BLOCKED`: never estimate, infer from a similar interaction, or reason from code to a number.
- Preserve public contracts, security, permissions, data integrity, observability, and unrelated staged, unstaged, and untracked work byte-for-byte. Never reset, checkout, stash, clean, rebase, or broadly restore; undo only this work's exact patch.
- Do not stage, commit, publish, or message an external system unless the user or a parent workflow explicitly requests it. Parent authorization is enough; never re-ask.
- Stop after two cycles unless new measured evidence appears. Never weaken the validator, the budget table, or a test to reach a status.

## Paths and Reads

Write literal absolute paths in every command (shell variables do not persist): `<skill>` = this file's directory, `<tmp>` = one scratch directory outside the repository (`mktemp -d` once) for every temporary artifact, `<repo>` = the repository root.

| Read | Read when |
| --- | --- |
| [references/technique-catalog.md](references/technique-catalog.md) | step 3, before choosing a technique |
| [references/honesty-policy.md](references/honesty-policy.md) | step 3, when an optimistic, cached, or progress technique is a candidate |
| [references/output-contract.md](references/output-contract.md) | step 6, before scaffolding the report |

Do not re-read a file already read in this context unless context was compacted since or you cannot quote the section you need. Read measured numbers from `<tmp>/receipts/<id>.run1.log`; never open `*.receipt.json` or scope bundles. The validator recomputes every receipt (`scripts/verify_receipts.py`) and budget (`scripts/classify_latency.py`); a typed `PASS` never closes a gate.

## 1. Freeze the Request and Scope

```bash
python3 <skill>/scripts/capture_scope.py --repo <repo> > <tmp>/baseline.json
```

Add repeated `--path <repo-relative-path>` only for explicit scope; reuse the exact arguments for every later capture. An interaction is one user intent with one entry point: the trigger, the code path handling it, and the work that must finish before the result is final. Before touching anything, freeze each interaction's id, name, entry point, trigger, and blocking work; what must not change (public contracts, totals, ordering, permissions, security); honesty invariants (outcomes never shown before confirmation, data never shown stale); owned paths, no-go paths, and the baseline fingerprint.

If the request names only a feeling ("the app is slow"), pick the interactions on the described path, state the choice, and proceed. Under a parent never ask; return `BLOCKED` with receipts if scope cannot be established safely. Standalone, ask one blocking question only if no interaction can be identified.

## 2. Measure the Baseline

Measure what the user perceives at the interaction boundary, all four numbers from the same input event; server-side or single-request timings do not count.

| Metric | Input event to |
| --- | --- |
| `feedback_ms` | first paint reflecting the input (event-to-paint mark or frame trace, not a log line before the paint) |
| `meaningful_ms` | first paint of real content in the affected region's primary element (a skeleton does not count) |
| `settled_ms` | last state mutation of the interaction, including retries and reconciliation (not one request's response) |
| `dead_time_ms` | sum of pending intervals with neither an acknowledged state nor a progress signal |

Ordering is physical: `feedback <= meaningful <= settled` and `dead_time <= settled`.

- Hold environment, device profile, network profile, data volume, and cache state identical before and after, and record them in `environment`. If they cannot be held constant, the interaction is unmeasurable and `BLOCKED`; continue with the rest, and never compare a throttled run with an unthrottled one.
- Take at least 5 samples per block and report the median, not the best run, naming the metric in `detail`. Discard the first run after a cold start unless cold start is under test, and say which. Keep sample count and selection rule identical before and after.
- Run every measurement and test through `scripts/run_checked.py` under its own `--id`; reuse an id only to rerun the identical invocation (same command and classification) after fixing its harness. Classifications: `BASELINE` pre-change measurement, run once; `TARGET` post-change measurement cited by `after` and `INTRODUCED` tests this work adds (step 4), both run with `--repeat 2` or more and need identical exit codes, else fix the harness or mark the interaction `BLOCKED`; `ENVIRONMENT` profile capture, throttling, seed data; `EXTERNAL` systems you do not control.

```bash
python3 <skill>/scripts/run_checked.py --id E-001 --receipts-dir <tmp>/receipts \
  --classification BASELINE -- <measurement command>
```

Then locate the real cost in the handler and the work it awaits: what must finish before a correct result is visible, what is awaited but not needed for the first useful paint, and how long the wait stays unacknowledged. Inspect changed command definitions before executing them.

## 3. Select Techniques by Class and Reversibility

```bash
python3 <skill>/scripts/classify_latency.py --label I-001 --settled-ms <baseline> \
  --feedback-ms <baseline> --dead-time-ms <baseline>
```

Its JSON gives the class (from `settled_ms`), the budgets, the required affordances (a minimum), and the forbidden ones; never restate budgets from memory. Only when an interaction misses its budget or lacks a required affordance, choose a technique from the catalog.

For an optimistic or cached candidate, decide reversibility per the honesty policy before writing code. Mark every technique `APPLIED`, `REJECTED` (a result, with its reason), or `BLOCKED`.

## 4. Implement the Smallest Honest Illusion

Apply one coherent technique at a time. After each change:

1. Inspect the exact diff; only owned paths changed.
2. Re-measure as `TARGET --repeat 2` under a new id, then run `capture_scope.py` with the step-1 arguments `> <tmp>/measured-<E-id>.json`; compare with the baseline.
3. Run the failure-path proof for any optimistic commit.
4. Undo only that patch if it fails, regresses real latency, or needs a hidden error.

A technique counts as applied only with passing `INTRODUCED` tests for the fast path, an optimistic commit's driven failure (asserting rollback and the failure surface), and the pending, settled, and failed announcements, and only when it meets the accessibility rules in the technique catalog.

If a necessary change exceeds the authorized goal, contract, or owner boundary, return the exact gap to the parent (ask the user when standalone). More files alone do not widen scope; justify each added path against the criteria.

## 5. Prove the Perceived Improvement

Each non-`BLOCKED` interaction's `after` is a `TARGET` measurement taken with the identical procedure: reuse the last step-4 measurement when no code changed since; otherwise, and always when nothing was applied, measure again and capture `measured-<E-id>.json`. A classify_latency run on `after` is only a self-check, never evidence.

An interaction is `IMPROVED` only when first feedback moved measurably earlier and `after` meets its class budget. Run a second cycle only for a new measured gap. When an interaction still misses its class budget and the rest of the wait is real latency no honest affordance can mask, stop: that interaction is `BLOCKED`, naming the latency in `remaining`. Real latency behind an in-budget interaction is reported, not blocked.

## 6. Validate and Return

```bash
python3 <skill>/scripts/capture_scope.py --repo <repo> > <tmp>/current.json
python3 <skill>/scripts/scaffold_perceived_report.py --baseline <tmp>/baseline.json \
  --current <tmp>/current.json --receipts-dir <tmp>/receipts \
  --measured-scope <tmp>/measured-<E-id>.json --out <tmp>/report.json
python3 <skill>/scripts/validate_perceived_report.py --baseline <tmp>/baseline.json \
  --current <tmp>/current.json <tmp>/report.json
```

Repeat `--measured-scope` per measurement cited as `after` (its `measured-<E-id>.json`), or pass `--no-after` when every interaction is `BLOCKED`. If anything changes after scaffolding, recapture `current.json` and rerun the scaffold with `--check` in place of `--out` before validating. Complete the report per references/output-contract.md. Retain the report and cited evidence for caller re-validation; remove only unused scratch.
