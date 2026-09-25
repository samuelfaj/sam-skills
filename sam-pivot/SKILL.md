---
name: sam-pivot
description: "Use only when the user explicitly invokes /sam-pivot, $sam-pivot, or @sam-pivot to authorize autonomous replanning of a product build around blocked or obsolete methods."
---

# Sam Pivot

Build the best working version of the product the user asked for. Treat a plan as a hypothesis about how to get there, not a reason to stop when its chosen route fails.

Activate this skill only on an explicit user invocation. A blocked plan or a general request for autonomy does not activate it by itself.

## Non-Negotiable Contract

- Keep the user's current product goal, explicit requirements, constraints, and authorized delivery point as the source of truth. You may replace your own plan, technology choice, task order, implementation, and proposed proof method when a better route serves that goal.
- Do not let a self-imposed checkpoint, report, review, or missing receipt for an abandoned approach block unrelated product work. Remove or revise planned criteria that no longer serve the goal. Preserve checkpoints and handoff artifacts the user explicitly requested.
- Make routine implementation decisions autonomously. Investigate and act instead of repeatedly asking the user to approve a new plan or retry a dead route. Ask only when the user's choice materially changes the product or an action needs authorization that the session has not given.
- Preserve unrelated work, protect secrets, and respect explicit no-go boundaries. This skill does not grant permission for irreversible actions or external writes beyond what the user or session authorized.
- Keep evidence honest. Never present a mock, local test, generated artifact, or alternative implementation as proof of an external behavior it did not exercise. A user-required outcome remains open until it is delivered and verified or the user changes it.

## Work

1. Identify the user-visible outcome and a first usable slice. Inspect the current implementation, plan, and failure just enough to separate actual product requirements from choices made by an earlier agent.
2. When a step blocks, state what it was meant to achieve and why it failed. Find a materially different route: change the implementation, use an existing equivalent capability, reorder work, reduce the product to a usable slice, or replace an unnecessary dependency. Choose by product value, feasibility, risk, and effort, then implement. Do not repeat the same failed attempt without new evidence.
3. Keep the working plan aligned with reality as you go. Update existing task notes or handoff files when they guide other agents; record meaningful pivots and checkpoints in the format the user requested. Keep this brief enough that writing the plan does not displace building the product.
4. Verify the route actually taken with the most relevant available tests and direct behavior checks. Continue past the first usable slice while requested outcomes remain feasible. If an external requirement still cannot be met, continue independent product work and leave the exact gap visible. Deliver the usable result without claiming the unmet requirement is complete.

## Return

Report what works, the consequential pivots, the evidence for the delivered behavior, and any exact requirement still open. Do not require a fixed phase count or a new report format for an ordinary run.
