"""Characterization test pinning pre-005 forecast outputs (T001, SC-006).

Records the current `ForecastResult.outcomes`, `trials_run`, and `periods_used`
for fixed seeds and a fixed reference date. This test MUST pass before any
005-forecast-charts change and MUST keep passing after every later task - if it
ever fails, a change altered existing forecast values, which spec 005 forbids.
"""

from datetime import date, timedelta

from agile_metrics.forecast import forecast_by_date, forecast_by_items
from agile_metrics.models import ThroughputHistory

_REFERENCE_DATE = date(2026, 10, 3)


def _history(values: list[int]) -> ThroughputHistory:
    return ThroughputHistory(completed_per_period=values, period_duration=timedelta(days=7))


def test_backlog_mode_example_history_outcomes_unchanged() -> None:
    result = forecast_by_items(
        _history([3, 5, 4, 6, 2, 5, 4, 3]), 20, seed=42, reference_date=_REFERENCE_DATE
    )
    assert result.outcomes == {
        50: date(2026, 11, 7),
        70: date(2026, 11, 14),
        85: date(2026, 11, 14),
        95: date(2026, 11, 21),
    }
    assert result.trials_run == 10000
    assert result.periods_used == 8


def test_target_date_mode_example_history_outcomes_unchanged() -> None:
    result = forecast_by_date(
        _history([3, 5, 4, 6, 2, 5, 4, 3]),
        date(2026, 11, 14),
        seed=42,
        reference_date=_REFERENCE_DATE,
    )
    assert result.outcomes == {50: 24, 70: 22, 85: 21, 95: 19}
    assert result.trials_run == 10000
    assert result.periods_used == 8


def test_history_containing_zeros_outcomes_unchanged() -> None:
    result = forecast_by_items(
        _history([3, 0, 4, 6, 2, 5, 4, 3]), 20, seed=42, reference_date=_REFERENCE_DATE
    )
    assert result.outcomes == {
        50: date(2026, 11, 14),
        70: date(2026, 11, 21),
        85: date(2026, 11, 28),
        95: date(2026, 12, 5),
    }
    assert result.trials_run == 10000
    assert result.periods_used == 8


def test_constant_history_outcomes_unchanged() -> None:
    result = forecast_by_items(_history([5] * 6), 20, seed=42, reference_date=_REFERENCE_DATE)
    assert result.outcomes == {
        50: date(2026, 10, 31),
        70: date(2026, 10, 31),
        85: date(2026, 10, 31),
        95: date(2026, 10, 31),
    }
    assert result.trials_run == 10000
    assert result.periods_used == 6


def test_large_backlog_outcomes_unchanged() -> None:
    result = forecast_by_items(
        _history([3, 5, 4, 6, 2, 5, 4, 3]), 200, seed=42, reference_date=_REFERENCE_DATE
    )
    assert result.outcomes == {
        50: date(2027, 9, 18),
        70: date(2027, 10, 2),
        85: date(2027, 10, 9),
        95: date(2027, 10, 16),
    }
    assert result.trials_run == 10000
    assert result.periods_used == 8
