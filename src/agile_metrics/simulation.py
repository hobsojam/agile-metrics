"""Pure Monte Carlo resampling core for throughput forecasting.

Internal module — not part of the public API (Constitution Principle II).
Callers outside this package must go through `agile_metrics.forecast`.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from agile_metrics.models import ThroughputHistory


def periods_to_complete(
    history: ThroughputHistory,
    backlog_size: int,
    trials: int,
    seed: int | None,
) -> NDArray[np.int64]:
    """For each trial, resample future periods until `backlog_size` items are reached.

    Returns an array of shape (trials,): the number of periods each trial took.
    """
    rng = np.random.default_rng(seed)
    historical = np.asarray(history.completed_per_period, dtype=np.int64)
    horizon = max(backlog_size * 50, 500)
    samples = rng.choice(historical, size=(trials, horizon), replace=True)
    cumulative = np.cumsum(samples, axis=1)
    reached = cumulative >= backlog_size
    first_reach = reached.argmax(axis=1)
    never_reached = ~reached.any(axis=1)
    first_reach = np.where(never_reached, horizon - 1, first_reach)
    return np.asarray(first_reach + 1, dtype=np.int64)


def items_completed_after(
    history: ThroughputHistory,
    num_periods: int,
    trials: int,
    seed: int | None,
) -> NDArray[np.int64]:
    """For each trial, resample `num_periods` future periods and sum items completed.

    Returns an array of shape (trials,): total items completed per trial.
    """
    rng = np.random.default_rng(seed)
    historical = np.asarray(history.completed_per_period, dtype=np.int64)
    samples = rng.choice(historical, size=(trials, num_periods), replace=True)
    return np.asarray(samples.sum(axis=1), dtype=np.int64)
