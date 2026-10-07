---

description: "Task list for Cycle Time Scatterplot with Percentile Lines (012-cycle-time-scatterplot)"
---

# Tasks: Cycle Time Scatterplot with Percentile Lines

**Input**: Design documents from `specs/012-cycle-time-scatterplot/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/forecast-api.md, quickstart.md

**Tests**: Included and placed before implementation in every phase (Constitution
Principle III). Percentile computation is deterministic (not randomized), so
"test-first" here means known, hand-computed cycle-time values checked against exact
`np.percentile` output, mirroring how `forecast.py`'s own percentile calls are already
tested indirectly via `test_forecast.py`.

**Organization**: One new backend field (`FlowMetrics.cycle_time_percentiles`) is
foundational to both user stories — US1 (Cycle Time scatterplot) and US2 (Aging WIP
threshold) both only *consume* it, computed once. This mirrors spec 009's
`PrecisionWarning` pattern (model/field in Setup, computation wired in Foundational)
rather than spec 011's larger multi-entity Foundational phase, since this feature adds
one field, not several entities.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Per plan.md: `src/agile_metrics/models.py`, `src/agile_metrics/jira_client.py`
(backend, both existing, additive); `frontend/src/charts/chartData.ts`,
`CycleTimeChart.tsx`, `AgingWipChart.tsx` (frontend, all existing, additive);
`frontend/openapi.json`, `frontend/src/api-types.ts` (regenerated, not hand-edited).
No new files beyond tests. `web.py` and `cli.py` are unchanged (contracts/forecast-api.md).

---

## Phase 1: Setup

- [ ] T001 Write failing tests in `tests/test_models.py` for
  `FlowMetrics.cycle_time_percentiles`: accepts `None`; accepts a dict with exactly the
  four keys `50, 70, 85, 95`, each value `>= 0` and non-decreasing across ascending
  levels (`[50] <= [70] <= [85] <= [95]`); rejects a dict missing any of the four keys
  when not `None`; rejects a dict with a non-monotonic value (e.g. `70` less than `50`)
  (data-model.md).
- [ ] T002 Implement the field in `src/agile_metrics/models.py`: add
  `cycle_time_percentiles: dict[Literal[50, 70, 85, 95], int] | None = None` to
  `FlowMetrics`, after `capped_count`, with a `@model_validator(mode="after")`
  enforcing completeness and monotonicity, satisfying T001 — mirror
  `_validate_flow_state_counts_sum`'s existing validator style in the same class.

**Checkpoint**: The field and its validation exist; `FlowMetrics` still constructs
with no `cycle_time_percentiles` argument supplied (defaults to `None`), so every
existing construction call site in `jira_client.py` and every existing test keeps
passing unmodified until Phase 2 wires in the computation.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: `compute_jira_flow_metrics` actually computes and populates
`cycle_time_percentiles` — both user stories below only consume this, so it must be
correct and tested in isolation first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Write failing tests in `tests/test_jira_client.py` for the percentile
  computation inside `compute_jira_flow_metrics`: given a resolved-issue fixture whose
  `cycle_time` entries produce 5 or more known `(resolved_at - started_at).days`
  values, `cycle_time_percentiles` matches `np.percentile(values, [50, 70, 85, 95])`
  rounded with the same `int(...)` truncation the forecast module already uses
  (research.md §1, data-model.md's computation); with exactly 4 entries,
  `cycle_time_percentiles` is `None`; with 0 entries (empty `cycle_time`),
  `cycle_time_percentiles` is `None` (research.md §2, FR-006).
- [ ] T004 Implement the computation in `compute_jira_flow_metrics`
  (`src/agile_metrics/jira_client.py`): after the existing `cycle_time` list is built,
  compute `cycle_time_days = [(e.resolved_at - e.started_at).days for e in cycle_time]`,
  then `cycle_time_percentiles = None if len(cycle_time_days) < 5 else
  {level: int(p) for level, p in zip((50, 70, 85, 95), np.percentile(cycle_time_days,
  [50, 70, 85, 95]), strict=True)}` (data-model.md), and pass it into the returned
  `FlowMetrics`. Add the `numpy` import to this module if not already present.
  Satisfies T003.
- [ ] T005 Write a regression test in `tests/test_jira_client.py`: for an existing
  fixture already used by a pre-012 `compute_jira_flow_metrics` test, every other
  field of the returned `FlowMetrics` (`cycle_time`, `wip`, `flow_state_counts`,
  `excluded_count`, `capped_count`) is unchanged from before this feature (FR-008) —
  only `cycle_time_percentiles` is new.
- [ ] T006 Fix any gap T005 surfaces. Expected to be none — the computation reads
  already-built `cycle_time` entries without mutating them.
- [ ] T007 Run `cd frontend && npm run generate-types` and commit the resulting diff
  to `frontend/openapi.json` and `frontend/src/api-types.ts` (constitution's
  generated-types freshness gate), exposing `cycle_time_percentiles` to the frontend.

**Checkpoint**: `cycle_time_percentiles` is computed correctly, tested in isolation,
and exposed through the API response and generated frontend types. Each user story
phase below only needs to consume it.

---

## Phase 3: User Story 1 - Read a service-level expectation from historical cycle time (Priority: P1) 🎯 MVP

**Goal**: The Cycle Time view becomes a scatterplot (resolution date × cycle-time
days) with up to four labeled percentile reference lines, replacing the current
bar-per-item view (FR-001, FR-002).

**Independent Test**: Load flow metrics for a project with 5+ resolved issues
spanning several weeks; confirm the Cycle Time view renders one point per issue and
four reference lines whose values match `cycle_time_percentiles`.

- [ ] T008 [P] [US1] Write failing tests in `frontend/src/charts/chartData.test.ts`
  for a new `toCycleTimeScatter(flowMetrics)` function: given `cycle_time` entries and
  a populated `cycle_time_percentiles`, returns one point per entry (`{ date:
  resolved_at, days, key }`) and up to four markers (`{ level, label, color, days }`)
  built from `CONFIDENCE_LEVEL_STYLES`; given `cycle_time_percentiles: null`, returns
  all points with an empty markers array (data-model.md).
- [ ] T009 [US1] Implement `toCycleTimeScatter` in `frontend/src/charts/chartData.ts`,
  satisfying T008, following this file's existing pure-function "API response ->
  chart-ready series" pattern (module docstring, no React import).
- [ ] T010 [P] [US1] Write failing tests in
  `frontend/src/charts/CycleTimeChart.test.tsx`: renders a scatter point per
  `cycle_time` entry positioned by `resolved_at` (X) and days (Y); renders up to four
  labeled horizontal reference lines matching `cycle_time_percentiles` values; with
  `cycle_time_percentiles` absent, still renders the points with zero reference lines,
  not an empty or error state (spec Edge Cases, FR-001/FR-002/FR-006); the existing
  zero-entries "nothing to show yet" empty state is unchanged (FR-007).
- [ ] T011 [US1] Reimplement `CycleTimeChart` in
  `frontend/src/charts/CycleTimeChart.tsx`: replace `BarChart`/`Bar` with
  `ScatterChart`/`Scatter`, `XAxis dataKey` the resolution date with
  `type="category"` (matching every other chart's category-axis convention,
  research.md §3), and render up to four `<ReferenceLine y={marker.days} .../>`
  elements from `toCycleTimeScatter`'s markers, using the same label/color convention
  `DistributionChart`'s markers already use. Satisfies T010.
- [ ] T012 [US1] Run quickstart.md Scenarios 1 and 5 and confirm they pass.

**Checkpoint**: MVP. The Cycle Time view is a scatterplot with correct percentile
lines, or correctly line-less when there isn't enough history.

---

## Phase 4: User Story 2 - Spot at-risk work in progress against the historical threshold (Priority: P2)

**Goal**: The Aging WIP view gains a reference line at the historical 85th-percentile
cycle time and visually distinguishes any in-progress item whose age already exceeds
it (FR-004, FR-005).

**Independent Test**: Load flow metrics with both resolved issues (establishing an
85th-percentile cycle time) and in-progress issues of varying ages; confirm the
threshold line appears and items older than it are visually flagged.

- [ ] T013 [P] [US2] Write failing tests in `frontend/src/charts/chartData.test.ts`
  for a new `agingWipThreshold(flowMetrics)` function: given a `cycle_time_percentiles`
  with an `85` key, returns `{ days, color, label }` built from
  `CONFIDENCE_LEVEL_STYLES[85]`; given `cycle_time_percentiles: null`, returns `null`
  (data-model.md).
- [ ] T014 [US2] Implement `agingWipThreshold` in `frontend/src/charts/chartData.ts`,
  satisfying T013.
- [ ] T015 [P] [US2] Write failing tests in
  `frontend/src/charts/AgingWipChart.test.tsx`: with a threshold available, renders
  one horizontal reference line at its value, and any bar whose `age_days` exceeds it
  is rendered in a visually distinct style from bars that don't (spec Acceptance
  Scenarios 1-2); with `agingWipThreshold` returning `null`, renders the existing bars
  with no reference line and no distinguishing style (spec Edge Cases, FR-006); the
  existing zero-snapshots "nothing currently in progress" empty state is unchanged
  (FR-007).
- [ ] T016 [US2] Implement the changes in `frontend/src/charts/AgingWipChart.tsx`: add
  one `<ReferenceLine y={threshold.days} .../>` using `agingWipThreshold`'s
  color/label, and per-bar conditional coloring via `<Cell>` children keyed on
  whether `snapshot.age_days` exceeds `threshold.days` (research.md §3). Satisfies
  T015.
- [ ] T017 [US2] Run quickstart.md Scenario 6 and confirm it passes.

**Checkpoint**: Both user stories complete and independently functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T018 [P] Update `README.md` to describe the redesigned Cycle Time scatterplot
  and the new Aging WIP threshold (constitution Development Workflow: README MUST be
  updated in the same pull request as a completed feature).
- [ ] T019 Run quickstart.md Scenario 7 (manual visual check against the local dev
  server) and confirm the percentile lines and at-risk bar styling are legible and
  colorblind-safe, not clipped at the chart edges (research.md §3; this is the same
  clipping bug class fixed for `DistributionChart` in PR #382 — verify this chart
  didn't inherit it).
- [ ] T020 Run quickstart.md Scenario 8 (full quality gates): `ruff check`,
  `ruff format --check`, `mypy --strict src`, `pytest --cov`, `pip-audit`, `bandit`;
  frontend `eslint`, `tsc --noEmit`, `npm test`, `npm audit`; confirm the
  generated-types freshness check from T007 still produces no diff.
- [ ] T021 Write the pull request description, including which constitution
  principles this feature touches (Development Workflow requirement) and a note on
  the FR-008 correction made during planning (spec.md's Assumptions already explain
  it; the PR description should summarize it, not restate it in full).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion. No dependency on
  User Story 2.
- **User Story 2 (Phase 4)**: Depends on Foundational completion. No dependency on
  User Story 1 — both consume `cycle_time_percentiles` independently, in different
  files (`CycleTimeChart.tsx` vs. `AgingWipChart.tsx`).
- **Polish (Phase 5)**: Depends on both user stories being complete.

### Within Each Phase

- Tests MUST be written and FAIL before implementation (T001→T002, T003→T004,
  T008→T009, T010→T011, T013→T014, T015→T016).
- Model/field before computation; computation before frontend consumption.

### Parallel Opportunities

- T001 has no sibling to parallelize with in Phase 1.
- Phase 3 and Phase 4 can proceed in parallel once Phase 2 completes — they touch
  disjoint files (`CycleTimeChart.tsx`/test vs. `AgingWipChart.tsx`/test), both
  reading the same `chartData.ts` and `FlowMetrics.cycle_time_percentiles` without
  modifying anything the other depends on.
- Within Phase 3: T008 and T010 (different test files, no dependency between them).
- Within Phase 4: T013 and T015 (same reasoning).

---

## Parallel Example: Phase 3 and Phase 4 together

```bash
# Once Phase 2 (Foundational) is complete, both stories' test-writing tasks
# can run in parallel:
Task: "Write failing tests for toCycleTimeScatter in frontend/src/charts/chartData.test.ts"
Task: "Write failing tests for CycleTimeChart in frontend/src/charts/CycleTimeChart.test.tsx"
Task: "Write failing tests for agingWipThreshold in frontend/src/charts/chartData.test.ts"
Task: "Write failing tests for AgingWipChart in frontend/src/charts/AgingWipChart.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (the field).
2. Complete Phase 2: Foundational (the computation) — CRITICAL, blocks both stories.
3. Complete Phase 3: User Story 1 (the scatterplot).
4. **STOP and VALIDATE**: run quickstart.md Scenarios 1, 5, independently confirming
   the scatterplot and its percentile lines are correct.
5. Demo if ready — User Story 1 alone already delivers the feature's primary value
   (spec.md: "this is the reason a scatterplot-with-percentiles is more useful...
   without it, there's no improvement over the current chart").

### Incremental Delivery

1. Setup + Foundational → the field and computation are ready.
2. Add User Story 1 → validate independently → demo (MVP).
3. Add User Story 2 → validate independently → demo.
4. Polish → README, manual visual check, full quality gates, PR description.

---

## Notes

- [P] tasks = different files, no dependency between them.
- [Story] label maps task to specific user story for traceability.
- Both user stories are independently completable once Phase 2 lands — neither
  depends on the other being done first, unlike spec 011's three views (which shared
  one computation *and* needed sequential story completion for CFD to make sense).
- Commit after each task or logical group.
- Stop at either checkpoint to validate a story independently.
