---
name: sam-perceived-performance
description: "Make a requested interaction feel instantaneous while the real work is still running, using measured immediate feedback, optimistic updates with proven rollback, layout-stable placeholders, streaming, prefetch, and backgrounding — without faking progress, success, or freshness. Use when an action, screen, list, form, upload, search, or navigation feels slow, laggy, janky, or stuck behind a spinner, and real backend or network latency cannot be removed."
---

# Sam Perceived Performance

Analyze what was asked, then make the named interactions feel instantaneous while
the real work continues behind them. Remain stack-, provider-, host-, tool-, and
model-neutral.

Perceived performance is measured, not asserted. The deliverable is a first
feedback inside 100 ms with no unacknowledged pending time — proven by before and
after measurements, not by the presence of a spinner.

## Non-Negotiable Contract

- Never expose secrets, credentials, private data, or sensitive paths in diffs,
  commands, reports, artifacts, or returned evidence.
- Never fake progress: a determinate bar or percentage must come from a real
  signal. Never fake success: an optimistic outcome requires a reversible effect,
  a proven rollback, and a visible failure surface. Never fake freshness.
- Never make the real interaction slower to make it feel faster. An increase in
  settled latency beyond `max(25ms, 5%)` is a regression to revert.
- Never suppress or delay an error to protect the illusion.
- Never add artificial delay beyond a 200 ms anti-flicker floor, and state why.
- Never claim a timing improvement without a receipted measurement of the same
  interaction, in the same environment, before and after.
- Preserve public contracts, security, permissions, data integrity, and
  observability. Preserve unrelated staged, unstaged, and untracked work
  byte-for-byte.
- Never reset, checkout, stash, clean, rebase, or broadly restore the workspace.
  Undo only the exact patch this work introduced.
- Do not stage, commit, publish, or message an external system unless the user or
  a parent workflow explicitly requests it. Parent authorization is enough; do
  not re-ask.
- Stop after two cycles unless new measured evidence appears.

## Resource Routing

- Read [references/latency-classes.md](references/latency-classes.md) before
  choosing any affordance.
- Read [references/measurement-protocol.md](references/measurement-protocol.md)
  before recording a baseline.
- Read [references/technique-catalog.md](references/technique-catalog.md)
  selectively while selecting techniques.
- Read [references/honesty-policy.md](references/honesty-policy.md) before
  applying any optimistic, cached, or progress affordance.
- Read [references/output-contract.md](references/output-contract.md) before
  drafting the report.
- Run `scripts/capture_scope.py` before and after implementation.
- Run every measurement and test through `scripts/run_checked.py`.
- Run `scripts/classify_latency.py` per interaction for the budget verdict.
- Run `scripts/validate_perceived_report.py` before returning the decision. It
  recomputes receipts through `scripts/verify_receipts.py`, so a typed `PASS`
  cannot close a gate.

## 1. Freeze the Request and the Scope

```bash
SAM_PERCEIVED_DIR="<absolute directory containing this SKILL.md>"
WORK_TMP="$(mktemp -d)"
python3 "$SAM_PERCEIVED_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/baseline.json"
```

Use repeated `--path <repo-relative-path>` only for explicit scope and reuse the
exact arguments later. Keep all temporary artifacts outside the repository.

From the request, name each interaction that should feel instantaneous. An
interaction is one user intent with one entry point: the trigger, the code path
that handles it, and the work that must finish before the result is final.

Freeze, before touching anything:

- Each interaction's id, name, entry point, trigger, and blocking work.
- What must not change: public contracts, totals, ordering, permissions, security.
- Honesty invariants for this domain — which outcomes may never be shown before
  confirmation, and which data may never be shown stale.
- Owned paths, no-go paths, and the baseline fingerprint.

If the request names a feeling ("the app is slow") without an interaction, pick the
interactions on the described path, state that choice, and proceed. Under a parent
workflow, never ask; return `BLOCKED` with receipts if scope cannot be established
safely. Standalone, ask one blocking question only if no interaction can be
identified at all.

## 2. Measure the Baseline

Follow [references/measurement-protocol.md](references/measurement-protocol.md).
Record `feedback_ms`, `meaningful_ms`, `settled_ms`, and `dead_time_ms` per
interaction, from at least five samples, with the device and network profile
written down.

```bash
python3 "$SAM_PERCEIVED_DIR/scripts/run_checked.py" \
  --id E-001 --receipts-dir "$WORK_TMP/receipts" \
  --classification BASELINE --repeat 2 \
  -- <baseline measurement command>
```

