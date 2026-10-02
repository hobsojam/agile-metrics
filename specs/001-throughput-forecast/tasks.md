# Tasks: Throughput-Based Monte Carlo Forecast

**Input**: Design documents from `specs/001-throughput-forecast/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecasting-api.md, quickstart.md

**Tests**: Included and sequenced before implementation in every phase. The project
constitution's Principle III ("Test-First & Statistically Validated") is NON-NEGOTIABLE and
supersedes the default task-template guidance that treats tests as optional.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project, per plan.md: `src/agile_metrics/`, `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — nothing in later phases can run without this.

- [X] T001 Create `src/agile_metrics/` and `tests/` directories per plan.md's Project Structure (empty `__init__.py` in `src/agile_metrics/`)
- [X] T002 Initialize a `uv`-managed Python 3.11+ project: `pyproject.toml` with `setuptools` build backend, `src/` layout (`[tool.setuptools.packages.find] where = ["src"]`), package name `agile-metrics`, dependencies `numpy`, `pydantic>=2`; dev-group dependencies `pytest`, `pytest-cov`, `mypy`, `ruff`, `hypothesis`, `pip-audit`, `bandit`, `pre-commit` — all with minimum-version (`>=`) bounds per constitution Technology Stack & Constraints
- [X] T003 [P] Configure `[tool.ruff]` (lint + format) and `[tool.mypy]` (`strict = true`) in `pyproject.toml`, and `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) per constitution Technology Stack & Constraints
- [X] T004 [P] Add `.pre-commit-config.yaml` running `ruff-format` and `ruff` per constitution Quality Gates
- [X] T005 [P] Add `.github/workflows/ci.yml` running, in order: `ruff` lint/format check → `mypy --strict` → `pytest --cov` → `pip-audit` → `bandit` — exact order required by constitution Quality Gates ("CI MUST run, in order... A pull request MUST NOT merge if any gate fails")

**Checkpoint**: `uv sync` succeeds; `uv run pytest` runs (0 tests); `uv run ruff check .` and `uv run mypy src` run clean on the empty package.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The three shared pydantic models and the simulation core that every user story
depends on. **No user story work may begin until this phase is complete.**

### Tests for Foundational (write first — MUST fail before implementation exists)

- [X] T006 [P] Validation tests for `ThroughputHistory` in `tests/test_models.py`: reject `completed_per_period` containing a negative or non-whole value (FR-010); reject fewer than `MIN_HISTORICAL_PERIODS` (6) elements (FR-006); reject a series where every element is 0 (FR-007); reject a non-positive `period_duration` (FR-001)
- [X] T007 [P] Validation tests for `ForecastRequest` in `tests/test_models.py`: reject when both `backlog_size` and `target_date` are set, and when neither is set — "exactly one of the two is required" (FR-011); reject `backlog_size` ≤ 0 (FR-008); reject `target_date` not strictly after `reference_date` (FR-008)
- [X] T008 [P] Reproducibility test in `tests/test_simulation.py`: the same `ThroughputHistory` + same integer seed, run twice, produce byte-identical simulated trial arrays (FR-009)
- [X] T009 [P] Statistical convergence test using `hypothesis` in `tests/test_statistical.py`: for a fixed synthetic throughput series, as trial count increases the simulated 50th/70th/85th/95th percentiles converge toward the analytically-computable percentiles of resampling that same series (Constitution Principle III; research.md "Statistical validation strategy")

### Foundational Implementation

- [X] T010 [P] Define `MIN_HISTORICAL_PERIODS = 6` and `DEFAULT_TRIALS = 10_000` constants in `src/agile_metrics/models.py` (research.md "Minimum historical periods" and "Trial count and performance" decisions)
- [X] T011 [P] Implement `ThroughputHistory` pydantic model in `src/agile_metrics/models.py` satisfying T006 (depends on T006, T010)
- [X] T012 [P] Implement `ForecastRequest` pydantic model in `src/agile_metrics/models.py` satisfying T007, including a model validator enforcing the FR-011 exactly-one-of rule (depends on T007)
- [X] T013 Implement `ForecastResult` pydantic model in `src/agile_metrics/models.py`: `outcomes: dict[Literal[50, 70, 85, 95], date | int]`, `trials_run: int`, `periods_used: int` — all three fields always present, never a bare point estimate (FR-004, FR-005; Constitution Principle IV) (depends on T010)
- [X] T014 Implement the seeded bootstrap resampling core in `src/agile_metrics/simulation.py`: `numpy.random.Generator` (PCG64) seeded from an optional integer seed, vectorized sampling-with-replacement from `completed_per_period` across `DEFAULT_TRIALS` trials, satisfying T008 and T009 (depends on T008, T009, T010, T011)
- [X] T015 [P] Shared `pytest` fixtures in `tests/conftest.py`: a valid `ThroughputHistory` (≥6 periods, not all-zero) and a `ForecastRequest` factory for reuse across test files (depends on T011, T012)

**Checkpoint**: Foundation ready — `uv run pytest tests/test_models.py tests/test_simulation.py tests/test_statistical.py` passes. User story implementation can now begin.

---

## Phase 3: User Story 1 - Forecast a completion date for a known backlog size (Priority: P1) 🎯 MVP

**Goal**: `forecast_by_items(history, backlog_size, seed=...)` returns completion dates at
the 50/70/85/95% confidence levels.

**Independent Test**: Supply a historical throughput series and a backlog size; verify the
result contains four distinct confidence-level dates, non-decreasing as confidence rises.

### Tests for User Story 1 (write first — MUST fail before implementation exists)

- [X] T016 [P] [US1] Acceptance test in `tests/test_forecast.py`: valid history + `backlog_size` returns dates at all four confidence levels with `outcomes[50] <= outcomes[70] <= outcomes[85] <= outcomes[95]` — "higher-confidence dates no earlier than lower-confidence dates" (spec US1 Acceptance Scenario 1; FR-005; data-model.md invariant)
- [X] T017 [P] [US1] Acceptance test in `tests/test_forecast.py`: identical history + `backlog_size` + `seed`, called twice, return identical `outcomes` (spec US1 Acceptance Scenario 2; FR-009; SC-003)
- [X] T018 [P] [US1] Acceptance test in `tests/test_forecast.py`: `backlog_size=0` raises a validation error rather than returning a forecast (spec US1 Acceptance Scenario 3; FR-008)

### Implementation for User Story 1

- [X] T019 [US1] Implement `forecast_by_items()` in `src/agile_metrics/forecast.py`: build a `ForecastRequest`, run the simulation core, convert each trial's simulated period-count into a calendar date via `reference_date + periods * history.period_duration`, compute the four percentiles with `numpy.percentile`, return a `ForecastResult` satisfying T016-T018 (depends on T012, T013, T014)
- [X] T020 [US1] Re-export `forecast_by_items` from `src/agile_metrics/__init__.py` per `contracts/forecasting-api.md` (depends on T019)
- [X] T021 [US1] Run `quickstart.md` Scenario 1 verbatim and confirm it matches the documented expected outcome (depends on T020)

**Checkpoint**: User Story 1 is fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Forecast items completed by a target date (Priority: P2)

**Goal**: `forecast_by_date(history, target_date, seed=...)` returns item counts at the
50/70/85/95% confidence levels.

**Independent Test**: Supply a historical throughput series and a future target date; verify
the result contains four distinct confidence-level item counts, non-increasing as confidence
rises.

### Tests for User Story 2 (write first — MUST fail before implementation exists)

- [X] T022 [P] [US2] Acceptance test in `tests/test_forecast.py`: valid history + `target_date` returns item counts at all four confidence levels with `outcomes[50] >= outcomes[70] >= outcomes[85] >= outcomes[95]` — "higher-confidence counts no greater than lower-confidence counts" (spec US2 Acceptance Scenario 1; FR-005; data-model.md invariant)
- [X] T023 [P] [US2] Acceptance test in `tests/test_forecast.py`: `target_date` equal to or before `reference_date` raises a validation error rather than returning a forecast (spec US2 Acceptance Scenario 2; FR-008)

### Implementation for User Story 2

- [X] T024 [US2] Implement `forecast_by_date()` in `src/agile_metrics/forecast.py`: build a `ForecastRequest`, compute the whole number of periods between `reference_date` and `target_date` using `history.period_duration`, run the simulation core, compute the four percentiles of items completed, return a `ForecastResult` satisfying T022-T023 (depends on T012, T013, T014; reuses the simulation core built for US1)
- [X] T025 [US2] Re-export `forecast_by_date` from `src/agile_metrics/__init__.py` per `contracts/forecasting-api.md` (depends on T024)
- [X] T026 [US2] Run `quickstart.md` Scenario 2 verbatim and confirm it matches the documented expected outcome (depends on T025)

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - See the full forecast distribution and its basis (Priority: P3)

**Goal**: Every forecast result states how many trials were run and how many historical
periods it was based on, not just the forecast values.

**Independent Test**: Request any valid forecast (either mode) and verify the result
includes `trials_run` and `periods_used` alongside the forecast values.

### Tests for User Story 3 (write first — MUST fail before implementation exists)

- [X] T027 [P] [US3] Acceptance test in `tests/test_forecast.py`: results from both `forecast_by_items` and `forecast_by_date` include `trials_run == DEFAULT_TRIALS` and `periods_used == len(history.completed_per_period)` (spec US3 Acceptance Scenario 1; FR-004)

### Implementation for User Story 3

- [X] T028 [US3] Verify T027 passes against the `forecast.py` implementations from US1/US2 (the fields are already mandatory on `ForecastResult` per T013); fix `forecast_by_items`/`forecast_by_date` if either leaves them unpopulated or incorrect (depends on T019, T024, T027) — passed without modification; both functions already populated these fields correctly

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Run `quickstart.md` Scenario 3 (rejecting insufficient/all-zero history) verbatim and confirm both `ValidationError` cases match the documented expected outcome (SC-006)
- [X] T030 [P] Update `README.md`'s "Usage (planned)" section: remove the "(planned)" marker and confirm the existing code example runs as-is against the real package
- [X] T031 Run the full constitution Quality Gate sequence clean across the repo: `ruff`, `mypy --strict`, `pytest --cov`, `pip-audit`, `bandit` (depends on all prior tasks)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational only (shares the Phase 3 simulation core, but does not depend on US1's forecast.py code)
- **User Story 3 (Phase 5)**: Depends on Foundational; its test (T027) exercises both US1 and US2 implementations, so in practice runs after both
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each Phase

- Tests MUST be written and FAIL before their corresponding implementation task
- Models before simulation core before orchestration (`forecast.py`)
- Each story's checkpoint must pass before moving to the next priority

### Parallel Opportunities

- All Setup tasks marked `[P]` (T003-T005) can run in parallel once T002 completes
- All Foundational test tasks (T006-T009) can run in parallel; T010-T012 and T015 can run in parallel; T013 and T014 are each gated by specific predecessors
- T016-T018 (US1 tests) can run in parallel; T022-T023 (US2 tests) can run in parallel
- US1 (Phase 3) and US2 (Phase 4) implementation can proceed in parallel once Foundational is done, since `forecast_by_items` and `forecast_by_date` are independent functions in the same file touching different code paths — coordinate to avoid merge conflicts in `forecast.py`/`__init__.py`

---

## Parallel Example: Foundational Tests

```bash
Task: "Validation tests for ThroughputHistory in tests/test_models.py"
Task: "Validation tests for ForecastRequest in tests/test_models.py"
Task: "Reproducibility test in tests/test_simulation.py"
Task: "Statistical convergence test in tests/test_statistical.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything else)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `quickstart.md` Scenario 1 independently
5. User Story 1 alone is a demonstrable MVP — "when will this backlog be done?"

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate → MVP
3. User Story 2 → validate → adds "how much by this date?"
4. User Story 3 → validate → adds transparency fields to every result
5. Polish

---

## Notes

- `[P]` tasks touch different files or independent code paths — no shared-state conflicts
- `[Story]` label maps each task to its user story for traceability back to spec.md
- Per the constitution's Development Workflow, this `tasks.md` is a disposable planning
  draft: **before any implementation task above begins, convert this file into GitHub
  Issues via `/speckit-taskstoissues`**, which then become the system of record for
  tracking the work — not this file.
- Commit after each task or logical group, on the `001-throughput-forecast` branch
- Verify each test fails before writing the implementation that makes it pass
