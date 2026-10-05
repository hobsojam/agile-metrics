---

description: "Task list for CSV item import (007-csv-item-import)"
---

# Tasks: CSV Item Import

**Input**: Design documents from `specs/007-csv-item-import/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecast-api.md, quickstart.md

**Tests**: Included and placed before implementation in every phase (Constitution
Principle III). Unlike Linear (006), there is no HTTP layer to mock here — CSV parsing and
bucketing are pure string/data-in, model-out logic, so every test in Foundational and US1/US2
runs with no mocking at all.

**Organization**: `csv_item_import.py` (header validation, row parsing into `Item`, period
derivation, bucketing) is needed by both the web UI (US1) and the CLI (US2), so it's built
once in Foundational, on top of a new `Item` model in `models.py`. Each story then wires its
own surface (web multipart endpoint / CLI flag) on top of the same shared functions. US3
(error clarity) is mostly verification that Foundational + US1 + US2 already produce the
right distinct messages, not new production code — same pattern 006 established.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Per plan.md: one new backend module (`src/agile_metrics/csv_item_import.py`), one new model
(`Item` in `src/agile_metrics/models.py`), additive changes to `src/agile_metrics/cli.py`
and `src/agile_metrics/web.py` (a new endpoint, not a change to the existing one), additive
changes to `frontend/src/App.tsx`. No new top-level directories.

---

## Phase 1: Setup

- [X] T001 Create `src/agile_metrics/csv_item_import.py` with the exception hierarchy:
  `CsvImportError` (base), `CsvMissingColumnError`, `CsvRowError`. Each MUST carry its
  final, user-facing message as the exception's own `str()` (data-model.md), naming the
  specific row number and/or column — same pattern as `LinearIntegrationError`'s
  subclasses (006).
- [X] T002 [P] Create `tests/test_csv_item_import.py` with a reusable fixture providing a
  well-formed sample CSV text (at least 6 periods' worth of completed items plus one
  still-open item with a blank `end_date`), for use by every later test task in this file.

**Checkpoint**: Module and test scaffolding exist; no parsing or bucketing logic yet.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: `parse_items_csv()` and `bucket_items_to_throughput()` end-to-end - these are
the two functions both US1 and US2 call.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### The `Item` model

- [X] T003 Write failing tests in `tests/test_models.py` for a new `Item` model: `id: str`
  MUST reject a blank value (data-model.md - "the one column this feature treats as
  required per row"); `type: str` and `title: str` accept any string including `""`, no
  format constraint; `start_date: date | None` and `end_date: date | None` each accept
  `None` and a valid ISO 8601 date string, and reject a non-blank, non-ISO-8601 string
  (e.g. `"not-a-date"`) with a `pydantic.ValidationError` naming that field.
- [X] T004 Implement `Item` in `src/agile_metrics/models.py` satisfying T003, relying on
  `pydantic`'s native `str -> date` coercion for `start_date`/`end_date` rather than
  hand-written date parsing (research.md §5 - "pydantic is the one source of truth").

### Header validation and row parsing

- [X] T005 Write failing tests in `tests/test_csv_item_import.py` for `parse_items_csv()`:
  a CSV with all five required columns (`id, type, title, start_date, end_date`), in any
  order, with extra unrecognized columns present, parses into one `Item` per data row in
  file order (research.md §1, Edge Cases); a CSV missing one of the five required columns
  raises `CsvMissingColumnError` naming the missing column, before any row is read
  (FR-008); a row with a blank `id` raises `CsvRowError` naming that 1-indexed data row and
  the `id` field (FR-007, research.md §5 - row numbers count data rows only, starting at 1,
  excluding the header); a row with a non-blank, unparsable `start_date` or `end_date`
  raises `CsvRowError` naming that row and the specific field; a row with a *blank*
  `end_date` is accepted, not rejected, and its `Item.end_date` is `None` (FR-010).
- [X] T006 Implement `parse_items_csv(csv_text: str) -> list[Item]` in
  `csv_item_import.py` satisfying T005, using `csv.DictReader` (research.md §1) and
  translating any `pydantic.ValidationError` raised while constructing an `Item` for a row
  into a `CsvRowError` naming that row number and the failing field(s).

### Period-count derivation and bucketing

- [X] T007 Write failing tests in `tests/test_csv_item_import.py` for
  `bucket_items_to_throughput()`: given a fixed set of `Item`s with known `end_date`
  values and a `period_duration`, bucket `k` (0 = oldest) covers exactly `[today -
  (periods - k) * period_duration, today - (periods - k - 1) * period_duration)`
  (data-model.md's formula), with `periods` derived from the earliest `end_date` to today
  (research.md §4); an `end_date` that falls before the computed range (a future-dated
  completion, relative to how the range is anchored) is silently excluded, not clamped
  into the wrong bucket; a case where **zero** items have any `end_date` produces a
  `ThroughputHistory` of exactly `MIN_HISTORICAL_PERIODS` all-zero periods, which raises
  the *existing* all-zero `pydantic.ValidationError` already pinned in `test_models.py`
  (FR-010) - not a new error; a case where completions span **fewer** than
  `MIN_HISTORICAL_PERIODS` periods raises the *existing* too-few-periods message instead
  (distinct from the all-zero case - research.md §4 explains why no clamping is applied).
- [X] T008 Implement `bucket_items_to_throughput(items: list[Item], period_duration:
  timedelta) -> ThroughputHistory` in `csv_item_import.py` satisfying T007.

**Checkpoint**: `parse_items_csv()` and `bucket_items_to_throughput()` are complete and
fully tested in isolation. Both user story phases below only need to call them in sequence.

---

## Phase 3: User Story 1 - Forecast from a CSV of completed items in the web UI (Priority: P1) 🎯 MVP

**Goal**: A user can get a forecast through the web UI using CSV import (upload or paste)
instead of manual paste or Linear.

**Independent Test**: `POST /api/forecast/csv` (multipart, `csv_file` or `csv_text`)
returns the same 200 response shape as manual paste for equivalent underlying data.

### Backend

- [X] T009 [US1] Write failing tests in `tests/test_web.py` for a new
  `POST /api/forecast/csv` endpoint: accepts `multipart/form-data` with either `csv_file`
  (an uploaded file) or `csv_text` (pasted text) plus `period_days`/`backlog_size`/
  `target_date`/`seed` form fields; rejects neither-or-both of `csv_file`/`csv_text` with
  `"exactly one of csv_file or csv_text is required"` (contracts/forecast-api.md); reuses
  the *existing* "exactly one of `backlog_size`/`target_date`" message unchanged; for the
  same underlying per-period counts and seed, returns a response whose `outcomes` are
  identical to `POST /api/forecast`'s manual-paste response.
- [X] T010 [US1] Implement `POST /api/forecast/csv` in `web.py` satisfying T009: read
  `csv_file`/`csv_text` into a single string, call `parse_items_csv()` then
  `bucket_items_to_throughput()`, then the same `forecast_by_items`/`forecast_by_date`
  branch `_compute_forecast` already uses, returning a `ForecastResponseBody` with
  `history` echoing the derived `completed_per_period` (same as Linear mode already does).
  Catch `CsvImportError` alongside the existing `ValidationError`/`ValueError` in this
  endpoint's error handling, rendering `str(exc)` through the existing 400
  `{"error": "..."}` path - no new formatting code.

### Frontend

- [X] T011 [US1] Regenerate `frontend/openapi.json` and `frontend/src/api-types.ts`
  (`npm run generate-types`) now that a new endpoint exists, and commit both.
- [X] T012 [US1] Write a failing test in `frontend/src/App.test.tsx`: the data-source
  toggle now has a third option ("CSV") alongside "Manual paste" and "Linear"; selecting it
  shows a file input and a textarea for pasted CSV text, and hides the manual-paste/Linear
  fields - never more than one data source's fields visible at once.
- [X] T013 [US1] Implement the third toggle option and the file/paste fields in
  `frontend/src/App.tsx` satisfying T012.
- [X] T014 [US1] Write a failing test: submitting the form in CSV mode (mocked `fetch`)
  sends a `FormData` multipart request to `/api/forecast/csv` with the pasted text or
  selected file, instead of a JSON request to `/api/forecast`, and renders the same
  four-confidence-level results and charts (spec 005, unmodified) as the other two modes'
  success paths already do.
- [X] T015 [US1] Implement the CSV submit-handler branch in `frontend/src/App.tsx`
  satisfying T014.
- [X] T016 [US1] Run quickstart.md Scenarios 1, 2, and 4 and confirm they pass; manually
  verify Scenario 6 in the browser (no real credentials needed, unlike Linear's
  equivalent manual scenarios). Verified via a real running `uvicorn` server (not just
  the ASGI TestClient) with `curl` simulating both the file-upload and pasted-text
  multipart requests a browser would send - both produced correct forecasts end-to-end.

**Checkpoint**: MVP. A user can get a CSV-backed forecast through the web UI.

---

## Phase 4: User Story 2 - Use CSV import from the command line (Priority: P2)

**Goal**: The same CSV-backed forecast is available from the command line, pointed at a
local file.

**Independent Test**: Running the CLI with `--csv-file <path>` instead of `--history`
prints the same output format as manual-paste mode.

- [X] T017 [US2] Write a failing test in `tests/test_cli.py`: a new `--csv-file <path>`
  option exists and is a third mutually-exclusive arm alongside `--history` and the
  `--linear-api-key`/`--linear-team` pair - providing none of the three, or more than one,
  raises the same "exactly one of" error message (extended to name all three options).
- [X] T018 [US2] Implement `--csv-file` in `cli.py` satisfying T017: read the file at the
  given path, call `parse_items_csv()` then `bucket_items_to_throughput()`, feeding the
  result into the same `forecast_by_items`/`forecast_by_date` branch already used for
  `--history` and Linear mode.
- [X] T019 [US2] Write a failing test: running the CLI with `--csv-file` (pointed at a
  temp file) prints the identical output `_render_result` already produces for
  manual-paste mode with the same underlying per-period counts.
- [X] T020 [US2] Confirm T019 passes against the T018 implementation; fix any gap.
- [X] T021 [US2] Catch `CsvImportError` in the CLI's existing exception handling,
  rendering the same `Error: <message>` on stderr / exit code 1 pattern already used for
  `ValueError`/`ValidationError`/`LinearIntegrationError` - no new formatting code.
- [X] T022 [US2] Run quickstart.md Scenarios 3 and 5 and confirm they pass.

**Checkpoint**: User Stories 1 AND 2 both independently complete - CSV-backed forecasting
works from both the web UI and the CLI.

---

## Phase 5: User Story 3 - Clear errors when the CSV is invalid (Priority: P3)

**Goal**: Every distinct CSV validation failure produces its own specific, actionable
message, through both surfaces.

**Independent Test**: Submitting a CSV missing a column, then one with a malformed row,
then one where every item lacks a completion date, produces three distinct, correct
messages - via both the web API and the CLI.

- [X] T023 [US3] Write failing end-to-end tests (web **and** CLI) for each row/column-level
  failure in contracts/forecast-api.md's error table: missing required column, blank `id`,
  malformed `start_date`, malformed `end_date` - asserting the exact row-and-column-naming
  message appears, distinct per case.
- [X] T024 [US3] Write failing end-to-end tests (web and CLI) for the two cases that reuse
  *existing* validators: zero items with any `end_date` (the "all incomplete" case) and
  completions spanning fewer than `MIN_HISTORICAL_PERIODS` periods - asserting the
  *existing* all-zero/too-few-periods messages appear unchanged, confirming no
  CSV-specific duplicate error was introduced (FR-005).
- [X] T025 [US3] Fix any gap T023/T024 surface. Expected to be none - Foundational
  (T001-T008) already defines the exact message text, and US1/US2's
  `except CsvImportError` clauses (T010, T021) already surface it unchanged on both
  surfaces. This task makes the verification-and-fix step explicit rather than assuming it.
  No gaps found - all 10 new tests passed on first run.

**Checkpoint**: All three user stories independently complete and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Update `README.md`: document CSV-backed forecasting (the web UI's third
  data-source option with file upload and paste, the CLI's `--csv-file` flag), and link
  `specs/007-csv-item-import/` from the Status section (constitution: README updated in
  the completing PR).
- [ ] T027 Run the full constitution Quality Gate sequence clean across the repo: `ruff`,
  `mypy --strict`, `pytest --cov`, `pip-audit`, `bandit`, `eslint`, `tsc --noEmit`,
  `vitest`, `npm audit`, and the generated-types freshness check (quickstart.md Scenario
  7).
- [ ] T028 Write the PR description: confirm no new runtime dependency was introduced
  (research.md §1 - nothing to justify), and the constitution principles touched
  (plan.md's Constitution Check table). List `Closes #N` for the parent feature-request
  issue and every per-task tracking issue created by `/speckit-taskstoissues` for this
  feature, per the `/speckit-implement` fix in PR #221 - this should now happen
  automatically as part of that command, not as a manual sweep afterward.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. **Blocks both US1 and US2** - neither story
  can call `parse_items_csv()`/`bucket_items_to_throughput()` before they exist and are
  tested.
