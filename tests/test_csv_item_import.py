"""Tests for CSV item import (spec 007).

No I/O to mock - CSV parsing and bucketing are pure string/data-in,
model-out logic.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from agile_metrics.csv_item_import import (
    CsvMissingColumnError,
    CsvRowError,
    bucket_items_to_throughput,
    parse_items_csv,
)
from agile_metrics.models import Item

SAMPLE_CSV = """id,type,title,start_date,end_date
1,story,First item,2026-08-01,2026-08-05
2,story,Second item,2026-08-03,2026-08-12
3,bug,Third item,2026-08-10,2026-08-19
4,story,Fourth item,2026-08-15,2026-08-26
5,bug,Fifth item,2026-09-01,2026-09-02
6,story,Sixth item,2026-09-10,2026-09-16
7,story,Still open,2026-09-20,
"""


class TestParseItemsCsv:
    def test_parses_well_formed_csv_in_order(self) -> None:
        items = parse_items_csv(SAMPLE_CSV)
        assert len(items) == 7
        assert [item.id for item in items] == ["1", "2", "3", "4", "5", "6", "7"]
        first = items[0]
        assert first.type == "story"
        assert first.title == "First item"
        assert first.start_date == date(2026, 8, 1)
        assert first.end_date == date(2026, 8, 5)

    def test_blank_end_date_is_accepted_as_not_yet_completed(self) -> None:
        items = parse_items_csv(SAMPLE_CSV)
        still_open = items[-1]
        assert still_open.end_date is None
        assert still_open.start_date == date(2026, 9, 20)

    def test_matches_columns_by_header_name_regardless_of_order(self) -> None:
        reordered = "end_date,id,start_date,title,type\n2026-08-05,1,2026-08-01,First item,story\n"
        items = parse_items_csv(reordered)
        assert items[0].id == "1"
        assert items[0].end_date == date(2026, 8, 5)

    def test_ignores_extra_unrecognized_columns(self) -> None:
        with_extra = (
            "id,type,title,start_date,end_date,priority\n"
            "1,story,First item,2026-08-01,2026-08-05,high\n"
        )
        items = parse_items_csv(with_extra)
        assert items[0].id == "1"

    def test_missing_required_column_raises_before_any_row_is_read(self) -> None:
        missing_end_date = "id,type,title,start_date\n1,story,Bad row,not-a-date\n"
        with pytest.raises(CsvMissingColumnError, match="end_date"):
            parse_items_csv(missing_end_date)

    def test_blank_id_raises_csv_row_error_naming_row_and_field(self) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First item,2026-08-01,2026-08-05\n"
            ",story,Blank id,2026-08-01,2026-08-05\n"
        )
        with pytest.raises(CsvRowError, match="row 2") as exc_info:
            parse_items_csv(csv_text)
        assert "id" in str(exc_info.value)

    def test_malformed_start_date_raises_csv_row_error_naming_row_and_field(self) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First item,2026-08-01,2026-08-05\n"
            "2,story,Bad start,not-a-date,2026-08-05\n"
        )
        with pytest.raises(CsvRowError, match="row 2") as exc_info:
            parse_items_csv(csv_text)
        assert "start_date" in str(exc_info.value)

    def test_malformed_end_date_raises_csv_row_error_naming_row_and_field(self) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First item,2026-08-01,2026-08-05\n"
            "2,story,Bad end,2026-08-01,not-a-date\n"
        )
        with pytest.raises(CsvRowError, match="row 2") as exc_info:
            parse_items_csv(csv_text)
        assert "end_date" in str(exc_info.value)


def _item(item_id: str, end_date: date | None, start_date: date | None = None) -> Item:
    return Item(id=item_id, type="story", title="Item", start_date=start_date, end_date=end_date)


class TestBucketItemsToThroughput:
    """T007: Item.end_date values -> ThroughputHistory (data-model.md's bucket formula,
    research.md §4's period-count derivation)."""

    _TODAY = date(2026, 10, 5)
    _WEEK = timedelta(days=7)

    def test_derives_periods_from_earliest_end_date_and_buckets_in_order(self) -> None:
        # Earliest item is 5 full periods (35 days) before today, so periods
        # derives to exactly 6 (research.md §4): one item per bucket, oldest first.
        items = [
            _item(str(n), end_date=self._TODAY - timedelta(days=days))
            for n, days in enumerate([35, 28, 21, 14, 7, 0])
        ]
        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = self._TODAY
            history = bucket_items_to_throughput(items, self._WEEK)
        assert history.completed_per_period == [1, 1, 1, 1, 1, 1]

    def test_multiple_items_in_the_same_period_are_summed(self) -> None:
        items = [
            _item("1", end_date=self._TODAY - timedelta(days=35)),
            _item("2", end_date=self._TODAY),
            _item("3", end_date=self._TODAY),
            _item("4", end_date=self._TODAY),
        ]
        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = self._TODAY
            history = bucket_items_to_throughput(items, self._WEEK)
        assert history.completed_per_period == [1, 0, 0, 0, 0, 3]

    def test_items_without_end_date_are_excluded_from_bucketing(self) -> None:
        items = [
            _item(str(n), end_date=self._TODAY - timedelta(days=days))
            for n, days in enumerate([35, 28, 21, 14, 7, 0])
        ]
        items.append(_item("open", end_date=None, start_date=self._TODAY))
        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = self._TODAY
            history = bucket_items_to_throughput(items, self._WEEK)
        assert history.completed_per_period == [1, 1, 1, 1, 1, 1]
        assert sum(history.completed_per_period) == 6

    def test_zero_items_with_any_end_date_raises_the_existing_all_zero_error(self) -> None:
        items = [
            _item("1", end_date=None, start_date=date(2026, 9, 1)),
            _item("2", end_date=None, start_date=date(2026, 9, 5)),
        ]
        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = self._TODAY
            with pytest.raises(ValidationError, match="all zero"):
                bucket_items_to_throughput(items, self._WEEK)

    def test_narrow_date_range_raises_the_existing_too_few_periods_error(self) -> None:
        items = [
            _item("1", end_date=date(2026, 10, 1)),
            _item("2", end_date=date(2026, 10, 3)),
        ]
        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = self._TODAY
            with pytest.raises(ValidationError, match="historical periods"):
                bucket_items_to_throughput(items, self._WEEK)
