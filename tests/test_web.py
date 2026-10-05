"""Tests for the forecast web API (T008-T009 Foundational, T016-T018 US1,
T022-T023 US2, T027-T028 US3)."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agile_metrics.models import ThroughputHistory
from agile_metrics.web import ForecastRequestBody, _compute_forecast, app

_CSV_TODAY = date(2026, 10, 5)
_CSV_COUNTS = [3, 5, 4, 6, 2, 5, 4, 3]


def _csv_text_for_counts(counts: list[int], today: date, period_days: int) -> str:
    """Build CSV text whose end dates bucket to exactly `counts`, oldest first,
    anchored to `today` (mirrors `_bucket_items`'s own formula)."""
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


client = TestClient(app)
_HISTORY_BODY = {"history": [3, 5, 4, 6, 2, 5, 4, 3], "period_days": 7}


def _body(**overrides: object) -> ForecastRequestBody:
    defaults: dict[str, object] = {
        "history": [3, 5, 4, 6, 2, 5, 4, 3],
        "period_days": 7,
    }
    defaults.update(overrides)
    return ForecastRequestBody(**defaults)  # type: ignore[arg-type]


class TestForecastRequestBody:
    def test_valid_body_parses_backlog_size_request(self) -> None:
        body = _body(backlog_size=20, seed=42)
        assert body.history == [3, 5, 4, 6, 2, 5, 4, 3]
        assert body.period_days == 7
        assert body.backlog_size == 20
        assert body.target_date is None
        assert body.seed == 42

    def test_valid_body_parses_target_date_request(self) -> None:
        body = _body(target_date=date(2026, 12, 1))
        assert body.target_date == date(2026, 12, 1)
        assert body.backlog_size is None

    def test_rejects_non_integer_history_entries(self) -> None:
        with pytest.raises(ValidationError):
            _body(history=["a", "b", "c"], backlog_size=20)

    def test_accepts_linear_fields_in_place_of_history(self) -> None:
        body = ForecastRequestBody(
            period_days=7,
            backlog_size=20,
            linear_api_key="lin_api_test",
            linear_team_id="team-123",
            linear_periods=26,
        )
        assert body.history is None
        assert body.linear_api_key == "lin_api_test"
        assert body.linear_team_id == "team-123"
        assert body.linear_periods == 26

    def test_linear_periods_is_optional(self) -> None:
        body = ForecastRequestBody(
            period_days=7,
            backlog_size=20,
            linear_api_key="lin_api_test",
            linear_team_id="team-123",
        )
        assert body.linear_periods is None


class TestComputeForecast:
    def test_backlog_size_calls_forecast_by_items(self) -> None:
        body = _body(backlog_size=20, seed=42)
        result = _compute_forecast(body)
        assert all(isinstance(v, date) for v in result.outcomes.values())

    def test_target_date_calls_forecast_by_date(self) -> None:
        body = _body(target_date=date(2026, 12, 1), seed=42)
        result = _compute_forecast(body)
        assert all(isinstance(v, int) for v in result.outcomes.values())

    def test_rejects_both_backlog_size_and_target_date(self) -> None:
        body = _body(backlog_size=20, target_date=date(2026, 12, 1))
        with pytest.raises(ValueError, match="exactly one"):
            _compute_forecast(body)

    def test_rejects_neither_backlog_size_nor_target_date(self) -> None:
        body = _body()
        with pytest.raises(ValueError, match="exactly one"):
            _compute_forecast(body)

    def test_rejects_neither_history_nor_linear_fields(self) -> None:
        body = ForecastRequestBody(period_days=7, backlog_size=20)
        with pytest.raises(ValueError, match="exactly one"):
            _compute_forecast(body)

    def test_rejects_both_history_and_linear_fields(self) -> None:
        body = ForecastRequestBody(
            history=[3, 5, 4, 6, 2, 5],
            period_days=7,
            backlog_size=20,
            linear_api_key="lin_api_test",
            linear_team_id="team-123",
        )
        with pytest.raises(ValueError, match="exactly one"):
            _compute_forecast(body)

    def test_rejects_linear_api_key_without_team_id(self) -> None:
        """A bare linear_api_key (nothing else given) must not be reported via the
        generic "none provided" message - it names the actual problem:
        linear_team_id is missing, not that nothing was supplied at all."""
        body = ForecastRequestBody(period_days=7, backlog_size=20, linear_api_key="lin_api_test")
        with pytest.raises(ValueError, match="linear_team_id") as exc_info:
            _compute_forecast(body)
        assert "not both or neither" not in str(exc_info.value)

    def test_rejects_linear_team_id_without_api_key(self) -> None:
        body = ForecastRequestBody(period_days=7, backlog_size=20, linear_team_id="team-123")
        with pytest.raises(ValueError, match="linear_api_key") as exc_info:
            _compute_forecast(body)
        assert "not both or neither" not in str(exc_info.value)

    def test_linear_fields_call_fetch_linear_throughput(self) -> None:
        body = ForecastRequestBody(
            period_days=7,
            backlog_size=20,
            seed=42,
            linear_api_key="lin_api_test",
            linear_team_id="team-123",
            linear_periods=26,
        )
        mocked_history = ThroughputHistory(
            completed_per_period=[3, 5, 4, 6, 2, 5], period_duration=timedelta(days=7)
        )
        with patch(
            "agile_metrics.web.fetch_linear_throughput", return_value=mocked_history
        ) as mocked_fetch:
            result = _compute_forecast(body)

        mocked_fetch.assert_called_once_with(
            api_key="lin_api_test",
            team_id="team-123",
            period_duration=timedelta(days=7),
            periods=26,
        )
        assert all(isinstance(v, date) for v in result.outcomes.values())


class TestForecastEndpointUS1:
    """User Story 1 (P1): completion-date forecast via the HTTP API."""

    def test_returns_dates_at_all_confidence_levels(self) -> None:
        response = client.post(
            "/api/forecast", json={**_HISTORY_BODY, "backlog_size": 20, "seed": 42}
        )
        assert response.status_code == 200
        outcomes = response.json()["outcomes"]
        assert set(outcomes) == {"50", "70", "85", "95"}
        for value in outcomes.values():
            date.fromisoformat(value)  # raises if not a valid date string

    def test_same_seed_is_reproducible(self) -> None:
        body = {**_HISTORY_BODY, "backlog_size": 20, "seed": 42}
        first = client.post("/api/forecast", json=body)
        second = client.post("/api/forecast", json=body)
        assert first.json() == second.json()

    def test_rejects_zero_backlog_size(self) -> None:
        response = client.post("/api/forecast", json={**_HISTORY_BODY, "backlog_size": 0})
        assert response.status_code == 400
        assert "error" in response.json()


class TestForecastEndpointUS2:
    """User Story 2 (P2): items-completed forecast via the HTTP API."""

    def test_returns_item_counts_at_all_confidence_levels(self) -> None:
        response = client.post(
            "/api/forecast",
            json={**_HISTORY_BODY, "target_date": "2026-12-01", "seed": 42},
        )
        assert response.status_code == 200
        outcomes = response.json()["outcomes"]
        assert set(outcomes) == {"50", "70", "85", "95"}
        assert all(isinstance(value, int) for value in outcomes.values())

    def test_rejects_target_date_not_in_future(self) -> None:
        response = client.post("/api/forecast", json={**_HISTORY_BODY, "target_date": "2020-01-01"})
        assert response.status_code == 400
        assert "error" in response.json()


class TestForecastEndpointUS3:
    """User Story 3 (P3): clear errors for bad/contradictory input via the HTTP API."""

    def test_rejects_both_backlog_size_and_target_date(self) -> None:
        response = client.post(
            "/api/forecast",
            json={**_HISTORY_BODY, "backlog_size": 20, "target_date": "2026-12-01"},
        )
        assert response.status_code == 400
        assert "exactly one" in response.json()["error"]

    def test_rejects_insufficient_history_naming_the_problem(self) -> None:
        response = client.post(
            "/api/forecast", json={"history": [1, 2, 3], "period_days": 7, "backlog_size": 20}
        )
        assert response.status_code == 400
        assert "historical periods" in response.json()["error"]

    def test_rejects_all_zero_history_naming_the_problem(self) -> None:
        response = client.post(
            "/api/forecast",
            json={
                "history": [0, 0, 0, 0, 0, 0],
                "period_days": 7,
                "backlog_size": 20,
            },
        )
        assert response.status_code == 400
        assert "zero" in response.json()["error"]


class TestForecastEndpointLinearMode:
    """T017 (US1): POST /api/forecast in Linear mode matches manual paste."""

    def test_linear_mode_returns_the_same_shape_as_manual_paste(self) -> None:
        mocked_history = ThroughputHistory(
            completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3], period_duration=timedelta(days=7)
        )
        with patch("agile_metrics.web.fetch_linear_throughput", return_value=mocked_history):
            linear_response = client.post(
                "/api/forecast",
                json={
                    "period_days": 7,
                    "backlog_size": 20,
                    "seed": 42,
                    "linear_api_key": "lin_api_test",
                    "linear_team_id": "team-123",
                },
            )
        manual_response = client.post(
            "/api/forecast", json={**_HISTORY_BODY, "backlog_size": 20, "seed": 42}
        )

        assert linear_response.status_code == 200
        assert linear_response.json()["outcomes"] == manual_response.json()["outcomes"]

    def test_linear_error_returns_400_with_its_message(self) -> None:
        from agile_metrics.linear_client import LinearAuthenticationError

        with patch(
            "agile_metrics.web.fetch_linear_throughput", side_effect=LinearAuthenticationError()
        ):
            response = client.post(
                "/api/forecast",
                json={
                    "period_days": 7,
                    "backlog_size": 20,
                    "linear_api_key": "lin_api_bad",
                    "linear_team_id": "team-123",
                },
            )

        assert response.status_code == 400
        assert response.json() == {"error": "Linear API key is invalid or expired"}


