"""Shared pytest fixtures (T015)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from agile_metrics.models import ForecastRequest, ThroughputHistory


@pytest.fixture
def valid_history() -> ThroughputHistory:
    return ThroughputHistory(
        completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3],
        period_duration=timedelta(days=7),
    )


@pytest.fixture
def forecast_request_factory(valid_history: ThroughputHistory):
    def _make(**overrides: Any) -> ForecastRequest:
        defaults: dict[str, Any] = {"history": valid_history, "backlog_size": 20}
        defaults.update(overrides)
        return ForecastRequest(**defaults)

    return _make
