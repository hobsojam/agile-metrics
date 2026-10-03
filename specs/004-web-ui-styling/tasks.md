---

description: "Task list for web UI visual styling (004-web-ui-styling)"
---

# Tasks: Web UI Visual Styling

**Input**: Design documents from `/specs/004-web-ui-styling/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/design-tokens.md, quickstart.md

**Tests**: Not requested for this feature (spec is presentation-only; research.md §4 explicitly
defers adding new automated accessibility/visual tests). The existing `frontend/src/App.test.tsx`
suite is a regression guard, not new test-writing — see Polish phase.

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3) to enable
independent implementation and testing of each story. All tasks touch the same file
(`frontend/src/App.tsx`) within a story, so within-story tasks are sequential by design (no
same-file `[P]` conflicts).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single frontend app (per plan.md Project Structure): `frontend/src/`, `frontend/vite.config.ts`,
`frontend/package.json`. No backend paths — this feature does not touch `src/agile_metrics/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bring in the Tailwind CSS v4 build pipeline (plan.md, research.md §1–2) before any
visual work begins.

- [ ] T001 Add `tailwindcss` and `@tailwindcss/vite` as devDependencies in `frontend/package.json` (run inside a `node:22-slim` container to match CI, per project convention — local npm has a known arborist bug on Node 20)
- [ ] T002 Register the `@tailwindcss/vite` plugin alongside the existing `@vitejs/plugin-react` plugin in `frontend/vite.config.ts`
- [ ] T003 [P] Create `frontend/src/index.css` containing `@import "tailwindcss";` as the Tailwind entry point (research.md §2)
- [ ] T004 [P] Import `./index.css` once from `frontend/src/main.tsx`

