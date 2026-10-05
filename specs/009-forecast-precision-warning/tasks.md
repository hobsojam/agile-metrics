---

description: "Task list for Forecast precision warning (009-forecast-precision-warning)"
---

# Tasks: Forecast Precision Warning

**Input**: Design documents from `specs/009-forecast-precision-warning/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecast-api.md,
quickstart.md

**Tests**: Included and placed before implementation in every phase (Constitution
Principle III). The core computation is deterministic given its inputs (no new randomness),
so "test-first" here means seeded simulations with known-wide and known-narrow historical
throughput, mirroring every other `forecast.py` test already in `test_forecast.py`.

**Organization**: One new model (`PrecisionWarning`) and one new private helper
(`_compute_precision_warning`) in the library, called from both `forecast_by_items` and
`forecast_by_date` right before each builds its `ForecastResult` (data-model.md). `web.py`
needs zero code changes — `ForecastResponseBody(ForecastResult)` inherits the new field
automatically. `cli.py` and `frontend/src/App.tsx` each need one explicit rendering change.
US3 (consistency) is almost entirely a verification phase, same pattern as 006/007/008's
lowest-priority story — there's exactly one computation site, so there's little left to
wire by the time US1/US2 land.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Per plan.md: `src/agile_metrics/models.py`, `src/agile_metrics/forecast.py`,
`src/agile_metrics/cli.py` (backend); `frontend/openapi.json`, `frontend/src/api-types.ts`,
`frontend/src/App.tsx` (frontend). No new files beyond tests. `web.py` is explicitly
unchanged.

---

## Phase 1: Setup

- [X] T001 Add the `PrecisionWarning` model to `src/agile_metrics/models.py`, alongside
  `ForecastResult`: a single field `message: str` (data-model.md) — "Plain-language
  explanation of why this forecast's precision is low." No validation beyond pydantic's
  default non-empty-string behavior; absence is modeled as the field being absent entirely,
  not an empty message. Add `precision_warning: PrecisionWarning | None = None` as a new,
  fully optional field on `ForecastResult`, after `projection` — MUST NOT change the type,
  meaning, or validation of any existing `ForecastResult` field (spec FR-004).

**Checkpoint**: The model and field exist; `ForecastResult` still constructs with no
`precision_warning` argument supplied (defaults to `None`), so every existing call site in
`forecast.py` keeps compiling unmodified until Phase 2 wires it in.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: `_compute_precision_warning()` fully correct and tested in isolation — this is
the one function both `forecast_by_items()` and `forecast_by_date()` will call (US1/US2/US3
all depend on it existing and being right before any wiring happens).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Write failing tests in `tests/test_forecast.py` for
  `_compute_precision_warning(outcomes, reference_date)` per research.md §1's formula:
  - Date-mode (`p50`/`p95` are `date` values): `center = (p50 - reference_date).days`,
    `spread = (p95 - p50).days`, `ratio = spread / max(center, 1)`. A wide pair (e.g. `p50`
    9 years out, `p95` 23 years out → `ratio ≈ 1.6`) returns a `PrecisionWarning`. A tight
    pair (e.g. `p50` 10 weeks out, `p95` 13 weeks out → `ratio ≈ 0.3`) returns `None`.
  - Count-mode (`p50`/`p95` are `int` values, `p95 <= p50` per the mirrored-percentile
    convention): `center = p50`, `spread = p50 - p95`, same `ratio`/threshold — confirm both
    a wide and a tight count-mode pair produce the same present/absent result as their
    date-mode equivalents at the same ratio.
  - Threshold boundary: `ratio` exactly `1.0` MUST NOT warn (the condition is `ratio >
    1.0`, strictly greater, per research.md §2's confirmed decision) — construct `center`/
    `spread` values that divide to exactly `1.0` and assert the result is `None`.
  - `max(center, 1)` floor: `center == 0` (date-mode `p50 == reference_date`, or
    count-mode `p50 == 0`) with a non-zero `spread` MUST NOT raise `ZeroDivisionError` and
    MUST still return a `PrecisionWarning` (research.md §1's documented floor rationale).
- [X] T003 Implement `_compute_precision_warning(outcomes: dict[int, date | int],
  reference_date: date) -> PrecisionWarning | None` in `src/agile_metrics/forecast.py`,
  satisfying T002, following the existing private-helper pattern
  (`_build_distribution_dates`/`_build_distribution_ints`) of branching on whether
  `outcomes[50]` is a `date` or an `int`.

**Checkpoint**: `_compute_precision_warning()` is complete and fully tested in isolation.
Each user story phase below only needs to confirm it's wired in and reachable end-to-end.

---

## Phase 3: User Story 1 - See a warning when a forecast is too imprecise to plan against (Priority: P1) 🎯 MVP

**Goal**: `forecast_by_items()` and `forecast_by_date()` each set `precision_warning` on
their returned `ForecastResult` when the computed ratio exceeds the threshold, and leave it
`None` otherwise — with every other field on the result untouched (spec FR-004).

**Independent Test**: Run a forecast against historical throughput known to be sparse or
highly inconsistent, and confirm `precision_warning` is set; run one against consistent,
ample historical data, and confirm it's `None`. Both modes.

- [X] T004 [US1] Write a failing test in `tests/test_forecast.py`: `forecast_by_items()`
  called with a seeded, sparse/zero-heavy history against a large backlog produces a
  `ForecastResult` with `precision_warning` set (not `None`); called with a seeded,
  consistent/ample history against a small backlog, `precision_warning` is `None`.
- [X] T005 [US1] Implement the wiring in `forecast_by_items()`: compute
  `precision_warning = _compute_precision_warning(outcomes, ref_date)` right before
  constructing `ForecastResult`, and pass it through, satisfying T004.
- [X] T006 [US1] Write a failing test in `tests/test_forecast.py`: the same two scenarios
  (wide vs. tight) for `forecast_by_date()` (count-mode) — a seeded sparse/inconsistent
  history produces `precision_warning` set; a seeded consistent/ample one produces `None`.
- [X] T007 [US1] Implement the identical wiring in `forecast_by_date()`, satisfying T006.
- [X] T008 [US1] Write a failing regression test in `tests/test_forecast.py`: for a fixed
  seed, `outcomes`, `distribution`, `projection`, `trials_run`, and `periods_used` are
  exactly identical to their values before this feature existed (spec FR-004 — purely
  additive). The simplest check: every pre-existing assertion in `test_forecast.py` and
  `test_models.py` that doesn't reference `precision_warning` must still pass unmodified.
- [X] T009 [US1] Fix any gap T008 surfaces. Expected to be none — `_compute_precision_warning`
  reads `outcomes`/`reference_date` without mutating them, and the new field defaults to
  `None`, so no existing field's value or type changes.
- [X] T010 [US1] Run quickstart.md Scenarios 1-2 and confirm they pass.

**Checkpoint**: MVP. Both forecast modes correctly flag (or don't flag) a forecast's
imprecision, with zero regression to existing output.

---

## Phase 4: User Story 2 - Understand why a forecast was flagged (Priority: P2)

**Goal**: The warning carries a plain-language message naming the actual computed ratio
(research.md §4), and that message is visible through the CLI and the web UI, not just
present on the `ForecastResult` object.

**Independent Test**: Trigger the warning and confirm the message explains, in plain
language, why this forecast is imprecise. Confirm the CLI prints it and the web UI shows a
visible, distinctly-styled banner for it.

- [X] T011 [US2] Write a failing test in `tests/test_forecast.py`: the `message` on a
  triggered `PrecisionWarning` is a non-empty, plain-language sentence that names the actual
  computed ratio (e.g. contains a number formatted to one decimal place) — not a static,
  unexplained label. Confirm two different wide scenarios with different ratios produce
  messages containing their respective different numbers.
- [X] T012 [US2] Implement the message text in `_compute_precision_warning` per
  contracts/forecast-api.md's example wording ("This forecast's range is very wide: the 95%
  outcome is roughly {ratio:.1f}x further from the median than the median itself is from
  today. Treat these numbers as a rough risk range, not a committed plan."), satisfying
  T011.
- [X] T013 [US2] Write a failing test in `tests/test_cli.py`: `_render_result` appends one
  additional line, prefixed `⚠`, containing the warning's message, after the four
  confidence-level lines, when `result.precision_warning` is present; when it is `None`,
  the rendered output is byte-identical to today's (no blank line, no placeholder).
- [X] T014 [US2] Implement the line in `src/agile_metrics/cli.py`'s `_render_result`,
  satisfying T013.
- [X] T015 [US2] Regenerate `frontend/openapi.json` and `frontend/src/api-types.ts` to
  include the new `precision_warning` field on the forecast response schema
  (contracts/forecast-api.md).
- [X] T016 [US2] Write a failing test in `frontend/src/App.test.tsx`: a visible,
  amber/warning-styled banner (distinct from the existing red `role="alert"` error banner)
  renders below the four confidence-level outcomes when `result.precision_warning` is
  present, showing its `message`; no banner renders when it's absent, and the existing
  confidence-level list and charts are unaffected either way.
- [X] T017 [US2] Implement the banner in `frontend/src/App.tsx`, rendered inside the
  existing `result && submittedInputs` block alongside the confidence-level list,
  satisfying T016.
- [X] T018 [US2] Run quickstart.md Scenarios 3-4 and confirm they pass.

**Checkpoint**: User Stories 1 AND 2 both independently complete — the warning fires
correctly and explains itself everywhere a human reads a forecast result.

---

## Phase 5: User Story 3 - Consistent warning across every data source, mode, and surface (Priority: P3)

**Goal**: The same underlying `ForecastResult` produces an identical warning through every
presentation surface (CLI, web UI, JSON API) and regardless of which data source populated
the `ThroughputHistory` that fed it — trivially true once computed once in the library, but
verified explicitly rather than assumed (mirrors 006/007/008's lowest-priority phases).

**Independent Test**: Request a forecast expected to trigger the warning through the JSON
API directly and confirm the response's `precision_warning` field matches exactly what
calling `forecast_by_items`/`forecast_by_date` directly would produce — no divergence, no
recomputation in `web.py`.

- [X] T019 [US3] Write a failing end-to-end test in `tests/test_web.py`: `POST
  /api/forecast` (and, separately, `/api/forecast/csv`) with inputs expected to trigger the
  warning returns a JSON response whose `precision_warning` object (`message`) is identical
  to calling `forecast_by_items`/`forecast_by_date` directly with the same
  `ThroughputHistory` and parameters; and a request expected *not* to trigger it returns
  `precision_warning: null`.
- [X] T020 [US3] Fix any gap T019 surfaces. Expected to be none —
  `ForecastResponseBody(ForecastResult)` inherits the field automatically (data-model.md);
  `web.py` requires zero code changes for this feature.
- [X] T021 [US3] Write a failing test in `tests/test_forecast.py` confirming the warning is
  identical regardless of how the `ThroughputHistory` feeding it was constructed: build the
  same `completed_per_period`/`period_duration` once directly and once via
  `csv_item_import`'s CSV-parsing path, run `forecast_by_items` on both with the same seed,
  and confirm `precision_warning` (presence and message) is equal. (The Linear import path
  already produces a `ThroughputHistory` of the identical shape per spec 006 — no separate
  check needed, since the warning is computed downstream of `ThroughputHistory`
  construction, not aware of which path built it.)
- [X] T022 [US3] Fix any gap T021 surfaces. Expected to be none — `_compute_precision_warning`
  depends only on `outcomes`/`reference_date`, which are computed identically regardless of
  how `ThroughputHistory` was constructed upstream.

**Checkpoint**: All three user stories independently complete and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T023 [P] Update `README.md`: briefly document the precision warning (what it means,
  that there's no new flag/configuration, and where it appears — CLI output, web UI banner,
  JSON API response); bump the Status section to "Nine features" and link
  `specs/009-forecast-precision-warning/`.
- [X] T024 Run quickstart.md Scenario 5 (manual CLI end-to-end comparison: a sparse
  `--history "1,0,2,0,1,0" --backlog-size 50` triggers the warning; a consistent `--history
  "8,9,7,8,10,9,8,7" --backlog-size 10` does not) and Scenario 6's full quality gate
  sequence — backend (`ruff check`, `ruff format --check`, `mypy --strict src`, `pytest
  --cov`) and frontend (`npm run lint`, `npm run typecheck`, `npm test`, `npm audit`), since
  this feature touches both.
- [X] T025 Write the PR description: confirm no new runtime dependency was introduced
  (plan.md "Primary Dependencies: None new"), and the constitution principles touched
  (plan.md's Constitution Check table, especially Principle IV — explicitly strengthened by
  this feature). List `Closes #N` for every per-task tracking issue created by
  `/speckit-taskstoissues` for this feature, per the `/speckit-implement` fix in PR #221.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup (`PrecisionWarning` must exist before
  `_compute_precision_warning` can return one). **Blocks all three user stories**.
