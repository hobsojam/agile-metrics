# Feature Specification: Forecast Web UI

**Feature Branch**: `003-forecast-web-ui`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "A minimal web UI for the throughput forecast library: a user
pastes or uploads their historical throughput data (and period length) into a web form,
chooses either a backlog size or a target date, submits, and sees the resulting Monte Carlo
forecast rendered on the page. No accounts, no persistence, no database — stateless, same
as the CLI. Live integrations with external trackers (Jira, MCP, or any other API) are
explicitly out of scope for this feature; only manual paste/CSV-style input is supported."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a completion-date forecast in a browser (Priority: P1)

A user who doesn't want to install anything or use a command line opens a web page, enters
their team's historical throughput and a backlog size, submits the form, and sees a
completion-date forecast at standard confidence levels displayed on the page.

**Why this priority**: This is the entire reason the web UI exists — it reaches people
who would never use the CLI, with zero install step. Without it, the forecasting capability
remains reachable only by programmers or command-line users.

**Independent Test**: Can be fully tested by loading the page, entering a sample historical
throughput series and a backlog size, submitting, and verifying the page displays completion
dates at all four confidence levels.

**Acceptance Scenarios**:

1. **Given** a valid historical throughput series and a backlog size entered on the page,
   **When** the user submits the form, **Then** the page displays a completion-date
   forecast at all four confidence levels.
2. **Given** the same inputs and an explicit seed, **When** the form is submitted twice,
   **Then** both submissions display identical results.
3. **Given** a backlog size of zero, **When** the user submits the form, **Then** the page
   displays a clear, understandable error message instead of a forecast or a technical
   error page.

---

### User Story 2 - Get an items-completed forecast in a browser (Priority: P2)

A user has a target date in mind and wants to know how many items are likely to be done by
then. They enter their historical throughput and the target date instead of a backlog size.

**Why this priority**: The inverse question to User Story 1, and the second most valuable
capability, but the page delivers its core value without it.

**Independent Test**: Can be fully tested by loading the page, entering a sample historical
throughput series and a future target date, submitting, and verifying the page displays
item-count forecasts at all four confidence levels.

**Acceptance Scenarios**:

1. **Given** a valid historical throughput series and a future target date entered on the
   page, **When** the user submits the form, **Then** the page displays an items-completed
   forecast at all four confidence levels.
2. **Given** a target date that is not in the future, **When** the user submits the form,
   **Then** the page displays a clear error message instead of a forecast.

---

### User Story 3 - Understand what went wrong with bad input (Priority: P3)

A user pastes malformed data, forgets to choose a backlog size or target date, or fills in
both. Rather than seeing a blank page, a technical error page, or a silent failure, they see
a plain-language explanation of what to fix.

**Why this priority**: Builds trust and keeps the page usable for non-technical visitors,
but is a refinement of how failures are presented — the happy path (User Stories 1-2)
already delivers the core value.

**Independent Test**: Can be fully tested by submitting the form with invalid or
contradictory input and verifying a clear, in-page message appears, with no raw error page
or technical stack trace visible.

**Acceptance Scenarios**:

1. **Given** the form is submitted with both a backlog size and a target date filled in, or
   neither, **When** the result is shown, **Then** a clear message explains that exactly one
   is required.
2. **Given** the pasted/uploaded historical data fails validation (too few periods, all-zero
   history, non-numeric values), **When** the result is shown, **Then** a clear message
   states what is wrong with the data, not a technical error.

### Edge Cases

- What happens when the form is submitted with no historical data at all? The page MUST
  show a clear validation message, not a server error.
- What happens when an uploaded file isn't readable as the expected plain-text/CSV-style
  format? The page MUST show a clear message, not a raw error.
- What happens while the forecast is being computed? If it takes any noticeable time, the
  page MUST show that the request is in progress, so the user does not think it has frozen.
- What happens if the user reloads the page or closes the browser? Since nothing is
  persisted, the form simply resets — this is expected, not an error condition.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a web page where a user can input a historical throughput
  series and its period length by pasting text or uploading a file — no installation or
  command-line use required.
- **FR-002**: System MUST let the user choose exactly one of a backlog size or a target
  date, and MUST reject submissions that provide both or neither with a clear, in-page
  explanation (mirrors the underlying library's FR-011).
- **FR-003**: System MUST display the resulting forecast on the page showing all four
  confidence levels — never a single point estimate.
- **FR-004**: System MUST translate every validation failure (insufficient history,
  all-zero history, invalid backlog size or target date, unreadable uploaded data) into a
  clear, human-readable, in-page message — never a raw error page or stack trace.
- **FR-005**: System MUST NOT require account creation or login, and MUST NOT persist
  submitted data beyond handling the single request that submitted it.
- **FR-006**: System MUST display the number of simulation trials and historical periods
  used alongside the forecast.
- **FR-007**: System MUST support an optional random seed input, so a user can reproduce an
  identical result.
- **FR-008**: This feature explicitly excludes any live integration with external issue
  trackers (e.g., Jira) or protocol-based data connectors (e.g., MCP) — all data entry is
  manually supplied by the user in the browser, via pasted text or an uploaded file.

### Key Entities

- **Web Form Submission**: The user-supplied data for one forecast request — historical
  throughput, period length, a chosen mode (backlog size or target date) and its value, and
  an optional seed. Maps onto the underlying library's `ThroughputHistory`/
  `ForecastRequest`.
- **Forecast Page Result**: The on-page rendering of the underlying library's
  `ForecastResult` — all four confidence levels plus trial count and periods used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time visitor can get a completion-date forecast using only the page's
  own labels and instructions, with no external documentation, in a single form
  submission.
- **SC-002**: A first-time visitor can get an items-completed forecast the same way.
- **SC-003**: 100% of invalid submissions show a clear, in-page error message — none show a
  raw error page or a technical stack trace.
- **SC-004**: The forecast appears on the page within 5 seconds of submission for a typical
  input, with visible in-progress feedback if it takes any noticeable time.
- **SC-005**: No submitted data is observable after the browser is closed or the page is
  reloaded, confirming the stateless design.

## Assumptions

- "Paste or upload" are both satisfied by the same simple input format (e.g.
  comma/newline-separated numbers); whether the page offers one combined input or two
  separate affordances is a planning-level UI decision, not user-facing scope.
- The forecasting behavior, validation rules, and result invariants are inherited unchanged
  from `001-throughput-forecast`; this spec defines only the browser-based interface around
  it.
- No authentication or authorization is in scope; the page is used by one person at a time,
  consistent with the CLI/library's single-user scope.
- A visual chart of the forecast distribution is not required for this slice — displaying
  the four confidence-level values as text/numbers satisfies the transparency requirement.
  Charting is a possible future enhancement, not required now.
- Live integration with Jira, MCP, or any other external data source is explicitly out of
  scope, per the feature request — all input is manual.
