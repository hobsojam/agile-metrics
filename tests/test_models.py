"""Validation tests for ThroughputHistory and ForecastRequest (T006, T007)."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from agile_metrics.models import ForecastRequest, ThroughputHistory


def _history(**overrides: object) -> ThroughputHistory:
    defaults: dict[str, object] = {
        "completed_per_period": [3, 5, 4, 6, 2, 5],
        "period_duration": timedelta(days=7),
    }
    defaults.update(overrides)
    return ThroughputHistory(**defaults)  # type: ignore[arg-type]


class TestThroughputHistory:
    def test_accepts_valid_history(self) -> None:
        history = _history()
        assert history.completed_per_period == [3, 5, 4, 6, 2, 5]

    def test_rejects_negative_count(self) -> None:
        with pytest.raises(ValidationError):
            _history(completed_per_period=[3, 5, 4, 6, 2, -1])

    def test_rejects_non_whole_count(self) -> None:
        with pytest.raises(ValidationError):
            _history(completed_per_period=[3, 5, 4, 6, 2, 5.5])

    def test_rejects_fewer_than_minimum_periods(self) -> None:
        with pytest.raises(ValidationError):
            _history(completed_per_period=[3, 5, 4, 6, 2])

    def test_rejects_all_zero_history(self) -> None:
        with pytest.raises(ValidationError):
            _history(completed_per_period=[0, 0, 0, 0, 0, 0])

    def test_rejects_non_positive_period_duration(self) -> None:
        with pytest.raises(ValidationError):
            _history(period_duration=timedelta(0))


class TestForecastRequest:
    def test_rejects_both_backlog_size_and_target_date(self) -> None:
        history = _history()
        target_date = date(2099, 1, 1)
        with pytest.raises(ValidationError):
            ForecastRequest(history=history, backlog_size=10, target_date=target_date)

    def test_rejects_neither_backlog_size_nor_target_date(self) -> None:
        history = _history()
        with pytest.raises(ValidationError):
            ForecastRequest(history=history)

    def test_rejects_non_positive_backlog_size(self) -> None:
        history = _history()
        with pytest.raises(ValidationError):
            ForecastRequest(history=history, backlog_size=0)

    def test_rejects_target_date_not_after_reference_date(self) -> None:
        today = date(2026, 10, 1)
        history = _history()
        with pytest.raises(ValidationError):
            ForecastRequest(history=history, target_date=today, reference_date=today)

    def test_accepts_valid_backlog_request(self) -> None:
        request = ForecastRequest(history=_history(), backlog_size=10)
        assert request.backlog_size == 10
        assert request.target_date is None

    def test_accepts_valid_date_request(self) -> None:
        request = ForecastRequest(
            history=_history(),
            target_date=date(2099, 1, 1),
            reference_date=date(2026, 10, 1),
        )
        assert request.target_date == date(2099, 1, 1)
        assert request.backlog_size is None
