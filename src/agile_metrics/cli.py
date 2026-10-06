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
from agile_metrics.jira_client import (
    JiraConnection,
    JiraIntegrationError,
    fetch_jira_throughput,
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


def _render_result(result: ForecastResult, done_statuses: list[str] | None = None) -> str:
    """Render a ForecastResult as human-readable text, all four levels and metadata.

    `done_statuses` is passed only for Jira results (spec 010, clarification Q3) and
    adds one line naming the statuses treated as done.
    """
    lines = [f"Forecast ({result.trials_run} trials, {result.periods_used} historical periods):"]
    for level in _CONFIDENCE_LEVELS:
        lines.append(f"  {level}% confidence: {result.outcomes[level]}")
    if done_statuses:
        lines.append(f"Done statuses: {', '.join(done_statuses)}")
    if result.precision_warning is not None:
        lines.append(f"⚠ {result.precision_warning.message}")
    return "\n".join(lines)


def _build_throughput_history(
    *,
    history: str | None,
    linear_api_key: str | None,
    linear_team: str | None,
    linear_periods: int | None,
    csv_file: Path | None,
    period_days: int,
    jira_site: str | None = None,
    jira_email: str | None = None,
    jira_api_token: str | None = None,
    jira_project: str | None = None,
    jira_periods: int | None = None,
) -> tuple[ThroughputHistory, list[str]]:
    """Exactly one of --history, (--linear-api-key and --linear-team), --csv-file, or
    the Jira options is required - mirrors web.py's _build_history dispatch.

    Returns the history and the Jira done statuses (empty for every other source).
    """
    has_linear = linear_api_key is not None and linear_team is not None
    partial_linear = (linear_api_key is not None) != (linear_team is not None)
    jira_missing = _missing_jira_options(jira_site, jira_email, jira_api_token, jira_project)
    if jira_missing and len(jira_missing) < len(_JIRA_REQUIRED):
        raise ValueError(
            "--jira-site, --jira-email, --jira-api-token and --jira-project must all be "
            "provided together - missing: " + ", ".join(jira_missing)
        )
    has_jira = not jira_missing
    sources_given = sum([history is not None, has_linear, csv_file is not None, has_jira])
    if sources_given == 0 and partial_linear:
        missing = "--linear-team" if linear_api_key is not None else "--linear-api-key"
        raise ValueError(
            f"--linear-api-key and --linear-team must both be provided together - "
            f"{missing} is missing"
        )
    if sources_given != 1:
        raise ValueError(
            "exactly one of --history, (--linear-api-key and --linear-team), --csv-file, "
            "or (--jira-site, --jira-email, --jira-api-token and --jira-project) is required, "
            "not multiple or none"
        )

    if history is not None:
        return _build_history(history, period_days), []
    if has_linear and linear_api_key is not None and linear_team is not None:
        linear_history = fetch_linear_throughput(
            api_key=linear_api_key,
            team_id=linear_team,
            period_duration=timedelta(days=period_days),
            periods=linear_periods if linear_periods is not None else DEFAULT_LOOKBACK_PERIODS,
        )
        return linear_history, []
    if csv_file is not None:
        items = parse_items_csv(csv_file.read_text())
        return bucket_items_to_throughput(items, timedelta(days=period_days)), []
    if has_jira:
        connection = JiraConnection(
            site=jira_site or "",
            email=jira_email or "",
            api_token=jira_api_token or "",
            project_key=jira_project or "",
            period_days=period_days,
            periods=jira_periods if jira_periods is not None else DEFAULT_LOOKBACK_PERIODS,
        )
        jira_result = fetch_jira_throughput(connection)
        return jira_result.history, jira_result.done_statuses
    raise ValueError("exactly one of the four data sources is required")


_JIRA_REQUIRED = ("--jira-site", "--jira-email", "--jira-api-token", "--jira-project")


def _missing_jira_options(
    site: str | None, email: str | None, api_token: str | None, project: str | None
) -> list[str]:
    """The Jira options that were NOT given. Empty when none is given, and also
    when all four are given; `_build_throughput_history` tells those apart."""
    values = dict(zip(_JIRA_REQUIRED, (site, email, api_token, project), strict=True))
    return [name for name, value in values.items() if value is None]


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
    jira_site: str | None = typer.Option(
        None,
        "--jira-site",
        envvar="AGILE_METRICS_JIRA_SITE",
        help="Jira Cloud site host, e.g. acme.atlassian.net (alternative to --history)",
    ),
    jira_email: str | None = typer.Option(
        None,
        "--jira-email",
        envvar="AGILE_METRICS_JIRA_EMAIL",
        help="Atlassian account email for the Jira API token",
    ),
    jira_api_token: str | None = typer.Option(
        None,
        "--jira-api-token",
        envvar="AGILE_METRICS_JIRA_API_TOKEN",
        help="Jira API token (prefer the env var; a flag value lands in shell history)",
    ),
    jira_project: str | None = typer.Option(
        None, "--jira-project", help="Jira project key, e.g. ENG"
    ),
    jira_periods: int | None = typer.Option(
        None, "--jira-periods", help="Jira lookback window in periods (default: 26)"
    ),
) -> None:
    """Forecast completion dates or items-completed from historical throughput."""
    try:
        throughput_history, done_statuses = _build_throughput_history(
            history=history,
            linear_api_key=linear_api_key,
            linear_team=linear_team,
            linear_periods=linear_periods,
            csv_file=csv_file,
            period_days=period_days,
            jira_site=jira_site,
            jira_email=jira_email,
            jira_api_token=jira_api_token,
            jira_project=jira_project,
            jira_periods=jira_periods,
        )
        result = _run_forecast(throughput_history, backlog_size, target_date, seed)
    except (
        ValidationError,
        ValueError,
        LinearIntegrationError,
        CsvImportError,
        JiraIntegrationError,
    ) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(_render_result(result, done_statuses))
