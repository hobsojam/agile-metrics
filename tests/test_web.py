"""Tests for the forecast web API (T008-T009 Foundational, T016-T018 US1,
T022-T023 US2, T027-T028 US3)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

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
        response = client.post(
            "/api/forecast", json={**_HISTORY_BODY, "target_date": "2020-01-01"}
        )
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
