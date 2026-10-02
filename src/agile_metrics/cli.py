"""Command-line interface for agile_metrics.

Per Constitution Principle II, this module only calls the public
`forecast_by_items`/`forecast_by_date` API - never `simulation.py` internals.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

import typer
from pydantic import ValidationError

from agile_metrics import forecast_by_date, forecast_by_items
from agile_metrics.models import ForecastResult, ThroughputHistory

app = typer.Typer(add_completion=False)

_CONFIDENCE_LEVELS: tuple[Literal[50, 70, 85, 95], ...] = (50, 70, 85, 95)


def _build_history(history: str, period_days: int) -> ThroughputHistory:
    """Parse a comma-separated throughput string into a ThroughputHistory."""
    try:
        completed_per_period = [int(value.strip()) for value in history.split(",")]
    except ValueError as exc:
        raise ValueError(f"--history must be comma-separated integers, got: {history!r}") from exc
    return ThroughputHistory(
        completed_per_period=completed_per_period,
        period_duration=timedelta(days=period_days),
    )


def _render_result(result: ForecastResult) -> str:
    """Render a ForecastResult as human-readable text, all four levels and metadata."""
    lines = [f"Forecast ({result.trials_run} trials, {result.periods_used} historical periods):"]
    for level in _CONFIDENCE_LEVELS:
        lines.append(f"  {level}% confidence: {result.outcomes[level]}")
    return "\n".join(lines)


@app.command()
def main(
    history: str = typer.Option(
        ..., "--history", help="Comma-separated historical throughput, e.g. '3,5,4,6'"
    ),
    period_days: int = typer.Option(
        ..., "--period-days", help="Real-world length of one period, in days"
    ),
    backlog_size: int | None = typer.Option(
        None, "--backlog-size", help="Forecast a completion date for this many remaining items"
    ),
    target_date: str | None = typer.Option(
        None, "--target-date", help="Forecast items completed by this date (YYYY-MM-DD)"
    ),
    seed: int | None = typer.Option(None, "--seed", help="Random seed for a reproducible forecast"),
) -> None:
    """Forecast completion dates or items-completed from historical throughput."""
    try:
        throughput_history = _build_history(history, period_days)
        parsed_target_date: date | None = (
            date.fromisoformat(target_date) if target_date is not None else None
        )

        if backlog_size is not None and parsed_target_date is None:
            result = forecast_by_items(throughput_history, backlog_size, seed=seed)
        elif parsed_target_date is not None and backlog_size is None:
            result = forecast_by_date(throughput_history, parsed_target_date, seed=seed)
        else:
            raise ValueError(
                "exactly one of --backlog-size or --target-date is required, not both or neither"
            )
    except (ValidationError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(_render_result(result))
