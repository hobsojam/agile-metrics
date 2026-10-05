# Contract Delta: Forecast Response

This document describes **only what changes** relative to
[specs/006-linear-integration/contracts/forecast-api.md](../../006-linear-integration/contracts/forecast-api.md)
and [specs/007-csv-item-import/contracts/forecast-api.md](../../007-csv-item-import/contracts/forecast-api.md).
No request shape changes at all — this feature only adds one optional field to the
response every forecast-producing endpoint (`POST /api/forecast`, `POST /api/forecast/csv`)
and the CLI already return.

## Response: one new optional field

```json
{
  "outcomes": { "50": "2035-03-12", "70": "2039-01-10", "85": "2043-06-08", "95": "2049-12-13" },
  "trials_run": 10000,
  "periods_used": 6,
  "reference_date": "2026-10-05",
  "distribution": [ "..." ],
  "projection": [ "..." ],
  "precision_warning": {
    "message": "This forecast's range is very wide: the 95% outcome is roughly 1.6x further from the median than the median itself is from today. Treat these numbers as a rough risk range, not a committed plan."
  }
}
```

`precision_warning` is `null` (the field's default) whenever the computed ratio
(research.md §1) is at or below the confirmed threshold (1.0x, research.md §2) — the
overwhelming majority of forecasts, including every one of this project's existing test
fixtures, which were built from small, consistent seeded histories.

## CLI

`_render_result` appends one additional line after the four confidence levels when
`precision_warning` is present:

```text
Forecast (10000 trials, 6 historical periods):
  50% confidence: 2035-03-12
  70% confidence: 2039-01-10
  85% confidence: 2043-06-08
  95% confidence: 2049-12-13
⚠ This forecast's range is very wide: the 95% outcome is roughly 1.6x further from the
  median than the median itself is from today. Treat these numbers as a rough risk range,
  not a committed plan.
```

No new CLI flag — nothing about this feature is user-configurable (spec Assumptions).

## Web UI

A visible warning banner (amber/warning styling, distinct from the existing red/error
banner) renders below the four confidence-level outcomes whenever
`result.precision_warning` is present, showing its `message`. No change to how charts
render — the warning is informational text, not a new chart.

## Library (`agile_metrics` public API)

New: `agile_metrics.models.PrecisionWarning`, and
`ForecastResult.precision_warning: PrecisionWarning | None`. `forecast_by_items` and
`forecast_by_date` keep their existing signatures — this is a new field on their return
value, not a new parameter.
