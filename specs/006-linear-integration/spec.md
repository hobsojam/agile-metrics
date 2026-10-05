# Feature Specification: Linear Integration

**Feature Branch**: `006-linear-integration`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Add Linear as a data source for the forecast web UI and CLI, alongside the existing manual paste input. A user provides a Linear personal API key and selects a team (or project), and the tool fetches completed issues' completion dates, buckets them into weekly (or configurable period-length) throughput counts, and feeds that directly into the existing forecast_by_items/forecast_by_date functions as a ThroughputHistory - producing identical forecast output to manual paste, just with the history populated automatically instead of typed in. No OAuth app registration needed (personal API key only, for personal/single-user use). No item-level flow metrics (cycle time, aging WIP, cumulative flow diagram) in this feature - those need start dates too, not just completion dates, and are explicitly out of scope. No change to the existing manual-paste input path - Linear import is an additional way to populate the same history field, not a replacement."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Forecast from Linear without typing throughput numbers (Priority: P1)

A user who tracks their team's work in Linear wants a forecast without manually counting and typing how many items were completed each week. They provide a Linear personal API key and pick their team, choose a period length and either a backlog size or a target date (exactly as they would with manual paste), and get the same four-confidence-level forecast — with the throughput history populated automatically from their team's completed issues instead of typed in.

**Why this priority**: This is the entire point of the feature — removing the manual data-entry step that is the main friction in using the tool today.

**Independent Test**: With a valid Linear API key and a team that has enough completed issues, submit a backlog-size forecast through the web UI using Linear import instead of manual paste, and confirm a forecast renders with the same four confidence levels as the manual-paste flow.

**Acceptance Scenarios**:

1. **Given** a valid Linear API key and a team with completed issues spanning at least six periods, **When** the user selects Linear as the data source, picks the team, period length, and a backlog size, **Then** a forecast renders with outcomes at all four confidence levels, without the user having typed any throughput numbers.
2. **Given** the same Linear-derived throughput history entered manually as comma-separated counts instead, **When** both are forecast with the same period length, mode, and seed, **Then** the two forecasts produce identical outcomes — Linear import is strictly an alternate way to populate the same history, not a different forecasting path.

---

### User Story 2 - Use Linear import from the command line (Priority: P2)

A user who automates their forecasting (e.g., in a script or scheduled job) wants the same Linear-backed forecast available from the CLI, without needing the web UI.

**Why this priority**: Important for the tool's existing CLI-first users, but the web UI is where most people will first encounter this, so it's second.

**Independent Test**: Run the CLI with a Linear API key and team identifier instead of `--history`, and confirm the printed forecast matches what the web UI would show for the same team and parameters.

**Acceptance Scenarios**:

1. **Given** a valid Linear API key and team identifier supplied to the CLI, **When** the user runs a backlog-size or target-date forecast without `--history`, **Then** the CLI prints the same four-confidence-level output format as manual-paste mode, populated from Linear.

---

### User Story 3 - Clear errors when Linear access fails (Priority: P3)

A user whose API key is wrong, expired, or lacking access to the chosen team — or whose team has no completed work yet — needs to understand exactly what went wrong, not see a crash or a silently-wrong forecast.

**Why this priority**: Important for trust and usability, but only encountered when something is already wrong — the happy path (Stories 1-2) matters more.

**Independent Test**: Submit a forecast with an invalid API key, then with a team the key can't access, then with a team that has zero completed issues, and confirm each produces a distinct, specific error message.

**Acceptance Scenarios**:

1. **Given** an invalid or expired Linear API key, **When** the user submits a Linear-backed forecast, **Then** they see an error naming the credential as the problem, not a generic failure.
2. **Given** a valid key without access to the selected team, **When** the user submits a Linear-backed forecast, **Then** they see an error naming the access problem.
3. **Given** a team with zero completed issues in the lookback window, **When** the user submits a Linear-backed forecast, **Then** they see the same "no completed work to forecast from" message already used for an all-zero manually-entered history — not a different or confusing error.
4. **Given** Linear's API is temporarily unavailable or rate-limiting the request, **When** the user submits a Linear-backed forecast, **Then** they see an error naming that specifically, distinct from a credential or access error.

---

### Edge Cases