class TestForecastEndpointLinearErrors:
    """T031/T032 (US3): every distinct Linear-side failure produces its own specific
    message through the web API, and the two reused-validator cases keep the existing
    (non-Linear-specific) messages unchanged."""

    _LINEAR_BODY = {
        "period_days": 7,
        "backlog_size": 20,
        "linear_api_key": "lin_api_test",
        "linear_team_id": "team-123",
    }

    @staticmethod
    def _post_with_fetch_error(exc: Exception) -> object:
        with patch("agile_metrics.web.fetch_linear_throughput", side_effect=exc):
            return client.post("/api/forecast", json=TestForecastEndpointLinearErrors._LINEAR_BODY)

    def test_team_not_found_names_the_team(self) -> None:
        from agile_metrics.linear_client import LinearTeamNotFoundError

        response = self._post_with_fetch_error(LinearTeamNotFoundError("team-123"))
        assert response.status_code == 400
        assert response.json() == {
            "error": "Linear team 'team-123' was not found or is not accessible with this API key"
        }

    def test_rate_limited_names_the_problem(self) -> None:
        from agile_metrics.linear_client import LinearRateLimitedError

        response = self._post_with_fetch_error(LinearRateLimitedError())
        assert response.status_code == 400
        assert response.json() == {"error": "Linear API rate limit exceeded - try again later"}

    def test_api_unavailable_names_the_problem(self) -> None:
        from agile_metrics.linear_client import LinearAPIUnavailableError

        response = self._post_with_fetch_error(LinearAPIUnavailableError())
        assert response.status_code == 400
        assert response.json() == {"error": "Linear API is currently unavailable - try again later"}

    def test_zero_completed_issues_reuses_the_existing_all_zero_message(self) -> None:
        try:
            ThroughputHistory(completed_per_period=[0] * 6, period_duration=timedelta(days=7))
        except ValidationError as exc:
            zero_history_error = exc

        response = self._post_with_fetch_error(zero_history_error)
        assert response.status_code == 400
        assert "zero" in response.json()["error"]

    def test_too_few_periods_reuses_the_existing_message(self) -> None:
        try:
            ThroughputHistory(completed_per_period=[1, 2, 3], period_duration=timedelta(days=7))
        except ValidationError as exc:
            too_few_error = exc

        response = self._post_with_fetch_error(too_few_error)
        assert response.status_code == 400
        assert "historical periods" in response.json()["error"]


