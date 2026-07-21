# Prompt Contract

## Contents

1. Blind packet
2. Blind reviewer mission
3. Author cross-examination
4. Verification packet
5. Arbiter mission

## Blind packet

Send each reviewer only:

1. frozen charter and thesis ID;
2. exact thesis text;
3. evidence index and raw task-local artifacts;
4. assumption ledger;
5. one assigned reviewer lens;
6. the response contract below.

Do not send peer reviews, desired verdict, likely defect, planned correction,
private author reasoning, or a prior answer from the same context.

## Blind reviewer mission

Use this mission with role-specific questions appended:

> Try to falsify this system-development thesis within your assigned lens.
> Search for a concrete failure mechanism and the evidence that supports or
> would disprove it. Do not invent a criticism quota. Do not infer peer views.
> Return `NO_MATERIAL_OBJECTION` if the search finds none.

Require this response shape:

```text
Reviewer ID:
Thesis ID:
Search performed:
Verdict: OBJECTIONS | NO_MATERIAL_OBJECTION | BLOCKED
Objections:
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

Reject a response that omits the search performed, failure mechanism, or
disconfirming evidence.

## Author cross-examination

Give the author normalized objections without vote counts. Require one response
per objection:

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

A rejection without stronger evidence remains open. An investigation must name
method, owner, pass threshold, and execution gate. An accepted risk is not a
resolved risk.

## Verification packet

Send fresh verifiers the prior and revised thesis IDs, every material objection,
author responses, evidence, and traceability map. Do not send the desired final
status or blind reviewers' vote-like summaries.

Require this response shape:

```text
Verifier ID:
Revised thesis ID:
Objection checks:
- Objection ID:
  Verdict: CLOSED | STILL_OPEN | CONDITION_VALIDATED
  Evidence IDs:
  Rationale:
New risks:
- Claim:
  Failure mode:
  Suggested severity:
  Evidence IDs or evidence needed:
Complexity delta:
Problem displacement check:
Final verdict: PASS | REVISE | BLOCKED
```

Convert every material new risk into a new objection before another round.

## Arbiter mission

Require the arbiter to weigh evidence quality, failure severity, reversibility,
and proof of closure. Forbid majority counting. Require an explanation for any
severity downgrade or unsupported classification. Preserve a supported
minority objection until evidence closes it.
