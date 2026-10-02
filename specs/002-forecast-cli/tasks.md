# Tasks: Forecast CLI

**Input**: Design documents from `specs/002-forecast-cli/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-interface.md, quickstart.md

**Tests**: Included and sequenced before implementation in every phase. The project
constitution's Principle III ("Test-First & Statistically Validated") is NON-NEGOTIABLE and
supersedes the default task-template guidance that treats tests as optional.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent testing
of each story. Note: unlike `001-throughput-forecast` (where each story was a separate
library function), User Stories 1 and 2 here share one CLI command implementation that
branches on which flag was supplied — this is called out explicitly where it affects task
dependencies.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project, per plan.md: adds `src/agile_metrics/cli.py` and `tests/test_cli.py` to the
existing package; `Dockerfile`/`.dockerignore` at the repository root.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Add `typer` (core dependency, not dev-only) to `pyproject.toml`'s
  `[project.dependencies]`, and register the console-script entry point
  `[project.scripts] agile-metrics = "agile_metrics.cli:app"`
- [ ] T002 [P] Add `.dockerignore` at the repository root excluding `.venv/`, `.git/`,
  `__pycache__/`, `*.egg-info/`, `specs/`, `.github/`, `tests/`, and dev-only config files,
  to keep the Docker build context minimal
- [ ] T003 [P] Run `uv lock` to update `uv.lock` for the new `typer` dependency (required
  before any `--locked` command succeeds again)

**Checkpoint**: `uv sync --locked` installs `typer`; the `agile-metrics` console script is
registered (it will fail to import until `cli.py` exists in later phases — expected at this
stage, since there is no code yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The CLI's shared helpers (input parsing, output rendering) and command
skeleton that both User Story 1 and User Story 2 build on. **No user story work may begin
until this phase is complete.**

### Tests for Foundational (write first — MUST fail before implementation exists)

- [ ] T004 [P] Unit tests in `tests/test_cli.py` for a `_build_history(history: str,
  period_days: int) -> ThroughputHistory` helper: valid comma-separated input builds the
  correct `ThroughputHistory`; a malformed history string (e.g. non-numeric) raises
  `ValueError` (contracts/cli-interface.md's `--history`/`--period-days` flags; FR-001)
- [ ] T005 [P] Unit tests in `tests/test_cli.py` for a `_render_result(result:
  ForecastResult) -> str` helper: output text contains `trials_run`, `periods_used`, and all
  four confidence levels, for both a date-valued and an int-valued `ForecastResult` (FR-003;
  Constitution Principle IV)

### Foundational Implementation

- [ ] T006 [P] Implement `_build_history()` in `src/agile_metrics/cli.py` satisfying T004
  (depends on T004)
- [ ] T007 [P] Implement `_render_result()` in `src/agile_metrics/cli.py` satisfying T005
  (depends on T005)
- [ ] T008 Implement the `typer` `app` and its single command in `src/agile_metrics/cli.py`
  declaring all five flags (`--history`, `--period-days`, `--backlog-size`, `--target-date`,
  `--seed` — contracts/cli-interface.md) with the body wrapped in a `try`/`except` that
  catches `pydantic.ValidationError` and `ValueError`, prints a single `Error: <message>`
  line to stderr, and raises `typer.Exit(1)` — no forecast call wired in yet (FR-005;
  research.md "Error handling") (depends on T006, T007)

**Checkpoint**: `uv run --locked pytest tests/test_cli.py` passes for the helper unit tests;
the CLI skeleton parses its flags and maps errors correctly, but does not yet produce a
forecast.

---

## Phase 3: User Story 1 - Completion-date forecast from the command line (Priority: P1) 🎯 MVP

**Goal**: `agile-metrics --history ... --period-days ... --backlog-size ...` prints a
completion-date forecast.

**Independent Test**: Invoke the CLI with a sample history and backlog size; verify the
output contains dates at all four confidence levels.

### Tests for User Story 1 (write first — MUST fail before implementation exists)

- [ ] T009 [P] [US1] `CliRunner` test in `tests/test_cli.py`: valid `--history`/
  `--period-days`/`--backlog-size`/`--seed` exits 0 and prints four confidence-level dates
  (spec US1 Acceptance Scenario 1)
- [ ] T010 [P] [US1] `CliRunner` test in `tests/test_cli.py`: identical inputs run twice
  produce identical stdout (spec US1 Acceptance Scenario 2; FR-004)
- [ ] T011 [P] [US1] `CliRunner` test in `tests/test_cli.py`: `--backlog-size 0` exits 1
  with a clean `Error: ...` message, never a traceback (spec US1 Acceptance Scenario 3)

### Implementation for User Story 1

- [ ] T012 [US1] Wire the `--backlog-size` branch into the command body in
  `src/agile_metrics/cli.py`: build the history via `_build_history`, call
  `forecast_by_items`, render via `_render_result`, print to stdout — satisfying T009-T011
  (depends on T008, T009, T010, T011)
- [ ] T013 [US1] Run `quickstart.md` Scenario 1 verbatim and confirm it matches the
  documented expected outcome (depends on T012)

**Checkpoint**: User Story 1 is fully functional and independently testable — this is the
MVP.

---

## Phase 4: User Story 2 - Items-completed forecast from the command line (Priority: P2)

**Goal**: `agile-metrics --history ... --period-days ... --target-date ...` prints an
items-completed forecast.

**Independent Test**: Invoke the CLI with a sample history and a future target date; verify
the output contains item counts at all four confidence levels.

**Note on dependencies**: Unlike `001-throughput-forecast`'s two separate library
functions, both forecast modes here are branches of the *same* command function built in
Phase 2/3. T016 therefore depends on T012 existing (same function), even though the
*behavior* it adds is independently testable once built.

### Tests for User Story 2 (write first — MUST fail before implementation exists)

- [ ] T014 [P] [US2] `CliRunner` test in `tests/test_cli.py`: valid `--history`/
  `--period-days`/`--target-date`/`--seed` exits 0 and prints four confidence-level item
  counts (spec US2 Acceptance Scenario 1)
- [ ] T015 [P] [US2] `CliRunner` test in `tests/test_cli.py`: a `--target-date` that is not
  in the future exits 1 with a clean error message (spec US2 Acceptance Scenario 2)

### Implementation for User Story 2

- [ ] T016 [US2] Wire the `--target-date` branch into the same command body in
  `src/agile_metrics/cli.py`: call `forecast_by_date` instead, reusing `_build_history`/
  `_render_result` — satisfying T014-T015 (depends on T012, T014, T015)
- [ ] T017 [US2] Run `quickstart.md` Scenario 2 verbatim and confirm it matches the
  documented expected outcome (depends on T016)

**Checkpoint**: User Stories 1 AND 2 both work.

---

## Phase 5: User Story 3 - Run without installing Python or any dependencies (Priority: P3)

**Goal**: The CLI runs as a container image, producing identical output to a local run.

**Independent Test**: Build the container image and run it with the same input as User
Story 1; verify identical output with no local Python installation involved.

### Tests for User Story 3 (write first — MUST fail before implementation exists)

- [ ] T018 [P] [US3] Add a step to `.github/workflows/ci.yml` that builds the Docker image
  and runs it against the Scenario 1 sample input, asserting exit code 0 and the expected
  date substring in stdout — written now, expected to fail (no `Dockerfile` exists yet)
  (spec US3 Acceptance Scenario 1; research.md "CI coverage for the container")

### Implementation for User Story 3

- [ ] T019 [US3] Write a multi-stage `Dockerfile` at the repository root: `builder` stage
  (`python:3.11-slim` + `uv`, running `uv sync --locked --no-dev` — installing only
  `[project.dependencies]`, never the dev/test extras); `runtime` stage (fresh
  `python:3.11-slim`, copies only the built venv and `src/` from `builder`, `ENTRYPOINT` the
  `agile-metrics` console script) — satisfying T018 (depends on T006, T007, T008, T012,
  T016, T018)
- [ ] T020 [US3] Run `quickstart.md` Scenario 3 (container build + run) verbatim and confirm
  the output matches Scenario 1's local run exactly (depends on T019)
- [ ] T021 [US3] Confirm the CI Docker smoke-test step added in T018 now passes (depends on
  T019, T020)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T022 [P] Run `quickstart.md` Scenario 4 (neither `--backlog-size` nor `--target-date`
  supplied) verbatim and confirm the clean error + exit 1 (SC-003)
- [ ] T023 [P] Update `README.md` to document CLI and container usage, replacing/extending
  the existing Python-library usage section (constitution: README MUST be updated when a
  feature completes)
- [ ] T024 Run the full constitution Quality Gate sequence clean across the repo: `ruff`,
  `mypy --strict`, `pytest --cov`, `pip-audit`, `bandit`, plus the new Docker CI smoke-test
  step (depends on all prior tasks)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational *and* on User Story 1's command
  function existing (T012) — see the note under Phase 4
- **User Story 3 (Phase 5)**: Depends on the finished command (T012, T016) since the
  Dockerfile packages the whole CLI, not a specific forecast mode
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each Phase

- Tests MUST be written and FAIL before their corresponding implementation task
- Helpers (`_build_history`, `_render_result`) before the command skeleton before either
  forecast-mode branch before the Dockerfile

### Parallel Opportunities

- T002-T003 (Setup) can run in parallel once T001 completes
- T004-T005 (Foundational tests) can run in parallel; T006-T007 (their implementations) can
  run in parallel with each other, but both must precede T008
- T009-T011 (US1 tests) can run in parallel; T014-T015 (US2 tests) can run in parallel
- T022-T023 (Polish) can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything else)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `quickstart.md` Scenario 1 independently
5. User Story 1 alone is a demonstrable MVP — forecasting from the command line

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate → MVP (CLI forecasting works locally)
3. User Story 2 → validate → adds the items-by-date question
4. User Story 3 → validate → adds the container distribution path
5. Polish

---

## Notes

- `[P]` tasks touch different files or independent code paths — no shared-state conflicts
- `[Story]` label maps each task to its user story for traceability back to spec.md
- Per the constitution's Development Workflow, this `tasks.md` is a disposable planning
  draft: **before any implementation task above begins, convert this file into GitHub
  Issues via `/speckit-taskstoissues`**, which then become the system of record for
  tracking the work — not this file.
- Commit after each task or logical group, on the `002-forecast-cli` branch
- Verify each test fails before writing the implementation that makes it pass
