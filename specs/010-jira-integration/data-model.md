# Data Model: Jira Integration

No new simulation-side entities. The forecasting library still consumes only
`ThroughputHistory` (Principle II). What this feature adds is an adapter-side input and one
response field.

## Adapter input: `JiraConnection` (in `jira_client.py`, never serialized)

| Field | Type | Meaning | Validation |
|---|---|---|---|
| `site` | `str` | Jira Cloud site host, e.g. `acme.atlassian.net` | non-empty; no scheme or path |
| `email` | `str` | Account email used for Basic auth | non-empty |
| `api_token` | `str` | Jira API token | non-empty; **never logged, printed, or persisted** (FR-008) |
| `project_key` | `str` | Project key, e.g. `ENG` | non-empty |
| `periods` | `int` | Lookback window in periods | `>= 1`, default 26 |
| `period_days` | `int` | Period length (passed through from the request) | `>= 1` |

`JiraConnection` is a plain frozen dataclass rather than a pydantic model, so its `repr` can be
overridden to mask `api_token` - a defence against accidental logging.

## Adapter output: `ThroughputHistory` (existing, unchanged)

Produced by `fetch_jira_throughput(connection) -> ThroughputHistory`. Its validators
(`MIN_HISTORICAL_PERIODS`, not-all-zero, non-negative) are reused, not duplicated (research §5).

## Response field: `done_statuses` (new, web/CLI reporting only)

Clarification Q3 requires the forecast to report which statuses were treated as done. This is
carried alongside, not inside, `ForecastResult`:

- Web: `ForecastResponseBody` gains `done_statuses: list[str]` (empty list for manual, Linear,
  and CSV requests) - additive, web-layer only, matching how `history` was added for charts
  (spec 005/006 precedent).
- CLI: printed as one extra line after the confidence levels when the source is Jira.
- `ForecastResult` itself is unchanged (Principle II; the same reasoning as spec 006).

## Entities and their relationships

- A **project** has issue types and, per issue type, a workflow of **statuses**; each status
  has a fixed **status category** (`new`, `indeterminate`, `done`, plus the no-category key).
- A **done status set** is derived from a project's statuses: every status name whose category
  is `done`.
- An **issue** (resolved, non-epic, non-sub-task) contributes one completion to the period
  containing its UTC `resolutiondate`. Issues with no `resolutiondate` contribute nothing.

## Validation rules carried from the spec

- Epics and sub-tasks are excluded (FR-002, clarification Q1).
- Issues with no resolution date are excluded (FR-003).
- A status is "done" only if the project's workflow classifies it as `done` (FR-004).
- Zero completed issues, too few periods, or all-zero counts reuse the existing messages via
  `ThroughputHistory` validation (FR-010).
