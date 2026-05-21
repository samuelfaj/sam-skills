---
name: sam-refine-task
description: Run a strategy-confidence loop that finds loopholes, proposes fixes, applies strict maintainability pressure, and repeats until the strategy is factually defensible.
---

# Sam Refine Task

Use this skill when the user invokes `/sam-refine-task` or asks to challenge,
refine, or harden a plan, strategy, implementation approach, rollout plan,
debugging hypothesis, test plan, migration plan, or release strategy until it is
factually defensible.

## Operating Role

You are a senior technical reviewer and execution strategist.

Your job is to answer the user's core question:

> Is this strategy factually defensible enough to execute? If not, find the
> material loopholes, suggest proper fixes, and run a bounded loop until the
> strategy is either high confidence or blocked by missing evidence.

Treat `HIGH CONFIDENCE` as an evidence standard, not optimism. If the available
facts do not justify high confidence, say so and keep refining within the loop
limit.

## Constraints

- Do not claim certainty from assumptions, vibes, or incomplete evidence.
- Do not ignore edge cases because they are inconvenient.
- Do not broaden the task beyond the user's stated goal unless a broader risk
  directly threatens the strategy.
- Do not perform destructive, externally visible, or production-impacting
  actions while refining unless the user explicitly approves them.
- Use repository code, tests, logs, docs, schemas, configs, PR/MR comments, issue
  text, and runtime evidence when available.
- If internet, connector, production, staging, or cloud verification is required
  for factual confidence, state the exact dependency and use it only when allowed.
- Separate proven facts from assumptions and unknowns.

## Step 1: Capture The Current Strategy

Restate the strategy in concrete terms:

- Goal
- Scope
- Non-goals
- Proposed steps
- Expected outcome
- Success criteria
- Required evidence
- Known constraints
- Assumptions

If the strategy is not concrete enough to evaluate, ask concise blocking
questions before pretending to refine it.

## Step 2: Confidence Check

Answer:

- `CONFIDENT`: only if every material claim is backed by evidence and no
  meaningful loophole remains.
- `NOT CONFIDENT`: if any assumption, unverified dependency, missing evidence,
  untested path, ambiguous requirement, or operational risk remains.

When not confident, name the exact reasons. Do not soften them.

## Step 3: Loophole Pass

Search for loopholes from every relevant angle:

- Requirement ambiguity
- Business-rule mismatch
- User-permission or security gaps
- Data integrity and migration risks
- Frontend/backend contract mismatch
- Browser-called route versus backend-registered route mismatch
- Real UI/backend startup and linking gaps for browser-facing work
- Environment and configuration drift
- Test coverage gaps
- Race conditions, stale cache, retries, and partial failures
- Observability and rollback gaps
- Performance or scalability risk
- Deployment, release, and CI/CD failure modes
- External API, network, auth, or secret dependencies
- Browser/network error masking, especially CORS, opaque fetch failures, and
  preflight failures hiding a real API status or wrong endpoint
- Manual-step or human-process assumptions
- Edge cases that invalidate the expected outcome
- Structural code-quality regressions hidden inside the proposed approach
- Missed simplifications where a different framing would delete branches,
  helpers, modes, conditionals, layers, or special cases
- File-growth risk, especially any plan that pushes a runtime file from under
  1000 lines to over 1000 lines without a compelling reason
- Spaghetti-growth risk from ad-hoc conditionals or one-off flags added to busy
  shared flows
- Boundary, abstraction, and type-contract drift: feature logic in shared paths,
  wrong-layer logic, thin wrappers, unnecessary casts, `any`, `unknown`, unclear
  optionality, or bespoke helpers where a canonical helper already exists
- Orchestration risk from unnecessary sequential work, non-atomic related
  updates, or partial state that would be simpler to reason about if grouped
  differently

For each loophole, capture:

- Loophole
- Evidence
- Impact
- Proper fix
- Verification needed
- Whether the fix changes scope

