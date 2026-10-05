# Research: Linear Integration

## 1. Authentication

**Decision**: Personal API key, sent as `Authorization: <API_KEY>` — **no `Bearer` prefix**.

**Rationale**: Verified directly against Linear's own docs and empirically against the real
API (an intentionally-invalid key against `https://api.linear.app/graphql` returns HTTP
**401**, body `{"errors":[{"message":"Authentication required, not authenticated",
"extensions":{"code":"AUTHENTICATION_ERROR","statusCode":401,...}}]}`). This is the one
detail easiest to get wrong (OAuth access tokens *do* use `Bearer`; personal API keys do
not), so it was confirmed against the live API rather than assumed.

**Alternatives considered**: OAuth 2.0 app registration — explicitly out of scope per spec
Assumptions (personal/single-user tool, no multi-tenant app to register).

## 2. GraphQL query shape

**Decision**:

- Endpoint: `https://api.linear.app/graphql` (confirmed; introspection works even
  unauthenticated, which is how the field names below were verified against the live
  schema rather than guessed).
- Validate the team first: `query { team(id: $teamId) { id name } }` — a team that doesn't
  exist or isn't accessible to this key returns a GraphQL error distinguishable from an
  auth failure, giving a clear "team not found" message (FR-007) before spending a
  paginated fetch on it.
- Fetch completed issues:
  ```graphql
  query($teamId: ID!, $since: DateTimeOrDuration!, $after: String) {
    issues(
      filter: { team: { id: { eq: $teamId } }, completedAt: { gte: $since, null: false } }
      first: 100
      after: $after
    ) {
      nodes { completedAt }
      pageInfo { hasNextPage endCursor }
    }
  }
  ```
  `completedAt` is `NullableDateComparator` on `IssueFilter` (confirmed via schema
  introspection) — `null: false` excludes issues that haven't completed, `gte: $since`
  bounds the lookback window. `team` filters via `TeamFilter.id: IDComparator`.
