# Feature Specification: Cycle Time Scatterplot with Percentile Lines

**Feature Branch**: `012-cycle-time-scatterplot`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Redesign the Cycle Time flow-metrics chart as a scatterplot (issue resolution date on the X axis, cycle time in days on the Y axis) instead of the current bar-per-issue view, with the same 50/70/85/95% percentile reference lines already used in the forecast Distribution chart, so teams can read off a service-level expectation directly from historical data. Overlay the 85th-percentile cycle-time threshold as a reference line on the Aging Work In Progress chart too, so an in-progress item that has already exceeded the historical 85th-percentile cycle time is visually flagged as at-risk. Both charts are part of the existing Jira flow-metrics feature (spec 011) and only apply when flow_metrics data is present; this is a visualization/analysis change only, no new backend data is needed beyond what compute_jira_flow_metrics already returns (CycleTimeEntry list and WipSnapshot list) plus percentile computation done client-side or reusing existing forecast percentile logic."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a service-level expectation from historical cycle time (Priority: P1)

A team member reviewing Jira flow metrics wants to know, from historical data alone, "how long does work usually take, and what's a safe commitment?" Today the Cycle Time view shows one bar per resolved item with no sense of trend or distribution, so answering that question means eyeballing a list of numbers. Redesigning it as a scatterplot - resolution date across time, cycle time in days up the Y axis - with the same four confidence-level lines (50/70/85/95%) already familiar from the forecast chart lets them read the answer directly off the picture: "85% of recent work finished within N days."

**Why this priority**: This is the core value of the redesign - it's the reason a scatterplot-with-percentiles is more useful than a bar-per-item view. Without it, there's no improvement over the current chart.

**Independent Test**: Load flow metrics for a Jira project with several resolved issues; confirm the Cycle Time view renders a scatterplot with resolution date on the X axis, cycle time in days on the Y axis, and four labeled percentile lines whose values match each percentile of the plotted cycle times.

**Acceptance Scenarios**:

1. **Given** flow metrics with 10 resolved issues spanning several weeks, **When** the Cycle Time view renders, **Then** it shows one point per issue positioned by its resolution date and cycle time, plus four reference lines labeled 50%, 70%, 85%, and 95%, each at the correct percentile value for the plotted cycle times.
2. **Given** a user hovers or focuses a single point, **When** they inspect it, **Then** they can see that issue's key and exact cycle time in days.
3. **Given** flow metrics with zero resolved issues, **When** the Cycle Time view renders, **Then** it shows the existing "nothing to show yet" message instead of an empty chart or lines.

---

### User Story 2 - Spot at-risk work in progress against the historical threshold (Priority: P2)

A team member scanning the Aging Work In Progress view wants to know which in-progress items are already taking longer than most finished work does, without cross-referencing the Cycle Time view by hand. Overlaying the historical 85th-percentile cycle time as a threshold line - and visually distinguishing any in-progress item whose current age has already crossed it - turns that into a glance instead of a calculation.

**Why this priority**: This is the second half of the value proposition and depends on User Story 1's percentile computation, but it's a smaller, additive change to an existing chart rather than a redesign, and the feature is still useful without it.

**Independent Test**: Load flow metrics with both resolved issues (to establish an 85th-percentile cycle time) and in-progress issues of varying ages; confirm the Aging WIP view shows a labeled threshold reference line at that value, and that bars for items older than the threshold are visually distinguished from items that are not.

**Acceptance Scenarios**:

1. **Given** an 85th-percentile historical cycle time of 12 days and an in-progress item aged 15 days, **When** the Aging WIP view renders, **Then** that item's bar is visually marked as exceeding the threshold and a reference line appears at 12 days.
2. **Given** the same threshold and an in-progress item aged 5 days, **When** the Aging WIP view renders, **Then** that item's bar is shown in the normal (non-flagged) style.
3. **Given** flow metrics with zero in-progress issues, **When** the Aging WIP view renders, **Then** it shows the existing "nothing currently in progress" message instead of an empty chart.

---

### Edge Cases

