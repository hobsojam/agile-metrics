# Data Model: Forecast CLI

This feature introduces no new persistent entities — it maps CLI arguments onto the models
already defined in `001-throughput-forecast` (`specs/001-throughput-forecast/data-model.md`)
and renders the existing `ForecastResult` as text. There is nothing new to validate at the
model layer; all validation continues to live in the library.

## CLI Invocation → library models

| CLI flag | Type | Maps to |
|---|---|---|
| `--history` | comma-separated integers, e.g. `"3,5,4,6,2,5"` | `ThroughputHistory.completed_per_period` (parsed to `list[int]`) |
| `--period-days` | integer | `ThroughputHistory.period_duration` (`timedelta(days=...)`) |
| `--backlog-size` | integer, optional | `ForecastRequest.backlog_size` (mutually exclusive with `--target-date`) |
| `--target-date` | `YYYY-MM-DD`, optional | `ForecastRequest.target_date` (mutually exclusive with `--backlog-size`) |
| `--seed` | integer, optional | `ForecastRequest.seed` |

**Validation**: Parsing `--history` into integers and `--period-days`/`--backlog-size` into
positive integers is the CLI's own job (malformed input raises a `ValueError`, caught and
formatted per research.md's Error handling decision). Every other rule — minimum periods,
all-zero rejection, exactly-one-of backlog/target-date, future target date — is enforced by
`ThroughputHistory`/`ForecastRequest` themselves, unchanged from spec 001.

## CLI Output ← ForecastResult

The CLI renders `ForecastResult` (spec 001's data-model.md) as plain text:

```text
Forecast (10000 trials, 8 historical periods):
  50% confidence: 2026-11-05
  70% confidence: 2026-11-12
  85% confidence: 2026-11-12
  95% confidence: 2026-11-19
```

(Or item counts instead of dates, when `--target-date` was used.) All four confidence
levels and both metadata fields (`trials_run`, `periods_used`) are always printed — never a
subset — per Constitution Principle IV.
