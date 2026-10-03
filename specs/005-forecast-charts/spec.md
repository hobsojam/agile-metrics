# Feature Specification: Forecast Charts

**Feature Branch**: `005-forecast-charts`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Forecast charts for the web UI. Add graphical representations
of forecasts built only from the data the tool already accepts (aggregate throughput per
period; no item-level data). Charts: (1) forecast distribution histogram of simulated
outcomes (completion dates for backlog-size mode, items completed for target-date mode) with
markers at the 50/70/85/95% confidence levels; (2) cumulative probability curve so a user
can read the likelihood of finishing by any date / completing at least N items; (3) burn-up
with forecast fan: cumulative historical throughput followed by shaded projected confidence
bands toward the backlog line or target date; (4) throughput run chart of historical periods
with a median reference line. The library's public forecast result must be extended
additively to carry the data the charts need (e.g. binned distribution and per-period
projection percentiles) so presentation layers do not re-run the simulation; existing fields
and the CLI output stay unchanged. Charts must stay consistent with the four existing
confidence levels and never present a single point estimate. Clean-room: ideas inspired by
predictability-engine are allowed, but no copying of its code, naming, or structure."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the spread of possible outcomes (Priority: P1)

A user submits a forecast and, alongside the four confidence-level answers they already get,
sees a chart of every simulated outcome grouped into bars: how many simulated futures
finished on each possible completion date (or completed each possible number of items). The
four confidence levels are marked on the chart, so the user can see at a glance whether the
outcomes are tightly clustered (a predictable team) or widely spread (a risky forecast).

**Why this priority**: Four numbers alone hide the most important thing about a probabilistic
forecast: how uncertain it is. The distribution chart is the most direct way to show that
uncertainty, and the other charts build on the same data.

**Independent Test**: Submit a valid backlog-size forecast and confirm a distribution chart
appears with one bar per possible completion date and four labelled markers at positions
matching the four confidence-level dates shown in the results; repeat in target-date mode
with item counts.

**Acceptance Scenarios**:

1. **Given** a valid history and backlog size, **When** the user submits the form, **Then**
   a distribution chart of simulated completion dates appears, with labelled markers for
   the 50%, 70%, 85% and 95% confidence levels at the same dates shown in the results.
2. **Given** a valid history and target date, **When** the user submits the form, **Then**
   a distribution chart of simulated items completed appears, with labelled markers for
   the four confidence levels at the same item counts shown in the results.
3. **Given** the same inputs and the same seed, **When** the form is submitted twice,
   **Then** both charts are identical.

---

### User Story 2 - Read off the chance of any outcome (Priority: P2)

A stakeholder asks "what are the odds we're done by 15 December?", and that date isn't one of
the four confidence levels. The user looks at a cumulative probability curve and reads
the likelihood for any date (backlog-size mode) or any item count (target-date mode)
directly, including by pointing at the curve to see the exact value.

**Why this priority**: It answers the question people actually ask, which is about a
specific date or scope, not the tool's fixed confidence levels. It reuses the User Story 1
distribution, so it's cheap once that exists.

**Independent Test**: Submit a forecast and confirm the curve rises from 0% to 100% (date mode) or falls from 100% to 0% (items mode), and that the curve's value at each
confidence-level outcome is at least that confidence level.

**Acceptance Scenarios**:

1. **Given** a backlog-size forecast result, **When** the user inspects the curve at any
   date, **Then** they see the percentage of simulated futures that finished on or before
   that date.
2. **Given** a target-date forecast result, **When** the user inspects the curve at any item
   count, **Then** they see the percentage of simulated futures that completed at least
   that many items.
3. **Given** any forecast result, **When** the user inspects the curve at the outcome listed
   for confidence level L, **Then** the displayed likelihood is at least L%.

---

### User Story 3 - See history and forecast as one picture (Priority: P3)

A user presenting to stakeholders wants one chart that tells the whole story: how much work
the team has completed so far, and how the future could unfold. They see a burn-up chart:
cumulative completed items over the historical periods, then a widening fan of projected
cumulative completions with one line per confidence level and shading between them. In
backlog-size mode a horizontal line marks the total to reach. In target-date mode a vertical
line marks the target date.