Then locate the real cost. Read the handler and the work it awaits, and answer:

- What must finish before the user can see a correct result?
- What is awaited but not actually needed for the first useful paint?
- Which part of the wait is unacknowledged, and how long is it?

Inspect changed command definitions before executing them. If an interaction
cannot be measured comparably, mark it `BLOCKED` and keep going with the rest. Do
not estimate a number you could not measure.

## 3. Select Techniques by Class and Reversibility

Classify each interaction by its measured `settled_ms`:

```bash
python3 "$SAM_PERCEIVED_DIR/scripts/classify_latency.py" \
  --label I-001 --settled-ms <baseline settled> --feedback-ms <baseline feedback> \
  --dead-time-ms <baseline dead time>
```

The class sets the minimum affordance and names what is forbidden. Then choose
from [references/technique-catalog.md](references/technique-catalog.md), cheapest
first, and gate every optimistic or progress affordance against
[references/honesty-policy.md](references/honesty-policy.md).

Decide reversibility before writing code. For each candidate optimistic commit,
state the failure mode, what rollback restores, what the user sees on failure, and
the reconciliation rule for concurrent or out-of-order results. If the effect is
irreversible, reject the optimistic path and use acknowledgement plus real
progress instead — a rejected optimistic technique is a result, recorded as
`REJECTED` with its reason.

Classify each technique `APPLIED`, `REJECTED`, or `BLOCKED`. Prefer one
acknowledgement that lands in 40 ms over three stacked loading affordances.

## 4. Implement the Smallest Honest Illusion

Apply one coherent technique at a time. After each meaningful change:

1. Inspect the exact diff and confirm only owned paths changed.
2. Re-measure the interaction and compare against the baseline.
3. Run the failure-path proof for any optimistic commit.
4. Undo only that exact patch if it fails, regresses real latency, or requires
   hiding an error.

Every applied technique needs, before it counts as applied:

- A passing test for the fast path.
- A passing test that drives the failure and asserts the rollback and the failure
  surface, for any optimistic commit.
- A passing test that the pending, settled, and failed states are announced, and a
  stated reduced-motion behavior.

If owned scope exceeds twice the frozen initial set, or the work crosses an owner,
protocol, storage, migration, or release boundary: under a parent workflow return
`BLOCKED` with the exact breach; standalone, stop and request approval.

## 5. Prove the Perceived Improvement

Re-measure with the identical procedure, then receipt the budget verdict so the
gates are executed rather than asserted:

```bash
python3 "$SAM_PERCEIVED_DIR/scripts/run_checked.py" \
  --id E-006 --receipts-dir "$WORK_TMP/receipts" \
  --classification TARGET --repeat 2 \
  -- python3 "$SAM_PERCEIVED_DIR/scripts/classify_latency.py" \
     --label I-001 --settled-ms <after settled> --feedback-ms <after feedback> \
     --meaningful-ms <after meaningful> --dead-time-ms <after dead time> \
     --baseline-settled-ms <baseline settled>
```

An interaction is `IMPROVED` only when first feedback moved measurably earlier,
lands inside 100 ms, and its unacknowledged pending time is within budget. It
feels instantaneous only when `dead_time_ms` is zero.

Run a second cycle only when the first exposes a new measured gap. Stop when the
remaining gap is real latency that no honest affordance can mask — say so instead
of adding another layer.

## 6. Validate and Return

```bash
python3 "$SAM_PERCEIVED_DIR/scripts/capture_scope.py" --repo "$PWD" \
  > "$WORK_TMP/current.json"
python3 "$SAM_PERCEIVED_DIR/scripts/validate_perceived_report.py" \
  --baseline "$WORK_TMP/baseline.json" \
  --current "$WORK_TMP/current.json" "$WORK_TMP/report.json"
```

Follow [references/output-contract.md](references/output-contract.md). Cover every
post-baseline path exactly once.

Return `PERCEIVED_INSTANT` only when every improved interaction acknowledges
inside 100 ms with zero unacknowledged pending time, no interaction is blocked,
every mandatory gate passes, and no evidence is flaky. Return `IMPROVED` when
first feedback moved earlier but pending time remains, and say what remains.
Return `NO_CHANGE` when the interactions already met their budgets or no honest
technique existed. Return `BLOCKED` when measurement, authorization, or a safe
technique is unavailable.

Do not weaken the validator, the budget table, or a test to reach a status. Report
real latency alongside perceived latency so the improvement cannot be mistaken for
the work getting faster. Remove temporary artifacts before returning.
