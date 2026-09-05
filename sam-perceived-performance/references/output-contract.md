# Output Contract

## Contents

- [Report Shape](#report-shape)
- [Field Rules](#field-rules)
- [Gates](#gates)
- [Decisions](#decisions)
- [Returned Summary](#returned-summary)

## Report Shape

Write `report.json` and validate it before returning anything.

```json
{
  "schema_version": 1,
  "workflow": "perceived-performance",
  "target": {
    "baseline_fingerprint": "<baseline bundle fingerprint>",
    "current_fingerprint": "<current bundle fingerprint>",
    "paths": []
  },
  "intent": {
    "goal": "<what should feel instantaneous>",
    "owner_boundary": "<what this work owns>",
    "must_not_change": ["<contract or behavior held fixed>"],
    "invariants": ["<what must remain true, including honesty invariants>"]
  },
  "environment": {
    "kind": "local",
    "identity": "<machine or runner>",
    "device_profile": "<CPU throttle, viewport, cache state>",
    "network_profile": "<bandwidth and latency profile>"
  },
  "evidence": [
    {
      "id": "E-001",
      "kind": "MEASUREMENT",
      "classification": "BASELINE",
      "status": "PASS",
      "command": "<argv joined by spaces>",
      "receipt": "<absolute receipt path>",
      "detail": "median of 7 samples"
    }
  ],
  "interactions": [
    {
      "id": "I-001",
      "name": "<interaction>",
      "entry_point": "<path:line>",
      "trigger": "<what the user does>",
      "blocking_work": "<the real work that cannot be removed>",
      "technique_ids": ["T-001"],
      "status": "IMPROVED",
      "baseline": {
        "feedback_ms": 1820, "meaningful_ms": 1820, "settled_ms": 1840,
        "dead_time_ms": 1820, "samples": 7, "evidence_ids": ["E-001"]
      },
      "after": {
        "feedback_ms": 40, "meaningful_ms": 120, "settled_ms": 1830,
        "dead_time_ms": 0, "samples": 7, "evidence_ids": ["E-002"]
      }
    }
  ],
  "techniques": [
    {
      "id": "T-001",
      "name": "optimistic-update",
      "status": "APPLIED",
      "interaction_ids": ["I-001"],
      "paths": ["<changed path>"],
      "optimistic": true,
      "reversible": true,
      "irreversible_effect": false,
      "failure_mode": "<how the real work fails>",
      "rollback": "<what is restored>",
      "on_failure_ui": "<what the user sees and can do>",
      "accessibility": "<announcement and reduced-motion handling>",
      "progress_signal": "NONE",
      "progress_presentation": "NONE",
      "added_delay_ms": 0,
      "evidence_ids": ["E-003"],
      "failure_path_evidence_ids": ["E-004"]
    }
  ],
  "file_coverage": [{"path": "<changed path>", "reason": "<why it changed>"}],
  "scope": {
    "initial_owned_paths": [],
    "current_owned_paths": [],
    "scope_expansion_approved": false,
    "cycle": 1
  },
  "gates": [
    {"name": "honest-feedback", "mandatory": true, "status": "PASS",
     "evidence_ids": ["E-006"]}
  ],
  "decision": {"result": "PERCEIVED_INSTANT", "remaining": []}
}
```

## Field Rules

- Ids use `E-`, `I-`, and `T-` with at least three digits and are unique.
- `interactions[].technique_ids` and `techniques[].interaction_ids` must link both
  ways.
- Every metric block cites passing `MEASUREMENT` or `TEST` evidence and reports at
  least five samples. `INSPECTION` evidence may never close a proof citation.
- An `APPLIED` technique lists only paths that actually changed, all inside
  `scope.current_owned_paths`.
- `progress_presentation: DETERMINATE` requires `progress_signal: REAL`.
- `added_delay_ms` is capped at 200 and requires `added_delay_reason` above zero.
- An `APPLIED` optimistic technique requires `reversible: true`,
  `irreversible_effect: false`, `failure_mode`, `rollback`, `on_failure_ui`, and
  passing `failure_path_evidence_ids`.
- `REJECTED`, `BLOCKED`, and `UNCHANGED` entries require a `reason`.
- A `BLOCKED` interaction omits metric blocks and blocks the decision.
- `file_coverage` covers every changed path exactly once.

## Gates

All four are mandatory. Applicability is derived from the change, so a gate cannot
be waived by declaring it moot.

| Gate | Proven by | `NOT_APPLICABLE` allowed |
| --- | --- | --- |
| `honest-feedback` | receipted `classify_latency.py` verdict | never |
| `real-latency-non-regression` | receipted verdict with `--baseline-settled-ms` | never |
| `failure-path-proof` | passing failure-path test | only with no applied optimistic technique |
| `accessibility-announcement` | passing announcement test | only with no applied technique |

## Decisions

- `PERCEIVED_INSTANT` — every improved interaction has `feedback_ms <= 100` and
  `dead_time_ms == 0`, no interaction is blocked, all gates pass, and no evidence
  is flaky. This is the only status that claims the system feels instantaneous.
- `IMPROVED` — first feedback measurably moved earlier and every gate passes, but
  at least one interaction still has unacknowledged pending time. Say what remains.
- `NO_CHANGE` — nothing was applied and nothing changed, because the interactions
  already met their budgets or no honest technique existed.
- `BLOCKED` — measurement, authorization, or a safe technique is unavailable. List
  what is needed.

Completion contradicts any blocker. A completed decision lists no remaining work;
a non-complete decision must.

## Returned Summary

Return, in prose:

1. The decision and, for each interaction, `feedback_ms` and `dead_time_ms` before
   and after with the class of the real latency.
2. Each applied technique, what it makes feel instant, and what happens when the
   underlying work fails.
3. Techniques rejected for honesty reasons and why — an unshipped optimistic path
   on an irreversible action is a result, not an omission.
4. Real latency before and after, stated plainly, including any regression inside
   the noise budget.
5. Anything blocked, and what would unblock it.

State the illusion's boundary explicitly: what the user now sees immediately
versus what is still settling behind it.

Scope authorization records changes to the agreed goal or contracts. File and
line counts are evidence, not an automatic approval threshold. Every changed
path must still be in scope and accounted for.
