"""CSV item import: parse a CSV of per-item records into `Item`s and bucket
their completion dates into a `ThroughputHistory` (spec 007), so the web UI
and CLI can forecast from a CSV through the exact same
`forecast_by_items`/`forecast_by_date` path already used for manually-entered
and Linear-derived history (Constitution Principle II).
"""

from __future__ import annotations


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
