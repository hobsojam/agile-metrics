# Contract: Jira Error Messages

Each category is a distinct exception type whose `str()` is the final user-facing text. None
of them includes the API token, and none reveals whether a project exists to an account that
cannot see it (spec FR-007).

| Category | Trigger | Message |
|---|---|---|
| Authentication | 401/403 from `GET /rest/api/3/myself` | `Jira authentication failed - check the email and API token` |
| Site not Jira | network error, or non-Jira response on `/myself` | `Could not reach a Jira site at '<site>' - check the site address` |
| Project not found / not visible | 404 (or 400 "project does not exist") from project statuses | `Jira project '<key>' was not found or is not visible to this account` |
| Rate limited | 429 | `Jira is rate-limiting requests - try again in <N> seconds` (or `later` when no Retry-After) |
| API unavailable | 5xx, or a 2xx body missing expected keys | `Jira API is currently unavailable - try again later` |
| No done statuses | project has no status with category `done` | `Jira project '<key>' has no statuses in the Done category` |
| No completed work / too few periods | `ThroughputHistory` validation | existing messages, reused unchanged |