- **Fewer completed issues than the minimum required history length**: surfaces the same "at least N historical periods required" message already used for manual paste with too few periods.
- **A team with far more completed issues than fit in one API response**: all of them are counted — none are silently dropped because of pagination.
- **An issue completed, then reopened and completed again**: counted once, at its current completion date (no double-counting across state changes).
- **Clock/timezone edge**: an issue completed right at a period boundary is assigned to one period consistently, not split or double-counted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to provide a Linear personal API key and select a Linear team as an alternative to manually entering throughput history, in both the web UI and the CLI.
- **FR-002**: The system MUST fetch the selected team's completed issues and group their completion dates into fixed-length periods matching the period length the user specifies (the same period-length concept already used by manual paste).
- **FR-003**: The throughput history derived from Linear MUST be passed through the exact same forecasting functions already used for manually-entered history — no parallel or duplicate forecasting logic for Linear-sourced data.
- **FR-004**: The same validation rules that apply to manually-entered history (minimum historical periods, not all-zero, non-negative whole counts) MUST apply identically to Linear-derived history, surfacing the same error messages on failure.
- **FR-005**: The system MUST NOT persist a user's Linear API key beyond the single request that uses it — no accounts, no credential storage, consistent with the tool's existing stateless design.
- **FR-006**: The system MUST NOT log, print, or otherwise expose a Linear API key in error messages, logs, or responses.
- **FR-007**: The system MUST surface clear, specific error messages for each distinct Linear-side failure: invalid/expired credential, inaccessible or nonexistent team, and Linear API unavailability/rate-limiting — each distinguishable from the others and from manual-paste validation errors.
- **FR-008**: The existing manual-paste input path MUST remain unchanged and fully functional — Linear import is an additional option, never a replacement.
- **FR-009**: The system MUST correctly include every completed issue in the lookback window regardless of how many pages of results Linear's API returns for a given team — no silent truncation.
- **FR-010**: A team with zero completed issues in the lookback window MUST surface the same message already used for an all-zero manually-entered history, not a distinct error.

### Key Entities

- **Linear Credential**: a user-supplied personal API key, used for exactly one request and never stored.
- **Linear Team Selector**: identifies which team's completed issues to fetch; the unit of grouping is the team (not a sub-project or individual workflow state).
- **Throughput History** (existing entity, new source): the same `completed_per_period` history the tool already models — Linear import is simply a second way to produce its values, alongside manual entry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a valid Linear API key can get a complete forecast without manually typing any throughput numbers.
- **SC-002**: For the same team, period length, and seed, a Linear-derived forecast and a manually-entered forecast built from the same underlying per-period counts produce identical outcomes — zero divergence between the two input paths.
- **SC-003**: Every distinct Linear-side failure (invalid credential, inaccessible team, zero completions, API unavailability) produces its own specific, actionable error message — never a generic failure or an unhandled crash.
- **SC-004**: A team with thousands of completed issues is forecast with none of them silently dropped due to pagination limits.

## Assumptions

- **Personal API key only**: no OAuth application registration or multi-user credential management — matches the tool's existing single-user, stateless design. A later feature could add OAuth if the tool ever needs to serve multiple users from one deployment.
- **"Completed" definition**: an issue counts as completed when Linear records a completion timestamp for it (i.e., it reached a state in Linear's built-in "completed" state category), consistent with Linear's fixed state-category taxonomy across all teams (no per-team workflow mapping needed, unlike Jira).
- **Grouping unit**: the Linear *team* is the primary selector for this feature's first version; filtering further by a specific Linear project within a team is not included here.
- **Lookback window**: the system fetches enough completed issues to cover at least the minimum required historical periods; the exact default window length is a planning-phase decision, not a product requirement.
- **Period anchoring**: Linear-derived periods are anchored the same way the library already anchors `reference_date` — the most recent period ends today, consistent with how manually-entered history is already interpreted.
- **Out of scope**: item-level flow metrics (cycle time, aging WIP, cumulative flow diagram) are not part of this feature — those need each issue's start date as well as its completion date, and are tracked separately (see the CSV-import path for item-level data). This feature only extracts completion-date counts for aggregate throughput.
- **No library changes**: `ForecastResult`, `ForecastRequest`, and the simulation core are unchanged — this feature is a new data-source adapter in front of the existing `ThroughputHistory` construction, not a change to forecasting logic itself.
