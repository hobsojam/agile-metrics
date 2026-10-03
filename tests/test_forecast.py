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


class TestForecastDistributionAndProjection:
    """T008: distribution/projection follow research.md §2, §3, §5 (spec 005)."""

    def test_reference_date_matches_passed_value(self) -> None:
        result = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        assert result.reference_date == _REFERENCE_DATE

    def test_reference_date_defaults_to_today_when_not_passed(self) -> None:
        result = forecast_by_items(_history(), backlog_size=20, seed=42)
        assert result.reference_date == date.today()

    def test_distribution_trials_sum_to_trials_run(self) -> None:
        result = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        assert sum(bucket.trials for bucket in result.distribution) == result.trials_run

    def test_backlog_mode_distribution_bounds_are_dates_one_period_apart(self) -> None:
        result = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        for bucket in result.distribution:
            assert isinstance(bucket.lower, date)
            assert isinstance(bucket.upper, date)
        # Narrow spread (small backlog): span <= 60, so one bucket per value and
        # buckets tile contiguously with no gap (research.md §3).
        for earlier, later in zip(result.distribution, result.distribution[1:], strict=False):
            assert (later.lower - earlier.upper).days == 7

    def test_constant_history_gives_exactly_one_bucket(self) -> None:
        constant_history = ThroughputHistory(
            completed_per_period=[5] * 6, period_duration=timedelta(days=7)
        )
        result = forecast_by_items(
            constant_history, backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        assert len(result.distribution) == 1
        assert result.distribution[0].trials == result.trials_run

    def test_large_backlog_distribution_has_equal_width_buckets_capped_at_60(self) -> None:
        result = forecast_by_items(
            _history(), backlog_size=200, seed=42, reference_date=_REFERENCE_DATE
        )
        assert 1 <= len(result.distribution) <= 60
        widths_in_days = {
            (later.lower - earlier.upper).days
            for earlier, later in zip(result.distribution, result.distribution[1:], strict=False)
        }
        assert len(widths_in_days) <= 1  # every gap between buckets is the same width
        if widths_in_days:
            assert next(iter(widths_in_days)) % 7 == 0  # a whole number of periods

    def test_target_date_mode_distribution_bounds_are_ints(self) -> None:
        result = forecast_by_date(
            _history(), target_date=date(2026, 12, 1), seed=42, reference_date=_REFERENCE_DATE
        )
        for bucket in result.distribution:
            assert isinstance(bucket.lower, int)
            assert isinstance(bucket.upper, int)

    def test_target_date_projection_covers_one_to_num_periods(self) -> None:
        target_date = date(2026, 12, 1)
        result = forecast_by_date(
            _history(), target_date=target_date, seed=42, reference_date=_REFERENCE_DATE
        )
        num_periods = max(1, (target_date - _REFERENCE_DATE) // timedelta(days=7))
        assert [point.period for point in result.projection] == list(range(1, num_periods + 1))
        assert result.projection[-1].period_end == _REFERENCE_DATE + num_periods * timedelta(days=7)

    def test_target_date_projection_last_point_matches_outcomes_exactly(self) -> None:
        result = forecast_by_date(
            _history(), target_date=date(2026, 12, 1), seed=42, reference_date=_REFERENCE_DATE
        )
        assert result.projection[-1].cumulative == result.outcomes

    def test_backlog_mode_projection_covers_one_to_p95_plus_one(self) -> None:
        result = forecast_by_items(
            _history(), backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        p95_periods = (result.outcomes[95] - _REFERENCE_DATE) // timedelta(days=7)
        assert [point.period for point in result.projection] == list(range(1, p95_periods + 2))
