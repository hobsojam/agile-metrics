# Data Model: Linear Integration

No new `pydantic` models in `agile_metrics.models`. `ThroughputHistory`, `ForecastRequest`,
and `ForecastResult` are all **unchanged** — this feature's only job is producing a
`ThroughputHistory` from a second source.

## New function (not a model): `fetch_linear_throughput`

| Parameter | Type | Meaning |
|---|---|---|
| `api_key` | `str` | Linear personal API key, used for exactly one request, never persisted (FR-005) |
| `team_id` | `str` | The Linear team whose completed issues to fetch |
| `period_duration` | `timedelta` | Length of one period — the same concept `ThroughputHistory.period_duration` already uses |
| `periods` | `int` | How many periods of history to fetch (default 26, research.md §7) |

**Returns**: `ThroughputHistory` — bucket `k` (0 = oldest) holds the count of completed
issues whose `completedAt` falls within `[today - (periods - k) * period_duration, today -
(periods - k - 1) * period_duration)`, anchored to today exactly as `reference_date`
already is for manually-entered history.

**Raises** (research.md §3 — one type per distinguishable failure, FR-007):

| Exception | Condition |
|---|---|
| `LinearAuthenticationError` | HTTP 401 / `AUTHENTICATION_ERROR` |
| `LinearTeamNotFoundError` | The team-validation query finds no accessible team with that id |
| `LinearRateLimitedError` | HTTP 400 with GraphQL error code `RATELIMITED` |
| `LinearAPIUnavailableError` | Network failure, timeout, or any 5xx |

All four inherit from a common `LinearIntegrationError` so callers can catch broadly or
specifically. **Not** a new exception: an all-zero or too-short bucketed history raises the
*existing* `pydantic.ValidationError` from `ThroughputHistory`'s own validators (FR-004,
FR-010) — the function does not catch or wrap that; it propagates exactly like a
manually-entered all-zero history already does.

## Request/response changes (web layer)

See [contracts/forecast-api.md](./contracts/forecast-api.md) for the full delta.

- `ForecastRequestBody.history` changes from required to **optional**.
- Three new optional fields: `linear_api_key`, `linear_team_id`, `linear_periods`.
- Validation: exactly one of `history` or (`linear_api_key` **and** `linear_team_id`) must
  be present — enforced the same way the existing "exactly one of `backlog_size`/
  `target_date`" rule already is, as a plain `ValueError` caught by the existing
  `_format_error` path (no new error-formatting code needed).

## CLI changes

- `--history` changes from required to optional.
- Three new options: `--linear-api-key` (also readable from the `AGILE_METRICS_LINEAR_API_KEY`
  environment variable), `--linear-team`, `--linear-periods` (default 26).
- Same "exactly one of" validation as the web layer, same error-rendering path
  (`typer.echo(f"Error: {exc}", err=True)`).