**Why this priority**: This is the most persuasive chart for non-technical stakeholders, but
it needs projection data beyond the basic distribution, so it comes after Stories 1 and 2.

**Independent Test**: Submit a backlog-size forecast and confirm the historical line ends
where the projection fan begins, and that each confidence-level line reaches the backlog
line at that level's completion date. Submit a target-date forecast and confirm each
confidence-level line, at the target date, equals that level's item count.

**Acceptance Scenarios**:

1. **Given** any forecast result, **When** the burn-up renders, **Then** the historical
   portion shows cumulative items completed per historical period, ending at the reference
   date.
2. **Given** a backlog-size forecast, **When** the burn-up renders, **Then** the fan
   continues until at least the 95% completion date, and each confidence-level line first
   reaches the backlog line at the date listed for that level.
3. **Given** a target-date forecast, **When** the burn-up renders, **Then** the fan ends at
   the last whole period on or before the target date, and each confidence-level line's
   final value equals the item count listed for that level.

---

### User Story 4 - Check whether the history is trustworthy (Priority: P4)

Before trusting a forecast, a user wants to check that the history it was built from is
reasonably stable. They see a run chart with one bar per historical period's throughput and a
median reference line, so trends, outliers, and zero-throughput periods stand out.

**Why this priority**: It helps people judge the input, not the answer. It's useful but the
least important of the four, and it needs no new simulation data.

**Independent Test**: Submit a forecast with a known history and confirm the run chart shows
one bar per period in input order, with heights equal to the entered values and a reference
line at their median.

**Acceptance Scenarios**:

1. **Given** a history of N periods, **When** the forecast renders, **Then** the run chart
   shows N bars in the order entered (oldest first), each labelled with the period it
   covers.
2. **Given** any history, **When** the run chart renders, **Then** a reference line is drawn
   at the median of the entered values.

---

### Edge Cases

- **All simulated outcomes identical** (e.g. a history where every period has the same
  value): the distribution shows a single bar, all four markers coincide and stay legible,
  and the probability curve is a single step.
- **Very wide outcome ranges** (a large backlog with low, erratic throughput): the
  distribution groups outcomes into a bounded number of bars so the chart stays readable,
  and confidence markers still sit at the exact outcome values.
- **Zero-throughput periods** in the history: shown as zero-height bars in the run chart and
  flat segments in the burn-up history, not omitted.
- **Simulated futures that never complete the backlog within the simulation horizon**: they
  are counted at the horizon (as today), and the distribution and curve stay consistent
  with the existing confidence-level outcomes.
- **Target date less than one full period away**: the projection covers exactly one period,
  matching the existing items-mode behaviour.
- **Error responses** (invalid input): no charts are shown; the existing error message
  behaviour is unchanged.
- **Narrow viewports**: charts resize to fit the available width without horizontal page
  scrolling.

## Requirements *(mandatory)*

### Functional Requirements

**Forecast data (library and API)**

- **FR-001**: The forecast result MUST additionally carry the distribution of simulated
  outcomes: for each possible outcome value (or outcome range, when grouped), the number of
  simulated futures that produced it.
- **FR-002**: The forecast result MUST additionally carry a projection: for each future
  period from the reference date up to the forecast horizon, the cumulative items completed
  at each of the four confidence levels.
- **FR-003**: All additions MUST be additive. Existing result fields, their meanings, and
  their values for a given input and seed MUST be unchanged.
- **FR-004**: The distribution, projection, and existing confidence-level outcomes MUST all
  come from the same simulation run, so they are mutually consistent and reproducible under
  a fixed seed.
- **FR-005**: The distribution MUST use at most 60 groups. When the range of
  outcomes is wider than that, adjacent values MUST be grouped into equal-width ranges, and
  group boundaries MUST be included in the result.
- **FR-006**: The command-line tool's output MUST be unchanged.

**Charts (web UI)**

- **FR-007**: After a successful forecast, the web UI MUST show the four charts described in
  User Stories 1–4, in addition to (not instead of) the existing confidence-level results.
