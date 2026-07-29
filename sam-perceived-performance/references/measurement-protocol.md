# Measurement Protocol

A perceived-performance claim is a timing claim. Read this before recording a
baseline, and use the identical procedure for the post-change run.

## Comparability First

Baseline and post-change measurements must come from the same environment, device
profile, network profile, data volume, and cache state. Record all of them in the
report's `environment` block; `device_profile` and `network_profile` are required
because a timing pair measured under different conditions compares nothing.

If the environment cannot be held constant, the interaction is `BLOCKED` for
measurement. Do not compare a throttled baseline to an unthrottled result.

## What to Record

For each interaction, capture the four primitives defined in
[latency-classes.md](latency-classes.md): `feedback_ms`, `meaningful_ms`,
`settled_ms`, `dead_time_ms`.

Anchor every one to the same input event:

- `feedback_ms` — from the input event to the first paint that reflects it. In a
  browser, an event-to-paint mark or a frame-level trace; not a log line before
  the paint happens.
- `meaningful_ms` — to the first paint showing real content in the primary
  element of the affected region. A skeleton does not count.
- `settled_ms` — to the last state mutation of the interaction, including retries
  and reconciliation. Not the response time of one request.
- `dead_time_ms` — sum of pending intervals with no acknowledged state and no
  progress signal. Zero is the target and is what `PERCEIVED_INSTANT` requires.

Record what the user perceives, from the interaction boundary. A server-side
duration or an isolated request timing is not one of these numbers.

## Sampling

- At least five samples per measurement block; the validator rejects fewer.
- Report the median, not the best run. State the metric in `detail`.
- Discard the first run after a cold start unless cold start is the interaction
  under test; say which you did.
- Keep the sample count and selection rule identical between baseline and after.

## Receipts

Every measurement and every test is executed through `scripts/run_checked.py`, so
the report cites a receipt instead of asserting a result:

```bash
python3 "$SAM_PERCEIVED_DIR/scripts/run_checked.py" \
  --id E-002 --receipts-dir "$WORK_TMP/receipts" \
  --classification TARGET --repeat 2 \
  -- <measurement command>
```

Three couplings are enforced by `scripts/verify_receipts.py` through the report
validator, so they are worth getting right the first time:

- The receipt `--id` must equal the evidence id (`E-002` above).
- The evidence `command` text must equal the executed argv, joined by spaces.
- The evidence `classification` must equal the receipt's classification.

`TARGET` and `INTRODUCED` evidence must run at least twice with identical exit
codes. A flaky measurement cannot support `IMPROVED` or `PERCEIVED_INSTANT`; fix
the harness or classify the interaction `BLOCKED`.

## Classification

- `BASELINE` — pre-change measurement.
- `TARGET` — post-change measurement that proves the improvement.
- `INTRODUCED` — tests added by this work, including the failure-path and
  announcement tests.
- `ENVIRONMENT` — profile capture, throttling setup, seed data.
- `EXTERNAL` — anything from a system you do not control.

## Budget Verdicts

Run `scripts/classify_latency.py` per interaction and receipt it. Its exit code is
the `honest-feedback` and `real-latency-non-regression` gate result, so the gates
are executed rather than asserted:

```bash
python3 "$SAM_PERCEIVED_DIR/scripts/run_checked.py" \
  --id E-006 --receipts-dir "$WORK_TMP/receipts" \
  --classification TARGET --repeat 2 \
  -- python3 "$SAM_PERCEIVED_DIR/scripts/classify_latency.py" \
     --label I-001 --settled-ms 1830 --feedback-ms 40 --meaningful-ms 120 \
     --dead-time-ms 0 --baseline-settled-ms 1840
```

## When Measurement Is Not Possible

Set the interaction to `BLOCKED` with a reason and let it block the decision. Do
not estimate, infer from a similar interaction, or reason from the code to a
number. An unmeasured perceived-performance claim is indistinguishable from a
guess, which is why the workflow refuses to close on one.
