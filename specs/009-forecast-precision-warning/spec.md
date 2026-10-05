# Feature Specification: Forecast Precision Warning

**Feature Branch**: `009-forecast-precision-warning`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "When a forecast's confidence interval is so wide that it isn't practically useful for planning (e.g. the 50% and 95% confidence dates span over a decade, because the underlying historical throughput is sparse, zero-heavy, or highly inconsistent relative to the backlog being forecast), the system should surface a clear warning alongside the existing four confidence-level outcomes, rather than silently presenting the numbers as if any other forecast. This is not a hard gate - the full forecast must still be computed and shown (never hidden or refused), consistent with the project's existing principle of always surfacing real uncertainty rather than a false point estimate. The warning should explain, in plain language, why precision is low, and must apply consistently across both forecast modes (backlog-size and target-date), all three data sources (manual paste, Linear import, CSV import), and all three presentation surfaces (CLI, web UI, JSON API) - since it reflects a property of the underlying simulation output, not any particular input path or forecasting mode."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a warning when a forecast is too imprecise to plan against (Priority: P1)

A user runs a forecast and gets back four confidence-level outcomes that span an
impractically wide range (for example, years apart for a date-based forecast, or wildly
different item counts for a count-based one). Without a clear signal, they might mistake
this for a normal, trustworthy result and make a commitment based on it. They need an
unmistakable indication that this particular forecast's precision is too low to plan
against, right alongside the numbers themselves.

**Why this priority**: This is the entire point of the feature — preventing a
technically-correct-but-practically-useless forecast from being mistaken for a reliable
one, which is the exact risk that prompted this feature.

**Independent Test**: Run a forecast against historical throughput data known to be sparse
or highly inconsistent, and confirm a precision warning appears alongside the four
confidence-level outcomes. Run a forecast against consistent, ample historical data, and
confirm no warning appears.

**Acceptance Scenarios**:

1. **Given** historical throughput data that is sparse, zero-heavy, or highly inconsistent
   relative to the size of the backlog (or target date) being forecast, **When** a user
   requests a forecast, **Then** the response includes a clear warning that this forecast's
   precision is too low to be practically useful for planning, in addition to the usual
   four confidence-level outcomes.
2. **Given** historical throughput data that produces a reasonably tight, useful spread of
   outcomes, **When** a user requests a forecast, **Then** no precision warning appears.
3. **Given** a forecast that triggers the warning, **When** the user views the result,
   **Then** all four confidence-level outcomes are still fully present and usable — the
   warning is additive, never a replacement for or suppression of the underlying forecast.

---

### User Story 2 - Understand why a forecast was flagged (Priority: P2)

A user sees the precision warning and needs to know what to actually do about it — whether
to gather more data, wait for throughput to stabilize, or shrink the scope of what they're
forecasting — rather than just seeing an unexplained "low confidence" label that leaves
them guessing.

**Why this priority**: The warning alone (User Story 1) already prevents the main harm
(false trust in a bad forecast); explaining *why* is valuable for the user to actually
improve their next forecast, but is secondary to the warning existing at all.

**Independent Test**: Trigger the warning and confirm the message explains, in plain
language, what about the historical data made this forecast imprecise (e.g., too little
history, too much inconsistency) rather than a generic, unexplained flag.

**Acceptance Scenarios**:

1. **Given** a forecast flagged as low-precision, **When** the user reads the warning,
   **Then** it names the reason in plain language (for example, pointing to limited or
   highly inconsistent historical data) rather than showing an unexplained label.

---

### User Story 3 - Consistent warning across every data source, mode, and surface (Priority: P3)

A user forecasting via the CLI, the web UI, or the JSON API directly — using manually
pasted history, Linear import, or CSV import, in either backlog-size or target-date mode —
needs the same warning to appear under the same conditions everywhere, since the underlying
forecast computation is identical regardless of how the history was supplied or how the
result is consumed.

**Why this priority**: Important for trust and consistency, but it's a guarantee about
uniform behavior rather than new user-facing value beyond User Stories 1-2, so it's lower
priority.

**Independent Test**: Produce the same underlying throughput history through each of the
three data sources, request a forecast expected to trigger the warning through each of the
three presentation surfaces, and confirm the warning (and its explanation) is identical
every time.

**Acceptance Scenarios**:

