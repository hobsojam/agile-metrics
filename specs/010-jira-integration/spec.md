# Feature Specification: Jira Integration - Import Throughput from Resolved Issues

**Feature Branch**: `010-jira-integration`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Jira integration: import throughput from resolved issues (issue #180). Add Jira as a data source alongside manual paste, Linear, and CSV, so a team's throughput history can be pulled directly from Jira instead of copy-pasted. Forecast from a Jira project's issues that were resolved within a chosen lookback window, bucketed into equal-length periods to produce the same throughput history the forecasting library already consumes. Standard "Done" resolution is assumed for the basic version; custom workflows are a known harder case. Authentication must support Jira Cloud (email plus API token) at minimum; Jira Server/Data Center (personal access token) is the open question. No change to the forecasting library itself - this is a new data-source adapter. Out of scope: cycle time, aging WIP, cumulative flow, which need start dates, not just resolution dates."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Forecast from a Jira project's throughput instead of pasting it (Priority: P1)

A team that tracks work in Jira wants to forecast from its own history without
copying completed-item counts by hand. They supply their Jira site, their account
credentials, and a project key; the system fetches the issues that were resolved in
the chosen lookback window, buckets their resolution dates into equal-length periods,
and produces the same forecast the manual, Linear, and CSV paths already produce.

**Why this priority**: This is the entire value of the feature - a fourth,
zero-copy-paste source for the history every forecast consumes. Without it, nothing
else in this spec matters.

**Independent Test**: Supply a Jira site, valid credentials, and a project with a known
set of resolved issues in a known window; confirm the forecast's period counts match
the number of issues resolved in each period, and that the forecast is produced
through the same path a manually-pasted history of those counts would use.

**Acceptance Scenarios**:

1. **Given** a Jira project with issues resolved across several weeks, **When** the
   user requests a forecast using that project and a lookback window, **Then** the
   system returns a forecast whose underlying per-period counts equal the number of
   issues whose resolution date falls in each period.
2. **Given** a project with no issues resolved in the lookback window, **When** the
   user requests a forecast, **Then** the system reports that there is not enough
   resolved work to forecast from, naming the project and window, rather than
   producing a misleading forecast.
3. **Given** valid credentials but a project key that does not exist or is not visible
   to those credentials, **When** the user requests a forecast, **Then** the system
   reports that the project could not be found or accessed, without revealing whether
   the project exists to an account that cannot see it.

---

### User Story 2 - Clear, specific errors for authentication and access problems (Priority: P2)

A user who mistypes an API token, uses the wrong email, or points at the wrong Jira
site needs to know which of those went wrong, not a generic "Jira is unavailable"
message, so they can fix it without guessing.

**Why this priority**: Credential and access failures are the most common first-time
problem for any external integration; distinct messages are what make the feature
usable. Secondary to the happy path, which must work first.

**Independent Test**: Trigger each distinct failure (bad token, bad site address, rate
limit, unreachable site) and confirm each produces its own message naming the actual
problem.

**Acceptance Scenarios**:

1. **Given** an incorrect API token, **When** the user requests a forecast, **Then**
   the system reports an authentication failure, distinct from access or availability
   problems.
2. **Given** a site address that is not a Jira site, **When** the user requests a
   forecast, **Then** the system reports that the site could not be reached as a Jira
   site, naming the address it tried.
3. **Given** Jira rejects requests because too many have been made recently, **When**
   the user requests a forecast, **Then** the system reports that Jira is rate-limiting
   requests and that the user should retry later, rather than a generic failure.

---

### User Story 3 - Same forecast regardless of which source supplied the history (Priority: P3)

A user comparing a Jira-sourced forecast with a manually pasted one for the same
completed-item counts must get identical numbers, so Jira is demonstrably just another
way of supplying the same history, not a different forecasting method.

**Why this priority**: A consistency guarantee rather than new user-facing capability;
it protects trust in the existing forecast once a new source is added.

**Independent Test**: Supply the same per-period counts once via Jira and once via
manual paste, request forecasts with the same seed, and confirm the outcomes are
identical.

**Acceptance Scenarios**:

1. **Given** identical per-period completion counts supplied via Jira and via manual
   paste, **When** a forecast is requested from each with the same parameters and seed,
   **Then** the resulting outcomes are identical.

---

### Edge Cases

- **Issues resolved exactly on a period boundary**: each issue is counted in exactly one
  period, determined by its resolution date, with no double-counting across boundaries.
- **Issues without a resolution date** (still open, or resolved in a way Jira records
  without a date): excluded from the counts, not counted as zero-day completions.
- **Very large result sets**: all issues in the lookback window are counted, however
  many pages Jira returns; the system does not silently truncate after the first page.
- **Issues moved out of and back into a Done state**: counted by their most recent
  resolution date within the window, so the same issue is never counted twice.
- **Custom workflows where "done" is not the standard Done category**: out of scope for
  this basic version. Items in a non-standard completion status are excluded from the
  counts rather than guessed at, and the limitation is stated in the documented
  behavior so users know to expect it.
- **Sparse history** (fewer than the minimum number of periods, or all zeros): the same
  existing "not enough history" and "no completed work" messages apply, unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a Jira site address, account email, API token, and
  project key as the inputs needed to fetch a team's resolved work, in the same way the
  Linear source accepts its credentials and team.
- **FR-002**: The system MUST fetch issues from the named project whose resolution date
  falls within a user-chosen lookback window, covering all matching issues regardless
  of how many pages Jira returns.
- **FR-003**: The system MUST count each issue in exactly one period, determined by its
  resolution date, and MUST exclude issues without a resolution date from the counts.
- **FR-004**: The system MUST treat "done" as Jira's standard Done status category for
  the basic version, and MUST NOT guess at custom completion statuses.
- **FR-005**: The produced throughput history MUST be the same shape the existing
  manual-paste, Linear, and CSV sources already produce, so the forecasting library
  needs no change (Constitution Principle II).
- **FR-006**: The system MUST report authentication failures, unknown or inaccessible
  projects, unreachable sites, and rate limiting as distinct, specific messages.
- **FR-007**: The system MUST NOT reveal to a user without access to a project whether
  that project exists.
- **FR-008**: The system MUST NOT log, echo back, or persist the API token beyond the
  single request that uses it.
- **FR-009**: The Jira source MUST be selectable from both the command line and the web
  UI, alongside the existing manual-paste, Linear, and CSV options.
- **FR-010**: The system MUST reuse the existing sparse-history and no-completed-work
  messages when the fetched history fails the same checks manual history does.

### Key Entities *(include if feature involves data)*

- **Jira Connection**: the site address, account email, and API token a user supplies
  for one request. Used only for that request; never stored.
- **Resolved Issue**: a Jira issue in the chosen project with a resolution date inside
  the lookback window. Contributes exactly one completion to one period.
- **Throughput History**: the per-period completed-item counts derived from resolved
  issues. The same entity every existing source already produces.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can obtain a forecast from a Jira project by supplying only their
  site, credentials, and project key, with no manual counting or copying.
- **SC-002**: For a project whose resolved-issue counts are known, the per-period counts
  the forecast uses match those counts exactly in 100% of test cases.
- **SC-003**: A forecast from Jira-sourced counts and a forecast from manually pasted
  identical counts produce identical outcomes for the same seed in 100% of cases.
- **SC-004**: Each of the four distinct failure categories (authentication, unknown or
  inaccessible project, unreachable site, rate limiting) produces a message a user can
  act on without consulting the documentation.
- **SC-005**: Users with a project of at least several hundred resolved issues in the
  lookback window receive a forecast without the system silently dropping any issues.

## Assumptions

- **Done means Jira's standard Done status category** for the basic version. Teams with
  custom workflows will see resolved work excluded from their counts, and this is stated
  as a known limitation rather than solved here.
- **Resolution date is the completion signal.** Items are counted by when Jira records
  them as resolved, consistent with how Linear's completion dates are used.
- **Lookback window is user-chosen** and follows the same convention as the existing
  Linear source's lookback period, so the two sources are interchangeable in the UI.
- **Jira Cloud only for this version**: authentication is an account email plus an API
  token. Jira Server/Data Center (personal access token) is deferred to a follow-up
  feature. (Decided by the user, 2026-10-06.)
- **Read-only access**: the integration only reads issues; it never creates, updates, or
  transitions anything in Jira.
- **No change to the forecasting library** (Constitution Principle II); this is a new
  data-source adapter only.
- **Out of scope**: cycle time, aging work in progress, and cumulative flow metrics, which
  require item-level start dates in addition to resolution dates. These belong to a
  separate, larger feature noted in `specs/005-forecast-charts/spec.md`.
