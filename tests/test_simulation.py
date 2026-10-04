"""Reproducibility test for the Monte Carlo simulation core (T008)."""

from datetime import timedelta

import numpy as np
import pytest

from agile_metrics.models import ThroughputHistory
from agile_metrics.simulation import (
    cumulative_paths,
    cumulative_paths_until_reached,
    items_completed_after,
    periods_to_complete,
)


def _history() -> ThroughputHistory:
    return ThroughputHistory(
        completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3], period_duration=timedelta(days=7)
    )


class TestReproducibility:
    def test_periods_to_complete_same_seed_is_identical(self) -> None:
        history = _history()
        first = periods_to_complete(history, backlog_size=20, trials=1000, seed=42)
        second = periods_to_complete(history, backlog_size=20, trials=1000, seed=42)
        assert first.tolist() == second.tolist()

    def test_periods_to_complete_different_seed_can_differ(self) -> None:
        history = _history()
        first = periods_to_complete(history, backlog_size=20, trials=1000, seed=1)
        second = periods_to_complete(history, backlog_size=20, trials=1000, seed=2)
        assert first.tolist() != second.tolist()

    def test_items_completed_after_same_seed_is_identical(self) -> None:
        history = _history()
        first = items_completed_after(history, num_periods=4, trials=1000, seed=42)
        second = items_completed_after(history, num_periods=4, trials=1000, seed=42)
        assert first.tolist() == second.tolist()

    def test_items_completed_after_different_seed_can_differ(self) -> None:
        history = _history()
        first = items_completed_after(history, num_periods=4, trials=1000, seed=1)
        second = items_completed_after(history, num_periods=4, trials=1000, seed=2)
        assert first.tolist() != second.tolist()


class TestCumulativePaths:
    """T003: cumulative_paths must agree with the two existing functions (research.md §1)."""

    def test_shape_is_trials_by_horizon(self) -> None:
        history = _history()
        paths = cumulative_paths(history, horizon=10, trials=1000, seed=42)
        assert paths.shape == (1000, 10)

    def test_last_column_equals_items_completed_after(self) -> None:
        history = _history()
        paths = cumulative_paths(history, horizon=4, trials=1000, seed=42)
        items = items_completed_after(history, num_periods=4, trials=1000, seed=42)
        assert paths[:, -1].tolist() == items.tolist()

    def test_first_reach_column_equals_periods_to_complete(self) -> None:
        history = _history()
        backlog_size = 20
        horizon = max(backlog_size * 50, 500)
        paths = cumulative_paths(history, horizon=horizon, trials=1000, seed=42)
        reached = paths >= backlog_size
        first_reach = reached.argmax(axis=1)
        never_reached = ~reached.any(axis=1)
        first_reach = np.where(never_reached, horizon - 1, first_reach)
        derived_periods = first_reach + 1

        periods = periods_to_complete(history, backlog_size, trials=1000, seed=42)
        assert derived_periods.tolist() == periods.tolist()

    def test_rows_never_decrease(self) -> None:
        history = _history()
        paths = cumulative_paths(history, horizon=20, trials=500, seed=7)
        assert bool(np.all(np.diff(paths, axis=1) >= 0))


class TestCumulativePathsUntilReached:
    """Fix for issue #178: an inadequate horizon must never silently clamp a
    trial that hasn't reached the target - it must retry with a larger
    horizon, or fail loudly if even that isn't enough."""

    def test_adequate_initial_horizon_is_returned_unchanged(self) -> None:
        # Same shape, same seed as plain cumulative_paths when the first
        # attempt already succeeds - byte-identical, so every
        # currently-working case is completely unaffected by this fix.
        history = _history()
        plain = cumulative_paths(history, horizon=1000, trials=100, seed=42)
        retried = cumulative_paths_until_reached(
            history, target=20, initial_horizon=1000, trials=100, seed=42
        )
        assert retried.tolist() == plain.tolist()

    def test_extends_the_horizon_when_the_initial_guess_is_insufficient(self) -> None:
        # 1 item in 50 periods (mean 0.02): the issue #178 finding showed 46%
        # of trials don't reach backlog_size=20 within horizon=1000.
        sparse_history = ThroughputHistory(
            completed_per_period=[0] * 49 + [1], period_duration=timedelta(days=7)
        )
        paths = cumulative_paths_until_reached(
            sparse_history, target=20, initial_horizon=1000, trials=200, seed=42
        )
        assert paths.shape[1] > 1000
        assert bool(np.all(paths[:, -1] >= 20))

    def test_raises_when_even_the_capped_horizon_is_not_enough(self) -> None:
        # mean=1: needs ~10,000 periods on average. Starting from 2 and
        # doubling 8 times only reaches 2 * 2**8 = 512 - nowhere close, so
        # this must raise rather than return a wrong (clamped) answer.
        history = ThroughputHistory(completed_per_period=[1] * 6, period_duration=timedelta(days=7))
        with pytest.raises(ValueError, match="too sparse"):
            cumulative_paths_until_reached(
                history, target=10_000, initial_horizon=2, trials=5, seed=42
            )

    def test_never_reached_clamping_cannot_occur_in_the_result(self) -> None:
        # Every trial's final column must be >= target - there must be no
        # trace of the old silent-clamp-to-horizon-minus-one behavior.
        sparse_history = ThroughputHistory(
            completed_per_period=[0] * 99 + [1], period_duration=timedelta(days=7)
        )
        paths = cumulative_paths_until_reached(
            sparse_history, target=20, initial_horizon=1000, trials=200, seed=42
        )
        assert bool(np.all(paths[:, -1] >= 20))
