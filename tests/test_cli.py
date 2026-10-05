"""Tests for the forecast CLI (T004-T005 Foundational, T009-T011 US1, T014-T015 US2)."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from agile_metrics.cli import _build_history, _render_result, app
from agile_metrics.models import ForecastResult, OutcomeBucket, ProjectionPoint, ThroughputHistory

runner = CliRunner()
_HISTORY_ARGS = ["--history", "3,5,4,6,2,5,4,3", "--period-days", "7"]

_CSV_TODAY = date(2026, 10, 5)
_CSV_COUNTS = [3, 5, 4, 6, 2, 5, 4, 3]


def _csv_text_for_counts(counts: list[int], today: date, period_days: int) -> str:
    """Build CSV text whose end dates bucket to exactly `counts`, oldest first,
    anchored to `today` (mirrors `_bucket_items`'s own formula - see test_web.py's
    identical helper for the same reasoning)."""
    periods = len(counts)
    rows = ["id,type,title,start_date,end_date"]
    next_id = 1
    for bucket_index, count in enumerate(counts):
        periods_ago = periods - 1 - bucket_index
        end_date = today - timedelta(days=periods_ago * period_days)
        for _ in range(count):
            rows.append(f"{next_id},story,Item {next_id},,{end_date.isoformat()}")
            next_id += 1
    return "\n".join(rows) + "\n"


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


class TestLinearOptions:
    """T025 (US2): --history becomes optional; new Linear flags exist."""

    _MOCKED_HISTORY = ThroughputHistory(
        completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3], period_duration=timedelta(days=7)
    )

    def test_history_is_not_required_when_linear_flags_are_given(self) -> None:
        with patch("agile_metrics.cli.fetch_linear_throughput", return_value=self._MOCKED_HISTORY):
            result = runner.invoke(
                app,
                [
                    "--period-days",
                    "7",
                    "--backlog-size",
                    "20",
                    "--seed",
                    "42",
                    "--linear-api-key",
                    "lin_api_test",
                    "--linear-team",
                    "team-123",
                ],
            )
        assert result.exit_code == 0, result.output

    def test_linear_periods_option_is_passed_through(self) -> None:
        with patch(
            "agile_metrics.cli.fetch_linear_throughput", return_value=self._MOCKED_HISTORY
        ) as mocked_fetch:
            runner.invoke(
                app,
                [
                    "--period-days",
                    "7",
                    "--backlog-size",
                    "20",
                    "--linear-api-key",
                    "lin_api_test",
                    "--linear-team",
                    "team-123",
                    "--linear-periods",
                    "12",
                ],
            )
        mocked_fetch.assert_called_once_with(
            api_key="lin_api_test",
            team_id="team-123",
            period_duration=timedelta(days=7),
            periods=12,
        )

    def test_linear_api_key_readable_from_environment_variable(self) -> None:
        with patch(
            "agile_metrics.cli.fetch_linear_throughput", return_value=self._MOCKED_HISTORY
        ) as mocked_fetch:
            runner.invoke(
                app,
                [
                    "--period-days",
                    "7",
                    "--backlog-size",
                    "20",
                    "--linear-team",
                    "team-123",
                ],
                env={"AGILE_METRICS_LINEAR_API_KEY": "lin_api_from_env"},
            )
        mocked_fetch.assert_called_once_with(
            api_key="lin_api_from_env",
            team_id="team-123",
            period_duration=timedelta(days=7),
            periods=26,
        )

    def test_rejects_neither_history_nor_linear_flags(self) -> None:
        result = runner.invoke(app, ["--period-days", "7", "--backlog-size", "20"])
        assert result.exit_code == 1
        assert "exactly one" in result.output

    def test_rejects_both_history_and_linear_flags(self) -> None:
        result = runner.invoke(
            app,
            [
                *_HISTORY_ARGS,
                "--backlog-size",
                "20",
                "--linear-api-key",
                "lin_api_test",
                "--linear-team",
                "team-123",
            ],
        )
        assert result.exit_code == 1
        assert "exactly one" in result.output

    def test_linear_mode_prints_identical_output_to_manual_paste(self) -> None:
        """T027 (US2): same underlying history, same rendered output, either surface."""
        with patch("agile_metrics.cli.fetch_linear_throughput", return_value=self._MOCKED_HISTORY):
            linear_result = runner.invoke(
                app,
                [
                    "--period-days",
                    "7",
                    "--backlog-size",
                    "20",
                    "--seed",
                    "42",
                    "--linear-api-key",
                    "lin_api_test",
                    "--linear-team",
                    "team-123",
                ],
            )
        manual_result = runner.invoke(
            app,
            [
                "--history",
                "3,5,4,6,2,5,4,3",
                "--period-days",
                "7",
                "--backlog-size",
                "20",
                "--seed",
                "42",
            ],
        )
        assert linear_result.exit_code == 0
        assert linear_result.output == manual_result.output

    def test_linear_integration_error_renders_as_error_and_exits_1(self) -> None:
        """T029 (US2): LinearIntegrationError surfaces via the existing Error:/exit-1 path."""
        from agile_metrics.linear_client import LinearAuthenticationError

        with patch(
            "agile_metrics.cli.fetch_linear_throughput", side_effect=LinearAuthenticationError()
        ):
            result = runner.invoke(
                app,
                [
                    "--period-days",
                    "7",
                    "--backlog-size",
                    "20",
                    "--linear-api-key",
                    "lin_api_bad",
                    "--linear-team",
                    "team-123",
                ],
            )
        assert result.exit_code == 1
        assert "Error: Linear API key is invalid or expired" in result.output
        assert "Traceback" not in result.output


class TestLinearErrorsEndToEnd:
    """T031/T032 (US3): every distinct Linear-side failure produces its own specific
    message through the CLI, and the two reused-validator cases keep the existing
    (non-Linear-specific) messages unchanged."""

    _ARGS = [
        "--period-days",
        "7",
        "--backlog-size",
        "20",
        "--linear-api-key",
        "lin_api_test",
        "--linear-team",
        "team-123",
    ]

    @staticmethod
    def _invoke_with_fetch_error(exc: Exception):  # type: ignore[no-untyped-def]
        with patch("agile_metrics.cli.fetch_linear_throughput", side_effect=exc):
            return runner.invoke(app, TestLinearErrorsEndToEnd._ARGS)

    def test_team_not_found_names_the_team(self) -> None:
        from agile_metrics.linear_client import LinearTeamNotFoundError

        result = self._invoke_with_fetch_error(LinearTeamNotFoundError("team-123"))
        assert result.exit_code == 1
        assert (
            "Error: Linear team 'team-123' was not found or is not accessible with this API key"
            in result.output
        )

    def test_rate_limited_names_the_problem(self) -> None:
        from agile_metrics.linear_client import LinearRateLimitedError

        result = self._invoke_with_fetch_error(LinearRateLimitedError())
        assert result.exit_code == 1
        assert "Error: Linear API rate limit exceeded - try again later" in result.output

    def test_api_unavailable_names_the_problem(self) -> None:
        from agile_metrics.linear_client import LinearAPIUnavailableError

        result = self._invoke_with_fetch_error(LinearAPIUnavailableError())
        assert result.exit_code == 1
        assert "Error: Linear API is currently unavailable - try again later" in result.output

    def test_zero_completed_issues_reuses_the_existing_all_zero_message(self) -> None:
        try:
            ThroughputHistory(completed_per_period=[0] * 6, period_duration=timedelta(days=7))
        except ValidationError as exc:
            zero_history_error = exc

        result = self._invoke_with_fetch_error(zero_history_error)
        assert result.exit_code == 1
        assert "zero" in result.output

    def test_too_few_periods_reuses_the_existing_message(self) -> None:
        try:
            ThroughputHistory(completed_per_period=[1, 2, 3], period_duration=timedelta(days=7))
        except ValidationError as exc:
            too_few_error = exc

        result = self._invoke_with_fetch_error(too_few_error)
        assert result.exit_code == 1
        assert "historical periods" in result.output


class TestCsvOptions:
    """T017 (US2): --history/--linear-* become optional with --csv-file as a third
    mutually-exclusive arm."""

    def test_history_is_not_required_when_csv_file_is_given(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "items.csv"
        csv_path.write_text(_csv_text_for_counts(_CSV_COUNTS, _CSV_TODAY, period_days=7))

        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = _CSV_TODAY
            result = runner.invoke(
                app,
                [
                    "--period-days",
                    "7",
                    "--backlog-size",
                    "20",
                    "--seed",
                    "42",
                    "--csv-file",
                    str(csv_path),
                ],
            )
        assert result.exit_code == 0, result.output

    def test_csv_mode_prints_identical_output_to_manual_paste(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "items.csv"
        csv_path.write_text(_csv_text_for_counts(_CSV_COUNTS, _CSV_TODAY, period_days=7))

        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = _CSV_TODAY
            csv_result = runner.invoke(
                app,
                [
                    "--period-days",
                    "7",
                    "--backlog-size",
                    "20",
                    "--seed",
                    "42",
                    "--csv-file",
                    str(csv_path),
                ],
            )
        manual_result = runner.invoke(app, [*_HISTORY_ARGS, "--backlog-size", "20", "--seed", "42"])
        assert csv_result.exit_code == 0
        assert csv_result.output == manual_result.output

    def test_rejects_neither_history_linear_nor_csv_file(self) -> None:
        result = runner.invoke(app, ["--period-days", "7", "--backlog-size", "20"])
        assert result.exit_code == 1
        assert "exactly one" in result.output

    def test_rejects_both_history_and_csv_file(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "items.csv"
        csv_path.write_text(_csv_text_for_counts(_CSV_COUNTS, _CSV_TODAY, period_days=7))

        result = runner.invoke(
            app, [*_HISTORY_ARGS, "--backlog-size", "20", "--csv-file", str(csv_path)]
        )
        assert result.exit_code == 1
        assert "exactly one" in result.output

    def test_rejects_both_linear_and_csv_file(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "items.csv"
        csv_path.write_text(_csv_text_for_counts(_CSV_COUNTS, _CSV_TODAY, period_days=7))

        result = runner.invoke(
            app,
            [
                "--period-days",
                "7",
                "--backlog-size",
                "20",
                "--linear-api-key",
                "lin_api_test",
                "--linear-team",
                "team-123",
                "--csv-file",
                str(csv_path),
            ],
        )
        assert result.exit_code == 1
        assert "exactly one" in result.output

    def test_csv_import_error_renders_as_error_and_exits_1(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "items.csv"
        csv_path.write_text("id,type,title,start_date\n1,story,Bad,2026-08-01\n")

        result = runner.invoke(
            app,
            ["--period-days", "7", "--backlog-size", "20", "--csv-file", str(csv_path)],
        )
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "end_date" in result.output
        assert "Traceback" not in result.output


class TestCsvErrorsEndToEnd:
    """T023/T024 (US3): every distinct CSV-side failure produces its own specific
    message through the CLI, and the two reused-validator cases keep the existing
    (non-CSV-specific) messages unchanged."""

    @staticmethod
    def _invoke_with_csv_text(tmp_path: Path, csv_text: str):  # type: ignore[no-untyped-def]
        csv_path = tmp_path / "items.csv"
        csv_path.write_text(csv_text)
        return runner.invoke(
            app,
            ["--period-days", "7", "--backlog-size", "20", "--csv-file", str(csv_path)],
        )

    def test_blank_id_names_the_row_and_field(self, tmp_path: Path) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,,2026-08-05\n"
            ",story,Blank id,,2026-08-12\n"
        )
        result = self._invoke_with_csv_text(tmp_path, csv_text)
        assert result.exit_code == 1
        assert "row 2" in result.output
        assert "id" in result.output

    def test_malformed_start_date_names_the_row_and_field(self, tmp_path: Path) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,,2026-08-05\n"
            "2,story,Bad start,not-a-date,2026-08-12\n"
        )
        result = self._invoke_with_csv_text(tmp_path, csv_text)
        assert result.exit_code == 1
        assert "row 2" in result.output
        assert "start_date" in result.output

    def test_malformed_end_date_names_the_row_and_field(self, tmp_path: Path) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,,2026-08-05\n"
            "2,story,Bad end,,not-a-date\n"
        )
        result = self._invoke_with_csv_text(tmp_path, csv_text)
        assert result.exit_code == 1
        assert "row 2" in result.output
        assert "end_date" in result.output

    def test_zero_items_with_any_end_date_reuses_the_existing_all_zero_message(
        self, tmp_path: Path
    ) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,2026-09-01,\n"
            "2,story,Second,2026-09-05,\n"
        )
        result = self._invoke_with_csv_text(tmp_path, csv_text)
        assert result.exit_code == 1
        assert "zero" in result.output

    def test_narrow_date_range_reuses_the_existing_too_few_periods_message(
        self, tmp_path: Path
    ) -> None:
        today = date.today()
        csv_text = (
            "id,type,title,start_date,end_date\n"
            f"1,story,First,,{today.isoformat()}\n"
            f"2,story,Second,,{today.isoformat()}\n"
        )
        result = self._invoke_with_csv_text(tmp_path, csv_text)
        assert result.exit_code == 1
        assert "historical periods" in result.output
