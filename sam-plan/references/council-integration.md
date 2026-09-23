# Council Integration

## Who Runs Council

Council needs parallel seats, so it runs at controller level.

- Standalone, or inline in the controller: run `sam-council` yourself (you
  spawn the seats).
- Phase worker (child mode; workers never spawn): finish the draft freeze with
  `council.required=true` and empty `runs`, write the packet below to
  `<PLAN_DIR>/council-packet.md`, and run the Workflow step 5 command (render
  && validate); its only error must be `council.runs must not be empty when
  required`. Return `RESULT sam-plan COUNCIL_REQUIRED` with the packet path as
  the open item. The controller then does exactly one of: (a) runs
  `sam-council` and re-dispatches this phase with the validated council report
  path (fold it, then step 5), or (b) re-runs this phase inline, which reuses
  the draft (same prompt hash) and runs council itself. Never both.

| Situation | Council |
| --- | --- |
| Any risk flag | At least one `fast` pass on the executable thesis (escalate per council) |
| User requests deep adversarial review | Honor; use `full` when council triggers demand it |

## Packet

Relevant-only, never a restatement of the prompt without failure modes:
frozen goal, non-goals, constraints, and no-go; thesis approach, steps, risks,
and success criteria; evidence and assumption ledgers with locators; risk
flags and only the chapter text under review. Cap reviewers per the council
contract. Prefer fewer load-bearing objections.

## Folding Results

For each material objection:

1. Disposition: `ACCEPT`, `PARTIAL`, `REJECT`, `INVESTIGATE`, or `ACCEPT_RISK`.
2. Apply the smallest plan correction when accepted or partial.
3. Map it to step, risk, verification, or residual IDs.
4. Store the validated council report path in `council.runs[].report_path`.

One council run per plan freeze. After that run, apply the smallest accepted
corrections in the freeze. Do not mint a new thesis id and re-dispatch council
unless the user asked in this turn. `REVISE` after the authorized round makes
the plan `NOT_CONFIDENT` (residuals listed) or `BLOCKED`, not a
self-authorized T-00N loop.

A recorded `BLOCKED`, `REVISE`, or `ESCALATE_TO_FULL` terminal blocks READY
(output-contract READY 15); only a correction pass inside the same authorized
council round can change it. `TRIAGE_PASS` is not implementation approval: it
only means bounded triage found no reason to escalate; still require a
coherent freeze and verification map.
