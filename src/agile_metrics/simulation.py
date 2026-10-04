"""Pure Monte Carlo resampling core for throughput forecasting.

Internal module — not part of the public API (Constitution Principle II).
Callers outside this package must go through `agile_metrics.forecast`.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from agile_metrics.models import ThroughputHistory


def cumulative_paths(
    history: ThroughputHistory,
    horizon: int,
    trials: int,
    seed: int | None,
) -> NDArray[np.int64]:
    """Resample `horizon` future periods per trial and return their running total.

    Returns an array of shape (trials, horizon): row `t`, column `p` is the total
    items completed by trial `t` through future period `p` (1-based). This is the
    one random draw that `periods_to_complete` and `items_completed_after` are
    both re-expressed on top of (research.md §1), so chart data derived from it
    is guaranteed consistent with the existing outcomes under a fixed seed.
    """
    rng = np.random.default_rng(seed)
    historical = np.asarray(history.completed_per_period, dtype=np.int64)
    samples = rng.choice(historical, size=(trials, horizon), replace=True)
    return np.asarray(np.cumsum(samples, axis=1), dtype=np.int64)


_MAX_HORIZON_DOUBLINGS = 8


def cumulative_paths_until_reached(
    history: ThroughputHistory,
    target: int,
    initial_horizon: int,
    trials: int,
    seed: int | None,
) -> NDArray[np.int64]:
    """Like `cumulative_paths`, but guarantees every trial reaches `target`.

    The first attempt uses `initial_horizon` unchanged, so a history/target
    combination that already succeeds gets the exact same draw (same
    `rng.choice` shape, same seed) as a plain `cumulative_paths` call -
    this only changes behavior for combinations where the initial horizon
    was insufficient, which previously produced silently wrong (clamped to
    the horizon) results (issue #178).

    Retries with a doubled horizon, up to `_MAX_HORIZON_DOUBLINGS` times, if
    any trial hasn't reached `target` yet. Raises `ValueError` rather than
    returning a wrong answer if even the fully-doubled horizon isn't enough.
    """
    horizon = initial_horizon
    for _ in range(_MAX_HORIZON_DOUBLINGS + 1):
        paths = cumulative_paths(history, horizon, trials, seed)
        if bool(np.all(paths[:, -1] >= target)):
            return paths
        horizon *= 2
    raise ValueError(
        "history is too sparse relative to the backlog size to forecast "
        f"reliably - not every simulated trial reached {target} items even "
        f"after extending the simulation horizon to {horizon} periods"
    )


def periods_to_complete(
    history: ThroughputHistory,
    backlog_size: int,
    trials: int,
    seed: int | None,
) -> NDArray[np.int64]:
    """For each trial, resample future periods until `backlog_size` items are reached.

    Returns an array of shape (trials,): the number of periods each trial took.
    """
    horizon = max(backlog_size * 50, 500)
    cumulative = cumulative_paths_until_reached(history, backlog_size, horizon, trials, seed)
    reached = cumulative >= backlog_size
    first_reach = reached.argmax(axis=1)
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
    cumulative = cumulative_paths(history, num_periods, trials, seed)
    return np.asarray(cumulative[:, -1], dtype=np.int64)