**Checkpoint**: `npm run dev` serves the page with the Tailwind pipeline active (confirm by
temporarily applying any utility class and observing it take effect, then proceed — no visual
redesign yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the page-level layout shell every user story's section nests inside
(contracts/design-tokens.md "Layout"), so stories don't each reinvent page structure.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — all three stories'
sections live inside this shell.

- [ ] T005 In `frontend/src/App.tsx`, apply the page-level layout shell to the root `<main>` element: `bg-slate-50` page background, `p-8` outer padding, a centered `max-w-xl` content column, `flex flex-col gap-6` stacking (contracts/design-tokens.md "Layout"; FR-008, SC-004 — must remain legible with no overlap between 1024px and 1280px+ container widths)

**Checkpoint**: Foundation ready — page has correct background/padding/column width; individual
sections (form/results/error/loading) still need their own styling, done in the stories below.

---

## Phase 3: User Story 1 - A polished forecast input form (Priority: P1) 🎯 MVP

**Goal**: The input form (history, period length, backlog size, target date, seed, submit) reads
as a clean, well-organized, professional form instead of plain stacked HTML (spec FR-001, FR-002).

**Independent Test**: Load the dev server with no other story's styling applied; the form alone
should already look finished (quickstart.md Scenario 2).

### Implementation for User Story 1

- [ ] T006 [US1] In `frontend/src/App.tsx`, wrap the `<form>` in a styled card: `bg-white rounded-lg border border-slate-200 p-6` (contracts/design-tokens.md "Layout"; FR-001)
- [ ] T007 [US1] Style each label/input field group with `gap-2` spacing between label and input and `gap-4` spacing between field groups; apply `text-sm font-medium` to labels (contracts/design-tokens.md "Spacing"/"Typography"; FR-001)
- [ ] T008 [US1] Style the submit button as the clear primary action: `bg-blue-600 hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2`, including a visually distinct `disabled` state (the button is already disabled while `loading`) (contracts/design-tokens.md "Color"; FR-002)
- [ ] T009 [US1] Add the page title "Agile Metrics Forecast" styling: `text-2xl font-semibold` (contracts/design-tokens.md "Typography")
- [ ] T010 [US1] Run quickstart.md Scenario 2: visually confirm field grouping/spacing/labels and that resizing the browser window between ~1024px and 1280px+ shows no overlapping or cut-off elements (FR-008)

**Checkpoint**: User Story 1 complete — the form is fully restyled and independently
demonstrable, even with results/error/loading still unstyled.

---

## Phase 4: User Story 2 - A polished forecast results display (Priority: P2)

**Goal**: The four confidence-level outcomes are presented with clear visual hierarchy, scannable
at a glance, with supporting context (trial/period counts) visually subordinate (spec FR-003,
FR-004).

**Independent Test**: Submit a valid forecast and visually confirm the results section is
clearly distinguishable from the form, with the four outcomes scannable (quickstart.md
Scenario 3).

### Implementation for User Story 2

- [ ] T011 [US2] In `frontend/src/App.tsx`, wrap the results `<section>` in its own styled card (`bg-white rounded-lg border border-slate-200 p-6`), visually separated from the form by the `gap-6` page-level stacking already in place from T005 (contracts/design-tokens.md "Layout"; FR-003)
- [ ] T012 [US2] Style the four confidence-level outcome rows with `text-base` body styling and clear per-row visual separation, so the percentage/outcome pairing is scannable without reading dense prose (FR-003)
- [ ] T013 [US2] Apply `text-sm text-slate-500` to the trial-count/periods-used supporting text so it is visually subordinate to the four confidence-level outcomes (contracts/design-tokens.md "Typography"; FR-004)
- [ ] T014 [US2] Run quickstart.md Scenario 3: submit a valid forecast and visually confirm the results card is clearly separated from the form, and that supporting context reads as secondary to the four outcomes (SC-002)

**Checkpoint**: User Stories 1 AND 2 both independently complete and visually demonstrable.

---

## Phase 5: User Story 3 - Polished loading and error states (Priority: P3)

**Goal**: The loading indicator and error message are styled consistently with the rest of the
page instead of plain unstyled text, while the error remains unambiguously distinguishable from
a successful result (spec FR-005, FR-006).

**Independent Test**: Trigger a validation error and observe an in-flight loading state;
visually confirm both are styled consistently with the page (quickstart.md Scenario 4).

### Implementation for User Story 3

- [ ] T015 [US3] In `frontend/src/App.tsx`, style the existing `<output>` loading element with `text-sm text-slate-500` consistent with the page's supporting-text styling, preserving its existing semantics (no change to the `<output>` element itself) (FR-005)
- [ ] T016 [US3] Style the existing `role="alert"` error element as a styled card using the error color tokens: `bg-red-50 border border-red-200 text-red-700 rounded-lg p-4` (contracts/design-tokens.md "Color"; FR-006 — must remain unambiguously distinct from the results card styled in T011)
- [ ] T017 [US3] Run quickstart.md Scenario 4: trigger a validation error and a loading state, and visually confirm both are styled consistently with the page while the error remains clearly marked as an error, not confusable with a result

**Checkpoint**: All three user stories independently functional and visually demonstrable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression checks and full-stack verification across all three stories.

- [ ] T018 [P] Run quickstart.md Scenario 1 (`npm run lint && npm run typecheck && npm test` in `frontend/`) and confirm all pass unchanged — a failure here means the restyle accidentally changed behavior or markup semantics, not just appearance
- [ ] T019 Run quickstart.md Scenario 6 (`npm run build` in `frontend/`) and confirm the combined JS+CSS gzip bundle size stays under 100 kB (plan.md Technical Context constraint)
- [ ] T020 Run quickstart.md Scenario 5: `podman build`/`docker build` the full image and smoke-test the served production build at `http://localhost:8000`, repeating Scenarios 2–4 against it to confirm the production build renders identically to the dev server
- [ ] T021 Confirm `README.md` needs no changes (no new usage instructions — this feature is presentation-only, FR-007) or update it if any Web UI section detail has gone stale
- [ ] T022 Run the full constitution Quality Gate sequence clean across the repo: `ruff`, `mypy --strict`, `pytest --cov`, `pip-audit`, `bandit`, `eslint`, `tsc --noEmit`, `vitest`, `npm audit`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion (needs the Tailwind pipeline active) — BLOCKS all user stories.
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion. Each story is independently testable once Foundational is done; this project is implemented solo, so stories proceed in priority order (P1 → P2 → P3) rather than in parallel by different people.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each Phase

- Setup: T001 before T002 (plugin registration needs the dependency installed); T003/T004 can follow in either order relative to T002, marked `[P]` only relative to each other (different files: `index.css` vs `main.tsx`'s single new import line) — T004 still needs T003's file to exist first in practice, so treat as T001 → T002 → T003 → T004.
- Foundational: single task (T005).
- Each user story: implementation tasks are sequential (same file, `frontend/src/App.tsx`), ending with a verification task that must run after that story's styling tasks.
- Polish: T018 has no dependency on T019-T022 and could run first or in parallel conceptually, but all of Phase 6 depends on Phases 3-5 being complete.

### Parallel Opportunities

- T003 and T004 are the only tasks marked `[P]` (different files), though in practice completing them in file-creation order (T003 then T004) is simplest for a single implementer.
- Given the single-file nature of this feature's main work (`App.tsx`), most parallelism opportunities that exist for multi-file features don't apply here — this is expected for a focused, presentation-only change.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (the form)
4. **STOP and VALIDATE**: Run quickstart.md Scenario 2 independently
5. Demo if ready — the form alone already looks finished, even with plain results/error/loading

### Incremental Delivery

1. Setup + Foundational → Tailwind pipeline active, page shell in place
2. Add User Story 1 (form) → validate independently → demo (MVP!)
3. Add User Story 2 (results) → validate independently → demo
4. Add User Story 3 (loading/error) → validate independently → demo
5. Polish (Phase 6) → full regression + bundle-size + Docker verification → ready to merge

---

## Notes

- `[P]` tasks = different files, no dependencies.
- `[Story]` label maps task to specific user story for traceability.
- This feature has no backend/API tasks — it is scoped entirely to `frontend/`.
- Verify `frontend/src/App.test.tsx` still passes after each story's styling tasks, not just at
  the end — catching a semantic regression immediately (while context is fresh) is cheaper than
  catching it only in Phase 6.
