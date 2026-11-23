---
name: sam-browse
description: "Read or screenshot a web page with the cheapest engine that works: plain HTTP, then a chromeless DOM engine, then a chromeless renderer, and only then Chromium. Use when a task needs web content, a DOM assertion, or a visual capture and browser CPU is scarce; not for full end-to-end suites, which belong in CI."
---

# Sam Browse

Browser work is usually the most expensive thing an agent does: a Chromium renderer sits at 20–40% of a core per tab, video recording adds an ffmpeg per test, and idle browsers stay resident. This skill keeps the same evidence quality with a fraction of that cost by picking the cheapest engine that can actually answer the question.

## Decide what the task really needs

Answer one question before opening anything: is this **data**, **DOM**, or **pixels**?

| Need | Tier | Cost |
|---|---|---|
| API, JSON, static HTML, server-rendered page | plain HTTP fetch | near zero |
| Content that appears only after page JavaScript, simple clicks, form fills | chromeless DOM engine (Lightpanda) | low, no GPU, no Chrome |
| Rendered layout, CSS gradients, a screenshot, before/after | chromeless renderer (Kitesurf) | moderate, no Chrome process tree |
| Pixel-faithful capture, file download, video, WebGL, device emulation, engine-specific bug | Chromium | highest |

Never start at the bottom of that table. Every step down must have a reason you can state: "tier 1 returned 200 but the list is empty without JS", "the SPA renders nothing without a DOM engine", "the screenshot needs real font metrics".

## Reference implementation

`pstech-browse` implements the ladder and is the intended command surface:

```
pstech-browse get URL [--json] [--out FILE]     # tier 1
pstech-browse dom URL [--selector CSS]          # tier 2, HTML after JS
pstech-browse text URL                          # tier 2, markdown
pstech-browse shot URL OUT.png [--engine kitesurf|chromium] [--width N] [--full-page]
pstech-browse doctor                            # which tiers are installed
pstech-browse stop                              # stop the warm renderer container
```

If the tool is absent, use its tiers directly: `curl` with a normal User-Agent (Cloudflare rejects the default Python urllib agent), `lightpanda fetch --dump html URL`, and Playwright's `chromium.connectOverCDP` against a Kitesurf container (`ghcr.io/cloudflare/kitesurf`, port 8787, CDP at `/devtools/browser`).

## Limits measured on the reference host

- One Kitesurf screenshot: about 370–440 MB RSS, 55–115% CPU after warm-up, one short spike near 300% while the WASM compiles.
- One Chromium screenshot: about 1.1 GB RSS, 120% CPU, plus an ffmpeg per recorded video.
- Kitesurf costs the image start (roughly 15 s of WASM compile) on a cold container, so keep it warm across a batch and stop it when the batch ends.
- Both engines were visually faithful on a marketing page, an app login screen, and a gradient-heavy SPA login. Small sub-pixel spacing differences exist; do not use the chromeless renderer for pixel-diff approval.

So the chromeless renderer buys memory and process hygiene, not raw CPU per page. The large savings come from never needing pixels for most tasks, from capping concurrent renders, and from removing video recording.

## Rules that keep it honest

- Cap concurrent renders with a lock or slot file (reference: one chromeless renderer, two Chromium). Wait for a slot instead of opening another browser.
- Full end-to-end suites belong in CI, not on a shared agent host. Read the CI result instead of re-running the suite locally.
- Leave video off by default; keep traces on failure so a red test still has a post-mortem. Trace with `on-first-retry` only when retries are enabled.
- Say which engine produced the evidence (`fetch`, `dom`, `chromeless-render`, `chromium`) and why the cheaper tier was insufficient. A screenshot from a chromeless renderer is not the same evidence as one from the user's browser.
- The chromeless renderer is not a hardened sandbox and has no authentication: open only pages you control or trust, bind it to loopback, never expose its port. Use Workers-hosted rendering only when you need isolation for untrusted pages, and treat that as a separate decision with its own cost.

## Failure that must not be hidden

If the cheap tier returns an empty page, a login wall, or a challenge page, say so and escalate — do not report "no results". If the renderer fails, report the engine, URL, and error, then decide whether Chromium is genuinely required.
