---

description: "Task list for 005-forecast-charts"
---

# Tasks: Forecast Charts

**Input**: Design documents from `specs/005-forecast-charts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecast-api.md, quickstart.md

**Tests**: Included and placed before implementation in every phase. Constitution
Principle III (Test-First & Statistically Validated) is NON-NEGOTIABLE and overrides the
template's "tests are optional" default. Every test task MUST be run and seen to fail
before its implementation task starts. The one exception is T001: it pins *current*
behaviour, so it passes from the start.

**Before implementation**: per the constitution's Development Workflow, convert this file
into GitHub Issues titled `[005-forecast-charts] T0xx: …` (`/speckit-taskstoissues`).
Also confirm the three decisions listed in plan.md, "Decisions needing confirmation before
implementation".

**Organization**: The library has to produce all three new result fields at once, because
`ForecastResult`'s validator requires them together. So the library and API work is
foundational (Phase 2). It is also the part that can start **before** spec 004 merges.
The user-story phases (4–7) are frontend chart work, one chart per story, done after 004
merges.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

Per plan.md: the library is in `src/agile_metrics/` with tests in `tests/`. The frontend
is in `frontend/`, and all new chart code goes in `frontend/src/charts/`.

---

## Phase 1: Setup

**Purpose**: Safety net and tracking before any code changes

- [X] T001 Write a characterization (regression) test in `tests/test_regression.py`. It
  records the **current** `ForecastResult.outcomes`, `trials_run` and `periods_used` from
  `forecast_by_items` and `forecast_by_date` for fixed seeds and a fixed `reference_date`.
  Cover at least: history `[3,5,4,6,2,5,4,3]` weekly with backlog 20 and with target
  2026-11-14 (expected outcomes: `{50: 2026-11-07, 70: 2026-11-14, 85: 2026-11-14, 95: 2026-11-21}`
  and `{50: 24, 70: 22, 85: 21, 95: 19}` at `seed=42`, `reference_date=2026-10-03`), a
  history containing zeros, a constant history (`[5]*6`), and a large backlog (200). Hard-code
  the literal values produced by the code on `main`. This test MUST pass now and keep
  passing after every later task (SC-006).
- [X] T002 [P] File a GitHub issue (not part of this feature's scope): backlog mode
  allocates a `trials × max(50·backlog, 500)` int64 matrix in `src/agile_metrics/simulation.py`
  (about 80 MB at backlog 20). Reference research.md §1.

**Checkpoint**: The regression pin is green on the unmodified code.

---

## Phase 2: Foundational — Library & API (blocks all user stories; can start before 004 merges)

**Purpose**: `ForecastResult` carries `reference_date`, `distribution` and `projection`,
all derived from one simulation run, exposed through the API, with the frontend types
regenerated.

### Simulation core

- [X] T003 Write failing tests in `tests/test_simulation.py` for a new internal function
  `cumulative_paths(history, horizon, trials, seed) -> NDArray[np.int64]` with shape
  `(trials, horizon)`. With equal seed and trials: (a) its last column equals
  `items_completed_after(history, num_periods=horizon, …)`; (b) the first column index where
  each row reaches `backlog_size` (+1) equals `periods_to_complete(history, backlog_size, …)`
  when `horizon = max(backlog_size * 50, 500)`; (c) every row never decreases.
- [X] T004 Implement `cumulative_paths` in `src/agile_metrics/simulation.py` as one
  `rng.choice(historical, size=(trials, horizon), replace=True)` followed by
  `np.cumsum(axis=1)`. Re-express `periods_to_complete` and `items_completed_after` on top
  of it without changing their RNG call (same generator, seed and shape). T001 and T003
  MUST both be green afterwards (research.md §1).

### Models

- [X] T005 [P] Write failing tests in `tests/test_models.py` for `OutcomeBucket`
  (`lower: date | int`, `upper: date | int`, `trials: int` ≥ 0), `ProjectionPoint`
  (`period: int` ≥ 1, `period_end: date`, `cumulative: dict[Literal[50,70,85,95], int]`),
  and the extended `ForecastResult` validator. Each rule gets a rejecting case, quoted
  from data-model.md: "`sum(b.trials for b in distribution) == trials_run`";
  "`1 ≤ len(distribution) ≤ 60`"; "Buckets are in ascending order, don't overlap, and each
  has `lower ≤ upper`. Bucket bounds are dates when `outcomes` holds dates, and integers
  when it holds integers."; "`projection` is non-empty, and `period` runs
  `1, 2, …, len(projection)` with no gaps". Also add one accepting case per mode.
- [X] T006 Implement `OutcomeBucket`, `ProjectionPoint`, and the new **required**
  `ForecastResult` fields `reference_date: date`, `distribution: list[OutcomeBucket]` and
  `projection: list[ProjectionPoint]`, plus the validator from T005, in
  `src/agile_metrics/models.py`. Existing fields stay unchanged.
- [X] T007 Update the two hand-built `ForecastResult` fixtures in `tests/test_cli.py`
  (`TestRenderResult`) to supply the new required fields (e.g. one bucket holding all
  10,000 trials, a one-point projection). The existing output assertions stay unchanged,
  confirming FR-006.

### Forecast derivation

- [X] T008 Write failing tests in `tests/test_forecast.py`: both `forecast_by_items` and
  `forecast_by_date` return `reference_date` equal to the passed or defaulted reference
  date; `distribution` follows research.md §3 (one bucket per value when
  `max − min + 1 ≤ 60`; otherwise `width = ceil(span / 60)` with inclusive integer
  bounds; empty in-range buckets kept with `trials = 0`; date bounds in backlog mode
  computed as `reference_date + n × period_duration`; constant history gives exactly one
  bucket); `projection` follows research.md §5 (backlog mode: periods `1 … P95 + 1`
  where `P95 = round(np.percentile(periods, 95))`; target-date mode: periods
  `1 … num_periods`; `period_end = reference_date + period × period_duration`).
- [X] T009 Refactor `src/agile_metrics/forecast.py` so each public function calls
  `cumulative_paths` **once** and derives the existing outcomes (formulas unchanged), the
  distribution, and the projection from that single matrix (FR-004). Add private helpers
  for bucketing (research.md §3) and projection (research.md §2:
  `int(np.percentile(cumulative[:, t-1], 100 - L))`). Export `OutcomeBucket` and
  `ProjectionPoint` from `agile_metrics.models`. T001, T008 and all existing tests stay green.
- [X] T010 [P] Add Hypothesis property tests in `tests/test_statistical.py`, which must
  fail against a deliberately broken helper before being trusted:
  - bucket trials add up to `trials_run` (SC-002);
  - each `outcomes[L]` falls inside exactly one bucket (SC-001);
  - in backlog mode, the fraction of trials whose outcome is ≤ `outcomes[L]` is ≥ `L/100`,
    and in target-date mode the fraction ≥ `outcomes[L]` is ≥ `L/100` (User Story 2,
    acceptance scenario 3; research.md §4);
  - per projection point, `cumulative[95] ≤ cumulative[85] ≤ cumulative[70] ≤ cumulative[50]`;
  - each level never decreases over periods;
  - target-date mode: `projection[-1].cumulative == outcomes`, exactly;
  - backlog mode: the first period where `cumulative[L] ≥ backlog_size` is within ±1 of
    the period count behind `outcomes[L]` (SC-003).

### API & generated types

- [X] T011 Write a failing test in `tests/test_web.py`: `POST /api/forecast` in both modes
  returns `reference_date`, `distribution` and `projection` with the field rules in
  contracts/forecast-api.md, and `outcomes` / `trials_run` / `periods_used` are unchanged
  for a fixed seed. It should pass once T009 lands, with no `web.py` change expected.
- [X] T012 Regenerate `frontend/openapi.json` and `frontend/src/api-types.ts` with
  `cd frontend && npm run generate-types`. Commit both and confirm the new fields are
  **non-optional** in the generated `ForecastResult` type.

**Checkpoint**: The library and API return chart data. `uv run pytest`, `ruff`,
`mypy --strict` and the types-freshness check pass. This phase can be opened as its own
PR before 004 merges.

---

## Phase 3: Foundational — Frontend (blocks US1–US4; starts after spec 004 merges)

**Purpose**: Chart scaffolding shared by all four charts

- [ ] T013 Rebase `005-forecast-charts` onto `main` after `004-web-ui-styling` has merged,
  and resolve any conflicts in `frontend/src/App.tsx`, keeping 004's styling.
- [ ] T014 Add `recharts@^3.10.1` and `react-is` (version matching React 19) as runtime
  dependencies in `frontend/package.json` and `frontend/package-lock.json`. Check that
  `npm audit` is clean (research.md §6).
- [ ] T015 [P] Stub `ResizeObserver` in `frontend/src/setupTests.ts` so Recharts'
  `ResponsiveContainer` renders under jsdom (research.md §6, testing note).
- [ ] T016 [P] Create `frontend/src/charts/confidenceLevels.ts`. It exports the four
  levels `50, 70, 85, 95` in order, each with a display label (`"50%"` …) and one shared
  colour drawn from 004's design-token palette: one hue at increasing strength for higher
  confidence (FR-010, research.md §7). Every chart imports from here, and nowhere else
  defines confidence colours.
- [ ] T017 Write a failing test in `frontend/src/App.test.tsx`: after a successful
  submission, a "Forecast charts" region renders below the existing confidence-level
  list, and the list is still present (FR-007). After an error response, no charts region
  renders. Charts use the inputs as **submitted**, so editing the form afterwards doesn't
  change the drawn charts.
- [ ] T018 Create `frontend/src/charts/ForecastCharts.tsx`, a wrapper taking the
  `ForecastResult` plus the submitted `history: number[]`, `periodDays: number`, and
  `backlogSize` or `targetDate`. It renders a labelled region holding the chart figures
  (empty for now) in a container wider than 004's `max-w-xl` form column (e.g.
  `max-w-4xl`; research.md §7, decision 3 in plan.md). In `frontend/src/App.tsx`, store
  the submitted inputs alongside the result and render `<ForecastCharts>` in the results
  section. T017 passes.

**Checkpoint**: An empty charts region appears after a successful forecast. The ready
state for chart work.

---

## Phase 4: User Story 1 — See the spread of possible outcomes (Priority: P1) 🎯 MVP

**Goal**: A histogram of simulated outcomes with the four confidence levels marked.

**Independent Test**: Submit history `3,5,4,6,2,5,4,3`, period 7, backlog 20, seed 42.
One bar per completion date appears, with 50/70/85/95% markers at exactly the listed
dates. Repeat with target date 2026-11-14 and check item-count bars and markers.

- [ ] T019 [US1] Write failing tests in `frontend/src/charts/chartData.test.ts` for
  `toDistributionSeries(result)`. It returns one entry per `distribution` bucket, in
  order, with a display label (a date when `lower === upper` in backlog mode, a
  `lower–upper` range when grouped, an item count or range in target-date mode) and
  `trials`. It also returns one marker per level, placed on the bucket containing
  `outcomes[L]` (SC-001). Constant-history input gives a single bar with all four
  markers on it (edge case).
- [ ] T020 [US1] Implement `toDistributionSeries` in `frontend/src/charts/chartData.ts`
  as a pure function with no React import.
- [ ] T021 [P] [US1] Write failing tests in `frontend/src/charts/DistributionChart.test.tsx`:
  the chart renders a `<figure>` with a visible title, a `<figcaption>` explaining how to
  read it (FR-011), and a visually hidden text alternative listing all four levels and
  their outcomes (FR-013). No "average" or "expected" value appears anywhere (FR-008).
  Cover both modes.
- [ ] T022 [US1] Implement `frontend/src/charts/DistributionChart.tsx` with a Recharts
  bar chart and a reference line per confidence level. Styles come from
  `confidenceLevels.ts`, axes are labelled ("Completion date" or "Items completed",
  "Simulated futures"), and a tooltip shows the bucket label and trial count (FR-012).
  Set the SVG to `aria-hidden` (research.md §8).
- [ ] T023 [US1] Render `DistributionChart` first inside `frontend/src/charts/ForecastCharts.tsx`,
  and extend `frontend/src/App.test.tsx` to assert its title appears after a successful
  forecast.

**Checkpoint**: MVP. Users see how spread out their forecast is.

---

## Phase 5: User Story 2 — Read off the chance of any outcome (Priority: P2)

**Goal**: A cumulative probability curve the user can read at any date or item count.

**Independent Test**: Submit a forecast. The curve rises from 0% to 100% (backlog mode)
or falls from 100% to 0% (target-date mode), and its value at each listed outcome is at
least that level.

- [ ] T024 [US2] Write failing tests in `frontend/src/charts/chartData.test.ts` for
  `toProbabilityCurve(result)`. In backlog mode, each point is the bucket's upper date
  with the running total of trials ÷ `trials_run` ("done on or before"), ending at 1. In
  target-date mode, accumulate from the highest bucket down, giving the bucket's lower
  count with "at least" probability, starting at 1 (research.md §4). At each `outcomes[L]`
  the value is ≥ `L/100`. Constant history gives a single step.
- [ ] T025 [US2] Implement `toProbabilityCurve` in `frontend/src/charts/chartData.ts`.
- [ ] T026 [P] [US2] Write failing tests in `frontend/src/charts/ProbabilityCurveChart.test.tsx`
  for the title, the caption ("how likely you are to be done by a date" / "to complete at
  least N items"), and a text alternative listing the likelihood at each of the four
  listed outcomes (FR-011, FR-013).
- [ ] T027 [US2] Implement `frontend/src/charts/ProbabilityCurveChart.tsx` with a Recharts
  step line on a 0–100% y-axis, dashed reference lines at the four levels (styled from
  `confidenceLevels.ts`), and a tooltip reading "x% of simulations done by \<date\>" or
  "x% of simulations completed at least \<n\> items" (FR-012).
- [ ] T028 [US2] Render `ProbabilityCurveChart` after the distribution in
  `frontend/src/charts/ForecastCharts.tsx`.

**Checkpoint**: Stakeholders can read the chance of any date or scope.

---

## Phase 6: User Story 3 — See history and forecast as one picture (Priority: P3)

**Goal**: A burn-up of historical cumulative throughput followed by the confidence fan.

**Independent Test**: In backlog mode, the history line ends where the fan begins, and
each level's line meets the backlog line within one period of its listed date. In
target-date mode, each line's final value equals its listed count.

- [ ] T029 [US3] Write failing tests in `frontend/src/charts/chartData.test.ts` for
  `toBurnUpSeries(result, history, periodDays, mode)`:
  - Historical points: period *i* of *n* ends at
    `reference_date − (n − i) × periodDays`, the value is the running total, and there
    is a starting point of 0 at the start of the oldest period (spec Assumptions).
    Zero-throughput periods appear as flat segments.
  - Fan points: one per `projection` entry, each value = historical total +
    `cumulative[L]`, starting from the last historical point.
  - Target line: in backlog mode, a horizontal value of historical total + backlog size;
    in target-date mode, a vertical marker at the target date.
- [ ] T030 [US3] Implement `toBurnUpSeries` in `frontend/src/charts/chartData.ts`
  (FR-014).
- [ ] T031 [P] [US3] Write failing tests in `frontend/src/charts/BurnUpChart.test.tsx` for
  the title, the caption, and a text alternative stating the historical total, the
  target, and each level's projected date (backlog mode) or count (target-date mode)
  (FR-011, FR-013).
- [ ] T032 [US3] Implement `frontend/src/charts/BurnUpChart.tsx`: a Recharts composed
  chart with the historical line, one line per confidence level, shading between the
  50% and 95% lines, the backlog or target-date reference line, a date x-axis, an
  "Items completed (cumulative)" y-axis, and a tooltip per period (FR-012).
- [ ] T033 [US3] Render `BurnUpChart` in `frontend/src/charts/ForecastCharts.tsx`.

**Checkpoint**: A presentation-ready single picture of past and future.

---

## Phase 7: User Story 4 — Check whether the history is trustworthy (Priority: P4)

**Goal**: A run chart of the historical periods with a median line.

**Independent Test**: For a known history, N bars appear in input order with the
entered heights, and a reference line sits at the median.

- [ ] T034 [US4] Write failing tests in `frontend/src/charts/chartData.test.ts` for
  `toRunChartSeries(history, referenceDate, periodDays)`. It returns one bar per period,
  oldest first, each labelled with the period's date range (same date anchoring as
  T029), with zero values kept. The median is correct for both odd and even lengths.
- [ ] T035 [US4] Implement `toRunChartSeries` in `frontend/src/charts/chartData.ts`.
- [ ] T036 [P] [US4] Write failing tests in `frontend/src/charts/ThroughputRunChart.test.tsx`
  for the title, the caption, and a text alternative stating the number of periods,
  the median, and the min and max (FR-011, FR-013).
- [ ] T037 [US4] Implement `frontend/src/charts/ThroughputRunChart.tsx` with Recharts
  bars, a median reference line in a neutral (non-confidence) style, an "Items completed"
  y-axis, and a tooltip with the period range and count (FR-012).
- [ ] T038 [US4] Render `ThroughputRunChart` last in `frontend/src/charts/ForecastCharts.tsx`.

**Checkpoint**: All four charts are live.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T039 [P] Check the narrow-viewport behaviour (about 400px; spec Edge Cases): charts
  resize with no horizontal page scroll. Fix layout in `frontend/src/charts/ForecastCharts.tsx`
  if needed.
- [ ] T040 [P] Measure SC-004: with 104 historical periods and default trials, all four
  charts render within 1 s of the results appearing. Record the result in the PR
  description.
- [ ] T041 [P] Update `README.md`: describe the charts in the Web UI section, the new
  `ForecastResult` fields in the Library section, and the 005 spec link in Status
  (constitution: README updated in the completing PR).
- [ ] T042 Run every scenario in `specs/005-forecast-charts/quickstart.md` and fix any
  failures.
- [ ] T043 Run all quality gates (ruff, mypy --strict, pytest --cov, pip-audit, bandit,
  eslint, tsc, vitest, npm audit, types freshness). Write the PR description(s) covering
  the Recharts/react-is justification (research.md §6) and the principles touched
  (I–V, per plan.md's Constitution Check).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies. T001 must land before T004.
- **Phase 2 (Library & API)**: Depends on T001. **Independent of spec 004.** It can ship
  as its own PR.
- **Phase 3 (Frontend foundation)**: Depends on Phase 2 *and* on 004 being merged (T013).
- **Phases 4–7 (US1–US4)**: Depend on Phase 3. They're sequential in priority order,
  because each extends `chartData.ts`, `chartData.test.ts` and `ForecastCharts.tsx`.
- **Phase 8 (Polish)**: Depends on whichever stories are shipping.

### User Story Dependencies

- **US1 (P1)**: Needs Phase 3 only.
- **US2 (P2)**: Uses the same `distribution` data as US1, but its own chart. Independently
  testable.
- **US3 (P3)**: Needs `projection` (Phase 2). Independently testable.
- **US4 (P4)**: Needs only the submitted history and `reference_date`. Independently
  testable.

### Within Each Phase

- Tests before implementation, confirmed failing (Principle III).
- Library: simulation → models → forecast derivation → API → types.
- Frontend per story: data function (test → impl) → component (test → impl) → wire-up.

### Parallel Opportunities

- T002 can run alongside T001.
- T005 (model tests) can run alongside T003/T004 (simulation), since they're different
  files.
- T010 (property tests) can be written alongside T008 once T006 lands.
- T015 and T016 can run in parallel within Phase 3.
- Within each story, the component test (T021/T026/T031/T036) can be written in parallel
  with the data-function work, because it's in a different file.
- T039, T040 and T041 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# After T020 lands (or alongside T019–T020, since they're different files):
Task: "T021 Write failing tests in frontend/src/charts/DistributionChart.test.tsx"
# while
Task: "T019/T020 toDistributionSeries tests + implementation in frontend/src/charts/chartData(.test).ts"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 → Phase 2 (library and API PR, can merge before 004).
2. After 004 merges: Phase 3 → Phase 4 (US1 distribution chart).
3. **STOP and VALIDATE** with the US1 independent test. Demo it.

### Incremental Delivery

1. Library and API PR: chart data is available to any consumer, and nothing visible
   changes.
2. US1 → US2 → US3 → US4, each adding one chart and each demoable on its own.
3. Polish and README in the final PR.

---

## Notes

- `[P]` = different files, no dependency on incomplete tasks.
- Commit after each task or logical group. Every commit keeps T001 green.
- Clean-room (Principle I): don't consult predictability-engine source while
  implementing.
