# Design Skill Manifest

Mandatory upstream skills consulted on every frontend/UI run, plus optional skills selected by task fit. Content is not vendored; each skill is installed from the pinned commit by `scripts/install_design_skills.py` and detected by `scripts/check_design_skills.py`. Both scripts parse the tables below. The original skills remain mandatory to consult; optional skills are selected only when their applicability matches the task.

## Repositories

| Key | URL | Commit | Skills root | License |
|---|---|---|---|---|
| `emil` | https://github.com/emilkowalski/skills | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | `skills` | MIT |
| `uupm` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | `.claude/skills` | MIT |
| `taste` | https://github.com/madebymustafa/design-taste | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | `skills` | MIT |
| `better` | https://github.com/marvkr/better-design | `e146625f3041ef8089a2013587435fc763dc3b15` | `skills` | MIT |

## Skills

`Install dir` is the directory name under a host skill dir. `Aliases` are other frontmatter names or directory names the check script also accepts. Source path = repo skills root + `/<install dir>`.

| Skill | Repo | Source path | Install dir | Aliases | Commit | License | Phase | Purpose | Applies when |
|---|---|---|---|---|---|---|---|---|---|
| `ui-ux-pro-max` | `uupm` | `.claude/skills/ui-ux-pro-max` | `ui-ux-pro-max` | - | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT | Direction + Review | Searchable UI/UX data (styles, palettes, fonts, UX rules, stacks) with a design-system generator and pre-delivery checklist. | Any page, component, or layout work; generate the design system first and run the checklist last. |
| `design-system` | `uupm` | `.claude/skills/design-system` | `design-system` | - | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT | Direction | Three-layer design tokens, CSS variables, spacing/type scales, component specs. | Tokens, theming, or component specs are created or changed. |
| `ui-styling` | `uupm` | `.claude/skills/ui-styling` | `ui-styling` | - | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT; Apache-2.0 in LICENSE.txt | Direction | shadcn/ui + Radix + Tailwind styling, themes, dark mode, accessible components, canvas visuals. | The repo uses (or needs) Tailwind/shadcn styling, themes, or accessible primitives. |
| `brand` | `uupm` | `.claude/skills/brand` | `brand` | - | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT | Direction | Brand voice, visual identity, messaging, style guides, consistency checks. | Copy, tone, logo, or brand colors appear in the UI. |
| `apple-design` | `emil` | `skills/apple-design` | `apple-design` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Direction | Apple-style interface principles and fluid physical motion translated for the web. | Gestures, springs, sheets, materials, typography, or reduced motion are involved. |
| `emil-design-eng` | `emil` | `skills/emil-design-eng` | `emil-design-eng` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Direction | Emil Kowalski's UI polish and component design philosophy. | Any UI component or interaction; sets the polish bar. |
| `pick-ui-library` | `emil` | `skills/pick-ui-library` | `pick-ui-library` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Direction | Opinionated library choices for numbers, OTP, charts, command menus, virtualization, drag and drop, toasts, state. | A new UI capability might need a library; defer to the repo's existing equivalent. |
| `animation-vocabulary` | `emil` | `skills/animation-vocabulary` | `animation-vocabulary` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Direction | Glossary mapping vague motion descriptions to exact effect names. | The request or design describes motion loosely; use it to name effects precisely. |
| `animate` | `emil` | `skills/animate` | `animate` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Build | Build web animation by deciding purpose, tool, properties, curve, duration, interruption, and exit. | Web motion, transitions, or micro-interactions are added or changed. |
| `animate-expo` | `emil` | `skills/animate-expo` | `animate-expo` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Build | Build React Native/Expo animation with Reanimated, Gesture Handler, Expo Router, and haptics. | The UI is React Native or Expo and has motion, gestures, or haptics. |
| `mobile-native` | `emil` | `skills/mobile-native` | `mobile-native` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Build | CSS and meta-tag fixes that make a web app feel native on phones (100vh, tap highlight, input zoom, safe areas). | A web UI runs on touch devices, PWA, bottom sheets, or full-screen layouts. |
| `prototype` | `emil` | `skills/prototype` | `prototype` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Build | Build several genuinely different UI versions behind a visual picker. | Multiple visual directions are useful or the user asks for options. |
| `ask-sonner` | `emil` | `skills/ask-sonner` | `ask-sonner` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Build | Sonner toast library setup, toast() calls, theming, and troubleshooting. | Toasts exist or are added in a React UI. |
| `write-swift` | `emil` | `skills/write-swift` | `write-swift` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Build | Modern Swift: value types, Swift 6 concurrency, API design, performance, Swift Testing. | Swift or SwiftUI code is written or reviewed. |
| `design` | `uupm` | `.claude/skills/design` | `design` | ckm:design, ckm-design | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT | Build | Umbrella for brand identity, logos, CIP, banners, icons, slides, and social images. | Logo, icon, social image, or identity assets are in scope. |
| `banner-design` | `uupm` | `.claude/skills/banner-design` | `banner-design` | - | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT | Build | Banner art direction for social, ads, website heroes, and print. | Banners or hero visuals are in scope. |
| `slides` | `uupm` | `.claude/skills/slides` | `slides` | - | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | MIT | Build | Strategic HTML presentations with Chart.js and design tokens. | Slide decks or presentation pages are in scope. |
| `find-animation-opportunities` | `emil` | `skills/find-animation-opportunities` | `find-animation-opportunities` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Review | Read-only search for places that should animate, with exact values; rejects the rest. | Always; run on the changed UI to decide where motion is justified. |
| `review-animations` | `emil` | `skills/review-animations` | `review-animations` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Review | Review motion code against a high craft bar; flags by default. | Any motion was added or changed. |
| `improve-animations` | `emil` | `skills/improve-animations` | `improve-animations` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Review | Audit a codebase's motion and write prioritized plans; read-only. | Motion touched across several files, or the user wants a roadmap. |
| `break-ui` | `emil` | `skills/break-ui` | `break-ui` | - | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | MIT | Review | Stress UI with worst-case data behind a demo toggle and report breakages with fixes. | Any component or screen that renders data. |

