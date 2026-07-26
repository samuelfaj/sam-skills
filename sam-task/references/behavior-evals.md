# Behavioral evaluation pack

## Contents

1. Purpose
2. Scenario catalog
3. Recorded run
4. Metrics
5. Running the evaluator

## Purpose

Deterministic harnesses prove that validators reject malformed receipts. They
do not prove that an agent using a skill solves representative tasks well. The
behavior pack adds a portable, recorded evaluation layer without embedding a
provider-specific runner.

Run it manually or on a periodic evaluation job. Do not add it to every commit
gate: live agent runs cost time and tokens and may be nondeterministic.

## Scenario catalog

`assets/behavior-eval-scenarios.json` contains eight versioned scenarios across
planning, bugs, features, stale evidence, risk routing, learning, and delegated
scope control. Each scenario defines accepted terminals, unsafe completion
terminals, and observable acceptance checks.

Do not change a scenario to make a failing run pass. Version the suite when its
meaning changes.

## Recorded run

Write a UTF-8 JSON object with:

- `schema_version: 1`
- `suite_id: sam-skills-behavior-v1`
- `skill_revision`: tested 40- or 64-character revision
- `results[]`: one result per scenario

Each result contains:

- `scenario_id`, `terminal`, `validator_receipt`, `report_sha256`
- `acceptance_checks[]`: exact catalog IDs, boolean `passed`, concrete `evidence`
- non-negative `human_corrections`, positive `iterations`, and
  `wall_time_seconds`
- `input_tokens`, `output_tokens`, and `cost_usd` as non-negative values or
  `null` when the host does not expose them

Unavailable metrics stay `null`; never convert them to zero.

## Metrics

The evaluator reports:

- scenario pass rate
- false completion count and rate
- average human corrections, iterations, and wall time
- average input tokens, output tokens, and cost across available observations

A false completion occurs when a run returns a completion terminal while its
validator receipt or an acceptance check fails.

## Running the evaluator

```bash
SAM_TASK_DIR="<absolute directory containing this SKILL.md>"
python3 -B "$SAM_TASK_DIR/scripts/validate_behavior_eval.py" \
  behavior-eval-run.json --require-complete-suite
```

Only a complete suite with every scenario passing is a baseline candidate.
Review the recorded evidence before comparing skill revisions.
