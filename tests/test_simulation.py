"""Reproducibility test for the Monte Carlo simulation core (T008)."""

from datetime import timedelta

import numpy as np

from agile_metrics.models import ThroughputHistory
from agile_metrics.simulation import cumulative_paths, items_completed_after, periods_to_complete


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