- Pagination: Relay-style, confirmed via Linear's docs — `pageInfo { hasNextPage
  endCursor }`, pass the cursor back as `after`. Loop until `hasNextPage` is `false`,
  concatenating every page's `completedAt` values (FR-009/FR-010 — no silent truncation).

**Rationale**: Filtering server-side by team and `completedAt` range means only the data
actually needed crosses the network, and pagination is exactly Linear's own documented
pattern — no custom protocol to reverse-engineer.

**Alternatives considered**: Fetching all issues and filtering client-side — rejected,
wastes the API's complexity budget (see §4) for no benefit.

## 3. Error classification

**Decision**: One exception type per distinguishable failure (FR-007), raised by the new
Linear-adapter module and caught in both the CLI and web layers:

| Condition | Detection |
|---|---|
| Invalid/expired credential | HTTP 401, body `errors[].extensions.code == "AUTHENTICATION_ERROR"` (confirmed live) |
| Team not found / inaccessible | The `team(id: ...)` validation query returns `data.team == null` or a GraphQL error |
| Rate limited | HTTP **400** (not 429) with `errors[].extensions.code == "RATELIMITED"` — confirmed via Linear's rate-limiting docs; this is a real gotcha since 400 is normally a generic client-error code |
| Linear API unavailable | Network-level failure (connection error, timeout) or any 5xx |
| Zero completed issues | **No new error type** — the adapter builds a `ThroughputHistory` with an all-zero `completed_per_period` exactly like manual paste would, and `ThroughputHistory`'s *existing* validator rejects it with the *existing* message (FR-010) — same for "fewer than `MIN_HISTORICAL_PERIODS`" when the lookback window is short. No duplicated validation logic. |

**Rationale**: Routing the "zero issues" and "too few periods" cases through the existing
`ThroughputHistory` validators (rather than writing parallel checks) is what FR-004 asks
for directly, and it's less code, not more.

## 4. Rate limits (for context, not enforced client-side in this feature)

Personal API keys: 2,500 requests/hour and 3,000,000 complexity points/hour per user
(shared across all of that user's keys), 10,000 complexity points per single query — all
confirmed via Linear's rate-limiting docs. A single team's throughput fetch (one team
lookup + a handful of paginated pages at 100 issues/page) is nowhere near these limits for
realistic team sizes; no client-side throttling is needed for this feature's scope, just
surfacing the `RATELIMITED` error cleanly if Linear ever returns it (§3).

## 5. HTTP client

**Decision**: Python's standard library (`urllib.request` + `json`) — no new runtime
dependency.

**Rationale**: This feature makes exactly one kind of call (a JSON POST with one header),
in a simple request/paginate loop. The project's existing HTTP-capable dependencies
(`httpx2`, `requests`, transitively via `pip-audit`) are **dev-only** — not present in the
production image (`uv sync --no-dev`) — so using them here would mean promoting a
dev-only transitive dependency to a direct runtime one, when the stdlib already does the
job. Constitution Technology Stack & Constraints: "prefer the standard library... before
adding new deps." No new dependency to justify in the implementing PR.

**Alternatives considered**: `httpx` as a new direct dependency — rejected; would need
justifying a new dependency (constitution) for functionality the stdlib already covers at
this scope. Worth revisiting if a future integration (e.g. #180 Jira) needs retries,
connection pooling, or async support this feature doesn't.

## 6. Module placement

**Decision**: A single new module, `src/agile_metrics/linear_client.py` — not a new
`integrations/` package.

**Rationale**: Constitution Principle V: "New abstractions MUST be justified by a current,
demonstrated need, not a hypothetical future one." Issue #180 (Jira) is a real backlog
item, but speculatively building an `integrations/` package *now*, before a second
integration actually exists, is exactly the kind of premature structure Principle V warns
against. If/when #180 lands, that's the point to decide whether the two adapters share
enough shape to warrant a common package — deferred, not skipped.

**Public surface**: `fetch_linear_throughput(api_key, team_id, period_duration, periods) ->
ThroughputHistory` is the only function the CLI and web layers call — both existing
presentation layers gain a new way to *produce* a `ThroughputHistory`, but still only ever
call `forecast_by_items`/`forecast_by_date` with it (FR-003; Principle II unaffected — the
simulation core doesn't know or care where the history came from).

## 7. Lookback window default

**Decision**: Default 12 periods (configurable via a new CLI flag / request-body field),
distinct from `MIN_HISTORICAL_PERIODS = 6` (the library's absolute minimum).

**Rationale**: Twelve periods (e.g. ~12 weeks, a quarter) is enough margin above the
6-period minimum that a team with a couple of unusually slow periods doesn't trip the
all-zero or too-few-periods validators by accident, while staying a small, fast fetch. The
spec leaves the exact number as a planning decision (Assumptions) — this is that decision,
not a product requirement, so it's adjustable later without a spec change.

**Alternatives considered**: Fetching a fixed date range (e.g. "last 90 days") instead of a
fixed period count — rejected for this feature; period *count* composes more directly with
the existing `period_duration` concept the library already uses, and avoids a second way to
express "how much history."

## 8. Credential handling in the web request body

**Decision**: The API key travels in the same JSON POST body as the rest of the forecast
request (`POST /api/forecast`), as an additional optional field — not a separate header or
endpoint.

**Rationale**: Matches the existing single-request, stateless contract exactly (spec FR-005:
never persisted beyond the one request). FastAPI/Starlette don't log request bodies by
default, and `_format_error` (existing code) only ever surfaces validation messages, never
raw field values — so the key can't leak through the existing error-formatting path by
accident. The frontend form field for the key should be a password-style input (not logged
to the browser console, not retained in any persisted state, not written to
`localStorage`) — a frontend implementation detail enforced at the task level, not a new
backend contract concern.

**Alternatives considered**: A custom `Authorization`-style header on the forecast
endpoint — rejected; it would create two different ways to authenticate the same single
endpoint for no benefit, since this isn't a multi-request session needing a persistent
credential.
