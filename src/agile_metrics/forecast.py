"""Public orchestration: build a request, run the simulation, shape the result.

Per Constitution Principle II, these two functions are the only supported
entry points into the forecasting library.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
from numpy.typing import NDArray

from agile_metrics.models import (
    ForecastRequest,
    ForecastResult,
    OutcomeBucket,
    PrecisionWarning,
    ProjectionPoint,
    ThroughputHistory,
)
from agile_metrics.simulation import cumulative_paths, cumulative_paths_until_reached

_CONFIDENCE_LEVELS: tuple[int, ...] = (50, 70, 85, 95)
_PRECISION_WARNING_THRESHOLD = 1.0


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
    period_duration = request.history.period_duration
    ref_date = request.reference_date

    horizon = max(backlog_size * 50, 500)
    paths = cumulative_paths_until_reached(
        request.history, backlog_size, horizon, request.trials, request.seed
    )

    reached = paths >= backlog_size
    first_reach = reached.argmax(axis=1)
    periods = np.asarray(first_reach + 1, dtype=np.int64)

    percentiles = np.percentile(periods, _CONFIDENCE_LEVELS)
    outcomes: dict[int, date | int] = {
        level: ref_date + round(float(p)) * period_duration
        for level, p in zip(_CONFIDENCE_LEVELS, percentiles, strict=True)
    }

    distribution = _build_distribution_dates(periods, ref_date, period_duration)
    p95_periods = round(float(np.percentile(periods, 95)))
    projection = _build_projection(paths, ref_date, period_duration, num_points=p95_periods + 1)
    precision_warning = _compute_precision_warning(outcomes, ref_date)

    return ForecastResult(
        outcomes=outcomes,  # type: ignore[arg-type]
        trials_run=request.trials,
        periods_used=len(request.history.completed_per_period),
        reference_date=ref_date,
        distribution=distribution,
        projection=projection,
        precision_warning=precision_warning,
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
    period_duration = request.history.period_duration
    ref_date = request.reference_date

    num_periods = max(1, (target_date - ref_date) // period_duration)
    paths = cumulative_paths(request.history, num_periods, request.trials, request.seed)
    items = np.asarray(paths[:, -1], dtype=np.int64)

    # Higher confidence must mean a fewer-or-equal item count (data-model.md
    # invariant), so read off the mirrored percentile of the raw distribution.
    percentiles = np.percentile(items, [100 - level for level in _CONFIDENCE_LEVELS])
    outcomes: dict[int, date | int] = {
        level: int(p) for level, p in zip(_CONFIDENCE_LEVELS, percentiles, strict=True)
    }

    distribution = _build_distribution_ints(items)
    projection = _build_projection(paths, ref_date, period_duration, num_points=num_periods)
    precision_warning = _compute_precision_warning(outcomes, ref_date)

    return ForecastResult(
        outcomes=outcomes,  # type: ignore[arg-type]
        trials_run=request.trials,
        periods_used=len(request.history.completed_per_period),
        reference_date=ref_date,
        distribution=distribution,
        projection=projection,
        precision_warning=precision_warning,
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


def _compute_precision_warning(
    outcomes: dict[int, date | int], reference_date: date
) -> PrecisionWarning | None:
    """Flag a forecast whose 50%-to-95% outcome spread is too wide to plan against.

    Date-mode and count-mode use different denominators (research.md §1,
    corrected 2026-10-05): item counts are bounded below by zero, so dividing
    by p50 (as date-mode does) caps count-mode's ratio at 1.0 and the warning
    could never fire - dividing by p95 instead removes that bound.
    """
    p50 = outcomes[50]
    p95 = outcomes[95]
    if isinstance(p50, date):
        assert isinstance(p95, date)
        center = (p50 - reference_date).days
        spread = (p95 - p50).days
        ratio = spread / max(center, 1)
    else:
        assert isinstance(p95, int)
        spread = p50 - p95
        ratio = spread / max(p95, 1)

    if ratio <= _PRECISION_WARNING_THRESHOLD:
        return None
    return PrecisionWarning(
        message=(
            f"This forecast's range is very wide: the 95% outcome is roughly {ratio:.1f}x "
            "further from the median than the median itself is from today. Treat these "
            "numbers as a rough risk range, not a committed plan."
        )
    )


def _bucket_bounds(values: NDArray[np.int64]) -> tuple[int, int, int]:
    """Return (min, width, bucket_count) per research.md §3's grouping rule."""
    low = int(values.min())
    high = int(values.max())
    span = high - low + 1
    width = 1 if span <= 60 else math.ceil(span / 60)
    bucket_count = math.ceil(span / width)
    return low, width, bucket_count


def _build_distribution_ints(values: NDArray[np.int64]) -> list[OutcomeBucket]:
    low, width, bucket_count = _bucket_bounds(values)
    indices = (values - low) // width
    counts = np.bincount(indices, minlength=bucket_count)
    return [
        OutcomeBucket(
            lower=low + k * width,
            upper=low + (k + 1) * width - 1,
            trials=int(counts[k]),
        )
        for k in range(bucket_count)
    ]


def _build_distribution_dates(
    periods: NDArray[np.int64], reference_date: date, period_duration: timedelta
) -> list[OutcomeBucket]:
    low, width, bucket_count = _bucket_bounds(periods)
    indices = (periods - low) // width
    counts = np.bincount(indices, minlength=bucket_count)
    return [
        OutcomeBucket(
            lower=reference_date + (low + k * width) * period_duration,
            upper=reference_date + (low + (k + 1) * width - 1) * period_duration,
            trials=int(counts[k]),
        )
        for k in range(bucket_count)
    ]


def _build_projection(
    paths: NDArray[np.int64],
    reference_date: date,
    period_duration: timedelta,
    *,
    num_points: int,
) -> list[ProjectionPoint]:
    horizon = paths.shape[1]
    points: list[ProjectionPoint] = []
    for period in range(1, num_points + 1):
        column = paths[:, min(period, horizon) - 1]
        cumulative: dict[int, int] = {
            level: int(np.percentile(column, 100 - level)) for level in _CONFIDENCE_LEVELS
        }
        points.append(
            ProjectionPoint(
                period=period,
                period_end=reference_date + period * period_duration,
                cumulative=cumulative,  # type: ignore[arg-type]
            )
        )
    return points
