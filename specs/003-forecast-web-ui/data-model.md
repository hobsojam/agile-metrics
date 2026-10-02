# Data Model: Forecast Web UI

As with the CLI, this feature introduces no new persistent entities — it maps a JSON
request body onto the models already defined in `001-throughput-forecast`
(`specs/001-throughput-forecast/data-model.md`) and returns the existing `ForecastResult`
as JSON. All validation continues to live in the library.

## Web Form Submission → library models

| Request field | Type | Maps to |
|---|---|---|
| `history` | `list[int]` | `ThroughputHistory.completed_per_period` — a native JSON array, no comma-string parsing needed (unlike the CLI) |
| `period_days` | `int` | `ThroughputHistory.period_duration` (`timedelta(days=...)`) |
| `backlog_size` | `int \| null`, optional | `ForecastRequest.backlog_size` (mutually exclusive with `target_date`) |
| `target_date` | `string \| null` (`YYYY-MM-DD`), optional | `ForecastRequest.target_date` (mutually exclusive with `backlog_size`) |
| `seed` | `int \| null`, optional | `ForecastRequest.seed` |

**Validation**: Parsing the JSON body's types is handled by FastAPI/pydantic automatically
(e.g. a non-integer in `history` is rejected before the route body even runs). Every
business rule — minimum periods, all-zero rejection, exactly-one-of backlog/target-date,
future target date — is enforced by `ThroughputHistory`/`ForecastRequest` themselves,
unchanged from spec 001.

## Forecast Page Result ← ForecastResult

Success response (HTTP 200):

```json
{
  "outcomes": {"50": "2026-11-05", "70": "2026-11-12", "85": "2026-11-12", "95": "2026-11-19"},
  "trials_run": 10000,
  "periods_used": 8
}
```

(Or integer values instead of date strings, when `target_date` was used.) All four
confidence levels and both metadata fields are always present — never a subset — per
Constitution Principle IV.

Error response (4xx):

```json
{"error": "exactly one of backlog_size or target_date is required, not both or neither"}
```

The React component renders either the four outcomes with their metadata, or the error
message — never a raw stack trace or an unhandled network error (spec FR-004/SC-003).
