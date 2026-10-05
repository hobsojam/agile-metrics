# Feature Specification: CSV Item Import

**Feature Branch**: `007-csv-item-import`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Support uploading or pasting a CSV of per-item records (columns: id, type, title, start_date, end_date — matching predictability-engine's format for easy comparison data) as an alternative data source to manual aggregate-throughput paste, for both the CLI and the web UI. Parsed items are bucketed by end_date into per-period completion counts, producing a ThroughputHistory fed through the exact same forecast_by_items/forecast_by_date path manual paste and Linear import already use - identical forecast output, just a third way to populate the history. The per-item start_date is accepted and retained as part of the parsed item records (not discarded), but this feature does not compute or expose any item-level flow metrics (cycle time, aging WIP, cumulative flow diagram, cycle-time scatter) from it - that is explicitly out of scope, tracked separately, and is the reason start_date is part of the CSV shape even though only end_date is used for forecasting today. No live API integration, no authentication - this is a local file/pasted-text import, closing the gap that neither the Linear (#179) nor the planned Jira (#180) integration fill, since those currently only fetch completion dates, not start dates. Rows with missing or malformed required fields should be rejected with a clear, specific error naming the problem (row number and field), consistent with how Linear's error messages name the specific problem rather than a generic parse failure."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Forecast from a CSV of completed items (Priority: P1)

A user who tracks work as a flat list of items (exported from a spreadsheet, a PM tool, or hand-maintained) wants a forecast without manually counting how many items finished in each period. They paste or upload a CSV of items — each with an id, type, title, start date, and end date — choose a period length and either a backlog size or a target date, and get the same four-confidence-level forecast as manual paste or Linear import, with the throughput history built automatically from the items' completion dates.

**Why this priority**: This is the entire point of the feature — a zero-API-integration way to populate throughput history from data a user already has in hand, and the cheapest of the three import paths to validate the idea before any live-API work.

**Independent Test**: Paste a CSV of at least six periods' worth of completed items through the web UI or CLI and confirm a forecast renders with the same four confidence levels as the manual-paste flow, using the period's completion counts computed from the CSV.

**Acceptance Scenarios**:

1. **Given** a CSV of items whose end dates span at least six periods, **When** the user selects CSV import as the data source, pastes or uploads the CSV, and chooses a period length and a backlog size, **Then** a forecast renders with outcomes at all four confidence levels, without the user having typed any throughput numbers.
2. **Given** the same items' completion dates counted by hand into per-period totals and entered as manual paste, **When** both are forecast with the same period length, mode, and seed, **Then** the two forecasts produce identical outcomes — CSV import is strictly an alternate way to populate the same history, not a different forecasting path.

---

### User Story 2 - Use CSV import from the command line (Priority: P2)

A user who automates their forecasting wants the same CSV-backed forecast available from the CLI, pointing at a local file instead of pasting into a web form.

**Why this priority**: Important for the tool's existing CLI-first users, but the web UI is where most people will first encounter this, so it's second.

**Independent Test**: Run the CLI with a path to a CSV file instead of `--history`, and confirm the printed forecast matches what the web UI would show for the same file and parameters.

**Acceptance Scenarios**:

1. **Given** a valid CSV file path supplied to the CLI, **When** the user runs a backlog-size or target-date forecast without `--history`, **Then** the CLI prints the same four-confidence-level output format as manual-paste mode, populated from the CSV's completion dates.

---

### User Story 3 - Clear errors when the CSV is invalid (Priority: P3)

A user whose CSV has a missing column, a malformed date, or a blank required field needs to know exactly which row and field is wrong, not see a crash, a silent skip, or a generic "parse failed" message.

**Why this priority**: Important for trust and usability, but only encountered when something is already wrong — the happy path (Stories 1-2) matters more.

**Independent Test**: Submit a CSV missing a required column, then one with a malformed date in a specific row, and confirm each produces a distinct, specific error naming the row and field at fault.

**Acceptance Scenarios**:

1. **Given** a CSV missing one of the required columns entirely, **When** the user submits it, **Then** they see an error naming the missing column, not a generic failure.
2. **Given** a CSV where one row has an unparsable date in `end_date`, **When** the user submits it, **Then** they see an error naming that row number and field, not a crash or a silently-wrong forecast.
3. **Given** a CSV whose completion dates, once bucketed, span fewer than the minimum required periods, **When** the user submits it, **Then** they see the same "at least N historical periods required" message already used for manual paste and Linear import — not a different or confusing error.
4. **Given** a CSV whose items all lack a completion date in the lookback window, **When** the user submits it, **Then** they see the same "no completed work to forecast from" message already used for an all-zero manually-entered history.

---

### Edge Cases

- **An item still in progress (no completion date yet)**: accepted as a valid row (not an error) and excluded from the throughput bucketing, since only completed items have a period to count toward; its start date and other fields are still retained in the parsed item records.
- **Duplicate `id` values across rows**: both rows are kept and counted independently — `id` is an opaque label carried through from the source system, not a uniqueness constraint this feature enforces.
- **An item's end date equal to its start date**: valid (completed the same period it started); counted normally by end date.
- **Extra, unrecognized columns in the CSV**: ignored rather than rejected, so exports with extra metadata columns don't need to be pre-trimmed.
- **Column order different from id, type, title, start_date, end_date**: accepted — columns are matched by header name, not position.
- **Empty CSV (header row only, no data rows)**: surfaces the same "no completed work to forecast from" message as a CSV with zero completed items.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to provide a CSV of per-item records — via pasted text or an uploaded/local file — as an alternative to manually entering throughput history, in both the web UI and the CLI.
- **FR-002**: Each CSV row MUST be read for five named columns: `id`, `type`, `title`, `start_date`, `end_date`, matched by header name rather than column position.
- **FR-003**: The system MUST group completed items' `end_date` values into fixed-length periods matching the period length the user specifies (the same period-length concept already used by manual paste and Linear import), producing a throughput history.
- **FR-004**: The throughput history derived from a CSV MUST be passed through the exact same forecasting functions already used for manually-entered and Linear-derived history — no parallel or duplicate forecasting logic for CSV-sourced data.
- **FR-005**: The same validation rules that apply to manually-entered and Linear-derived history (minimum historical periods, not all-zero, non-negative whole counts) MUST apply identically to CSV-derived history, surfacing the same error messages on failure.
- **FR-006**: `id`, `start_date`, and `end_date` MUST be retained per item in the parsed record set, even though only `end_date` is used for forecasting in this feature — so a later feature computing item-level flow metrics can reuse the same parsed representation without re-parsing the CSV.
- **FR-007**: A row with a missing or unparsable value in a column required for that row MUST be rejected with an error naming the specific row number and column — never a generic "parse failed" message.
- **FR-008**: A CSV missing one of the five required columns entirely MUST be rejected with an error naming the missing column, before any row-level validation runs.
- **FR-009**: The existing manual-paste and Linear-import input paths MUST remain unchanged and fully functional — CSV import is an additional option, never a replacement.
- **FR-010**: An item with a blank `end_date` MUST be treated as not yet completed: excluded from the throughput bucketing (it has no completion period to count toward) without being rejected as invalid, and still retained in the parsed item records.

### Key Entities

- **Item**: a single unit of work from the CSV, with an `id` (opaque label, not required to be unique), a `type` (free-text category, e.g. "story", "bug" — not validated against a fixed list), a `title`, a `start_date`, and an `end_date` that is blank for not-yet-completed items.
- **Throughput History** (existing entity, new source): the same `completed_per_period` history the tool already models — CSV import is a third way to produce its values, alongside manual entry and Linear import.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a CSV export of their work items can get a complete forecast without manually counting or typing any throughput numbers.
- **SC-002**: For the same period length, mode, and seed, a CSV-derived forecast and a manually-entered forecast built from the same underlying per-period counts produce identical outcomes — zero divergence between the two input paths.
- **SC-003**: Every distinct CSV validation failure (missing column, malformed row, too few periods, all-incomplete) produces its own specific, actionable error message — never a generic failure or an unhandled crash.
- **SC-004**: A CSV with thousands of item rows is parsed and forecast with none of them silently dropped or miscounted.

## Assumptions

- **Date format**: `start_date` and `end_date` are ISO 8601 calendar dates (`YYYY-MM-DD`), consistent with every other date field already in the tool (`target_date`, `reference_date`).
- **CSV dialect**: comma-delimited, with a header row; no support for alternate delimiters or header-less files in this version.
- **`type` and `title` are not validated**: they are passed through as free text and retained on the `Item` entity, but nothing in this feature filters, groups, or validates by them — that is left for a future item-level flow-metrics feature to decide how it wants to use them.
- **Period anchoring**: CSV-derived periods are anchored the same way the library already anchors `reference_date` — the most recent period ends today, consistent with manual paste and Linear import.
- **Lookback window**: unlike Linear import (which fetches a bounded recent window), a CSV is a complete, user-supplied dataset — every row with a parseable `end_date` is bucketed, with no separate "lookback periods" concept to configure.
- **Out of scope**: item-level flow metrics (cycle time, aging WIP, cumulative flow diagram, cycle-time scatter) are not part of this feature — `start_date` is accepted and retained specifically so a later feature can compute them without changing the CSV shape, but no such computation happens here.
- **No library changes**: `ForecastResult`, `ForecastRequest`, and the simulation core are unchanged — this feature is a new data-source adapter in front of the existing `ThroughputHistory` construction, not a change to forecasting logic itself.
