# Contract Delta: Forecast Web API (`POST /api/forecast`)

This document describes **only what changes** relative to
[specs/005-forecast-charts/contracts/forecast-api.md](../../005-forecast-charts/contracts/forecast-api.md).
Everything not mentioned here (the 200 response shape, static assets) is unchanged.

## Request

`history` becomes **optional**. Three new optional fields are added:

```json
{
  "history": [3, 5, 4, 6, 2, 5, 4, 3],
  "period_days": 7,
  "backlog_size": 20,
  "target_date": null,
  "seed": 42,
  "linear_api_key": null,
  "linear_team_id": null,
  "linear_periods": null
}
```

**Manual-paste mode** (unchanged): `history` present, all three `linear_*` fields absent or
null.

**Linear mode** (new): `history` absent or null; `linear_api_key` and `linear_team_id`
both present. `linear_periods` optional, defaults to 12 if omitted.

**Invalid combinations** (both new 400 cases, same `{"error": "..."}` shape as every
existing validation failure):

| Combination | Error |
|---|---|
| Neither `history` nor Linear fields present | `"exactly one of history or (linear_api_key and linear_team_id) is required"` |
| Both `history` and Linear fields present | Same message — this is symmetric with the existing `backlog_size`/`target_date` "exactly one of" rule |
| `linear_api_key` present without `linear_team_id` (or vice versa) | Same message — both are required together |

## New error cases

All still 400, same `{"error": "..."}` shape, each message naming the specific problem
(FR-007) so a user can tell a bad credential apart from an inaccessible team apart from a
rate limit:

| Condition | Example `error` message |
|---|---|
| Invalid/expired Linear API key | `"Linear API key is invalid or expired"` |
| Team not found or inaccessible | `"Linear team '<id>' was not found or is not accessible with this API key"` |
| Linear API rate-limited | `"Linear API rate limit exceeded - try again later"` |
| Linear API unavailable | `"Linear API is currently unavailable - try again later"` |
| Zero completed issues in the lookback window | The *existing* all-zero-history message, unchanged |
| Fewer completed periods than the minimum | The *existing* too-few-periods message, unchanged |

## CLI

New options: `--linear-api-key` (env var `AGILE_METRICS_LINEAR_API_KEY`), `--linear-team`,
`--linear-periods` (default 12). `--history` becomes optional. Same "exactly one of" and
Linear-error messages as the web API, rendered the same way existing CLI errors already are
(`Error: <message>` on stderr, exit code 1).

## Library (`agile_metrics` public API)

New: `agile_metrics.linear_client.fetch_linear_throughput()` and its
`LinearIntegrationError` subclasses (data-model.md). `forecast_by_items` and
`forecast_by_date` keep their existing signatures and behavior unchanged.
