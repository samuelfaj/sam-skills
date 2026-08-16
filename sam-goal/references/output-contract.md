# Output Contract

Write `$GOAL_DIR/goal-report.json`, then validate it:

```bash
python3 -B scripts/validate_goal_report.py "$GOAL_DIR/goal-report.json"
```

```json
{
  "schema_version": 1,
  "workflow": "goal",
  "goal": "Add a native date field to the booking form",
  "action": "execute",
  "intensity": "full",
  "mode": "solo",
  "tree_depth": 2,
  "goal_dir": "/abs/path/goal",
  "host": {
    "key": "grok",
    "status": "DETECTED",
    "detected_from": "env:GROK_AGENT"
  },
  "units": {
    "counted": 1,
    "gate": "closed",
    "reason": "single-agent: 1 unit, below threshold"
  },
  "ladder": {
    "rung": 4,
    "rationale": "native date input covers the request",
    "skipped": ["date-picker package", "wrapper component"],
    "new_dependencies": [],
    "authorized_dependencies": []
  },
  "gates": {
    "path": "/abs/path/goal/GATES.md",
    "total": 3,
    "met": 3,
    "abandoned": 0,
    "unmet": [],
    "abandoned_ids": []
  },
  "delegation": null,
  "overbuild_review": {
    "lean_already": true,
    "net_lines": 0,
    "findings": []
  },
  "checks": {
    "gates": {"exit_code": 0, "summary": "ALL MET (3 met)"},
    "ledger": null
  },
  "evidence": [
    {
      "id": "E1",
      "status": "PASS",
      "detail": "python3 -B scripts/check_gates.py --status: ALL MET (3 met)"
    }
  ],
  "decision": {"result": "COMPLETE", "remaining": []}
}
```

## Allowed values

- `action`: `execute` | `review` | `audit`
- `intensity`: `lite` | `full` | `ultra`
- `mode`: `solo` | `delegated`
- `units.gate`: `open` | `closed`
- `evidence[].status`: `PASS` | `FAIL` | `BLOCKED` | `NOT_RUN` | `INFO`
- `decision.result`: `COMPLETE` | `IN_PROGRESS` | `BLOCKED`
- `host.key`: `claude-code` | `codex` | `grok` | `null`
- `host.status`: `DETECTED` | `OVERRIDE` | `UNKNOWN` | `CONFLICT` | `INVALID`

`delegation` is `null` in solo mode. In delegated mode it is an object
with `path`, `units`, `verified`, `pending`, `complete`.

## Invariants

- `mode` is `delegated` if and only if `units.gate` is `open`.
- `COMPLETE` requires empty `decision.remaining`, empty `gates.unmet`,
  `checks.gates.exit_code == 0`, every `new_dependencies` entry listed in
  `authorized_dependencies`, and at least one `PASS` evidence item.
- Delegated `COMPLETE` also requires `delegation.complete`,
  `delegation.verified == delegation.units`, and
  `checks.ledger.exit_code == 0`.
- `review` / `audit` `COMPLETE` still needs the overbuild object and
  passing validation; they may have zero implementation gates only when
  `action` is not `execute`. `lean_already: true` forbids findings;
  `lean_already: false` requires at least one.
- `IN_PROGRESS` and `BLOCKED` require a non-empty `remaining` list.
- `goal_dir` and `gates.path` are absolute.
- `host.key` is required when `host.status` is `DETECTED` or `OVERRIDE`.
  It must be `null` for `UNKNOWN`, `CONFLICT`, and `INVALID`.
