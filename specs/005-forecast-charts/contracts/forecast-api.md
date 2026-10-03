# Contract Delta: Forecast Web API (`POST /api/forecast`)

This document describes **only what changes** relative to
[specs/003-forecast-web-ui/contracts/forecast-api.md](../../003-forecast-web-ui/contracts/forecast-api.md).
Everything not mentioned here (request body, the 400 error shape, static assets) is
unchanged.

As in spec 003, the source of truth is the backend's OpenAPI schema, which is generated
from the pydantic models in [data-model.md](../data-model.md). After the model change,
`npm run generate-types` regenerates `frontend/openapi.json` and `frontend/src/api-types.ts`.
Both are committed, and the existing CI freshness check gates them.

## Request

Unchanged.

## 200 OK: new fields

The three existing fields keep their names, types and values for a given input and seed
(FR-003, SC-006). Three fields are added and are always present.

**Backlog-size mode** (`backlog_size: 20`, `seed: 42`, history `3,5,4,6,2,5,4,3`, weekly,
run on 2026-10-03). The existing fields below are real output. The distribution counts and
projection values are illustrative and the arrays are shortened:

```json
{
  "outcomes": {"50": "2026-11-07", "70": "2026-11-14", "85": "2026-11-14", "95": "2026-11-21"},
  "trials_run": 10000,
  "periods_used": 8,
  "reference_date": "2026-10-03",
  "distribution": [
    {"lower": "2026-10-31", "upper": "2026-10-31", "trials": 1210},
    {"lower": "2026-11-07", "upper": "2026-11-07", "trials": 4630},
    {"lower": "2026-11-14", "upper": "2026-11-14", "trials": 3310},
    {"lower": "2026-11-21", "upper": "2026-11-21", "trials": 780},
    {"lower": "2026-11-28", "upper": "2026-11-28", "trials": 70}
  ],
  "projection": [
    {"period": 1, "period_end": "2026-10-10", "cumulative": {"50": 4, "70": 4, "85": 3, "95": 2}},
    {"period": 2, "period_end": "2026-10-17", "cumulative": {"50": 8, "70": 8, "85": 7, "95": 5}},
    "… one entry per period up to the rounded 95% period + 1 …"
  ]
}
```

**Target-date mode** (`target_date: "2026-11-14"`, same history and seed). The outcomes
are real output. Each level's final `projection` value equals its outcome exactly:

```json
{
  "outcomes": {"50": 24, "70": 22, "85": 21, "95": 19},
  "trials_run": 10000,
  "periods_used": 8,
  "reference_date": "2026-10-03",
  "distribution": [
    {"lower": 14, "upper": 14, "trials": 12},
    "… one bucket per item count (or per range, when there are more than 60 values) …"
  ],
  "projection": [
    "… periods 1–5 …",
    {"period": 6, "period_end": "2026-11-14", "cumulative": {"50": 24, "70": 22, "85": 21, "95": 19}}
  ]
}
```

### Field rules

| Field | Rule |
|---|---|
| `reference_date` | `YYYY-MM-DD`. The server's "today" for web requests (unchanged behaviour, now made visible) |
| `distribution[].lower` / `upper` | Date strings in backlog mode, integers in target-date mode, matching the type of `outcomes` values. Inclusive bounds, ascending order, no overlaps |
| `distribution[].trials` | Non-negative. Adds up to `trials_run` |
| `distribution` length | 1–60 |
| `projection[].period` | 1, 2, 3, … with no gaps |
| `projection[].cumulative` | Keys `"50"`, `"70"`, `"85"`, `"95"`. Integer item counts measured from the reference date, not including history |

## CLI

The CLI's output is unchanged (FR-006). It prints only `outcomes`, `trials_run` and
`periods_used`, which `tests/test_cli.py` already pins.

## Library (`agile_metrics` public API)

`forecast_by_items` and `forecast_by_date` keep their signatures. Their returned
`ForecastResult` gains the three fields above. `OutcomeBucket` and `ProjectionPoint` are
exported from `agile_metrics.models` alongside the existing models.
