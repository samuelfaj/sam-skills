# Council Provider Matrix

## Contents

- [Modes](#modes)
- [Activation](#activation)
- [Runtime bindings](#runtime-bindings)
- [Independence](#independence)
- [Confrontation](#confrontation)
- [Fallbacks](#fallbacks)

## Modes

- `single-host` (default): one active controller host runs all seats and
  verifiers as distinct subagents or host-native workers.
- `multi-provider`: **explicit opt-in only.** Two or more of `codex`,
  `claude-code`, and `grok` each run a full blind specialist panel on the same
  frozen thesis. Results are confronted until an evidence-weighted decision
  remains.

## Activation

**Default every run to `single-host`.** Enter `multi-provider` only when the
user clearly and explicitly requests a multi-host or multi-model council.

Clear requests (activate multi-provider):

- “use sam-council with grok, claude and codex”
- “council across codex + claude-code”
- “multi-provider council: grok and opus/claude”
- “run independent panels on grok and codex and confront them”

Not enough (stay single-host):

- running under Claude/Grok/Codex with no multi-host ask;
- naming one provider only;
- vague “second opinion”, “be thorough”, or “use the best models”;
- incidental product/model names inside the problem statement;
- ambiguous wording — do not upsell or switch modes to multi-provider.

Aliases when multi-provider is clearly requested:

| User phrase | Provider key |
| --- | --- |
| codex, openai codex | `codex` |
| claude, claude code, fable host | `claude-code` |
| grok, grok build, xai | `grok` |

If only one provider is named, stay in `single-host` on that provider. If none
are named, use the active controller host as `single-host`.

## Runtime bindings

Blind seats and verifiers use the host’s strongest practical reasoning tier
(read-only). Do not ask the user which model to pick.

| Provider | Model | Effort | Notes |
| --- | --- | --- | --- |
| `codex` | `gpt-5.6-sol` | `high` | read-only / sandbox; escalate rare cases to `xhigh` |
| `claude-code` | `opus` | `high` | plan / read-only tools; rare escalate `xhigh` |
| `grok` | `grok-4.5` | `high` | read-only contract in prompt; no write tools |

Optional pure-advisor second opinion (not a seat substitute):

| Provider | Advisor model | Effort |
| --- | --- | --- |
| `codex` | `gpt-5.6-sol` | `xhigh` or `max` |
| `claude-code` | `fable` if available, else `opus` | `high` |
| `grok` | `grok-4.5` | `high` |

## Independence

In multi-provider mode:

1. Freeze one charter and thesis packet for every provider.
2. Run all six required seats **per provider** under namespaced IDs:
   `{provider}/{seat}` (example: `codex/logic`, `grok/adversarial`).
3. Keep first-pass reviews blind across seats **and** providers. No provider may
   see another provider’s blind responses before its own terminal results.
4. Preserve raw terminal responses per provider in scratch space.
5. Conditional seats, when selected, run on every selected provider or record a
   provider-specific `NOT_APPLICABLE` with reason.

Fresh verification after revision:

- shared `closure-verifier` and `system-verifier` that inspect the combined
  ledger;
- `meta-arbiter` that must explicitly compare provider claims and may not use
  majority vote.

Per-provider verifier IDs (`codex/closure-verifier`, …) are allowed as extras
but never replace `meta-arbiter`.

## Confrontation

After blind panels and author synthesis:

1. Build one `provider_position` per provider: material objections owned or
   supported by that provider, preferred correction, and provisional stance
   (`APPROVE`, `APPROVE_WITH_CONDITIONS`, `REVISE`, `BLOCK`).
2. Run a confrontation pass: each provider panel receives only the other
   providers’ material claims (not desired verdict) and must
   `ACCEPT`, `REBUT`, or `CONCEDE` with evidence IDs.
3. Merge surviving claims by failure mechanism. Keep minority blockers when
   evidence supports them.
4. Revise the thesis toward the **strongest evidence**, not the most providers.
5. Stop when the meta-arbiter finds no supported provider disagreement on
   blockers/highs, or after the normal three-round council bound.

Never declare a winner because two of three providers agreed. Prefer the claim
with better evidence, clearer failure mode, and safer residual risk.

## Fallbacks

- If a named provider CLI/auth/model is unavailable, record the exact blocker
  for that provider. Continue other providers when ≥2 remain runnable.
- If fewer than two providers can run, downgrade to `single-host` on the
  surviving provider **or** return `BLOCKED` when multi-provider was mandatory.
- Never invent a provider’s review from the controller context.
