---
name: sam-design
description: "Run every installed design skill from emilkowalski/skills and ui-ux-pro-max on any frontend/UI work, with a per-skill coverage ledger and browser proof. Use for UI components, pages, styling, layout, motion, design systems, or mobile/web UI; called by sam-task for frontend work; not for backend-only changes."
---

# Sam Design

Orchestrate 21 upstream design skills on every frontend/UI task. The upstream skills stay installed in the host skill dir; this skill never copies their content. The manifest in [references/design-skills.md](references/design-skills.md) records each skill's repo, pinned commit, source path, install dir, aliases, phase, and purpose.

## Non-Negotiable Contract

- Consult all 21 skills on every run. No size exemption: a one-line CSS change still gets a full ledger.
- For each skill, read its installed `SKILL.md`, then either apply it (state what it changed or decided, with evidence) or mark it not-applicable with a one-line reason tied to this task. Never skip silently.
- Mark a skill `missing` when it is not installed. Never mark a missing skill `applied`.
- Return the coverage ledger with all 21 rows (see Output).

## Setup

1. Run `python3 scripts/check_design_skills.py` (add `--root DIR` for each extra skill dir, `--json` for machine output). It prints `installed <path>` or `missing` per skill; exit 0 means all installed.
2. If any are missing, tell the user which ones and propose `python3 scripts/install_design_skills.py --dest <host skill dir>` (`--dry-run` first; `--force` only to overwrite a differing dir). Install only with user approval. Without approval, continue with the installed skills and mark the rest `missing`.
3. Use each path the check script reports; some hosts list `design` as `ckm-design`.

## Phases

Run in order. Within a phase, consult every skill listed, then apply the relevant ones.

1. **Direction**
   - `ui-ux-pro-max`: generate the design system from the installed skill dir: `python3 <ui-ux-pro-max dir>/scripts/search.py "<product type> <industry> <keywords>" --design-system -p "<project>"`. Use `--domain` or `--stack` searches for specifics.
   - `design-system`, `ui-styling`, `brand`, `apple-design`, `emil-design-eng`, `pick-ui-library`, `animation-vocabulary`.
   - Output: a short direction note (tokens, type, color, motion intent, libraries) that reuses the repo's existing system first.
2. **Build**
   - `animate` for web motion, or `animate-expo` for React Native/Expo.
   - `mobile-native` for touch/mobile web; `prototype` when several visual directions help or the user asks; `ask-sonner` when toasts exist; `write-swift` for Swift UI code.
   - `design`, `banner-design`, `slides` when those assets are in scope.
3. **Review**
   - `find-animation-opportunities`, `review-animations`, `improve-animations`, `break-ui`, then the `ui-ux-pro-max` pre-delivery checklist (its `references/pro-rules.md`).

## Conflict precedence

Highest first:

1. The user's request.
2. The repository's existing design system, tokens, and components.
3. Accessibility: contrast, focus, reduced motion.
4. Platform guidance (`apple-design`).
5. Emil motion and polish rules.
6. `ui-ux-pro-max` style suggestions.

Never add a UI library when the repo already has an equivalent; `pick-ui-library` advice yields to it. Record each override in the ledger.

## Verify

- Run the UI in a real browser (simulator or device for native) and exercise the changed interaction end to end.
- Check desktop and mobile viewports, keyboard focus, and reduced-motion.
- Run `break-ui` worst-case data on every changed data-driven view.
- Report what was observed. If no browser or simulator is available, say so and mark the affected rows `unverified`.

## Output

Return one table with 21 rows, one per skill:

| Skill | Phase | Status (`applied` / `not-applicable` / `missing`) | What changed or decided / reason | Evidence |
|---|---|---|---|---|

Follow it with the precedence overrides made, the browser proof (viewports, interaction, worst-case data), and anything unverified.

## References

- [references/design-skills.md](references/design-skills.md): manifest of the 21 skills.
- `scripts/check_design_skills.py`: detect installed and missing skills.
- `scripts/install_design_skills.py`: install pinned upstream skills into a host skill dir.
- `scripts/test_design_harness.py`: offline tests for the manifest and scripts.
