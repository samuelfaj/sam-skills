# Design Skill Manifest

Upstream skills that sam-design consults on every frontend/UI run. Content is not vendored; each skill is installed from the pinned commit by `scripts/install_design_skills.py` and detected by `scripts/check_design_skills.py`. Both scripts parse the tables below.

## Repositories

| Key | URL | Commit | Skills root | License |
|---|---|---|---|---|
| `emil` | https://github.com/emilkowalski/skills | `e8a175de22ae1e49370fc144c1f3bb9aeedf988d` | `skills` | MIT |
| `uupm` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill | `477bcb28c9812b385cb51a4605ddf30d7b2266e2` | `.claude/skills` | MIT |

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
