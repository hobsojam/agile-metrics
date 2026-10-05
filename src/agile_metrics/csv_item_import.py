"""CSV item import: parse a CSV of per-item records into `Item`s and bucket
their completion dates into a `ThroughputHistory` (spec 007), so the web UI
and CLI can forecast from a CSV through the exact same
`forecast_by_items`/`forecast_by_date` path already used for manually-entered
and Linear-derived history (Constitution Principle II).
"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

from pydantic import ValidationError

from agile_metrics.models import MIN_HISTORICAL_PERIODS, Item, ThroughputHistory

_REQUIRED_COLUMNS = ["id", "type", "title", "start_date", "end_date"]


class CsvImportError(Exception):
    """Base class for every CSV-import failure this module can raise.

    Each subclass's message is the final, user-facing text (data-model.md) -
    callers render `str(exc)` directly, the same pattern already used for
    `LinearIntegrationError` in `linear_client.py`.
    """


class CsvMissingColumnError(CsvImportError):
    def __init__(self, missing_columns: list[str]) -> None:
        columns = ", ".join(missing_columns)
        super().__init__(f"CSV is missing required column(s): {columns}")


class CsvRowError(CsvImportError):
    def __init__(self, row_number: int, field: str, detail: str) -> None:
        super().__init__(f"row {row_number}: {field} {detail}")


def parse_items_csv(csv_text: str) -> list[Item]:
    """Parse `csv_text` into one `Item` per data row, in file order.

    Row numbers in raised errors count data rows only, starting at 1 for the
    first row after the header (research.md §5).
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = reader.fieldnames or []
    missing_columns = [column for column in _REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        raise CsvMissingColumnError(missing_columns)

    items: list[Item] = []
    for row_number, row in enumerate(reader, start=1):
        try:
            item = Item(
                id=row["id"],
                type=row["type"] or "",
                title=row["title"] or "",
                start_date=row["start_date"] or None,  # type: ignore[arg-type]
                end_date=row["end_date"] or None,  # type: ignore[arg-type]
            )
        except ValidationError as exc:
            error = exc.errors()[0]
            field = str(error["loc"][0])
            if field == "id":
                detail = "is required"
            else:
                detail = f"{row.get(field)!r} is not a valid date"
            raise CsvRowError(row_number, field, detail) from exc
        items.append(item)
    return items


def _derive_periods(items: list[Item], period_duration: timedelta, today: date) -> int:
    """How many periods to bucket into (research.md §4) - anchored to the
    earliest completion date, with no clamping to `MIN_HISTORICAL_PERIODS` so
    a too-narrow date range still raises `ThroughputHistory`'s own
    too-few-periods error rather than being silently padded away."""
    completed_end_dates = [item.end_date for item in items if item.end_date is not None]
    if not completed_end_dates:
        return MIN_HISTORICAL_PERIODS
    earliest = min(completed_end_dates)
    return (today - earliest).days // period_duration.days + 1


def _bucket_items(
    items: list[Item], periods: int, period_duration: timedelta, today: date
) -> list[int]:
    """Bucket `k` (0 = oldest) covers `[today - (periods-k)*period_duration,
    today - (periods-k-1)*period_duration)` (data-model.md) - same formula as
    `linear_client._bucket_completed_at`. An item without an `end_date`, or
    whose `end_date` falls outside this range, is excluded rather than
    clamped into the wrong bucket."""
    period_days = period_duration.days
    counts = [0] * periods
    for item in items:
        if item.end_date is None:
            continue
        periods_ago = (today - item.end_date).days // period_days
        bucket_index = periods - 1 - periods_ago
        if 0 <= bucket_index < periods:
            counts[bucket_index] += 1
    return counts


def bucket_items_to_throughput(items: list[Item], period_duration: timedelta) -> ThroughputHistory:
    """Shape `items`' completion dates into a `ThroughputHistory` - the same
    type manual paste and Linear import already produce (FR-004).
    `ThroughputHistory`'s own validators (not duplicated here) reject an
    all-zero or too-short result exactly as they already do for
    manually-entered history (FR-005/FR-010)."""
    today = date.today()
    periods = _derive_periods(items, period_duration, today)
    counts = _bucket_items(items, periods, period_duration, today)
    return ThroughputHistory(completed_per_period=counts, period_duration=period_duration)
