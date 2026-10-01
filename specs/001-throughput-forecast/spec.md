# Feature Specification: Throughput-Based Monte Carlo Forecast

**Feature Branch**: `001-throughput-forecast`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Throughput-based Monte Carlo forecast: given a history of
completed items per time period, run a Monte Carlo simulation to forecast when a backlog
will be finished, or how many items will be done by a target date — surfacing a probability
distribution rather than a single estimate."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Forecast a completion date for a known backlog size (Priority: P1)

A team has a backlog of a known number of remaining items and a record of how many items
they completed in each of several recent, equal-length periods (e.g., each week). They want
to know when the backlog is likely to be finished, expressed as a range of dates with
associated confidence levels, rather than a single promised date.

**Why this priority**: This is the question agile teams ask most often ("when will this be
done?") and is the minimal useful capability of the tool — it alone delivers the core value
proposition and matches the project's stated minimal starting scope.

**Independent Test**: Can be fully tested by supplying a historical throughput series and a
backlog size, and verifying the output contains multiple completion-date estimates, each
paired with a distinct confidence level, with later dates carrying higher confidence.

**Acceptance Scenarios**:

1. **Given** a historical throughput series of at least the minimum required number of
   periods and a backlog of N remaining items, **When** a completion-date forecast is
   requested, **Then** the system returns a set of candidate completion dates at standard
   confidence levels (e.g., 50%, 70%, 85%, 95%), with higher-confidence dates no earlier
   than lower-confidence dates.
2. **Given** the same historical throughput series, backlog size, and random seed, **When**
   the forecast is requested twice, **Then** both runs return identical results.
3. **Given** a backlog size of zero, **When** a completion-date forecast is requested,
   **Then** the system rejects the request with a clear error rather than returning a
   forecast.

---

### User Story 2 - Forecast items completed by a target date (Priority: P2)

A team has a target date (e.g., a release date) and wants to know how many items from their
backlog are likely to be completed by that date, expressed as a range of item counts with
associated confidence levels.

**Why this priority**: This is the inverse of User Story 1 ("how much will we get done by
X?") and is the second most common forecasting question, but it is not required for the tool
to deliver its first slice of value.

**Independent Test**: Can be fully tested by supplying a historical throughput series and a
future target date, and verifying the output contains multiple item-count estimates, each
paired with a distinct confidence level, with higher-confidence counts no greater than
lower-confidence counts.

**Acceptance Scenarios**:

1. **Given** a historical throughput series of at least the minimum required number of
   periods and a target date in the future, **When** an items-completed forecast is
   requested, **Then** the system returns a set of candidate item counts at standard
   confidence levels, with higher-confidence counts no greater than lower-confidence counts.
2. **Given** a target date that is not in the future, **When** an items-completed forecast
   is requested, **Then** the system rejects the request with a clear error rather than
   returning a forecast.

---

### User Story 3 - See the full forecast distribution and its basis (Priority: P3)

A user wants to see the complete picture behind a forecast — the confidence levels reported,
how many simulation trials were run, and how much historical data was used — so they can
judge for themselves how much to trust the result, rather than taking a single number on
faith.

**Why this priority**: Reinforces trust in the tool but is not required for the first two
user stories to deliver value; it is a refinement of how results are presented.

**Independent Test**: Can be fully tested by requesting any forecast and verifying the
result includes, alongside the forecast values, the number of simulation trials run and the
number of historical periods used as input.

**Acceptance Scenarios**:

1. **Given** any valid forecast request, **When** the forecast is returned, **Then** the
   result states the number of simulation trials run and the number of historical periods
   used, in addition to the forecast values themselves.

### Edge Cases

- What happens when the historical throughput series has fewer periods than the documented
  minimum? The system MUST refuse to produce a forecast and MUST explain why, rather than
  silently producing an unreliable one.
- What happens when every historical period has zero completed items? The system MUST
  refuse to produce a forecast (a simulation cannot project completion from an all-zero
  history) and MUST explain why.
- What happens when the historical series contains a negative count or a non-whole number?
  The system MUST reject the input as invalid.
- What happens when the requested backlog size is zero or negative, or the target date is
  today or in the past? The system MUST reject the request with a clear error.
- What happens when a user supplies a random seed? Repeated requests with the same inputs
  and seed MUST produce identical results.
- What happens when a forecast request supplies both a backlog size and a target date, or
  supplies neither? The system MUST reject the request with a clear error explaining that
  exactly one of the two must be supplied.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a historical throughput series: an ordered sequence of
  equal-length periods, each with a non-negative whole number of items completed.
- **FR-002**: System MUST support two forecast modes: (a) given a target backlog size,
  forecast completion dates; (b) given a target date, forecast items completed.
- **FR-003**: System MUST generate each forecast by repeatedly sampling, with replacement,
  from the supplied historical throughput series to simulate possible future outcomes
  (a Monte Carlo simulation), rather than by extrapolating a single average rate.
- **FR-004**: System MUST run enough simulation trials to produce a stable result, and MUST
  report the number of trials run as part of the result (User Story 3).
- **FR-005**: System MUST express every forecast as outcomes at multiple standard confidence
  levels (50%, 70%, 85%, and 95%), never as a single point estimate.
- **FR-006**: System MUST define and enforce a minimum number of historical periods required
  to produce a forecast, and MUST reject requests with fewer periods, explaining the
  shortfall.
- **FR-007**: System MUST reject a historical series in which every period has zero
  completed items, explaining that no completion can be projected.
- **FR-008**: System MUST validate that a requested backlog size is a positive whole number
  and that a requested target date is strictly after the forecast's reference date, rejecting
  invalid requests with a clear, specific error.
- **FR-009**: System MUST accept an optional random seed; given the same historical series,
  forecast request, and seed, repeated runs MUST produce identical results.
- **FR-010**: System MUST reject a historical series containing a negative or non-whole
  period count.
- **FR-011**: System MUST reject a forecast request that supplies both a backlog size and a
  target date, or neither, explaining that exactly one of the two is required.

### Key Entities

- **Throughput History**: An ordered sequence of periods, each recording the whole number of
  items completed in that period. The basis for every forecast.
- **Forecast Request**: A request for either a completion-date forecast (given a backlog
  size) or an items-completed forecast (given a target date), with an optional trial count
  and random seed.
- **Forecast Result**: The outcome of a forecast request: a set of values (dates or item
  counts) paired with their confidence levels, plus the number of simulation trials run and
  the number of historical periods used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user supplying a historical throughput series and a backlog size receives a
  completion-date forecast expressed across at least four distinct confidence levels, with
  no manual calculation required.
- **SC-002**: A user supplying a historical throughput series and a target date receives an
  items-completed forecast expressed across at least four distinct confidence levels, with
  no manual calculation required.
- **SC-003**: Repeating an identical forecast request (same history, same request, same
  seed) produces identical results 100% of the time.
- **SC-004**: A forecast over a typical historical series (12–26 periods) completes in under
  5 seconds.
- **SC-005**: A user given a forecast result can state the range of likely outcomes and the
  confidence associated with each, not just a single number, 100% of the time.
- **SC-006**: A user who supplies insufficient or all-zero historical data is told why a
  forecast cannot be produced, rather than receiving a misleading result, 100% of the time.

## Assumptions

- Historical periods are equal-length and consistently defined by the user (e.g., all days,
  all weeks, or all sprints); the feature treats a "period" as an opaque unit of time and
  does not need to know its real-world duration.
- The minimum number of historical periods required for a forecast, and the exact set of
  reported confidence levels (50/70/85/95%), are implementation-defined constants documented
  alongside the simulation core, not user-facing configuration in this first slice.
- A sensible default number of simulation trials (in the thousands) is chosen by the
  implementation to balance result stability against the 5-second performance target in
  SC-004; users are not required to choose a trial count to get a usable forecast.
- How a user actually supplies the throughput series and reads the result (CLI arguments,
  a file, a future dashboard, etc.) is a presentation-layer concern outside this spec, per
  the project's library-first principle — this spec defines the forecasting capability
  itself, not its interface.
- "Today"/the forecast's reference date is the date the forecast is run, not a user-supplied
  value.
