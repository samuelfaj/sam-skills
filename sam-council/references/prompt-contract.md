# Prompt Contract

## Contents

1. Packet budget
2. Blind reviewer mission
3. Author cross-examination
4. Verification
5. Multi-provider confrontation

## Packet budget

Send one frozen relevant-only core containing:

1. charter, profile, topology, and thesis ID;
2. exact concise thesis;
3. indexed evidence with precise locators;
4. assumption ledger;
5. exact task-local excerpts, diffs, or receipts needed for the lens;
6. response contract and reviewer-specific mission.

Exclude unrelated files, full repository dumps, peer reviews, desired verdict,
expected defects, private reasoning, and duplicated narrative. Link to local
artifacts when the worker can read them instead of copying their full contents.

Each reviewer may return at most 3 material objections and 1,000 words. Put the
most severe, best-supported mechanisms first. Stop after the cap; do not pad.

## Blind reviewer mission

Use this mission with the assigned lens:

> Try to falsify this system-development thesis within your assigned lens.
> Find at most three concrete, load-bearing failure mechanisms. Use the supplied
> evidence and name the proof that would settle uncertainty. Return
> `NO_MATERIAL_OBJECTION` when none exists. Stay under 1,000 words.

Require:

```text
Reviewer ID:
Provider:
Thesis ID:
Search performed:
Verdict: OBJECTIONS | NO_MATERIAL_OBJECTION | BLOCKED
Objections: (0-3)
- Claim:
  Failure mode:
  Severity: BLOCKER | HIGH | MEDIUM | LOW | UNSUPPORTED
  Confidence: 0-100
  Premise IDs:
  Evidence IDs:
  Evidence needed:
  Smallest correction:
Disconfirming evidence considered:
Residual uncertainty:
```

Provider is the runtime-supplied slug. In multi-provider mode, namespace the
reviewer as `{provider}/{seat}`. Reject responses that exceed 3 objections,
omit the search/failure mechanism/disconfirming evidence, or violate blindness.

## Author cross-examination

Give the author normalized objections without vote counts. Require exactly one
response per objection:

```text
Objection ID:
Disposition: ACCEPT | PARTIAL | REJECT | INVESTIGATE | ACCEPT_RISK
Rationale:
Evidence IDs:
Exact thesis change:
Validation or experiment:
Residual risk:
Decision-owner action:
```

A rejection without stronger evidence stays open. An investigation names a
method, owner, threshold, and gate. Never accept a blocker. Never accept a high
on the user's behalf.

## Verification

Give fresh verifiers only the prior/revised thesis, material objections, author
responses, evidence, and traceability map. Do not send the desired status.

Require:

```text
Verifier ID:
Revised thesis ID:
Objection checks:
- Objection ID:
  Verdict: CLOSED | STILL_OPEN | CONDITION_VALIDATED
  Evidence IDs:
  Rationale:
New risks: (0-3)
- Claim:
  Failure mode:
  Suggested severity:
  Evidence IDs or evidence needed:
Complexity delta:
Problem displacement check:
Final verdict: PASS | REVISE | BLOCKED
```

The `triage-arbiter` combines closure, displacement, and escalation checks but
cannot approve. Full closure/system verifiers use medium effort; the arbiter or
meta-arbiter alone uses high effort. Convert each material new risk into an
objection before any explicitly authorized later round.

## Multi-provider confrontation

Use only for explicit multi-provider `full` runs. Send each provider its prior
material claims plus peers' material claims, never a vote tally or desired
result. Require `ACCEPT`, `REBUT`, or `CONCEDE` with evidence IDs. A rebuttal
without stronger evidence leaves the claim open. The meta-arbiter compares
evidence quality, severity, reversibility, and proof of closure; provider count
has no decision weight.
