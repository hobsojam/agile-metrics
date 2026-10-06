# Contract Delta: Jira Source

This document describes **only what changes** relative to the existing forecast contracts
(specs 006 and 007). It adds a fourth data source; every existing source and response field is
unchanged.

## Web request: `POST /api/forecast` (JSON)

New optional fields, used together as one source (exactly one source must be given: `history`,
Linear fields, CSV, or Jira fields - see "Source selection" below):

| Field | Type | Required with | Notes |
|---|---|---|---|
| `jira_site` | string | `jira_email`, `jira_api_token`, `jira_project_key` | e.g. `acme.atlassian.net` |
| `jira_email` | string | as above | account email |
| `jira_api_token` | string | as above | never echoed back, never stored |
| `jira_project_key` | string | as above | e.g. `ENG` |
| `jira_periods` | integer | optional | lookback in periods, default 26 |

## Web response: `ForecastResponseBody`

One new field, additive:

```json
{
  "...existing fields unchanged...": "",
  "done_statuses": ["Done", "Released"]
}
```

`done_statuses` is `[]` for manual, Linear, and CSV requests.

## Web error responses

Jira failures use the existing `{"error": "<message>"}` shape with HTTP 400, one distinct
message per category (contracts/jira-errors.md):

- authentication failed
- site not reachable as a Jira site
- project not found or not visible to this account
- rate limited (includes retry-after when Jira provided it)
- Jira API unavailable / unexpected response
- too few periods / no completed work (existing messages, reused)

## CLI

| Flag | Env fallback | Default | Notes |
|---|---|---|---|
| `--jira-site` | `AGILE_METRICS_JIRA_SITE` | - | host only |
| `--jira-email` | `AGILE_METRICS_JIRA_EMAIL` | - | |
| `--jira-api-token` | `AGILE_METRICS_JIRA_API_TOKEN` | - | prefer the env var; a literal flag value lands in shell history |
| `--jira-project` | - | - | project key |
| `--jira-periods` | - | 26 | lookback in periods |

After the confidence levels, when the source is Jira, one line lists the done statuses used:

```text
Done statuses: Done, Released
```

## Source selection (all surfaces)

Exactly one source must be given. Accepted combinations:

- `history`, or
- Linear: `linear_api_key` + `linear_team_id`, or
- CSV: `csv_file` / `csv_text`, or
- Jira: `jira_site` + `jira_email` + `jira_api_token` + `jira_project_key`.

A partial set for any source names the missing field specifically, the same way the Linear
partial-credential fix does (spec 006 follow-up). None of the four sources given, or more than
one given, produces the existing "exactly one of ..." message, extended to name all four.

## Library (`agile_metrics` public API)

New module `agile_metrics.jira_client` exposing `fetch_jira_throughput(connection:
JiraConnection) -> ThroughputHistory` and `JiraConnection`. `forecast_by_items` and
`forecast_by_date` are unchanged.
