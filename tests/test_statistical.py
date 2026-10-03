"""Statistical convergence test (T009) — Constitution Principle III:

simulation correctness must be validated against known statistical properties,
not just example assertions. For a small, fixed historical series, the exact
distribution of "sum of N iid draws with replacement" is computable by
convolving the empirical pmf with itself. The Monte Carlo core's percentiles,
run with enough trials, must converge close to that exact distribution.
"""

from datetime import date, timedelta

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from numpy.typing import NDArray

from agile_metrics.forecast import forecast_by_date, forecast_by_items
from agile_metrics.models import ThroughputHistory
from agile_metrics.simulation import items_completed_after

_PERCENTILES = (50, 70, 85, 95)
_CONVERGENCE_TRIALS = 50_000
_TOLERANCE = 2.0


def _exact_value_at_percentile(cdf: NDArray[np.float64], p: float) -> float:
    idx = int(np.searchsorted(cdf, p / 100))
    return float(min(idx, len(cdf) - 1))


_BAND = 15  # percentage points either side — absorbs sharp CDF jumps near the target


@given(
    values=st.lists(st.integers(min_value=0, max_value=8), min_size=6, max_size=10).filter(
        lambda v: any(x > 0 for x in v)
    ),
    num_periods=st.integers(min_value=1, max_value=4),
)
@settings(max_examples=25, deadline=None)
def test_simulated_percentiles_converge_to_exact_distribution(
    values: list[int], num_periods: int
) -> None:
    history = ThroughputHistory(completed_per_period=values, period_duration=timedelta(days=7))
    trials = items_completed_after(
        history, num_periods=num_periods, trials=_CONVERGENCE_TRIALS, seed=7
    )
    counts = np.bincount(values)
    pmf = counts / counts.sum()
    total_pmf = pmf.copy()
    for _ in range(num_periods - 1):
        total_pmf = np.convolve(total_pmf, pmf)
    cdf = np.cumsum(total_pmf)

    for level in _PERCENTILES:
        sim_value = float(np.percentile(trials, level))
        lower = _exact_value_at_percentile(cdf, max(level - _BAND, 1))
        upper = _exact_value_at_percentile(cdf, min(level + _BAND, 99))
        assert lower - _TOLERANCE <= sim_value <= upper + _TOLERANCE, (
            f"level={level}, simulated={sim_value}, band=[{lower}, {upper}], "
            f"values={values}, num_periods={num_periods}"
        )


_REFERENCE_DATE = date(2026, 10, 1)
_WEEK = timedelta(days=7)
_LEVELS_HIGH_TO_LOW = (95, 85, 70, 50)

_history_strategy = st.lists(
    st.integers(min_value=0, max_value=10), min_size=6, max_size=10
).filter(lambda v: any(x > 0 for x in v))


def _history(values: list[int]) -> ThroughputHistory:
    return ThroughputHistory(completed_per_period=values, period_duration=_WEEK)


class TestDistributionAndProjectionInvariants:
    """T010 (spec 005): properties that must hold for every forecast, not just
    the worked examples in test_forecast.py (Constitution Principle III)."""

    @given(values=_history_strategy, backlog_size=st.integers(min_value=1, max_value=50))
    @settings(max_examples=20, deadline=None)
    def test_backlog_mode_invariants(self, values: list[int], backlog_size: int) -> None:
        result = forecast_by_items(
            _history(values), backlog_size, seed=11, reference_date=_REFERENCE_DATE
        )

        # Bucket trials add up to trials_run (SC-002).
        assert sum(bucket.trials for bucket in result.distribution) == result.trials_run

        # Each outcomes[L] falls inside exactly one bucket (SC-001).
        for level, outcome in result.outcomes.items():
            matches = [b for b in result.distribution if b.lower <= outcome <= b.upper]
            assert len(matches) == 1, f"level={level} outcome={outcome} matched {len(matches)}"

        # The fraction of trials done on or before outcomes[L] is >= L/100 (research.md §4).
        trials_run = result.trials_run
        for level, outcome in result.outcomes.items():
            trials_on_or_before = sum(
                bucket.trials for bucket in result.distribution if bucket.upper <= outcome
            )
            assert trials_on_or_before / trials_run >= level / 100 - 1e-9

        # Projection: levels ordered, each level non-decreasing over periods, and
        # the first period reaching the backlog is within one period of the
        # period count behind outcomes[L] (SC-003).
        period_count_at_level = {
            level: (outcome - _REFERENCE_DATE) // _WEEK
            for level, outcome in result.outcomes.items()
        }
        previous_cumulative: dict[int, int] | None = None
        first_reach_period: dict[int, int | None] = dict.fromkeys(_LEVELS_HIGH_TO_LOW)
        for point in result.projection:
            for high, low in zip(_LEVELS_HIGH_TO_LOW, _LEVELS_HIGH_TO_LOW[1:], strict=False):
                assert point.cumulative[high] <= point.cumulative[low]
            if previous_cumulative is not None:
                for level in _LEVELS_HIGH_TO_LOW:
                    assert point.cumulative[level] >= previous_cumulative[level]
            for level in _LEVELS_HIGH_TO_LOW:
                if first_reach_period[level] is None and point.cumulative[level] >= backlog_size:
                    first_reach_period[level] = point.period
            previous_cumulative = point.cumulative

        for level in _LEVELS_HIGH_TO_LOW:
            reach = first_reach_period[level]
            if reach is not None:
                assert abs(reach - period_count_at_level[level]) <= 1

    @given(values=_history_strategy, num_periods=st.integers(min_value=1, max_value=6))
    @settings(max_examples=20, deadline=None)
    def test_target_date_mode_invariants(self, values: list[int], num_periods: int) -> None:
        target_date = _REFERENCE_DATE + num_periods * _WEEK
        result = forecast_by_date(
            _history(values), target_date, seed=11, reference_date=_REFERENCE_DATE
        )

        assert sum(bucket.trials for bucket in result.distribution) == result.trials_run

        for level, outcome in result.outcomes.items():
            matches = [b for b in result.distribution if b.lower <= outcome <= b.upper]
            assert len(matches) == 1, f"level={level} outcome={outcome} matched {len(matches)}"

        # The fraction of trials completing at least outcomes[L] items is >= L/100.
        trials_run = result.trials_run
        for level, outcome in result.outcomes.items():
            trials_at_least = sum(
                bucket.trials for bucket in result.distribution if bucket.lower >= outcome
            )
            assert trials_at_least / trials_run >= level / 100 - 1e-9

        previous_cumulative = None
        for point in result.projection:
            for high, low in zip(_LEVELS_HIGH_TO_LOW, _LEVELS_HIGH_TO_LOW[1:], strict=False):
                assert point.cumulative[high] <= point.cumulative[low]
            if previous_cumulative is not None:
                for level in _LEVELS_HIGH_TO_LOW:
                    assert point.cumulative[level] >= previous_cumulative[level]
            previous_cumulative = point.cumulative

        # Target-date mode: the last point matches outcomes exactly.
        assert result.projection[-1].cumulative == result.outcomes
