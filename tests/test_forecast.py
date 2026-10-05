"""Acceptance tests for the public forecasting API (User Stories 1, 2, 3)."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from agile_metrics import forecast_by_date, forecast_by_items
from agile_metrics.csv_item_import import bucket_items_to_throughput, parse_items_csv
from agile_metrics.forecast import _compute_precision_warning
from agile_metrics.models import DEFAULT_TRIALS, PrecisionWarning, ThroughputHistory

_REFERENCE_DATE = date(2026, 10, 1)


def _csv_text_for_counts(counts: list[int], today: date, period_days: int) -> str:
    """Build CSV text whose end dates bucket to exactly `counts`, oldest first,
    anchored to `today` (mirrors `_bucket_items`'s own formula - see
    test_web.py's identical helper for the same reasoning)."""
    periods = len(counts)
    rows = ["id,type,title,start_date,end_date"]
    next_id = 1
    for bucket_index, count in enumerate(counts):
        periods_ago = periods - 1 - bucket_index
        end_date = today - timedelta(days=periods_ago * period_days)
        for _ in range(count):
            rows.append(f"{next_id},story,Item {next_id},,{end_date.isoformat()}")
            next_id += 1
    return "\n".join(rows) + "\n"


def _history() -> ThroughputHistory:
    return ThroughputHistory(
        completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3], period_duration=timedelta(days=7)
    )


class TestForecastPrecisionWarningWiring:
    """009 US1 (P1): both public functions set/clear precision_warning end-to-end."""

    def test_forecast_by_items_sets_warning_for_sparse_history_and_large_backlog(self) -> None:
        # Mostly zero with one rare burst: highly bursty relative to a backlog
        # small enough that an early lucky burst can nearly finish it outright.
        bursty_history = ThroughputHistory(
            completed_per_period=[0, 0, 0, 0, 0, 20], period_duration=timedelta(days=7)
        )
        result = forecast_by_items(
            bursty_history, backlog_size=5, seed=42, reference_date=_REFERENCE_DATE
        )
        assert isinstance(result.precision_warning, PrecisionWarning)

    def test_forecast_by_items_clears_warning_for_consistent_history_and_small_backlog(
        self,
    ) -> None:
        consistent_history = ThroughputHistory(
            completed_per_period=[8, 9, 7, 8, 10, 9, 8, 7], period_duration=timedelta(days=7)
        )
        result = forecast_by_items(
            consistent_history, backlog_size=10, seed=42, reference_date=_REFERENCE_DATE
        )
        assert result.precision_warning is None

    def test_forecast_by_date_sets_warning_for_sparse_inconsistent_history(self) -> None:
        sparse_history = ThroughputHistory(
            completed_per_period=[0, 0, 1, 0, 0, 1], period_duration=timedelta(days=7)
        )
        result = forecast_by_date(
            sparse_history,
            target_date=_REFERENCE_DATE + timedelta(weeks=8),
            seed=42,
            reference_date=_REFERENCE_DATE,
        )
        assert isinstance(result.precision_warning, PrecisionWarning)

    def test_forecast_by_date_clears_warning_for_consistent_ample_history(self) -> None:
        consistent_history = ThroughputHistory(
            completed_per_period=[8, 9, 7, 8, 10, 9, 8, 7], period_duration=timedelta(days=7)
        )
        result = forecast_by_date(
            consistent_history,
            target_date=_REFERENCE_DATE + timedelta(weeks=20),
            seed=42,
            reference_date=_REFERENCE_DATE,
        )
        assert result.precision_warning is None

    def test_warning_is_identical_regardless_of_how_throughput_history_was_built(
        self,
    ) -> None:
        # Same per-period counts, built two ways: directly, and via
        # csv_item_import's CSV-parsing path (009 US3 / FR-005). The Linear
        # import path (spec 006) already produces the identical
        # ThroughputHistory shape - no separate check needed, since
        # _compute_precision_warning only ever sees outcomes/reference_date,
        # downstream of ThroughputHistory construction either way.
        counts = [1, 1, 1, 1, 1, 20]
        period_duration = timedelta(days=7)
        direct_history = ThroughputHistory(
            completed_per_period=counts, period_duration=period_duration
        )

        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = _REFERENCE_DATE
            csv_text = _csv_text_for_counts(counts, _REFERENCE_DATE, period_days=7)
            items = parse_items_csv(csv_text)
            csv_history = bucket_items_to_throughput(items, period_duration)

        assert csv_history.completed_per_period == direct_history.completed_per_period

        direct_result = forecast_by_items(
            direct_history, backlog_size=10, seed=42, reference_date=_REFERENCE_DATE
        )
        csv_result = forecast_by_items(
            csv_history, backlog_size=10, seed=42, reference_date=_REFERENCE_DATE
        )
        assert direct_result.precision_warning is not None
        assert direct_result.precision_warning == csv_result.precision_warning


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


