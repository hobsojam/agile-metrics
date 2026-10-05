"""Tests for the forecast web API (T008-T009 Foundational, T016-T018 US1,
T022-T023 US2, T027-T028 US3)."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agile_metrics.models import ThroughputHistory
from agile_metrics.web import ForecastRequestBody, _compute_forecast, app

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
        body = ForecastRequestBody(period_days=7, backlog_size=20, linear_api_key="lin_api_test")
        with pytest.raises(ValueError, match="exactly one"):
            _compute_forecast(body)

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
