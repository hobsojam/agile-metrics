"""Validation tests for ThroughputHistory and ForecastRequest (T006, T007)."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from agile_metrics.models import (
    ForecastRequest,
    ForecastResult,
    OutcomeBucket,
    ProjectionPoint,
    ThroughputHistory,
)


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
        zero_duration = timedelta(0)
        with pytest.raises(ValidationError):
            _history(period_duration=zero_duration)


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


class TestOutcomeBucket:
    def test_accepts_valid_date_bucket(self) -> None:
        bucket = OutcomeBucket(lower=date(2026, 11, 7), upper=date(2026, 11, 7), trials=10)
        assert bucket.trials == 10

    def test_accepts_valid_int_bucket(self) -> None:
        bucket = OutcomeBucket(lower=10, upper=15, trials=3)
        assert bucket.upper == 15

    def test_rejects_negative_trials(self) -> None:
        with pytest.raises(ValidationError):
            OutcomeBucket(lower=1, upper=1, trials=-1)


class TestProjectionPoint:
    def test_accepts_valid_point(self) -> None:
        point = ProjectionPoint(
            period=1, period_end=date(2026, 10, 10), cumulative={50: 4, 70: 4, 85: 3, 95: 2}
        )
        assert point.period == 1

    def test_rejects_non_positive_period(self) -> None:
        cumulative = {50: 4, 70: 4, 85: 3, 95: 2}
        period_end = date(2026, 10, 10)
        with pytest.raises(ValidationError):
            ProjectionPoint(period=0, period_end=period_end, cumulative=cumulative)


class TestForecastResultExtended:
    """Rules quoted from data-model.md's ForecastResult validator (T005)."""

    def _date_result(self, **overrides: object) -> ForecastResult:
        defaults: dict[str, object] = {
            "outcomes": {
                50: date(2026, 11, 7),
                70: date(2026, 11, 14),
                85: date(2026, 11, 14),
                95: date(2026, 11, 21),
            },
            "trials_run": 10,
            "periods_used": 8,
            "reference_date": date(2026, 10, 3),
            "distribution": [
                OutcomeBucket(lower=date(2026, 11, 7), upper=date(2026, 11, 7), trials=10)
            ],
            "projection": [
                ProjectionPoint(
                    period=1,
                    period_end=date(2026, 10, 10),
                    cumulative={50: 1, 70: 1, 85: 1, 95: 1},
                )
            ],
        }
        defaults.update(overrides)
        return ForecastResult(**defaults)  # type: ignore[arg-type]

    def _int_result(self, **overrides: object) -> ForecastResult:
        defaults: dict[str, object] = {
            "outcomes": {50: 24, 70: 22, 85: 21, 95: 19},
            "trials_run": 10,
            "periods_used": 8,
            "reference_date": date(2026, 10, 3),
            "distribution": [OutcomeBucket(lower=24, upper=24, trials=10)],
            "projection": [
                ProjectionPoint(
                    period=1,
                    period_end=date(2026, 10, 10),
                    cumulative={50: 24, 70: 22, 85: 21, 95: 19},
                )
            ],
        }
        defaults.update(overrides)
        return ForecastResult(**defaults)  # type: ignore[arg-type]

    def test_accepts_valid_date_mode_result(self) -> None:
        result = self._date_result()
        assert result.reference_date == date(2026, 10, 3)

    def test_accepts_valid_int_mode_result(self) -> None:
        result = self._int_result()
        assert result.distribution[0].upper == 24

    def test_rejects_distribution_trials_not_summing_to_trials_run(self) -> None:
        bad_distribution = [
            OutcomeBucket(lower=date(2026, 11, 7), upper=date(2026, 11, 7), trials=5)
        ]
        with pytest.raises(ValidationError):
            self._date_result(distribution=bad_distribution)

    def test_rejects_empty_distribution(self) -> None:
        with pytest.raises(ValidationError):
            self._date_result(distribution=[], trials_run=0)

    def test_rejects_more_than_60_buckets(self) -> None:
        many_buckets = [OutcomeBucket(lower=i, upper=i, trials=0) for i in range(61)]
        with pytest.raises(ValidationError):
            self._int_result(distribution=many_buckets, trials_run=0)

    def test_rejects_buckets_out_of_order(self) -> None:
        out_of_order = [
            OutcomeBucket(lower=30, upper=30, trials=5),
            OutcomeBucket(lower=24, upper=24, trials=5),
        ]
        with pytest.raises(ValidationError):
            self._int_result(distribution=out_of_order, trials_run=10)

    def test_rejects_overlapping_buckets(self) -> None:
        overlapping = [
            OutcomeBucket(lower=20, upper=25, trials=5),
            OutcomeBucket(lower=24, upper=30, trials=5),
        ]
        with pytest.raises(ValidationError):
            self._int_result(distribution=overlapping, trials_run=10)

    def test_rejects_bucket_with_lower_greater_than_upper(self) -> None:
        bad_bucket = [OutcomeBucket(lower=30, upper=20, trials=10)]
        with pytest.raises(ValidationError):
            self._int_result(distribution=bad_bucket, trials_run=10)

    def test_rejects_bucket_bounds_type_mismatch_with_outcomes(self) -> None:
        mismatched = [OutcomeBucket(lower=1, upper=1, trials=10)]
        with pytest.raises(ValidationError):
            self._date_result(distribution=mismatched)

    def test_rejects_empty_projection(self) -> None:
        with pytest.raises(ValidationError):
            self._date_result(projection=[])

    def test_rejects_projection_period_gap(self) -> None:
        gapped = [
            ProjectionPoint(
                period=1, period_end=date(2026, 10, 10), cumulative={50: 1, 70: 1, 85: 1, 95: 1}
            ),
            ProjectionPoint(
                period=3, period_end=date(2026, 10, 24), cumulative={50: 2, 70: 2, 85: 2, 95: 2}
            ),
        ]
        with pytest.raises(ValidationError):
            self._date_result(projection=gapped)
