# Research: Cycle-Time, Aging-WIP, and Cumulative-Flow Metrics for Jira

Sources consulted (public Atlassian documentation and developer-community threads; no
flow-metrics code copied from any tool - Constitution Principle I):

- Changelog shape and `expand=changelog` bundling:
  https://community.atlassian.com/forums/App-Central-articles/Beyond-JQL-How-to-Query-Reconstruct-and-Export-Jira-Issue/ba-p/3255580,
  community threads on `POST /rest/api/2/search` with `expand=changelog`.
- Live introspection against Linear's GraphQL API (`api.linear.app/graphql`), run with the
  user's own key during planning - see §5. Confirms Linear's shape for the *next* source,
  even though this spec is Jira-only.

## 1. What "start" means for a Jira issue

**Decision**: an issue's start date is the timestamp of its *first* status change whose
destination status has category `indeterminate` (Jira's three categories are `new`,
`indeterminate`, `done` - confirmed already in spec 010's research for `done`; the same
project-statuses call this feature reuses also returns `indeterminate` for free).

**Rationale**: Jira has no direct "started" field (unlike Linear - see §5). The changelog's
`items` array, filtered to `field == "status"`, gives every transition with a timestamp
(`created`) and the destination status (`toString`/`to`). The first transition whose
destination resolves to `indeterminate` is the start signal (spec's Edge Cases: "first
entry, not most recent" - an issue that left and re-entered progress is still measured from
its first entry).

**To be verified live** (quickstart Scenario 6): whether `expand=changelog` on the *new*
`POST /rest/api/3/search/jql` endpoint (spec 010 migrated to this because the legacy
`/search` was removed) still bundles each issue's changelog in the same response, the way
community reports describe for the older `/rest/api/2/search`. If it does not, the fallback
is one `GET /rest/api/3/issue/{key}/changelog` call per issue - materially more expensive,
and the reason §4's scale decision exists.

## 2. Query shape: one fetch covers all three views

**Decision**: one JQL query covers every issue this feature needs:
`project = "<key>" AND ((status in (<done statuses>) AND resolved >= <window>) OR status
in (<in-progress statuses>))` - i.e., issues resolved inside the lookback window, plus every
issue currently in an in-progress status, regardless of age.

**Rationale**: cycle-time (User Story 1) needs resolved issues; aging-WIP (User Story 2)
needs currently-open in-progress issues, which may be older than the lookback window itself
(an issue stuck for months is exactly what that view exists to surface); cumulative-flow
(User Story 3) needs both, plus each one's `created` date (already free on every issue,
no changelog needed) to know when it entered the "not started" band. One query, reusing the
exact cursor-pagination loop `_fetch_resolved_issues` (spec 010) already implements, just a
different JQL and field set.

**In-progress status detection costs one more small request, not zero** (revised after
reading the merged spec 010 code, not just the plan): `fetch_jira_throughput`'s existing
`_detect_done_statuses` already calls the project-statuses endpoint once, for `done` only,
and its signature is already shipped/tested. Rather than change that signature to also
return the full category map - real regression risk to working code, for a tiny saving -
`compute_jira_flow_metrics` makes its own call to the same statuses endpoint to detect
`indeterminate` (in-progress) statuses, sharing the parsing logic with
`_detect_done_statuses` through one new private helper (`_fetch_status_categories`), not
sharing the network call. This endpoint returns a small, non-paginated payload - the same
cost class spec 010 already pays once per request, nowhere near the changelog cost §4
discusses. Two cheap calls, not one, is an acceptable trade for not touching tested code.

**Alternatives considered**: separate queries per view - rejected; they'd overlap almost
entirely (every resolved issue needed for cycle-time is also needed for cumulative-flow) and
would double-count API cost for no benefit.

## 3. One universe, reused across all three views

**Decision**: all three views share the same exclusion rule - an issue with no known
in-progress transition is excluded from cycle-time (FR-002), from the aging view
(it isn't open-in-progress if it was never in progress), and from cumulative-flow (its
"not started"/"in progress" boundary can't be placed, so it falls outside
cumulative-flow's own universe too - spec's SC-003 defines that universe as "issues with a
known in-progress transition").

**Rationale**: one consistent rule is simpler to implement, test, and explain than three
near-identical rules with subtly different edge cases (Principle V). An issue resolved
directly from its initial status (never touched "in progress") is real and not rare - closed
duplicates, won't-fix, etc. - and the spec already names this exclusion explicitly (Edge
Cases).

## 4. Scale: changelog fetches are the expensive part

**Decision** (user-confirmed 2026-10-07, plan.md "Decisions needing confirmation" §1):
cap changelog fetching at 500 issues (resolved-in-window + currently-in-progress,
combined). Issues beyond the cap are skipped for flow metrics only - the existing
throughput forecast is unaffected, since it never needs a changelog. The count of skipped
issues is reported in the response (`FlowMetrics.capped_count`), never silently dropped.

**Rationale**: unlike spec 010's throughput fetch (cheap: one page of plain issue fields),
a changelog fetch is confirmed, from community reports, to be resource-intensive enough
that fetching it for thousands of issues at once risks Jira's rate limits even when
requests are correctly paginated. This is a stricter, separate scale decision from spec
010's "no fixed limit" choice for plain throughput, which this project treats as a product
decision needing confirmation, not an implementation detail to assume (same precedent spec
010 itself set).

## 5. Linear's shape, for context (not implemented here)

**Finding** (live introspection, 2026-10-07, user's own key - revoked immediately after):
`Issue.startedAt: DateTime` exists as a direct, Linear-maintained field - no changelog
needed at all. `WorkflowState.type: String!` carries the same category concept Jira uses
(`backlog`/`unstarted`/`started`/`completed`/`canceled`/`duplicate`, confirmed against a
real team), and multiple status *names* can share one category (`"In Progress"` and `"In
Review"` both showed `type: "started"`) - validating that category-based detection (not
status-name matching) is correct for both sources, not just Jira.

**Rationale for recording this here**: this spec is Jira-only (clarified 2026-10-07), but
the finding directly informs the Linear follow-up's own future research.md - Linear will
not need anything like §1's changelog approach at all, just one new field on the existing
`_ISSUES_QUERY`.

## 6. No new dependency

**Decision**: no new runtime dependency on either side. The changelog fetch reuses
`jira_client.py`'s existing HTTP seam (`_jira_get`/`_jira_post`) and error taxonomy; the new
charts reuse `recharts`, already a frontend dependency since spec 005.
