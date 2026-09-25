# Behavioral evaluation pack

This pack scores the historical structured-report workflows. It does not evaluate the adaptive default of `sam-task`. Run it manually or on a periodic job, never as a per-commit gate.

## Scenario catalog

`assets/behavior-eval-scenarios.json` holds twelve versioned scenarios (planning, bugs, features, stale evidence, risk routing, learning, delegated scope control), each with accepted terminals, unsafe completion terminals, and observable acceptance checks. Never change a scenario to make a failing run pass; version the suite when its meaning changes.

## Recorded run

UTF-8 JSON object: `schema_version: 1`, `suite_id` matching the catalog, `skill_revision` (tested 40/64-hex revision), `results[]` with one result per scenario:

- `scenario_id`, `terminal`, `validator_receipt`, `report_sha256`
- `acceptance_checks[]`: exact catalog IDs, boolean `passed`, concrete `evidence`
- `iterations` (positive integer), `human_corrections` (non-negative integer), `wall_time_seconds` (non-negative)
- `input_tokens`, `output_tokens`, `cost_usd`: non-negative, or `null` when the host does not expose them; never convert unavailable metrics to zero

## Metrics and command

The evaluator reports scenario pass rate; false completion count and rate (a completion terminal whose validator receipt or any acceptance check fails); average human corrections, iterations, and wall time; and average input tokens, output tokens, and cost over available observations.

```bash
python3 -B <SAM_TASK_DIR>/scripts/validate_behavior_eval.py <abs>/behavior-eval-run.json --require-complete-suite
```

Only a complete suite with every scenario passing is a baseline candidate. Review the recorded evidence before comparing skill revisions.