- **User Stories (Phase 3-5)**: All depend on Foundational only. US1 (T004-T007) must land
  before US2's CLI/web rendering (T013-T017) has anything non-`None` to render, and before
  US3's end-to-end checks (T019, T021) have a wired code path to verify — same
  not-fully-independent relationship 008's three stories had, since all three verify facets
  of one computation.
- **Polish (Phase 6)**: Depends on all three user stories.

### Within Each Phase

- Tests before implementation, confirmed failing (Principle III).
- Foundational: model field (T001) -> computation (T002-T003).
- Each story: write the test -> implement/confirm -> quickstart verification.

### Parallel Opportunities

- T004-T005 (`forecast_by_items` wiring) and T006-T007 (`forecast_by_date` wiring) touch
  the same file but different functions — write both test pairs first, then implement both,
  rather than true parallel execution.
- T015 (frontend type regeneration) and T013-T014 (CLI render) touch disjoint files and
  can run in parallel.
- T023 (README) can run in parallel with T024/T025 once all three stories are done.

---

## Implementation Strategy

### MVP First

1. Phase 1 -> Phase 2 (`_compute_precision_warning()`, fully tested in isolation).
2. Phase 3 (US1): both forecast modes correctly set/clear `precision_warning`.
3. **STOP and VALIDATE** with quickstart.md Scenarios 1-2. Demo it.

### Incremental Delivery

1. Setup + Foundational -> the computation exists and is trustworthy on its own.
2. US1 -> validate -> demo (MVP!).
3. US2 -> the warning explains itself, visibly, on every human-facing surface.
4. US3 -> confirms zero divergence across data sources and the JSON API.
5. Polish (README, manual CLI comparison, quality gates, PR description) -> ready to merge.

---

## Notes

- `[P]` = different files or independent code paths, no dependency on incomplete tasks.
- Commit after each task or logical group.
- Clean-room (Principle I): a ratio computed entirely from this project's own existing
  `outcomes` values — no comparable code exists to study or avoid.
- This feature is purely additive by design (spec FR-004) — every "fix any gap" task
  (T009, T020, T022) is expected to find nothing, same as 006/007/008's equivalent
  verification tasks; they exist to make that confirmation explicit rather than assumed.
