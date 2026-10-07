# Research: Jira Integration

Sources consulted (public Atlassian documentation and developer community, no Jira
integration code copied - Constitution Principle I):

- Migration from `/rest/api/3/search` to `/rest/api/3/search/jql`: Atlassian's RFC-61
  announcement and the developer-community threads on the new endpoint's nextPageToken
  pagination (https://community.developer.atlassian.com/t/rfc-61-evolving-search-capabilities-addressing-scalability-with-a-new-enhanced-search-api/83027,
  https://community.developer.atlassian.com/t/jira-cloud-rest-api-v3-search-jql-slower-fetching-with-nextpagetoken-no-totalissues-any-workarounds/90176).
- Status categories: Atlassian's workflow status-categories API group
  (https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-workflow-status-categories/).

## 1. Search endpoint and pagination

**Decision**: Use `POST /rest/api/3/search/jql` with cursor pagination (`nextPageToken`,
`isLast`), requesting `resolutiondate`, `issuetype`, and `status` fields.

**Rationale**: The legacy `/rest/api/3/search` endpoint has been removed from Jira Cloud;
it cannot be the target of new code. The replacement is cursor-based and does not return a
total count, so the adapter must page until `isLast` (or no `nextPageToken`) rather than
computing page counts from a total. Pages are fetched sequentially, since the cursor forbids
parallel random access.

**Alternatives considered**:
- Legacy offset endpoint (`startAt`/`total`) - rejected: removed upstream.
- Single very large `maxResults` request - rejected: Jira caps page size, so pagination is
  needed regardless; the cursor loop is the same shape as Linear's cursor loop.

## 2. Authentication

**Decision**: HTTP Basic auth with `base64(email:api_token)` on every request, against the
site's own base URL (`https://<site>.atlassian.net`). A `GET /rest/api/3/myself` call is
used first to distinguish authentication failure (401) from an unreachable site.

**Rationale**: This is the documented Jira Cloud scheme for API tokens. A cheap identity
call first gives a clean authentication error before any project query, matching the
Linear source's team-validation step.

**Alternatives considered**:
- OAuth 2.0 (3LO) - rejected for the basic version: requires a registered app and a browser
  consent flow, far beyond "paste your token".
- Jira Server/Data Center personal access tokens - deferred by the user's clarification.

## 3. Done statuses: per-project detection

**Decision**: For the requested project, call `GET /rest/api/3/project/{projectKey}/statuses`,
which returns each issue type's statuses with their `statusCategory`. A status counts as done
when its `statusCategory.key` is `"done"`. The set of done status names is then reported back
to the user in the response.

**Rationale**: Clarification Q3 chose automatic detection from the project's own workflow.
Status categories are fixed by Atlassian (four of them, not user-editable), so `done` is a
stable signal, while status *names* vary per project - so categories, not names, are the
right key. Project-scoped statuses are used because a name like "Released" may be a done
status in one project and an in-progress status in another.

**Edge-case handling**: if the same status name is `done` in one issue type and not another,
the name is treated as done when any issue type classifies it so, and the resolution is
reported in the response's `done_statuses` list. A project whose statuses resolve to zero
done categories yields the existing "no completed work" error rather than an all-zero history.

**Alternatives considered**:
- Global `GET /rest/api/3/status` - rejected as the primary source: it is instance-wide and
  not project-scoped, so it can misclassify project-specific names.
- Matching the literal name "Done" - rejected by the clarification (custom workflows).

## 4. Issue-type exclusion (epics and sub-tasks)

**Decision**: Filter client-side on the returned `issuetype` object: exclude when
`issuetype.subtask` is `true` (sub-tasks) or when `issuetype.hierarchyLevel` is above the
story/task level (epics).

**Rationale**: Clarification Q1 excluded epics and sub-tasks. Issue-type *names* are localized
and customizable, so name-based JQL exclusion would be fragile; the `subtask` flag and
hierarchy level are structural. Filtering after fetch costs a few extra bytes per issue and no
extra requests.

**To be verified live** (the Linear `$teamId` lesson - mocked tests did not catch a schema
mismatch): the exact presence and naming of `subtask` and `hierarchyLevel` on the
`issuetype` object of the new search response. quickstart.md Scenario 5 checks this against a
real site before the adapter is considered done.

## 5. Period bucketing and the lookback window

**Decision**: Lookback is `jira_periods` (default 26), converted to a resolved-date window of
`periods × period_days`. Each issue is bucketed by its `resolutiondate` converted to UTC
(clarification Q5), using the same bucket formula as the Linear and CSV sources.

**Rationale**: Reuses the existing bucketing convention so Jira, Linear, and CSV histories are
built identically (spec FR-005). The JQL window is widened by one period on each side and the
exact UTC bucket check is done client-side, because JQL's relative and date-only comparisons are
interpreted in the API user's Jira timezone, which would disagree with the UTC boundaries the
spec requires.

**Alternatives considered**: a JQL-only window with `resolved >= "date"` - rejected, see above.

## 6. Rate limiting and errors

**Decision**: HTTP 429 raises a rate-limited error naming the retry request; the response's
`Retry-After` header, when present, is included in the message. No automatic retry (spec
clarification left retry behavior to planning; a bounded single wait is out of scope for the
basic version, matching the Linear source, which also reports rather than retries).

**Error taxonomy** (contracts/jira-errors.md): authentication (401/403 on `/myself`), site
unreachable (network error or non-Jira response on `/myself`), project not found or not visible
(404 on the statuses call - reported without revealing whether the project exists to a user who
cannot see it, FR-007), rate limited (429), API unavailable (5xx / malformed body).

**Hardening carried over from Linear**: a 2xx response whose body does not contain the expected
shape (e.g. missing `issues` or `nextPageToken` key) raises the API-unavailable error rather
than a `TypeError`. This is the exact crash pattern found and fixed in spec 006's live testing.

## 7. Credential handling

**Decision**: The API token is accepted as a CLI option, with an `AGILE_METRICS_JIRA_API_TOKEN`
environment-variable fallback (same pattern as the Linear key), and as a web request field.
It is used for the request only, never persisted, and never included in any exception message
or log line (spec FR-008), verified by a test asserting absence from `str()` of every raised
error.

## 8. Dependencies

**Decision**: No new runtime dependency. HTTP via the standard library (`urllib.request`,
`base64`, `json`), mirroring `linear_client.py`.

**Rationale**: Principle V; the Linear client already established this pattern. Basic auth is
one header.