- **User Stories (Phase 3-4)**: Both depend on Foundational only, not on each other - US1
  and US2 touch disjoint files (web.py+frontend vs. cli.py) and could be done in either
  order or in parallel by different people.
- **US3 (Phase 5)**: Depends on US1 **and** US2 - it verifies both surfaces.
- **Polish (Phase 6)**: Depends on all three user stories.

### Within Each Phase

- Tests before implementation, confirmed failing (Principle III).
- Foundational: `Item` model -> header validation/row parsing -> period derivation/bucketing
  (each layer builds on the last).
- Each story: backend test -> backend implementation -> (US1 only) frontend test ->
  frontend implementation -> quickstart verification.

### Parallel Opportunities

- T002 can run alongside T001 (different files).
- Once Foundational (T001-T008) is done, User Story 1 (T009-T016) and User Story 2
  (T017-T022) touch no shared files and could proceed in parallel.
- T026 (README) can run in parallel with T027/T028 once all three stories are done.

---

## Implementation Strategy

### MVP First

1. Phase 1 -> Phase 2 (the shared `parse_items_csv()`/`bucket_items_to_throughput()`,
   fully tested in isolation).
2. Phase 3 (US1): CSV-backed forecasting works end-to-end through the web UI.
3. **STOP and VALIDATE** with quickstart.md Scenarios 1, 2, and 4. Demo it.

### Incremental Delivery

1. Setup + Foundational -> the parsing/bucketing functions exist and are trustworthy on
   their own.
2. US1 (web) -> validate -> demo (MVP!).
3. US2 (CLI) -> validate -> demo.
4. US3 -> confirms both surfaces fail clearly, not just succeed clearly.
5. Polish (README, full quality gates, PR description) -> ready to merge.

---

## Notes

- `[P]` = different files, no dependency on incomplete tasks.
- Commit after each task or logical group.
- Clean-room (Principle I): this parser reads a plain CSV by its own documented column
  names - no comparable code exists in predictability-engine to consult or avoid; the
  column names matching its format is a data-comparability choice from the spec, not code
  copied from anywhere.
