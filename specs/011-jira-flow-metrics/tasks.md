---

description: "Task list for Cycle-time, aging-WIP, and cumulative-flow metrics for Jira (011-jira-flow-metrics)"
---

# Tasks: Cycle-Time, Aging-WIP, and Cumulative-Flow Metrics for Jira

**Input**: Design documents from `specs/011-jira-flow-metrics/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecast-api.md,
quickstart.md. **Branch note**: this branch merged `010-jira-integration` locally (not yet
on `main`) because every task here builds on `jira_client.py`'s existing functions
(`_detect_done_statuses`, `_fetch_resolved_issues`, `JiraConnection`, `fetch_jira_throughput`,
the HTTP seam). The completing PR will note this stacking, same as 008 on 251.

**Tests**: Included and placed before implementation in every phase (Constitution
Principle III). HTTP is mocked throughout - no real network calls in CI. quickstart.md
Scenario 6 (real Jira Cloud site) is a manual pre-merge gate, tracked in Polish, and is the
only way to confirm whether `expand=changelog` bundles on `/search/jql` (research.md §1).

**Organization**: `compute_jira_flow_metrics()` is one function that returns all three
views at once (cycle-time, WIP, flow-state counts) - they share one fetch and one exclusion
rule (research.md §2-§3), so they cannot be built as three independent library-level
slices. Foundational builds the whole computation; each user-story phase then verifies and
wires through one view end-to-end, the same pattern 010's US1/US2/US3 phases used once
their own foundational function existed.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Per plan.md: `src/agile_metrics/models.py`, `src/agile_metrics/jira_client.py`,
`src/agile_metrics/cli.py`, `src/agile_metrics/web.py` (all existing, additive);
`frontend/src/charts/CycleTimeChart.tsx`, `AgingWipChart.tsx`, `CumulativeFlowChart.tsx`
(new); `frontend/src/charts/ForecastCharts.tsx` (additive).

---

## Phase 1: Setup

- [X] T001 [P] Create empty `frontend/src/charts/CycleTimeChart.tsx`,
  `frontend/src/charts/AgingWipChart.tsx`, and `frontend/src/charts/CumulativeFlowChart.tsx`,
  each with only a module docstring-style comment naming its purpose (spec 011) and no
  exports yet. Create matching empty `*.test.tsx` files alongside them.

**Checkpoint**: Files exist and the frontend still builds (`npm run typecheck`).

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the full `compute_jira_flow_metrics()` computation, correct and tested in
isolation, before any user story wires it through the CLI or web.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Shared models

- [X] T002 Write failing tests in `tests/test_models.py` for `CycleTimeEntry` (`key: str`,
  `started_at: date`, `resolved_at: date`; rejects `resolved_at < started_at`), `WipSnapshot`
  (`key: str`, `started_at: date`, `age_days: int`; rejects `age_days < 0`), and
  `FlowStateCount` (`day: date`, `not_started: int`, `in_progress: int`, `done: int`; rejects
  any count `< 0`) (data-model.md).
- [X] T003 Implement `CycleTimeEntry`, `WipSnapshot`, and `FlowStateCount` as `pydantic`
  models in `src/agile_metrics/models.py`, satisfying T002.
- [X] T004 Write failing tests in `tests/test_models.py` for `FlowMetrics`
  (`cycle_time: list[CycleTimeEntry]`, `wip: list[WipSnapshot]`,
  `flow_state_counts: list[FlowStateCount]`, `excluded_count: int`, `capped_count: int`):
  constructing it with `flow_state_counts` whose `not_started + in_progress + done` does
  **not** equal `len(cycle_time) + len(wip)` for some day raises a validation error
  (data-model.md's invariant, SC-003); a consistent set of inputs constructs successfully.
- [X] T005 Implement `FlowMetrics` with a `@model_validator(mode="after")` enforcing the
  per-day sum invariant, satisfying T004 - mirror `ForecastResult`'s own
  distribution/trials-run validator style in the same file.

### Status-category detection (shared, not duplicated)

- [X] T006 Write failing tests in `tests/test_jira_client.py` for
  `_fetch_status_categories(connection) -> dict[str, str]`: given a mocked
  `GET /rest/api/3/project/{key}/statuses` response with statuses in the `new`,
  `indeterminate`, and `done` categories, returns every status name mapped to its category
  key; a 403 or 404 raises `JiraProjectNotFoundError`, same mapping as the existing
  `_detect_done_statuses` (research.md §2).
- [X] T007 Implement `_fetch_status_categories` in `src/agile_metrics/jira_client.py`,
  satisfying T006. Refactor `_detect_done_statuses` to call it and filter for `"done"` -
  **run the full existing `TestJiraErrors`/done-statuses test suite unmodified afterward
  and confirm it still passes** (no behavior change, pure extraction).
- [X] T008 Write failing tests for `_detect_in_progress_statuses(connection) -> list[str]`:
  returns every status name whose category is `indeterminate`; returns an empty list (not
  an error) when none exist, unlike `_detect_done_statuses` - a project with no in-progress
  statuses still has a forecast, just no WIP to show (contrast with
  `JiraNoDoneStatusesError`, which *is* an error, since a forecast needs a done category to
  mean anything at all).
- [X] T009 Implement `_detect_in_progress_statuses` in `jira_client.py`, satisfying T008.

### The combined, cheap issue fetch (no changelog yet)

- [X] T010 Write failing tests for `_fetch_flow_issues(connection, done_statuses,
  in_progress_statuses, *, today) -> list[dict]`: the JQL combines resolved-in-window
  issues with currently-in-progress issues
  (`(status in (done) AND resolved >= window) OR status in (in_progress)`, research.md §2);
  requested fields include `created` (needed for the "not started" band, data-model.md);
  cursor pagination follows the same `nextPageToken`/`isLast` loop as the existing
  `_fetch_resolved_issues`; a missing `issues` key raises `JiraAPIUnavailableError`
  (research.md §6 hardening, same as 010).
- [X] T011 Implement `_fetch_flow_issues` in `jira_client.py`, satisfying T010 - this is
  the cheap pass (plain fields only, no changelog) that also gives the exact total count
  used by T014/T015's cap logic, since Jira's `/search/jql` never returns one itself
  (spec 010 research.md §1).

### Changelog fetch, capped, with a bundled-first fallback

- [X] T012 Write failing tests for `_fetch_changelogs(connection, issue_keys) -> dict[str,
  list[dict]]`: when a mocked search response (requested with `expand: ["changelog"]`)
  carries each issue's `changelog.histories` inline, those are used directly, with zero
  extra requests; when an issue's response lacks a `changelog` key, falls back to one
  `GET /rest/api/3/issue/{key}/changelog` call for that issue specifically (research.md §1 -
  the actual bundling behavior on the new endpoint is unconfirmed until quickstart
  Scenario 6, so both paths MUST be covered by mocked tests now).
- [X] T013 Implement `_fetch_changelogs` in `jira_client.py`, satisfying T012.
- [X] T014 Write failing tests for the 500-issue changelog cap (plan.md "Decisions" §1,
  research.md §4): given more than 500 issues from `_fetch_flow_issues`, only the first 500
  (stable order) are passed to `_fetch_changelogs`; the remainder's count is reported, not
  silently dropped.
- [X] T015 Implement the cap in the orchestration added in T017/T018 (not a new function -
  a slice of the 500 issues before calling `_fetch_changelogs`), satisfying T014.

### Resolving start dates and shaping the three views

- [X] T016 Write failing tests for `_resolve_start_date(histories, in_progress_statuses) ->
  date | None` (singular, one issue's changelog histories): the *first* history entry whose
  `items` contains a `field == "status"` change into an in-progress-category status is the
  start date, even when a later entry leaves and re-enters progress (spec Edge Cases,
  "first entry, not most recent"); returns `None` when no such entry exists (FR-002).
- [X] T017 Implement `_resolve_start_date` in `jira_client.py`, satisfying T016.
- [X] T018 Write failing tests for `compute_jira_flow_metrics(connection, done_statuses, *,
  today=None) -> FlowMetrics` end-to-end (HTTP mocked): a mix of resolved-with-start,
  resolved-without-start (excluded, `excluded_count` reflects it), and currently-in-progress
  issues produces the correct `cycle_time`, `wip`, and `flow_state_counts` lists, with the
  per-day sum invariant holding; an issue beyond the 500 cap is reflected in `capped_count`
  and excluded from every view.
- [X] T019 Implement `compute_jira_flow_metrics` in `jira_client.py`, satisfying T018 -
  orchestrates T007/T009's category detection, T011's issue fetch, T013/T015's capped
  changelog fetch, and T017's per-issue resolution into the three view lists plus the two
  counts.

**Checkpoint**: `compute_jira_flow_metrics()` is complete and fully tested in isolation.
Each user-story phase below only needs to confirm it's wired in and reachable end-to-end.

---

## Phase 3: User Story 1 - See how long completed Jira work actually took (Priority: P1) 🎯 MVP

**Goal**: the cycle-time view reaches the user through both the JSON API and the CLI
summary line, for a Jira-sourced forecast.

**Independent Test**: forecast from a Jira project with mocked resolved issues (some with a
known start, some without) and confirm the cycle-time view is correct and visible through
both surfaces.

- [X] T020 [US1] Write a failing test in `tests/test_web.py`: `POST /api/forecast` with Jira
  fields, `fetch_jira_throughput` and `compute_jira_flow_metrics` mocked, returns
  `flow_metrics.cycle_time` matching the mocked entries; a manual/Linear/CSV request's
  response has `flow_metrics: null`.
- [X] T021 [US1] Wire `compute_jira_flow_metrics` into `src/agile_metrics/web.py`'s Jira
  branch (after `fetch_jira_throughput`, using its returned `done_statuses`) and add
  `flow_metrics: FlowMetrics | None = None` to `ForecastResponseBody`, satisfying T020.
- [X] T022 [US1] Write a failing test in `tests/test_cli.py`: for a Jira source with flow
  metrics available, the output includes a `Flow metrics:` line naming the count of
  resolved-with-known-start issues and the median cycle time (contracts/forecast-api.md);
  manual/Linear/CSV output is unchanged.
- [X] T023 [US1] Wire `compute_jira_flow_metrics` into `src/agile_metrics/cli.py`'s Jira
  branch and extend `_render_result`'s rendering with the `Flow metrics:` line (cycle-time
  portion only - US2 extends it), satisfying T022.
- [X] T024 [US1] Run quickstart.md Scenarios 1 and 4 (start-date detection; web/CLI
  surfaces, cycle-time portion) and confirm they pass.

**Checkpoint**: MVP. A Jira-sourced forecast shows cycle-time through both surfaces.

---

## Phase 4: User Story 2 - See which in-progress Jira issues have been open longest (Priority: P2)

**Goal**: the aging-WIP view reaches the user through both surfaces, including the
"nothing in progress" plain state.

**Independent Test**: forecast from a Jira project with mocked in-progress issues and
confirm the aging view lists them oldest-first through both surfaces; with none in
progress, confirm the plain empty state, not a broken chart.

- [X] T025 [US2] Write a failing test in `tests/test_web.py`: the response's
  `flow_metrics.wip` lists in-progress issues ordered oldest-first by `age_days`.
- [X] T026 [US2] Fix any gap T025 surfaces in `web.py`. Expected to be none -
  `compute_jira_flow_metrics` (T019) already orders `wip`; this task confirms it end-to-end
  rather than assuming it.
- [X] T027 [US2] Write a failing test in `tests/test_cli.py`: the `Flow metrics:` line
  extends with the in-progress count and the oldest age (e.g. `..., 6 in progress (oldest
  17 days)`); a project with none in progress states so plainly in the same line (e.g.
  `..., nothing currently in progress`), not an empty or missing section.
- [X] T028 [US2] Extend `_render_result`'s `Flow metrics:` line in `cli.py` with the WIP
  clause, satisfying T027.
- [X] T029 [US2] Run quickstart.md Scenario 4 (web/CLI surfaces, WIP portion) and confirm
  it passes, including the empty-WIP case.

**Checkpoint**: User Stories 1 AND 2 both independently complete.

---

## Phase 5: User Story 3 - See how Jira work-in-progress has built up over time (Priority: P3)

**Goal**: the cumulative-flow view's daily counts reach the user through the JSON API, with
the per-day invariant holding end-to-end (not just at the model-validator level already
covered in Foundational).

**Independent Test**: forecast from a Jira project spanning several weeks and confirm the
response's `flow_metrics.flow_state_counts` sums to the total tracked-issue count on every
day.

- [X] T030 [US3] Write a failing end-to-end test in `tests/test_web.py`: for a mocked
  multi-week Jira project, every entry in `flow_metrics.flow_state_counts` has
  `not_started + in_progress + done == len(flow_metrics.cycle_time) +
  len(flow_metrics.wip)` (SC-003), read from the actual HTTP response, not the model
  directly.
- [X] T031 [US3] Fix any gap T030 surfaces. Expected to be none - `FlowMetrics`'s own
  validator (T005) already enforces this; this task confirms the invariant survives the
  full JSON round-trip (serialization, web routing) rather than assuming it does.

**Checkpoint**: All three user stories independently complete and verified.

---

## Phase 6: Frontend

- [X] T032 Regenerate `frontend/openapi.json` and `frontend/src/api-types.ts`
  (`npm run generate-types` in `frontend/`) so `flow_metrics` and its nested types exist.
- [X] T033 [P] Write failing tests in `frontend/src/charts/CycleTimeChart.test.tsx`: renders
  one point per `cycle_time` entry with its duration; shows a plain "not enough data" state
  when the list is empty, mirroring the existing distribution chart's own empty-state
  convention (spec 005).
- [X] T034 [P] Implement `CycleTimeChart.tsx`, satisfying T033 - same accessibility pattern
  as the existing chart components (`figure`/`figcaption`/`sr-only` summary, spec 005
  research.md §7).
- [X] T035 [P] Write failing tests in `frontend/src/charts/AgingWipChart.test.tsx`: renders
  `wip` entries oldest-first; shows the plain "nothing in progress" state when empty, not a
  broken or empty-looking chart (spec Edge Cases).
- [X] T036 [P] Implement `AgingWipChart.tsx`, satisfying T035.
- [X] T037 [P] Write failing tests in `frontend/src/charts/CumulativeFlowChart.test.tsx`:
  renders a stacked area/band per day from `flow_state_counts`, labelled consistently with
  the other charts' confidence-level-style labeling conventions where applicable.
- [X] T038 [P] Implement `CumulativeFlowChart.tsx`, satisfying T037.
- [X] T039 Write a failing test in `frontend/src/charts/ForecastCharts.test.tsx` (or
  `App.test.tsx`, matching whichever file already covers `ForecastCharts`): the three new
  charts render only when `result.flow_metrics` is present, alongside the existing four
  forecast charts, not instead of them (FR-007); absent for manual/Linear/CSV results.
- [X] T040 Wire the three new charts into `frontend/src/charts/ForecastCharts.tsx`,
  satisfying T039.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T041 [P] Update `README.md`: document the Jira flow-metrics views (what they show, that
  they're Jira-only in this version, the 500-issue changelog cap and how it's reported); add
  a Status bullet and link `specs/011-jira-flow-metrics/`.
- [ ] T042 Run the live gate: quickstart.md Scenario 6 against a real Jira Cloud site.
  Confirms whether `expand=changelog` bundles on `/rest/api/3/search/jql` (research.md §1) -
  if the fallback path (T012/T013) is what actually runs in practice, note that plainly
  rather than silently; confirm the flow-metrics counts agree with a manual spot-check.
- [X] T043 Run quickstart.md Scenario 7 quality gates: `ruff check`, `ruff format --check`,
  `mypy --strict src`, `pytest --cov`, `pip-audit`, `bandit -c pyproject.toml -r src/`, and
  the frontend gates (`npm run lint`, `npm run typecheck`, `npm test`, `npm audit`, run in
  the node:22 container).
- [X] T044 Write the PR description: note the stacking on `010-jira-integration` (not yet on
  `main`) the same way PR #269 noted its own stacking; confirm no new runtime dependency
  (plan.md Technical Context); list `Closes #N` for every per-task tracking issue created by
  `/speckit-taskstoissues` for this feature.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup (trivially - the frontend file skeletons
  don't block backend work). **Blocks all three user stories** - none of them have a
  computation to wire in before T019 exists.
- **User Stories (Phase 3-5)**: All depend on Foundational (T019) only, but build on each
  other's wiring in practice - US2 (T025-T029) extends the same `Flow metrics:` CLI line
  US1 (T022-T023) created, and US3 (T030-T031) verifies a response shape US1's T021 already
  produces. Not fully independent of each other, same as 010's US1/US2/US3.
- **Frontend (Phase 6)**: Depends on US1's web wiring (T021) for the response shape; the
  three chart components (T033-T038) are independent of each other and of the user-story
  phases' CLI work.
- **Polish (Phase 7)**: Depends on all of the above. T042 (live gate) must pass before the
  PR is marked ready, not just opened.

### Within Each Phase

- Tests before implementation, confirmed failing (Principle III).
- Foundational order: models (T002-T005) -> status categories (T006-T009) -> cheap issue
  fetch (T010-T011) -> changelog fetch and cap (T012-T015) -> start-date resolution and
  the full orchestration (T016-T019). Each layer's tests assume the previous layer exists.

### Parallel Opportunities

- T001 (frontend file skeletons) can happen anytime, independent of all backend work.
- T002-T003 (models) and T006-T009 (status categories) touch different code and could be
  done in parallel, though both block T018-T019.
- T033/T035/T037 (chart tests) and T034/T036/T038 (chart implementations) are each
  independent across the three charts - different files, no shared state.
- T041 (README) can run in parallel with T043/T044 once all stories and the frontend are
  done.

---

## Implementation Strategy

### MVP First

1. Phase 1 -> Phase 2 (`compute_jira_flow_metrics()`, fully tested in isolation).
2. Phase 3 (US1): cycle-time reaches the user through both surfaces.
3. **STOP and VALIDATE** with quickstart.md Scenarios 1 and 4. Demo it.

### Incremental Delivery

1. Setup + Foundational -> the computation exists and is trustworthy on its own.
2. US1 -> validate -> demo (MVP!).
3. US2 -> aging WIP, including the empty state.
4. US3 -> the cumulative-flow invariant survives the full JSON round-trip.
5. Frontend -> the three charts render correctly, including every empty state.
6. Polish (README, the live gate, quality gates, PR description, noting the 010 stacking)
   -> ready to merge, after both this feature's and 010's live gates pass.

---

## Notes

- `[P]` = different files or independent code paths, no dependency on incomplete tasks.
- Commit after each task or logical group.
- Clean-room (Principle I): built from Atlassian's public changelog documentation and
  community write-ups (research.md header) - no comparable flow-metrics code was studied.
- This branch depends on `010-jira-integration` merging first in practice, even though it
  was merged locally to unblock this work - the PR (T044) must say so plainly, and neither
  PR should be treated as mergeable to `main` until both live gates (010's Scenario 5 and
  011's Scenario 6) have passed.
