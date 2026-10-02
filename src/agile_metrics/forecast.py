"""Public orchestration: build a request, run the simulation, shape the result.

Per Constitution Principle II, these two functions are the only supported
entry points into the forecasting library.
"""

from __future__ import annotations

from datetime import date

import numpy as np

from agile_metrics.models import ForecastRequest, ForecastResult, ThroughputHistory
from agile_metrics.simulation import items_completed_after, periods_to_complete

_CONFIDENCE_LEVELS: tuple[int, ...] = (50, 70, 85, 95)


def forecast_by_items(
    history: ThroughputHistory,
    backlog_size: int,
    *,
    seed: int | None = None,
    reference_date: date | None = None,
) -> ForecastResult:
    """Forecast completion dates for a backlog of `backlog_size` remaining items."""
    request = _build_request(
        history, backlog_size=backlog_size, seed=seed, reference_date=reference_date
    )

    periods = periods_to_complete(
        request.history, backlog_size, trials=request.trials, seed=request.seed
    )
    percentiles = np.percentile(periods, _CONFIDENCE_LEVELS)
    outcomes: dict[int, date | int] = {
        level: request.reference_date + round(float(p)) * request.history.period_duration
        for level, p in zip(_CONFIDENCE_LEVELS, percentiles, strict=True)
    }
    return ForecastResult(
        outcomes=outcomes,  # type: ignore[arg-type]
        trials_run=request.trials,
        periods_used=len(request.history.completed_per_period),
    )


def forecast_by_date(
    history: ThroughputHistory,
    target_date: date,
    *,
    seed: int | None = None,
    reference_date: date | None = None,
) -> ForecastResult:
    """Forecast how many items will be completed by `target_date`."""
    request = _build_request(
        history, target_date=target_date, seed=seed, reference_date=reference_date
    )

    num_periods = max(1, (target_date - request.reference_date) // request.history.period_duration)
    items = items_completed_after(
        request.history, num_periods=num_periods, trials=request.trials, seed=request.seed
    )
    # Higher confidence must mean a fewer-or-equal item count (data-model.md
    # invariant), so read off the mirrored percentile of the raw distribution.
    percentiles = np.percentile(items, [100 - level for level in _CONFIDENCE_LEVELS])
    outcomes: dict[int, date | int] = {
        level: int(p) for level, p in zip(_CONFIDENCE_LEVELS, percentiles, strict=True)
    }
    return ForecastResult(
        outcomes=outcomes,  # type: ignore[arg-type]
        trials_run=request.trials,
        periods_used=len(request.history.completed_per_period),
    )


def _build_request(
    history: ThroughputHistory,
    *,
    backlog_size: int | None = None,
    target_date: date | None = None,
    seed: int | None,
    reference_date: date | None,
) -> ForecastRequest:
    kwargs: dict[str, object] = {"history": history, "seed": seed}
    if backlog_size is not None:
        kwargs["backlog_size"] = backlog_size
    if target_date is not None:
        kwargs["target_date"] = target_date
    if reference_date is not None:
        kwargs["reference_date"] = reference_date
    return ForecastRequest(**kwargs)  # type: ignore[arg-type]