1. **Given** the same underlying historical throughput, supplied once via manual paste,
   once via Linear import, and once via CSV import, **When** a forecast is requested each
   way with the same parameters, **Then** the precision warning (present or absent, and its
   explanation if present) is identical across all three.
2. **Given** a forecast expected to trigger the warning, **When** it is requested via the
   CLI, the web UI, and the JSON API directly, **Then** the warning appears consistently
   through all three surfaces.

---

### Edge Cases

- **Minimum allowed historical periods, but consistent**: a forecast built from the fewest
  historical periods the system allows MUST NOT be flagged merely for having little data,
  if the resulting spread of outcomes is still tight and useful.
- **Ample historical periods, but highly inconsistent**: a forecast built from a long
  history that alternates wildly between zero and large throughput bursts MUST be flagged,
  even though it has "enough" data by period count alone.
- **Count-based forecasts (target-date mode)**: the same "is this spread too wide to be
  useful" judgment applies in item-count terms, not just date terms.
- **Intentionally long-range forecasts**: a forecast that is inherently far in the future
  (e.g., a very large backlog, forecast against a team with perfectly consistent but modest
  throughput) is not itself a reason to warn — the warning is about the *relative* spread
  between confidence levels (precision), not about how far out the dates land in absolute
  terms.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST compute and surface an indicator of whether a given
  forecast's precision is too low to be practically useful for planning, alongside the
  existing four confidence-level outcomes.
- **FR-002**: The indicator MUST be based on the actual spread of the computed forecast
  outcomes, not on an input characteristic (such as historical period count) considered in
  isolation — a forecast with little data that is nonetheless tightly clustered MUST NOT be
  flagged, and a forecast with ample data that is nonetheless widely spread MUST be
  flagged.
- **FR-003**: When a forecast is flagged, the system MUST explain, in plain language, why
  its precision is low — not merely display an unexplained label.
- **FR-004**: The system MUST still compute and present the full forecast (all four
  confidence-level outcomes) whether or not the warning is present — the warning is
  additive and MUST NOT suppress, hide, or replace any part of the existing forecast
  output.
- **FR-005**: The warning (presence and explanation) MUST be identical for the same
  underlying historical throughput, regardless of which data source populated it (manual
  paste, Linear import, or CSV import).
- **FR-006**: The warning MUST apply identically to both forecast modes (backlog-size and
  target-date).
- **FR-007**: The warning MUST be visible through every presentation surface that already
  shows the four confidence levels (CLI output, web UI, and the JSON API response) — not
  added to only one surface.

### Key Entities

- **Forecast Precision Warning**: an indicator attached to a forecast result, present only
  when that forecast's outcomes are judged too widely spread to be practically useful,
  carrying a plain-language explanation of why. Not a new standalone concept the user
  interacts with directly — an additional facet of the existing forecast result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user viewing a forecast whose confidence interval spans an impractically
  wide range sees a clear indication that the result has low practical precision, without
  needing to manually compare the four outcomes themselves to notice.
- **SC-002**: A user viewing a forecast with a reasonably tight, useful confidence interval
  sees no such warning — the indicator does not fire on forecasts that are already useful.
- **SC-003**: The full four-confidence-level forecast remains visible and usable whether or
  not the warning is present — nothing about the existing forecast output is hidden,
  replaced, or degraded.
- **SC-004**: The same underlying forecast produces an identical warning (presence and
  explanation) regardless of which data source or presentation surface it is viewed
  through.

## Assumptions

- **No hard gate**: the system always computes and displays the full forecast; the warning
  is advisory only, consistent with this project's existing principle of surfacing real
  uncertainty rather than hiding or refusing an imprecise result.
- **Not a statistical significance test**: this is a product-level judgment about whether a
  forecast's spread is practically useful for planning, not a rigorous hypothesis test —
  there is no null hypothesis being evaluated. The exact threshold/mechanism for "too wide"
  is a planning-phase decision, not fixed by this specification.
- **Computed once, shared everywhere**: because the warning is a property of the underlying
  simulation output (not of any particular data source, forecast mode, or presentation
  layer), it is computed once as part of the existing forecast computation and inherited
  identically by every consumer — the same pattern this project already uses for every
  other forecast metric (e.g., `distribution`, `projection`).
- **No new user-facing input or configuration**: this feature introduces no new
  user-supplied parameter — the warning is derived entirely from the existing forecast
  computation and its inputs.
