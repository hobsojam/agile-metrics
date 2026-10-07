# Feature Specification: Cycle-Time, Aging-WIP, and Cumulative-Flow Metrics for Jira

**Feature Branch**: `011-jira-flow-metrics`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Cycle-time, aging-WIP, and cumulative-flow charts: item-level flow metrics, deferred twice already (specs 005 and 010's own Assumptions, and issue #181's 'cheaper path to item-level flow metrics' note). Unlike the existing throughput-based forecast charts, these need item-level start AND end dates, not just completion/resolution dates. Add flow-metrics visualizations alongside the existing forecast charts: a cycle-time distribution/scatter showing how long completed items took from start to finish, an aging-WIP chart showing how long currently-in-progress items have been open, and a cumulative flow diagram showing the count of items in each workflow state over time. These are diagnostic/retrospective views of a team's actual flow, complementary to (not a replacement for) the existing Monte Carlo forecast. No change to the forecasting library itself. Scoped to Jira first (clarified 2026-10-07): Jira is the most common source, so it ships first as its own feature; CSV and Linear support are planned, incremental follow-ups reusing the same views, not part of this spec."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See how long completed Jira work actually took (Priority: P1)

A user forecasting from Jira wants to see, at a glance, how long their team's
completed issues actually took from start to finish - not just the aggregate
throughput count the forecast already uses, but the spread across individual
issues, so they can see whether most issues finish quickly with a few slow
outliers, or whether cycle time is consistently long.

**Why this priority**: This is the most direct, most requested gap - "why does
throughput look the way it does" is the question a forecast alone cannot answer.

**Independent Test**: Forecast from a Jira project with a known set of resolved
issues, and confirm the cycle-time view shows one data point per issue with its
correct duration, correctly excluding any issue that never entered an in-progress
status before it was resolved.

**Acceptance Scenarios**:

1. **Given** a Jira project with resolved issues that each entered an in-progress
   status before being resolved, **When** the user views flow metrics, **Then**
   the cycle-time view shows one entry per issue, each showing the time from when
   it first entered an in-progress status to its resolution.
2. **Given** a resolved issue that never entered an in-progress status (for
   example, closed directly from its initial status), **When** the user views flow
   metrics, **Then** that issue is excluded from the cycle-time view and the view
   indicates that some issues were excluded, rather than silently omitting them or
   showing a zero/negative duration.

---

### User Story 2 - See which in-progress Jira issues have been open longest (Priority: P2)

A user wants to see every issue that is currently in an in-progress status,
ordered by how long it has been in progress, so they can spot work that has been
open longer than the team's usual cycle time and may need attention.

**Why this priority**: Directly actionable for a daily/weekly team conversation,
but depends on the same start-signal data as User Story 1, so it naturally
follows it.

**Independent Test**: Forecast from a Jira project with a mix of resolved and
currently-in-progress issues, and confirm the aging view shows only the
in-progress issues, each with its current age, ordered oldest-first.

**Acceptance Scenarios**:

1. **Given** a Jira project with issues currently in an in-progress status,
   **When** the user views flow metrics, **Then** the aging view lists each such
   issue with how long it has been in progress as of today, oldest first.
2. **Given** no issues are currently in progress, **When** the user views flow
   metrics, **Then** the aging view states plainly that nothing is in progress,
   rather than showing an empty or broken chart.

---

### User Story 3 - See how Jira work-in-progress has built up over time (Priority: P3)

A user wants a view of how many issues were not yet started, in progress, and
done on each day over the lookback window, so they can see whether
work-in-progress has been growing (a sign the team is starting more than it
finishes) or staying flat.

**Why this priority**: Valuable but the least immediately actionable of the
three - useful for a retrospective trend conversation rather than a daily check,
and it reuses the same two signals (first in-progress transition, resolution)
as the other two stories, so it adds the least new data of the three once they
exist.

**Independent Test**: Forecast from a Jira project with issues spanning several
weeks, and confirm that for any day in the lookback window, the three counts
(not started, in progress, done) sum to the total number of issues with a known
in-progress transition.

**Acceptance Scenarios**:

1. **Given** a Jira project with issues spanning several weeks, **When** the user
   views flow metrics, **Then** the cumulative-flow view shows, for each day in
   the lookback window, how many issues were not yet started, in progress, and
   done, and the three counts sum to the total number of issues with a known
   in-progress transition.

---

### Edge Cases

- **Issue resolved without ever entering an in-progress status**: excluded from
  the cycle-time view (no start signal to measure from); the user is told issues
  were excluded, not left to wonder why counts don't match.
- **Issue that entered an in-progress status, left it, and re-entered it later**:
  the *first* entry into an in-progress status is the start signal, consistent
  with "how long since work on this genuinely began," not the most recent one.
- **No issues currently in progress**: the aging view says so plainly (User
  Story 2, Acceptance Scenario 2), not an empty or broken-looking chart.
