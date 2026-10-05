"""Command-line interface for agile_metrics.

Per Constitution Principle II, this module only calls the public
`forecast_by_items`/`forecast_by_date` API - never `simulation.py` internals.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import typer
from pydantic import ValidationError

from agile_metrics import forecast_by_date, forecast_by_items
from agile_metrics.csv_item_import import (
    CsvImportError,
    bucket_items_to_throughput,
    parse_items_csv,
)
from agile_metrics.linear_client import (
    DEFAULT_LOOKBACK_PERIODS,
    LinearIntegrationError,
    fetch_linear_throughput,
)
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


def _build_throughput_history(
    *,
    history: str | None,
    linear_api_key: str | None,
    linear_team: str | None,
    linear_periods: int | None,
    csv_file: Path | None,
    period_days: int,
) -> ThroughputHistory:
    """Exactly one of --history, (--linear-api-key and --linear-team), or
    --csv-file is required - mirrors web.py's _build_history dispatch for the
    same three data sources."""
    has_linear = linear_api_key is not None and linear_team is not None
    sources_given = sum([history is not None, has_linear, csv_file is not None])
    if sources_given != 1:
        raise ValueError(
            "exactly one of --history, (--linear-api-key and --linear-team), or "
            "--csv-file is required, not multiple or none"
        )

    if history is not None:
        return _build_history(history, period_days)
    if has_linear and linear_api_key is not None and linear_team is not None:
        return fetch_linear_throughput(
            api_key=linear_api_key,
            team_id=linear_team,
            period_duration=timedelta(days=period_days),
            periods=linear_periods if linear_periods is not None else DEFAULT_LOOKBACK_PERIODS,
        )
    if csv_file is not None:
        items = parse_items_csv(csv_file.read_text())
        return bucket_items_to_throughput(items, timedelta(days=period_days))
    raise ValueError("exactly one of --history, --linear-*, or --csv-file is required")


def _run_forecast(
    history: ThroughputHistory,
    backlog_size: int | None,
    target_date: str | None,
    seed: int | None,
) -> ForecastResult:
    """Exactly one of --backlog-size or --target-date is required."""
    parsed_target_date = date.fromisoformat(target_date) if target_date is not None else None
    if backlog_size is not None and parsed_target_date is None:
        return forecast_by_items(history, backlog_size, seed=seed)
    if parsed_target_date is not None and backlog_size is None:
        return forecast_by_date(history, parsed_target_date, seed=seed)
    raise ValueError(
        "exactly one of --backlog-size or --target-date is required, not both or neither"
    )


@app.command()
def main(
    history: str | None = typer.Option(
        None, "--history", help="Comma-separated historical throughput, e.g. '3,5,4,6'"
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
    linear_api_key: str | None = typer.Option(
        None,
        "--linear-api-key",
        envvar="AGILE_METRICS_LINEAR_API_KEY",
        help="Linear personal API key (alternative to --history)",
    ),
    linear_team: str | None = typer.Option(
        None, "--linear-team", help="Linear team ID to fetch completed-issue throughput from"
    ),
    linear_periods: int | None = typer.Option(
        None, "--linear-periods", help="Lookback window in periods (default: 26)"
    ),
    csv_file: Path | None = typer.Option(
        None,
        "--csv-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a CSV of per-item records (alternative to --history)",
    ),
) -> None:
    """Forecast completion dates or items-completed from historical throughput."""
    try:
        throughput_history = _build_throughput_history(
            history=history,
            linear_api_key=linear_api_key,
            linear_team=linear_team,
            linear_periods=linear_periods,
            csv_file=csv_file,
            period_days=period_days,
        )
        result = _run_forecast(throughput_history, backlog_size, target_date, seed)
    except (ValidationError, ValueError, LinearIntegrationError, CsvImportError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(_render_result(result))