class TestForecastEndpointChartFields:
    """T011 (spec 005): reference_date/distribution/projection pass through the
    API unchanged from the library, and existing fields stay as they were."""

    def test_backlog_mode_response_includes_chart_fields(self) -> None:
        response = client.post(
            "/api/forecast", json={**_HISTORY_BODY, "backlog_size": 20, "seed": 42}
        )
        assert response.status_code == 200
        body = response.json()

        assert set(body["outcomes"]) == {"50", "70", "85", "95"}
        assert body["trials_run"] == 10_000
        assert body["periods_used"] == 8

        date.fromisoformat(body["reference_date"])
        assert 1 <= len(body["distribution"]) <= 60
        for bucket in body["distribution"]:
            date.fromisoformat(bucket["lower"])
            date.fromisoformat(bucket["upper"])
            assert bucket["trials"] >= 0
        assert sum(bucket["trials"] for bucket in body["distribution"]) == body["trials_run"]

        assert len(body["projection"]) >= 1
        for index, point in enumerate(body["projection"], start=1):
            assert point["period"] == index
            date.fromisoformat(point["period_end"])
            assert set(point["cumulative"]) == {"50", "70", "85", "95"}

    def test_target_date_mode_response_includes_chart_fields(self) -> None:
        response = client.post(
            "/api/forecast",
            json={**_HISTORY_BODY, "target_date": "2026-12-01", "seed": 42},
        )
        assert response.status_code == 200
        body = response.json()

        assert all(isinstance(value, int) for value in body["outcomes"].values())
        for bucket in body["distribution"]:
            assert isinstance(bucket["lower"], int)
            assert isinstance(bucket["upper"], int)
        assert body["projection"][-1]["cumulative"] == body["outcomes"]

    def test_existing_fields_match_the_library_for_the_same_seed(self) -> None:
        body = {**_HISTORY_BODY, "backlog_size": 20, "seed": 42}
        response = client.post("/api/forecast", json=body)

        expected = _compute_forecast(_body(backlog_size=20, seed=42))
        outcomes = response.json()["outcomes"]
        assert outcomes == {str(k): str(v) for k, v in expected.outcomes.items()}
        assert response.json()["trials_run"] == expected.trials_run
        assert response.json()["periods_used"] == expected.periods_used