- **FR-008**: Every chart that shows forecast outcomes MUST show all four confidence levels
  (50/70/85/95%) and MUST NOT show a single "expected" or average point estimate as the
  forecast answer.
- **FR-009**: Charts MUST be built entirely from the forecast response. The web UI MUST NOT
  run its own simulation or send extra requests to draw them.
- **FR-010**: Confidence levels MUST be shown the same way in every chart (same labels and
  the same visual style per level) so users can match them between charts.
- **FR-011**: Each chart MUST have a title, labelled axes with units (dates, items, or
  percentage), and a short plain-language caption explaining how to read it.
- **FR-012**: Users MUST be able to see the exact value under the pointer (or the keyboard
  focus) in each chart.
- **FR-013**: Every chart MUST have a text alternative that states its key information
  (the confidence-level values it marks), so the charts don't make the page any less
  accessible.
- **FR-014**: Historical periods MUST be placed on the date axis as consecutive periods of
  the entered length, with the most recent period ending on the reference date.

### Key Entities

- **Outcome Distribution**: The simulated outcomes grouped into bars. Each group has a value
  or value range (completion date or item count) and the number of simulated futures that
  fell into it. The counts add up to the number of trials run.
- **Forecast Projection**: For each future period, the cumulative items completed at each
  of the four confidence levels. It starts at the reference date and ends at the forecast
  horizon.
- **Forecast Result** (existing, extended): The four confidence-level outcomes, trials run
  and periods used, now with the Outcome Distribution and Forecast Projection added.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of valid forecasts, each confidence-level marker on the distribution
  chart sits at exactly the outcome listed for that level in the results.
- **SC-002**: For 100% of valid forecasts, the bar counts in the distribution add up to
  the number of trials run.
- **SC-003**: For 100% of valid forecasts, the burn-up and the confidence-level results
  agree: in backlog-size mode each level's line reaches the backlog line at that level's
  completion date; in target-date mode each level's line ends at that level's item count.
- **SC-004**: All four charts appear within 1 second of the results appearing, for a
  forecast with up to 104 historical periods and default trial count, on a typical laptop.
- **SC-005**: In a walkthrough, a first-time user can correctly answer "what's the chance
  of finishing by [a date that isn't one of the four confidence levels]?" from the charts
  alone, within 30 seconds.
- **SC-006**: Existing command-line output and existing forecast result values are
  byte-for-byte identical before and after this feature for the same inputs and seed.

## Assumptions

- **Data scope**: Charts use only the inputs the tool already accepts: throughput per
  period, period length, backlog size or target date, and an optional seed. Item-level
  flow charts (cycle time, aging work in progress, cumulative flow) need per-item start and
  end dates and are out of scope here.
- **Future Jira data**: The user expects to have Jira data, so a later feature is expected
  to import per-item data and add those flow charts. That feature would also derive
  throughput per period from the items. These charts take throughput per period as input,
  whatever its source, so they should work unchanged once throughput comes from Jira.
- **Surface**: Charts appear only in the web UI. Exporting charts as images, PDFs, or
  static reports, and showing charts in the terminal, are out of scope.
- **Burn-up baseline**: The burn-up starts at zero at the start of the oldest historical
  period. In backlog-size mode the total to reach is the historical total plus the backlog
  size.
- **Confidence-level reading**: The existing reading stays: in backlog-size mode, level L
  means "done on or before this date in L% of simulated futures". In target-date mode, it
  means "at least this many items in L% of simulated futures". The probability curve and
  the projection follow the same reading.
- **Grouping limit**: 60 groups keeps the distribution readable at typical laptop widths.
  This is a presentation default, not a statistical choice.
- **Sequencing**: This feature builds on the web UI from spec 003. The visual-styling work
  in spec 004 is in progress separately; the charts should follow whatever visual style is
  current when they're implemented.
- **Clean-room**: Chart ideas are common practice in Monte Carlo forecasting (e.g. as seen
  in predictability-engine). Per Constitution Principle I, no code, naming, file structure,
  or documentation is copied from any existing tool.
