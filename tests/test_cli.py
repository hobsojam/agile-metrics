"""Tests for the forecast CLI (T004-T005 Foundational, T009-T011 US1, T014-T015 US2)."""

from datetime import date, timedelta

import pytest
from typer.testing import CliRunner

from agile_metrics.cli import _build_history, _render_result, app
from agile_metrics.models import ForecastResult, OutcomeBucket, ProjectionPoint

runner = CliRunner()
_HISTORY_ARGS = ["--history", "3,5,4,6,2,5,4,3", "--period-days", "7"]


class TestBuildHistory:
    def test_valid_history_builds_throughput_history(self) -> None:
        history = _build_history("3,5,4,6,2,5", 7)
        assert history.completed_per_period == [3, 5, 4, 6, 2, 5]
        assert history.period_duration == timedelta(days=7)

    def test_malformed_history_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _build_history("a,b,c", 7)


class TestRenderResult:
    def test_renders_date_outcomes_with_metadata(self) -> None:
        result = ForecastResult(
            outcomes={
                50: date(2026, 11, 5),
                70: date(2026, 11, 12),
                85: date(2026, 11, 12),
                95: date(2026, 11, 19),
            },
            trials_run=10_000,
            periods_used=8,
            reference_date=date(2026, 10, 3),
            distribution=[
                OutcomeBucket(lower=date(2026, 11, 5), upper=date(2026, 11, 5), trials=10_000)
            ],
            projection=[
                ProjectionPoint(
                    period=1,
                    period_end=date(2026, 10, 10),
                    cumulative={50: 4, 70: 4, 85: 3, 95: 2},
                )
            ],
        )
        text = _render_result(result)
        assert "10000" in text
        assert "8" in text
        assert "2026-11-05" in text
        assert "2026-11-12" in text
        assert "2026-11-19" in text

    def test_renders_int_outcomes_with_metadata(self) -> None:
        result = ForecastResult(
            outcomes={50: 32, 70: 30, 85: 28, 95: 26},
            trials_run=10_000,
            periods_used=8,
            reference_date=date(2026, 10, 3),
            distribution=[OutcomeBucket(lower=32, upper=32, trials=10_000)],
            projection=[
                ProjectionPoint(
                    period=1,
                    period_end=date(2026, 10, 10),
                    cumulative={50: 32, 70: 30, 85: 28, 95: 26},
                )
            ],
        )
        text = _render_result(result)
        assert "32" in text
        assert "30" in text
        assert "28" in text
        assert "26" in text


class TestForecastByItemsCommand:
    """User Story 1 (P1): completion-date forecast from the command line."""

    def test_returns_dates_at_all_confidence_levels(self) -> None:
        result = runner.invoke(app, [*_HISTORY_ARGS, "--backlog-size", "20", "--seed", "42"])
        assert result.exit_code == 0
        for level in (50, 70, 85, 95):
            assert f"{level}% confidence:" in result.output

    def test_same_seed_is_reproducible(self) -> None:
        args = [*_HISTORY_ARGS, "--backlog-size", "20", "--seed", "42"]
        first = runner.invoke(app, args)
        second = runner.invoke(app, args)
        assert first.output == second.output

    def test_rejects_zero_backlog_size(self) -> None:
        result = runner.invoke(app, [*_HISTORY_ARGS, "--backlog-size", "0"])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Traceback" not in result.output


class TestForecastByDateCommand:
    """User Story 2 (P2): items-completed forecast from the command line."""

    def test_returns_item_counts_at_all_confidence_levels(self) -> None:
        result = runner.invoke(app, [*_HISTORY_ARGS, "--target-date", "2026-12-01", "--seed", "42"])
        assert result.exit_code == 0
        for level in (50, 70, 85, 95):
            assert f"{level}% confidence:" in result.output

    def test_rejects_target_date_not_in_future(self) -> None:
        result = runner.invoke(app, [*_HISTORY_ARGS, "--target-date", "2020-01-01"])
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Traceback" not in result.output


class TestMutualExclusivity:
    def test_rejects_both_backlog_size_and_target_date(self) -> None:
        result = runner.invoke(
            app, [*_HISTORY_ARGS, "--backlog-size", "20", "--target-date", "2026-12-01"]
        )
        assert result.exit_code == 1
        assert "Error:" in result.output

    def test_rejects_neither_backlog_size_nor_target_date(self) -> None:
        result = runner.invoke(app, _HISTORY_ARGS)
        assert result.exit_code == 1
        assert "Error:" in result.output
