# Data Model: CSV Item Import

## New model: `Item` (in `agile_metrics.models`)

A new public `pydantic` model, alongside `ThroughputHistory`/`ForecastResult` (plan.md
"Decisions confirmed" §3) — not exposed via any API response in this feature, but available
for a later item-level flow-metrics feature to import directly.

| Field | Type | Validation |
|---|---|---|
| `id` | `str` | Non-blank (research.md §5) — the one column this feature treats as required per row |
| `type` | `str` | Free text, no constraint; blank stored as `""` |
| `title` | `str` | Free text, no constraint; blank stored as `""` |
| `start_date` | `date \| None` | `None` if blank; otherwise a valid ISO 8601 date |
| `end_date` | `date \| None` | `None` if blank (not yet completed, FR-010); otherwise a valid ISO 8601 date |

`ThroughputHistory`, `ForecastRequest`, and `ForecastResult` are all **unchanged** — this
feature's only job is producing a `ThroughputHistory` from a third source, same as 006 did
for Linear.

## New functions (not models): `csv_item_import` module

### `parse_items_csv(csv_text: str) -> list[Item]`

Reads `csv_text` as a comma-delimited file with a header row, matching columns by header
name (research.md §1, §5). Returns one `Item` per data row, in file order.

**Raises** (research.md §5 — one shape per distinguishable failure, FR-007/FR-008):

| Exception | Condition |
|---|---|
| `CsvMissingColumnError` | One or more of `id, type, title, start_date, end_date` is absent from the header row — raised before any row is read |
| `CsvRowError` | A specific data row has a blank `id`, or a non-blank `start_date`/`end_date` that fails to parse as `YYYY-MM-DD` — names the 1-indexed data row number and the offending column |

Both inherit from a common `CsvImportError` so callers can catch broadly or specifically,
mirroring `LinearIntegrationError`'s hierarchy (006 data-model.md).

### `bucket_items_to_throughput(items: list[Item], period_duration: timedelta) -> ThroughputHistory`

Derives the period count from the data itself (research.md §4) and buckets every item whose
`end_date` is not `None` into it. Bucket `k` (0 = oldest) holds the count of items whose
`end_date` falls within `[today - (periods - k) * period_duration, today - (periods - k -
1) * period_duration)`, anchored to today exactly as `reference_date` already is for
manually-entered and Linear-derived history.

**Not** a new exception: an all-zero or too-short bucketed history raises the *existing*
`pydantic.ValidationError` from `ThroughputHistory`'s own validators (FR-005, FR-010) — this
function does not catch or wrap that; it propagates exactly like a manually-entered all-zero
history already does.

## Request/response changes (web layer)

See [contracts/forecast-api.md](./contracts/forecast-api.md) for the full delta.

- **New endpoint**: `POST /api/forecast/csv`, `multipart/form-data`. The existing
  `POST /api/forecast` (JSON) is completely unchanged — no new fields, no interaction with
  `history`/`linear_*` (plan.md "Decisions confirmed" §1).
- Request fields: `csv_file` (`UploadFile | None`), `csv_text` (`str | None`) — exactly one
  required; `period_days`, `backlog_size`, `target_date`, `seed` — same fields and same
  "exactly one of `backlog_size`/`target_date`" rule the existing endpoint already has.
- Response: the same `ForecastResponseBody` (200) / `ErrorResponseBody` (400) shape as the
  existing endpoint — `history` in the response is the derived `completed_per_period` list,
  exactly as Linear mode already echoes it back for the burn-up/run charts (spec 006).

## CLI changes

- New option: `--csv-file <path>` — reads a local file, third arm of the existing "exactly
  one of `--history` / (`--linear-api-key` + `--linear-team`)" check (now three-way: add
  `--csv-file` as a mutually exclusive alternative to both).
- Same error-rendering path as every existing CLI error
  (`typer.echo(f"Error: {exc}", err=True)`, exit code 1) — `CsvImportError` joins the
  existing `except` clause alongside `ValidationError`/`ValueError`/`LinearIntegrationError`.