class TestSparseHistoryHorizonAdequacy:
    """Fix for issue #178: a sparse history must never silently clamp the
    outcome dates to an inadequate simulation horizon."""

    def test_sparse_history_produces_correctly_late_outcomes_not_clamped(self) -> None:
        # 1 item in 50 periods (mean 0.02): with the old fixed horizon of
        # max(20*50, 500)=1000, 46% of trials never reached backlog_size=20,
        # clamping those percentiles to an artificially early date.
        sparse_history = ThroughputHistory(
            completed_per_period=[0] * 49 + [1], period_duration=timedelta(days=7)
        )
        result = forecast_by_items(
            sparse_history, backlog_size=20, seed=42, reference_date=_REFERENCE_DATE
        )
        # At this throughput, finishing 20 items genuinely takes decades
        # (the real 50th-percentile date is ~979 weeks out). The old bug
        # would have clamped every percentile to the horizon (1000 periods),
        # so just confirm it's unambiguously past what a thin, broken
        # simulation could produce.
        assert result.outcomes[50] > _REFERENCE_DATE + timedelta(weeks=500)
        outcomes = result.outcomes
        assert outcomes[50] <= outcomes[70] <= outcomes[85] <= outcomes[95]
        assert sum(bucket.trials for bucket in result.distribution) == result.trials_run


class TestComputePrecisionWarning:
    """009 Foundational: _compute_precision_warning(outcomes, reference_date) in isolation
    (research.md §1, corrected 2026-10-05 - count-mode divides by p95, not p50)."""

    def test_date_mode_wide_spread_returns_a_warning(self) -> None:
        outcomes: dict[int, date | int] = {
            50: _REFERENCE_DATE + timedelta(days=900),
            70: _REFERENCE_DATE + timedelta(days=1200),
            85: _REFERENCE_DATE + timedelta(days=1800),
            95: _REFERENCE_DATE + timedelta(days=2400),
        }
        warning = _compute_precision_warning(outcomes, _REFERENCE_DATE)
        assert isinstance(warning, PrecisionWarning)

    def test_date_mode_tight_spread_returns_none(self) -> None:
        outcomes: dict[int, date | int] = {
            50: _REFERENCE_DATE + timedelta(weeks=10),
            70: _REFERENCE_DATE + timedelta(weeks=11),
            85: _REFERENCE_DATE + timedelta(weeks=12),
            95: _REFERENCE_DATE + timedelta(weeks=13),
        }
        assert _compute_precision_warning(outcomes, _REFERENCE_DATE) is None

    def test_count_mode_wide_spread_returns_a_warning(self) -> None:
        outcomes: dict[int, date | int] = {50: 10, 70: 8, 85: 5, 95: 2}
        warning = _compute_precision_warning(outcomes, _REFERENCE_DATE)
        assert isinstance(warning, PrecisionWarning)

    def test_count_mode_tight_spread_returns_none(self) -> None:
        outcomes: dict[int, date | int] = {50: 10, 70: 10, 85: 9, 95: 9}
        assert _compute_precision_warning(outcomes, _REFERENCE_DATE) is None

    def test_date_mode_threshold_boundary_at_exactly_one_does_not_warn(self) -> None:
        # center = 100 days, spread = 100 days -> ratio == 1.0 exactly, and the
        # confirmed condition is strictly `ratio > 1.0` (research.md §2).
        outcomes: dict[int, date | int] = {
            50: _REFERENCE_DATE + timedelta(days=100),
            70: _REFERENCE_DATE + timedelta(days=150),
            85: _REFERENCE_DATE + timedelta(days=180),
            95: _REFERENCE_DATE + timedelta(days=200),
        }
        assert _compute_precision_warning(outcomes, _REFERENCE_DATE) is None

    def test_date_mode_zero_center_floor_does_not_crash_and_still_warns(self) -> None:
        # p50 == reference_date -> center == 0, floored to max(center, 1) == 1.
        outcomes: dict[int, date | int] = {
            50: _REFERENCE_DATE,
            70: _REFERENCE_DATE + timedelta(days=100),
            85: _REFERENCE_DATE + timedelta(days=300),
            95: _REFERENCE_DATE + timedelta(days=500),
        }
        warning = _compute_precision_warning(outcomes, _REFERENCE_DATE)
        assert isinstance(warning, PrecisionWarning)

    def test_count_mode_zero_p95_floor_does_not_crash_and_still_warns(self) -> None:
        # p95 == 0 -> the corrected denominator max(p95, 1) == 1, not a ZeroDivisionError.
        outcomes: dict[int, date | int] = {50: 5, 70: 3, 85: 1, 95: 0}
        warning = _compute_precision_warning(outcomes, _REFERENCE_DATE)
        assert isinstance(warning, PrecisionWarning)

    def test_message_names_the_actual_computed_ratio_and_differs_between_scenarios(
        self,
    ) -> None:
        moderately_wide: dict[int, date | int] = {
            50: _REFERENCE_DATE + timedelta(days=900),
            70: _REFERENCE_DATE + timedelta(days=1200),
            85: _REFERENCE_DATE + timedelta(days=1800),
            95: _REFERENCE_DATE + timedelta(days=2400),
        }
        very_wide: dict[int, date | int] = {
            50: _REFERENCE_DATE + timedelta(days=100),
            70: _REFERENCE_DATE + timedelta(days=500),
            85: _REFERENCE_DATE + timedelta(days=900),
            95: _REFERENCE_DATE + timedelta(days=2000),
        }
        moderate_warning = _compute_precision_warning(moderately_wide, _REFERENCE_DATE)
        wide_warning = _compute_precision_warning(very_wide, _REFERENCE_DATE)
        assert isinstance(moderate_warning, PrecisionWarning)
        assert isinstance(wide_warning, PrecisionWarning)
        assert moderate_warning.message
        assert wide_warning.message
        # Not a static, unexplained label - each names its own distinct ratio.
        assert moderate_warning.message != wide_warning.message
        assert "1.7" in moderate_warning.message  # 1500/900 ≈ 1.667
        assert "19.0" in wide_warning.message  # 1900/100 = 19.0
