# Contract: Forecast Web API

The JSON contract between the React frontend and the FastAPI backend. Per Constitution
Principle II, the backend route only calls the public `agile_metrics` API
(`forecast_by_items`/`forecast_by_date`) to satisfy it.

## `POST /api/forecast`

### Request body

```json
{
  "history": [3, 5, 4, 6, 2, 5, 4, 3],
  "period_days": 7,
  "backlog_size": 20,
  "target_date": null,
  "seed": 42
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `history` | `int[]` | yes | Non-negative integers |
| `period_days` | `int` | yes | Positive |
| `backlog_size` | `int \| null` | exactly one of this or `target_date` | Positive |
| `target_date` | `string \| null` | exactly one of this or `backlog_size` | `YYYY-MM-DD`, must be in the future |
| `seed` | `int \| null` | no | Omit for a fresh random forecast each request |

### Responses

**200 OK** — forecast computed:

```json
{
  "outcomes": {"50": "2026-11-05", "70": "2026-11-12", "85": "2026-11-12", "95": "2026-11-19"},
  "trials_run": 10000,
  "periods_used": 8
}
```

`outcomes` values are date strings (`YYYY-MM-DD`) when `backlog_size` was supplied, or
integers when `target_date` was supplied.

**400 Bad Request** — any input validation failure (CLI-level type error or a library
validation rejection):

```json
{"error": "exactly one of backlog_size or target_date is required, not both or neither"}
```

The frontend MUST render this `error` message directly to the user — never show a generic
"something went wrong" or a raw network/stack-trace error (spec FR-004/SC-003).

## Static assets

Every other path (`GET /`, `GET /assets/*`, etc.) serves the built React app (`frontend/`'s
`dist/` output). There is no server-side rendering or templating involved.