- What happens when there are too few resolved issues to compute a reliable percentile (e.g., 1-4)? The threshold line and at-risk flagging are not shown, and the view indicates there isn't enough history yet rather than displaying a misleading single-point "percentile" (see Assumptions).
- What happens when several resolved issues share the same resolution date? Each is plotted as its own point on that date; overlapping points are not merged or deduplicated.
- What happens when all resolved issues have the same cycle time? All four percentile lines coincide at that value; this is shown as-is, not collapsed into one line.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Cycle Time view MUST render each resolved item as a point positioned by its resolution date (X axis) and cycle time in days (Y axis), replacing the current one-bar-per-item view.
- **FR-002**: The Cycle Time view MUST overlay four reference lines at the 50th, 70th, 85th, and 95th percentiles of the plotted cycle times, each labeled with its percentile and day value, using the same visual convention (color, labeling style) as the forecast Distribution view's confidence-level lines.
- **FR-003**: Percentile values shown on both the Cycle Time view and the Aging WIP threshold MUST be computed with the same method already used for the forecast's confidence-level outcomes, so the two kinds of view are numerically consistent given the same underlying data.
- **FR-004**: The Aging Work In Progress view MUST overlay a single reference line at the 85th-percentile cycle time computed from the resolved items in the same flow-metrics result, labeled as a threshold.
- **FR-005**: The Aging Work In Progress view MUST visually distinguish any in-progress item whose current age exceeds the 85th-percentile threshold from items that do not exceed it.
- **FR-006**: When fewer than 5 resolved items are available, both the Cycle Time view's percentile lines and the Aging WIP view's threshold line and at-risk flagging MUST be omitted, and the affected view MUST indicate that there isn't enough history yet rather than showing a misleading threshold.
- **FR-007**: Both views MUST continue to show their existing empty-state messaging when there are zero resolved items or zero in-progress items, respectively.
- **FR-008**: This feature MUST NOT change the `CycleTimeEntry` or `WipSnapshot` data contracts, and MUST NOT introduce a new backend endpoint. Percentile values MAY be added as a new field on the existing flow-metrics response of the current endpoint, if that is what reusing the forecast's percentile method (FR-003) requires.

### Key Entities

- **CycleTimeEntry** (existing, unchanged): one resolved issue's key, start date, and resolution date - the source of each scatterplot point and of the percentile computation.
- **WipSnapshot** (existing, unchanged): one in-progress issue's key, start date, and current age in days - the source of each Aging WIP bar and of the at-risk comparison against the threshold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can state the historical 85% service-level cycle time for a project directly from the Cycle Time view, without performing any calculation themselves.
- **SC-002**: A user can identify, within a few seconds of looking at the Aging WIP view, which in-progress items (if any) have already exceeded the historical 85% cycle-time threshold.
- **SC-003**: Both views reflect whatever flow-metrics data is currently loaded - there are no hardcoded or stale threshold values that fail to update when the underlying Jira data changes.
- **SC-004**: For a project with fewer than 5 resolved items, a user is never shown a percentile-based threshold that the data can't reliably support.

## Assumptions

- Percentile calculation reuses the method already used for the forecast Distribution view's 50/70/85/95% confidence-level outcomes. Since that method is computed server-side today (the frontend never recomputes percentiles, only renders values the backend already computed), the percentile values for this feature are computed server-side too, and added as a new field on the existing flow-metrics response - rather than reimplementing the same statistical method a second time in the frontend, which would risk the two silently drifting apart.
- The Cycle Time scatterplot's X axis uses each item's exact resolution date with no weekly/daily bucketing, matching how a typical cycle-time scatterplot is read.
- "Visually distinguished" (FR-005) means a different fill color/style for the bar itself on the existing chart, not a new filter, toggle, or separate view - keeping this a presentation-only change (FR-008).
- A minimum of 5 resolved items is treated as the smallest sample percentiles are shown for; this reuses the same "nothing to show yet" pattern already established for zero-item empty states, extended to a small-sample case specific to this feature.
- This feature only applies to Jira-sourced results (the only source `flow_metrics` is currently populated for, per spec 011); other data sources are unaffected.
