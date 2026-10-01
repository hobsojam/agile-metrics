"""Reproducibility test for the Monte Carlo simulation core (T008)."""

from datetime import timedelta

from agile_metrics.models import ThroughputHistory
from agile_metrics.simulation import items_completed_after, periods_to_complete


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