Upstream skills `pick-ui-library`, `prototype`, and `review-animations` declare they run only when explicitly invoked; consulting them from sam-design counts as that explicit invocation.

## Optional skills

Select these by task fit, not on every run. Genre packs are alternatives: choose one only when the brief calls for that identity. The installer includes these skills; the checker reports their availability without making them mandatory for every task.

| Skill | Repo | Source path | Install dir | Aliases | Commit | License | Phase | Purpose | Applies when |
|---|---|---|---|---|---|---|---|---|---|
| `brutalist-industrial` | `taste` | `skills/brutalist-industrial` | `brutalist-industrial` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the brutalist-industrial identity; choose instead of other genre packs. |
| `cinematic-motion` | `taste` | `skills/cinematic-motion` | `cinematic-motion` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the cinematic-motion identity; choose instead of other genre packs. |
| `corporate-trust` | `taste` | `skills/corporate-trust` | `corporate-trust` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the corporate-trust identity; choose instead of other genre packs. |
| `dark-tech` | `taste` | `skills/dark-tech` | `dark-tech` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the dark-tech identity; choose instead of other genre packs. |
| `design-taste` | `taste` | `skills/design-taste` | `design-taste` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | New visual direction, landing page, portfolio, redesign, or generic-looking output needs deliberate art direction. |
| `editorial-minimal` | `taste` | `skills/editorial-minimal` | `editorial-minimal` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the editorial-minimal identity; choose instead of other genre packs. |
| `japanese-minimal` | `taste` | `skills/japanese-minimal` | `japanese-minimal` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the japanese-minimal identity; choose instead of other genre packs. |
| `neo-brutalism` | `taste` | `skills/neo-brutalism` | `neo-brutalism` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the neo-brutalism identity; choose instead of other genre packs. |
| `playful-color` | `taste` | `skills/playful-color` | `playful-color` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the playful-color identity; choose instead of other genre packs. |
| `quiet-luxury` | `taste` | `skills/quiet-luxury` | `quiet-luxury` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the quiet-luxury identity; choose instead of other genre packs. |
| `retro-print` | `taste` | `skills/retro-print` | `retro-print` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Visual identity genre pack. | The brief explicitly fits the retro-print identity; choose instead of other genre packs. |
| `taste-accessibility` | `taste` | `skills/taste-accessibility` | `taste-accessibility` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | Accessibility needs specialist checks. |
| `taste-brand-identity` | `taste` | `skills/taste-brand-identity` | `taste-brand-identity` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | Brand identity or logo assets are in scope. |
| `taste-code-craft` | `taste` | `skills/taste-code-craft` | `taste-code-craft` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Build | Contextual design-taste guidance. | UI implementation needs semantic HTML or token-driven CSS guidance. |
| `taste-code-review` | `taste` | `skills/taste-code-review` | `taste-code-review` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Review | Contextual design-taste guidance. | UI code needs a focused review. |
| `taste-color` | `taste` | `skills/taste-color` | `taste-color` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | Palette, contrast, semantic colors, or dark mode changes. |
| `taste-design-review` | `taste` | `skills/taste-design-review` | `taste-design-review` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Review | Contextual design-taste guidance. | Visual or usability audit is requested or needed. |
| `taste-design-system` | `taste` | `skills/taste-design-system` | `taste-design-system` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | Tokens or component standards are created or audited. |
| `taste-gsap` | `taste` | `skills/taste-gsap` | `taste-gsap` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Build | Contextual design-taste guidance. | GSAP is already used or explicitly justified by the requested motion. |
| `taste-landing-page` | `taste` | `skills/taste-landing-page` | `taste-landing-page` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | Landing-page structure, conversion, proof, or calls to action are in scope. |
| `taste-motion` | `taste` | `skills/taste-motion` | `taste-motion` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Build | Contextual design-taste guidance. | Motion needs additional choreography or reduced-motion guidance. |
| `taste-typography` | `taste` | `skills/taste-typography` | `taste-typography` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | Type hierarchy, font pairing, or legibility needs work. |
| `taste-ux-copy` | `taste` | `skills/taste-ux-copy` | `taste-ux-copy` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Direction | Contextual design-taste guidance. | Interface text, error messages, empty states, or action labels change. |
| `taste-web-performance` | `taste` | `skills/taste-web-performance` | `taste-web-performance` | - | `c4a6bff0871eb4b15371b0e7d2751628b0ed4608` | MIT | Review | Contextual design-taste guidance. | Rendering, fonts, images, or Core Web Vitals need attention. |
| `better-design` | `better` | `skills/better-design` | `better-design` | - | `e146625f3041ef8089a2013587435fc763dc3b15` | MIT | Direction | Better Design MCP-backed interface guidance and review. | Specialist design guidance or review is useful and Better Design MCP tools are connected; otherwise report the connection blocker and continue the baseline workflow. |
