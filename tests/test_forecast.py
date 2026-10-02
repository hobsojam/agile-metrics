"""Acceptance tests for the public forecasting API (User Stories 1, 2, 3)."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from agile_metrics import forecast_by_date, forecast_by_items
from agile_metrics.models import DEFAULT_TRIALS, ThroughputHistory

_REFERENCE_DATE = date(2026, 10, 1)


def _history() -> ThroughputHistory:
    return ThroughputHistory(
        completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3], period_duration=timedelta(days=7)
    )


class TestForecastByItems:
    """User Story 1 (P1): forecast a completion date for a known backlog size."""

    def test_returns_dates_non_decreasing_with_confidence(self) -> None:
        result = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        outcomes = result.outcomes
        assert set(outcomes) == {50, 70, 85, 95}
        assert outcomes[50] <= outcomes[70] <= outcomes[85] <= outcomes[95]
        assert all(isinstance(v, date) for v in outcomes.values())

    def test_same_seed_is_reproducible(self) -> None:
        first = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        second = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        assert first.outcomes == second.outcomes

    def test_rejects_zero_backlog_size(self) -> None:
        history = _history()
        with pytest.raises(ValidationError):
            forecast_by_items(history, backlog_size=0, reference_date=_REFERENCE_DATE)


class TestForecastByDate:
    """User Story 2 (P2): forecast items completed by a target date."""

    def test_returns_counts_non_increasing_with_confidence(self) -> None:
        result = forecast_by_date(
            _history(),
            target_date=date(2026, 12, 1),
            seed=42,
            reference_date=_REFERENCE_DATE,
        )
        outcomes = result.outcomes
        assert set(outcomes) == {50, 70, 85, 95}
        assert outcomes[50] >= outcomes[70] >= outcomes[85] >= outcomes[95]
        assert all(isinstance(v, int) for v in outcomes.values())

    def test_rejects_target_date_not_in_future(self) -> None:
        history = _history()
        with pytest.raises(ValidationError):
            forecast_by_date(history, target_date=_REFERENCE_DATE, reference_date=_REFERENCE_DATE)


class TestForecastTransparency:
    """User Story 3 (P3): every result states its trial count and data basis."""

    def test_forecast_by_items_reports_trials_and_periods(self) -> None:
        result = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        assert result.trials_run == DEFAULT_TRIALS
        assert result.periods_used == len(_history().completed_per_period)

    def test_forecast_by_date_reports_trials_and_periods(self) -> None:
        result = forecast_by_date(
            _history(),
            target_date=date(2026, 12, 1),
            seed=42,
            reference_date=_REFERENCE_DATE,
        )
        assert result.trials_run == DEFAULT_TRIALS
        assert result.periods_used == len(_history().completed_per_period)