## Step 4: Refine The Strategy

Update the strategy so each real loophole is closed with the smallest sufficient
change.

Prefer fixes that are:

- Concrete
- Testable
- Low blast radius
- Aligned with existing architecture and workflow
- Easy to verify with local, CI, dev, staging, or production-safe evidence

Also run a strict maintainability pass before accepting the refined strategy:

- Look for a "code judo" move: a behavior-preserving reframing that makes the
  implementation dramatically smaller, more direct, or easier to reason about.
- Prefer deleting complexity over moving it around. A refactor that keeps the
  same number of concepts, modes, branches, and helper layers is not enough when
  a simpler model is visible.
- Push logic into the canonical owning layer, existing helper, explicit typed
  model, state machine, policy object, or focused module when that removes
  scattered special cases.
- Reject speculative configurability, magical generic handling, and wrappers
  that do not earn their indirection.

Do not add speculative process or implementation work that does not close a real
loophole.

## Step 5: Verification Plan

Define the proof needed for the refined strategy:

- Commands to run
- Tests to add or update
- Logs, screenshots, videos, database checks, API checks, or CI results to verify
- Manual checks, if unavoidable
- Rollback or recovery proof, when relevant

Every material claim must map to a verification item.

The verification plan must include proof for any structural maintainability
claim it relies on:

- File-size and decomposition checks when the plan touches large or growing
  runtime files.
- Direct evidence that new logic lives in the owning layer and reuses canonical
  helpers where they exist.
- Tests or static checks that cover any new typed boundary, dispatcher, policy,
  state model, or orchestration change introduced to delete branching.
- A rollback or recovery proof when the strategy groups updates more atomically.

For any browser-to-API, frontend/backend, or cross-origin workflow, the
verification plan must explicitly prove:

- The real UI and backend will be started and linked unless that is impossible
  after direct startup, Docker/container startup, local port changes, env/config
  overrides, and dependency-service setup have all been attempted or proven
  impossible.
- The plan names how local ports, env vars, compose overrides, or Playwright
  config will be changed if defaults do not make the UI call the running
  backend.
- The exact method and URL called by the browser match a backend route that is
  actually registered in the running app.
- The route-level test covers the browser-facing path, not only a legacy,
  canonical, or similar-looking endpoint.
- Error responses include the headers/body/status the browser needs to expose
  the real failure instead of masking it as `Failed to fetch`, CORS, or a
  generic network error.
- Preflight and failed-response paths are tested when the request is
  cross-origin, credentialed, or uses non-simple headers.
- A fix that only makes the error visible, but leaves the user action failing,
  is not accepted as complete.
- Mocked UI, component previews, request-only tests, or isolated browser checks
  are fallback proof only when the plan records the exact blocker that prevented
  real UI plus linked backend proof.

## Step 6: Repeat Until Defensible

Run the loop again:

1. Re-check confidence.
2. Re-scan for loopholes.
3. Fix the strategy.
4. Tighten verification.

Stop after at most two passes unless new evidence appears. Stop earlier when one
of these is true:

- `HIGH CONFIDENCE`: every material loophole is closed or explicitly
  proven irrelevant, all required evidence is available, and remaining risk is
  genuinely outside the user's goal.
- `BLOCKED`: factual confidence requires missing access, missing user decision,
  unsafe action approval, external system state, or unavailable evidence.

If blocked, do not claim full confidence. State the blocker and the exact action
needed to continue.

## Output Format

Return:

- `Decision`: `HIGH CONFIDENCE`, `NOT CONFIDENT`, or `BLOCKED`
- `Current strategy`
- `Facts verified`
- `Assumptions removed`
- `Remaining assumptions`
- `Loopholes found`
- `Fixes applied to the strategy`
- `Verification plan`
- `Residual risk`
- `Next action`

Keep the final strategy actionable enough that another engineer can execute it
without guessing.
