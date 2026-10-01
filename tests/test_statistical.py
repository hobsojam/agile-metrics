"""Statistical convergence test (T009) — Constitution Principle III:

simulation correctness must be validated against known statistical properties,
not just example assertions. For a small, fixed historical series, the exact
distribution of "sum of N iid draws with replacement" is computable by
convolving the empirical pmf with itself. The Monte Carlo core's percentiles,
run with enough trials, must converge close to that exact distribution.
"""

from datetime import timedelta

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from numpy.typing import NDArray

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
