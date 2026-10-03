# Implementation Plan: Web UI Visual Styling

**Branch**: `004-web-ui-styling` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-web-ui-styling/spec.md`

## Summary

Restyle the existing forecast web UI (spec 003's `frontend/src/App.tsx`) using Tailwind CSS,
replacing unstyled HTML with a cohesive visual design across the input form, results display,
loading state, and error state. Presentation-only: no change to form fields, API contract, or
forecast logic.

## Technical Context

**Language/Version**: TypeScript 5.9 / React 19 (frontend only; no backend changes in this feature)

**Primary Dependencies**: Tailwind CSS v4 (`tailwindcss`, `@tailwindcss/vite`) — the CSS/component
library decision deferred from the spec; no other new dependency

**Storage**: N/A (presentation-only; no data model changes)

**Testing**: Existing `vitest` + `@testing-library/react` suite (`frontend/src/App.test.tsx`) —
assertions target behavior/semantics (roles, text content), not CSS classes, so existing tests
should continue to pass unmodified; manual verification via the running dev server and a podman
Docker build, consistent with how 003 was verified

**Target Platform**: Browser (desktop web), same as spec 003 — no new platform

**Project Type**: Web application frontend (existing `frontend/` directory; additive change only,
no new top-level directories)

**Performance Goals**: No regression to existing `vitest`/CI runtime; Tailwind's JIT compiler
only emits CSS for classes actually used on the page, so the production CSS bundle should be
small relative to the existing JS bundle

**Constraints**: No backend/API changes (FR-007); no state-management or data-fetching library
introduced (constitution Technology Stack & Constraints — unaffected, since Tailwind is a CSS
tool, not a state/data library); combined production JS+CSS bundle (gzipped) MUST stay under
100 kB — current JS-only baseline is 69.4 kB gzipped (measured via `npm run build`), leaving
headroom for Tailwind's generated CSS

**Scale/Scope**: Single page; touches `frontend/src/App.tsx`, adds a global stylesheet entry
point, and `frontend/vite.config.ts`; no new routes, components beyond what 003 already has, or
pages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Clean-room design)**: N/A — no algorithm or data-model work; visual design
  choices (layout, color, spacing) are not the kind of "code/structure" this principle protects
  against copying, and no existing tool's code is being copied. PASS.
- **Principle II (Library-first simulation core)**: Unaffected — this feature touches only
  `frontend/`, never `src/agile_metrics/`. PASS.
- **Principle III (Test-first, statistically validated)**: N/A — no simulation logic changes.
  Existing frontend tests continue to assert behavior, not simulation statistics. PASS.
- **Principle IV (Transparent assumptions)**: Reinforced, not weakened — FR-003/FR-004 require
  the four confidence-level outcomes to remain visually present (just better organized), and
  trial/period context stays visible (de-emphasized, not removed). PASS.
- **Principle V (Simplicity/YAGNI)**: Tailwind CSS (utility classes only) is the smallest
  addition that satisfies the stakeholder's explicit decision to use a library instead of
  hand-rolled CSS — it adds no runtime behavior, no component framework, no new JS shipped to
  satisfy state/data concerns. A heavier component framework (Chakra, Mantine, MUI) was
  considered and rejected in `research.md` as more than this single-page form needs. PASS.
- **Technology Stack & Constraints** (frontend: React + TypeScript + Vite, no state-management/
  data-fetching library without demonstrated need): Tailwind CSS is a CSS build tool, not a
  state-management or data-fetching library, so this constraint is not implicated. PASS.
- **Quality Gates** (frontend CI: `eslint` → `tsc --noEmit` → `vitest` → `npm audit`; Dependabot
  npm ecosystem; generated-API-types freshness gate): all existing gates continue to apply
  unchanged — this feature adds a dependency (`tailwindcss`, `@tailwindcss/vite`) already
  covered by the existing npm Dependabot ecosystem block and `npm audit` step; no API/OpenAPI
  schema changes, so the generated-types freshness gate is unaffected. PASS.

No violations requiring justification. Complexity Tracking section omitted (no entries).

**Post-Phase-1 re-check**: Design artifacts (`research.md`, `data-model.md`,
`contracts/design-tokens.md`, `quickstart.md`) introduce exactly what was anticipated above —
Tailwind CSS utility classes and a fixed design-token vocabulary, no new runtime dependency
beyond `tailwindcss`/`@tailwindcss/vite`, no data model or API changes. All gate results above
stand unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/004-web-ui-styling/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── design-tokens.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── App.tsx           # Existing component — restyled with Tailwind utility classes
│   ├── App.test.tsx       # Existing tests — unchanged (asserts behavior, not styling)
│   ├── main.tsx            # Existing entry point — adds the new stylesheet import
│   ├── index.css           # NEW — Tailwind entry point (`@import "tailwindcss";`)
│   └── api-types.ts       # Unchanged (generated, out of scope)
├── vite.config.ts         # Adds the `@tailwindcss/vite` plugin
└── package.json            # Adds `tailwindcss` + `@tailwindcss/vite` devDependencies
```

**Structure Decision**: No new directories. This feature is additive within the existing
`frontend/` structure established by 003: one new file (`frontend/src/index.css`, the Tailwind
entry point), edits to `App.tsx` (utility classes), `main.tsx` (stylesheet import), and
`vite.config.ts` (plugin registration).

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
