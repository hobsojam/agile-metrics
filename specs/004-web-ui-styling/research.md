# Research: Web UI Visual Styling

## 1. CSS/component library choice

**Decision**: Tailwind CSS v4 (`tailwindcss` + `@tailwindcss/vite`), utility-classes only — no
headless/behavioral component library (e.g. Radix, shadcn/ui) layered on top.

**Rationale**: The page is one form and one results view with no custom interactive widgets
(no modals, dropdowns, date pickers, tooltips) — native `<input>`/`<button>`/`<form>` elements
already cover every interaction, so there is no behavior gap for a component library to fill.
What's missing is purely visual: layout, spacing, type, color. Tailwind's utility classes solve
exactly that, ship no JS runtime, and compose directly onto the existing semantic HTML (`App.tsx`
already uses proper `<label>`/`<input>`/`role="alert"`/`<output>` — Tailwind classes layer on
top without requiring new markup or component wrappers). This keeps the change surface small,
consistent with constitution Principle V (YAGNI) and the existing "no state-management/
data-fetching library without demonstrated need" stance — Tailwind is neither of those, but the
same minimalism applies to styling tools.

**Alternatives considered**:
- **Chakra UI / Mantine / MUI** (full component frameworks): rejected. These ship pre-built
  interactive components (modals, menus, form controls with their own state) this page doesn't
  need, add real runtime JS weight, and would mean rewriting `App.tsx`'s plain `<input>`
  elements as library-specific components for no functional gain — pure churn relative to the
  presentation-only goal in FR-007.
- **Bootstrap**: rejected. Pre-built component classes (cards, buttons, forms) assume Bootstrap's
  own visual language and grid system; retrofitting it onto an existing React app is more
  friction than Tailwind's utility-first approach, and its design defaults read as dated next to
  a "modern, professional" target (spec Assumptions).
- **CSS Modules / hand-rolled CSS with a design-system file**: rejected per the spec's own
  Assumptions — the stakeholder already decided against continuing with hand-rolled CSS in favor
  of a library.
- **styled-components / Emotion** (CSS-in-JS): rejected. Adds a runtime dependency and a
  different authoring model (JS template literals) for no benefit over Tailwind's zero-runtime
  utility classes, given there's no dynamic-at-runtime theming requirement.

## 2. Vite integration approach

**Decision**: Tailwind v4's official `@tailwindcss/vite` plugin, registered in
`frontend/vite.config.ts` alongside the existing `@vitejs/plugin-react` plugin. The stylesheet
entry point is a new `frontend/src/index.css` containing a single `@import "tailwindcss";`,
imported once from `frontend/src/main.tsx`.

**Rationale**: Tailwind v4 removed the PostCSS-config-file approach that earlier versions
required (`tailwind.config.js`, `postcss.config.js`) in favor of a first-class Vite plugin and
CSS-native configuration (the `@theme` directive, see below) — fewer config files, and it
composes with the existing Vite+React setup from 003 without touching `postcss.config.js` (none
exists today) or introducing one.

**Alternatives considered**:
- **PostCSS + `tailwind.config.js` (v3-style)**: rejected — this is the older integration path
  Tailwind v4 itself deprecated in favor of the Vite plugin; no reason to take on the extra
  config file and build step when v4's first-party Vite integration is simpler and current.
- **Tailwind CLI watch process** (separate from Vite's own dev server): rejected — would mean
  running two processes for local dev instead of one, with no benefit over the Vite plugin doing
  it inline.

## 3. Design-token consistency approach (FR-009)

**Decision**: Define a small, explicit set of design tokens (a limited color palette, spacing
scale, and type scale) once, via Tailwind v4's CSS-native `@theme` block in `index.css`, and
reuse only those tokens' utility classes throughout `App.tsx` — documented in
`contracts/design-tokens.md` as the concrete vocabulary every styled element must draw from.

**Rationale**: FR-009 requires the page read as one cohesive design, not independently-styled
pieces. Tailwind's large default palette/spacing scale makes it easy to accidentally use a
slightly different shade of gray or a slightly different padding value in two places. Committing
to a small named subset up front (e.g. exactly one primary color, one neutral scale, one error
color, a handful of spacing steps) and writing it down as a contract gives implementation tasks
a concrete, checkable target instead of "looks fine to me."

**Alternatives considered**:
- **No explicit token subset — use Tailwind's full default scale ad hoc**: rejected. Nothing
  stops accidental drift (e.g. `gray-100` here, `gray-200` there) without an explicit, written
  reference to check against, which is exactly the "patchwork" failure mode FR-009 calls out.

## 4. Accessibility baseline preservation (Assumptions)

**Decision**: No new accessibility work is required; the restyle must not remove or alter the
semantics already present in `App.tsx` from 003/the Sonar-fix pass (`<label htmlFor>` associations,
the `<output>` loading element, `role="alert"` on the error message). Verification is a manual
check (does every input still have an associated visible label; is the error still announced as
an alert) rather than a new automated axe/a11y test suite, since none exists today and adding
one is out of scope per the spec's Assumptions.

**Rationale**: Matches the spec's explicit assumption that this feature holds accessibility to
"at least the same bar" already established, not a goal of expanding it. Tailwind utility
classes affect visual presentation only, not DOM structure or ARIA attributes, so there is no
mechanical reason restyling would regress these unless markup is restructured — which FR-001
through FR-006 don't require.

**Alternatives considered**:
- **Add an automated accessibility test (e.g. `jest-axe`/`vitest-axe`)**: rejected for this
  feature — introducing a new test tool/dependency is a larger scope increase than "don't
  regress the existing bar" calls for, and isn't something the spec asked for (Assumptions).
  Worth a future issue, not this feature.