class TestForecastCsvEndpoint:
    """T009 (US1): POST /api/forecast/csv - a dedicated multipart endpoint,
    separate from the JSON POST /api/forecast (plan.md "Decisions confirmed" §1)."""

    def _csv_text(self) -> str:
        return _csv_text_for_counts(_CSV_COUNTS, _CSV_TODAY, period_days=7)

    def test_pasted_text_returns_the_same_outcomes_as_manual_paste(self) -> None:
        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = _CSV_TODAY
            csv_response = client.post(
                "/api/forecast/csv",
                data={"period_days": "7", "backlog_size": "20", "seed": "42"},
                files={"csv_text": (None, self._csv_text())},
            )
        manual_response = client.post(
            "/api/forecast",
            json={**_HISTORY_BODY, "backlog_size": 20, "seed": 42},
        )
        assert csv_response.status_code == 200
        assert csv_response.json()["outcomes"] == manual_response.json()["outcomes"]
        assert csv_response.json()["history"] == _CSV_COUNTS

    def test_uploaded_file_returns_the_same_outcomes_as_pasted_text(self) -> None:
        with patch("agile_metrics.csv_item_import.date") as mock_date:
            mock_date.today.return_value = _CSV_TODAY
            file_response = client.post(
                "/api/forecast/csv",
                data={"period_days": "7", "backlog_size": "20", "seed": "42"},
                files={"csv_file": ("items.csv", self._csv_text(), "text/csv")},
            )
        assert file_response.status_code == 200
        assert file_response.json()["history"] == _CSV_COUNTS

    def test_rejects_neither_csv_file_nor_csv_text(self) -> None:
        response = client.post(
            "/api/forecast/csv",
            data={"period_days": "7", "backlog_size": "20"},
        )
        assert response.status_code == 400
        assert "exactly one" in response.json()["error"]

    def test_rejects_both_csv_file_and_csv_text(self) -> None:
        response = client.post(
            "/api/forecast/csv",
            data={"period_days": "7", "backlog_size": "20"},
            files={
                "csv_file": ("items.csv", self._csv_text(), "text/csv"),
                "csv_text": (None, self._csv_text()),
            },
        )
        assert response.status_code == 400
        assert "exactly one" in response.json()["error"]

    def test_reuses_the_existing_backlog_size_target_date_exactly_one_of_check(self) -> None:
        response = client.post(
            "/api/forecast/csv",
            data={"period_days": "7"},
            files={"csv_text": (None, self._csv_text())},
        )
        assert response.status_code == 400
        assert "exactly one" in response.json()["error"]

    def test_malformed_csv_returns_400_with_its_message(self) -> None:
        response = client.post(
            "/api/forecast/csv",
            data={"period_days": "7", "backlog_size": "20"},
            files={"csv_text": (None, "id,type,title,start_date\n1,story,Bad,2026-08-01\n")},
        )
        assert response.status_code == 400
        assert "end_date" in response.json()["error"]