- **No resolved issues with a known start signal**: the cycle-time view says so
  plainly, mirroring the existing "not enough data" messages the forecast
  already uses.
- **A single extreme outlier issue** (e.g., one issue open for a year among many
  one-day issues): all views still render; an outlier is itself useful
  information about the team's flow and MUST NOT be hidden or clipped.
- **Custom workflows** where "in progress" is not Jira's standard category name:
  the same per-project, category-based detection spec 010 built for done
  statuses applies here to the `indeterminate` category, not literal status
  names - a custom workflow is supported the same way, not a separate gap.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST compute a cycle-time view listing, for every
  resolved Jira issue that has a known first-entered-in-progress date, the
  duration from that date to its resolution date.
- **FR-002**: The system MUST exclude from the cycle-time view, rather than
  guess about, any resolved issue with no known in-progress transition - and
  MUST tell the user when issues were excluded.
- **FR-003**: The system MUST compute an aging-WIP view listing, for every Jira
  issue currently in an in-progress status, how long it has been in that status
  as of today, ordered from longest to shortest.
- **FR-004**: The system MUST compute a cumulative-flow view showing, for each
  day in the lookback window, how many issues were not yet started, in progress,
  and done, derived only from each issue's first-in-progress and resolution
  signals (simplified three-band view, not a full multi-state workflow diagram -
  clarified 2026-10-07; see Assumptions).
- **FR-005**: These flow-metrics views apply to Jira-sourced forecasts only in
  this version (clarified 2026-10-07). Manual paste, Linear, and CSV are
  unaffected and keep showing only the existing throughput forecast and its four
  charts; CSV and Linear support are planned as incremental follow-up features
  (see Assumptions).
- **FR-006**: "In progress" MUST be detected the same way spec 010 detects
  "done" - from the project's own workflow status categories (the
  `indeterminate` category), not a hard-coded status name - so custom workflows
  are supported without special-casing.
- **FR-007**: The flow-metrics views MUST be presented alongside the existing
  Monte Carlo forecast and its four charts, not as a replacement for them - a
  user viewing flow metrics still sees the existing forecast charts too.
- **FR-008**: The system MUST NOT change the forecasting library's simulation
  logic, its inputs, or its outputs (Constitution Principle II) - flow metrics
  are an additional, read-only view built from Jira issue data.

### Key Entities *(include if feature involves data)*

- **Flow Issue**: a single Jira issue with an identity, an optional
  first-entered-in-progress date, and an optional resolution date.
- **Cycle-Time Entry**: one flow issue's duration from its in-progress date to
  its resolution date; exists only for resolved issues with a known in-progress
  date.
- **WIP Snapshot**: one currently-in-progress flow issue's age as of today;
  exists only for issues with a known in-progress date and no resolution date.
- **Flow-State Count**: for one day in the lookback window, the number of flow
  issues in each of the three bands (not started, in progress, done).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user forecasting from Jira sees a cycle-time view with no
  additional setup beyond the credentials and project they already provide for
  the existing Jira forecast.
- **SC-002**: A user can identify the longest-open in-progress issue from the
  aging view without consulting Jira directly.
- **SC-003**: In the cumulative-flow view, the three daily counts sum to the
  total number of issues with a known in-progress transition, for every day
  shown, in 100% of valid inputs.
- **SC-004**: An issue excluded from the cycle-time view for lacking an
  in-progress transition is always accompanied by a visible indication that
  exclusions occurred - never a silent count mismatch a user would have to
  notice themselves.

## Assumptions

- **Jira first, by design (clarified 2026-10-07)**: Jira is the most common
  data source, so it ships first as its own feature. CSV support (cheapest -
  `start_date`/`end_date` already exist unused in the `Item` model from spec
  007) and Linear support (needs its own research into whatever start-tracking
  its API offers) are planned, incremental follow-ups that reuse the same three
  views once Jira establishes the pattern - not part of this spec.
- **Simplified cumulative-flow bands (clarified 2026-10-07)**: the cumulative-flow
  view uses three bands (not started, in progress, done) derived from the two
  signals this feature already computes, not a full multi-state workflow
  diagram. Nothing in this system tracks a complete per-issue status-transition
  history today; building that would be a materially larger feature in its own
  right, not a chart.
- **First in-progress entry, not most recent**: an issue that moved into
  progress, back out, and in again is measured from its first entry (Edge
  Cases) - the question these views answer is "how long has real work been
  touching this," not the most recent attempt.
- **No alert threshold for aging WIP**: the aging view is a plain, sorted
  display, not a warning or quality gate - consistent with this project's
  existing preference for advisory, non-blocking information (spec 009).
- **Read-only and retrospective**: flow metrics do not feed back into the Monte
  Carlo forecast and do not change its outcomes (Constitution Principle II).
- **Presented alongside the existing Jira forecast UI**: flow metrics appear as
  additional views within the same request a user already makes, not a separate
  flow.
