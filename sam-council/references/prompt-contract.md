# Prompt Contract

## Contents

1. Blind packet
2. Blind reviewer mission
3. Author cross-examination
4. Multi-provider confrontation
5. Verification packet
6. Arbiter / meta-arbiter mission

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
Provider:
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

In multi-provider mode, `Reviewer ID` is namespaced as `{provider}/{seat}` and
`Provider` must match. Reject a response that omits the search performed,
failure mechanism, or disconfirming evidence.

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

## Multi-provider confrontation

Use only in `multi-provider` mode after blind panels return. Send each provider
panel:

1. its own prior material claims;
2. other providers’ material claims only (claim, failure mode, severity,
   evidence IDs, required proof);
3. the frozen thesis ID;
4. the response contract below.

Do not send the desired terminal status, author private diagnosis, or a vote
tally.

```text
Provider:
Thesis ID:
Peer claims reviewed:
For each peer claim:
- Claim ID or summary:
  Stance: ACCEPT | REBUT | CONCEDE
  Evidence IDs:
  Rationale:
Own claim withdrawals:
Provisional stance: APPROVE | APPROVE_WITH_CONDITIONS | REVISE | BLOCK
Strongest remaining disagreement:
```

A `REBUT` without stronger evidence leaves the peer claim open. A `CONCEDE`
requires an exact residual risk or correction recommendation.

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

## Arbiter / meta-arbiter mission

Require the arbiter to weigh evidence quality, failure severity, reversibility,
and proof of closure. Forbid majority counting. Require an explanation for any
severity downgrade or unsupported classification. Preserve a supported
minority objection until evidence closes it.

In multi-provider mode, the `meta-arbiter` must additionally:

- compare provider positions claim-by-claim;
- state which provider claims survived confrontation and why;
- forbid “two of three providers agreed” as a decision basis;
- prefer safer residual risk when evidence quality is equal;
- name any unresolved cross-provider disagreement that blocks approval.
