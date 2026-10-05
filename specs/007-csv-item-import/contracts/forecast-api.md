# Contract Delta: Forecast Web API

This document describes **only what changes** relative to
[specs/006-linear-integration/contracts/forecast-api.md](../../006-linear-integration/contracts/forecast-api.md).
Everything not mentioned here (the existing `POST /api/forecast` request/response shape,
static assets) is unchanged.

## New endpoint: `POST /api/forecast/csv`

`Content-Type: multipart/form-data`. Distinct from, and with no effect on, the existing
`POST /api/forecast` (JSON) endpoint — `history` and `linear_*` do not exist on this
endpoint, and `csv_file`/`csv_text` do not exist on the JSON one.

**Form fields**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `csv_file` | file | Exactly one of `csv_file`/`csv_text` | The CSV, as an uploaded file |
| `csv_text` | text | Exactly one of `csv_file`/`csv_text` | The CSV, as pasted text |
| `period_days` | int | Yes | Same meaning as the JSON endpoint |
| `backlog_size` | int | Exactly one of `backlog_size`/`target_date` | Same meaning as the JSON endpoint |
| `target_date` | date string | Exactly one of `backlog_size`/`target_date` | Same meaning as the JSON endpoint |
| `seed` | int | No | Same meaning as the JSON endpoint |

**Invalid combinations** (400, same `{"error": "..."}` shape as every existing validation
failure):

| Combination | Error |
|---|---|
| Neither `csv_file` nor `csv_text` present | `"exactly one of csv_file or csv_text is required"` |
| Both `csv_file` and `csv_text` present | Same message |
| Neither `backlog_size` nor `target_date` present (or both) | Same "exactly one of" message the JSON endpoint already uses |

**Response**: identical shape to `POST /api/forecast` — `ForecastResponseBody` (200) with
`history` echoing the derived `completed_per_period`, or `ErrorResponseBody` (400).

**New error cases** (400, each message naming the specific problem — FR-007):

| Condition | Example `error` message |
|---|---|
| CSV missing a required column | `"CSV is missing required column(s): end_date"` |
| A row has a blank `id` | `"row 3: id is required"` |
| A row has an unparsable `start_date` or `end_date` | `"row 5: end_date 'not-a-date' is not a valid date"` |
| Zero items have any completion date | The *existing* all-zero-history message, unchanged |
| Completion dates span fewer than the minimum required periods | The *existing* too-few-periods message, unchanged |

## CLI

New option: `--csv-file <path>`. Third arm of the existing "exactly one of" check alongside
`--history` and the `--linear-api-key`/`--linear-team` pair. Same error messages and
`Error: <message>` / exit-1 rendering as every other CLI error.

## Library (`agile_metrics` public API)

New: `agile_metrics.models.Item`, `agile_metrics.csv_item_import.parse_items_csv()` and
`bucket_items_to_throughput()`, and the `CsvImportError` subclasses (data-model.md).
`forecast_by_items` and `forecast_by_date` keep their existing signatures and behavior
unchanged.