class TestCsvErrorsEndToEnd:
    """T023/T024 (US3): every distinct CSV-side failure produces its own specific
    message through the web API, and the two reused-validator cases keep the existing
    (non-CSV-specific) messages unchanged."""

    _ARGS = {"period_days": "7", "backlog_size": "20"}

    @staticmethod
    def _post_with_csv_text(csv_text: str) -> object:
        return client.post(
            "/api/forecast/csv",
            data=TestCsvErrorsEndToEnd._ARGS,
            files={"csv_text": (None, csv_text)},
        )

    def test_blank_id_names_the_row_and_field(self) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,,2026-08-05\n"
            ",story,Blank id,,2026-08-12\n"
        )
        response = self._post_with_csv_text(csv_text)
        assert response.status_code == 400
        assert "row 2" in response.json()["error"]
        assert "id" in response.json()["error"]

    def test_malformed_start_date_names_the_row_and_field(self) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,,2026-08-05\n"
            "2,story,Bad start,not-a-date,2026-08-12\n"
        )
        response = self._post_with_csv_text(csv_text)
        assert response.status_code == 400
        assert "row 2" in response.json()["error"]
        assert "start_date" in response.json()["error"]

    def test_malformed_end_date_names_the_row_and_field(self) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,,2026-08-05\n"
            "2,story,Bad end,,not-a-date\n"
        )
        response = self._post_with_csv_text(csv_text)
        assert response.status_code == 400
        assert "row 2" in response.json()["error"]
        assert "end_date" in response.json()["error"]

    def test_zero_items_with_any_end_date_reuses_the_existing_all_zero_message(self) -> None:
        csv_text = (
            "id,type,title,start_date,end_date\n"
            "1,story,First,2026-09-01,\n"
            "2,story,Second,2026-09-05,\n"
        )
        response = self._post_with_csv_text(csv_text)
        assert response.status_code == 400
        assert "zero" in response.json()["error"]

    def test_narrow_date_range_reuses_the_existing_too_few_periods_message(self) -> None:
        today = date.today()
        csv_text = (
            "id,type,title,start_date,end_date\n"
            f"1,story,First,,{today.isoformat()}\n"
            f"2,story,Second,,{today.isoformat()}\n"
        )
        response = self._post_with_csv_text(csv_text)
        assert response.status_code == 400
        assert "historical periods" in response.json()["error"]
