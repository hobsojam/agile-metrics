"""Tests for the Linear integration adapter (spec 006).

The HTTP layer (`urllib.request.urlopen`) is mocked throughout - no real
network calls in CI. Query-building, pagination, error classification, and
bucketing are otherwise pure and tested directly.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, timedelta
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest
from pydantic import ValidationError

API_KEY = "lin_api_test_key_should_never_appear_in_errors"


class _FakeResponse:
    """Minimal stand-in for the object `urlopen` returns as a context manager."""

    def __init__(self, body: dict[str, object]) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def mock_urlopen_sequence(
    responses: list[dict[str, object] | Exception],
) -> Callable[..., _FakeResponse]:
    """Returns a function that yields one response per call, in order.

    Each entry is either a JSON-serializable body (200 OK) or an exception
    instance to raise (e.g. `HTTPError`, `URLError`) - lets a single test
    simulate a multi-page fetch, or a failure partway through.
    """
    responses_iter = iter(responses)

    def _fake_urlopen(*_args: object, **_kwargs: object) -> _FakeResponse:
        next_response = next(responses_iter)
        if isinstance(next_response, Exception):
            raise next_response
        return _FakeResponse(next_response)

    return _fake_urlopen


def http_error(status: int, code: str, message: str) -> HTTPError:
    """Build an `HTTPError` whose body matches Linear's GraphQL error shape."""
    body = json.dumps(
        {"errors": [{"message": message, "extensions": {"code": code, "statusCode": status}}]}
    ).encode("utf-8")
    error = HTTPError(
        url="https://api.linear.app/graphql",
        code=status,
        msg=message,
        hdrs=None,
        fp=None,  # type: ignore[arg-type]
    )
    error.read = lambda: body  # type: ignore[method-assign]
    return error


@pytest.fixture
def patched_urlopen():
    """Yields a helper to install a sequence of mocked urlopen responses."""

    def _patch(responses: list[dict[str, object] | Exception]):
        return patch(
            "agile_metrics.linear_client.urlopen", side_effect=mock_urlopen_sequence(responses)
        )

    return _patch


class TestQueryBuilding:
    """T003: query shapes from research.md §2, verified against the live schema."""

    def test_team_query_targets_the_right_team_id(self) -> None:
        from agile_metrics.linear_client import _build_team_query

        body = _build_team_query("team-123")
        assert "team(id: $teamId)" in body["query"]
        assert body["variables"] == {"teamId": "team-123"}

    def test_team_query_declares_team_id_as_string(self) -> None:
        """Confirmed live: the real API rejects `$teamId: ID!` with a
        GRAPHQL_VALIDATION_FAILED 400 ("used in position expecting type
        String!") - Query.team's `id` argument is `String!`, not `ID!`,
        despite `TeamFilter.id` elsewhere in the schema being an ID
        comparator. The mocked tests never caught this; only a real request
        does."""
        from agile_metrics.linear_client import _build_team_query

        body = _build_team_query("team-123")
        assert "$teamId: String!" in body["query"]

    def test_issues_query_filters_by_team_and_completed_date(self) -> None:
        from agile_metrics.linear_client import _build_issues_query

        body = _build_issues_query("team-123", since="2026-04-01T00:00:00Z", after=None)
        assert "completedAt" in body["query"]
        assert "null: false" in body["query"]
        assert "pageInfo" in body["query"]
        assert "hasNextPage" in body["query"]
        assert "endCursor" in body["query"]
        assert body["variables"] == {
            "teamId": "team-123",
            "since": "2026-04-01T00:00:00Z",
            "after": None,
        }

    def test_issues_query_carries_the_pagination_cursor(self) -> None:
        from agile_metrics.linear_client import _build_issues_query

        body = _build_issues_query("team-123", since="2026-04-01T00:00:00Z", after="cursor-abc")
        assert body["variables"]["after"] == "cursor-abc"


def _issues_page(dates: list[str], has_next: bool, end_cursor: str | None) -> dict[str, object]:
    return {
        "data": {
            "issues": {
                "nodes": [{"completedAt": d} for d in dates],
                "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
            }
        }
    }


class TestPagination:
    """T005: no completed issue is dropped across pages (FR-009/FR-010/SC-004)."""

    def test_concatenates_completed_at_values_across_two_pages(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import _fetch_all_completed_at

        page_1 = _issues_page(["2026-04-01T00:00:00Z", "2026-04-02T00:00:00Z"], True, "cursor-1")
        page_2 = _issues_page(["2026-04-03T00:00:00Z"], False, None)

        with patched_urlopen([page_1, page_2]):
            dates = _fetch_all_completed_at(
                api_key=API_KEY, team_id="team-123", since="2026-01-01T00:00:00Z"
            )

        assert dates == [
            "2026-04-01T00:00:00Z",
            "2026-04-02T00:00:00Z",
            "2026-04-03T00:00:00Z",
        ]

    def test_single_page_stops_after_one_call(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import _fetch_all_completed_at

        single_page = _issues_page(["2026-04-01T00:00:00Z"], False, None)

        with patched_urlopen([single_page]):
            dates = _fetch_all_completed_at(
                api_key=API_KEY, team_id="team-123", since="2026-01-01T00:00:00Z"
            )

        assert dates == ["2026-04-01T00:00:00Z"]


class TestErrorClassification:
    """T007: the four detection rules from research.md §3, confirmed live."""

    def test_401_authentication_error_raises_linear_authentication_error(
        self, patched_urlopen
    ) -> None:
        from agile_metrics.linear_client import LinearAuthenticationError, _fetch_all_completed_at

        error = http_error(401, "AUTHENTICATION_ERROR", "Authentication required")
        with patched_urlopen([error]), pytest.raises(LinearAuthenticationError):
            _fetch_all_completed_at(api_key=API_KEY, team_id="team-123", since="2026-01-01")

    def test_400_ratelimited_raises_linear_rate_limited_error(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import LinearRateLimitedError, _fetch_all_completed_at

        error = http_error(400, "RATELIMITED", "Rate limit exceeded")
        with patched_urlopen([error]), pytest.raises(LinearRateLimitedError):
            _fetch_all_completed_at(api_key=API_KEY, team_id="team-123", since="2026-01-01")

    def test_connection_failure_raises_linear_api_unavailable_error(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import LinearAPIUnavailableError, _fetch_all_completed_at

        connection_error = URLError("connection refused")
        with patched_urlopen([connection_error]), pytest.raises(LinearAPIUnavailableError):
            _fetch_all_completed_at(api_key=API_KEY, team_id="team-123", since="2026-01-01")

    def test_server_error_raises_linear_api_unavailable_error(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import LinearAPIUnavailableError, _fetch_all_completed_at

        error = http_error(503, "INTERNAL_ERROR", "Service unavailable")
        with patched_urlopen([error]), pytest.raises(LinearAPIUnavailableError):
            _fetch_all_completed_at(api_key=API_KEY, team_id="team-123", since="2026-01-01")

    def test_missing_team_raises_linear_team_not_found_error(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import LinearTeamNotFoundError, _validate_team

        team_missing = {"data": {"team": None}}
        with patched_urlopen([team_missing]), pytest.raises(LinearTeamNotFoundError):
            _validate_team(api_key=API_KEY, team_id="nonexistent-team")

    def test_accessible_team_passes_validation(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import _validate_team

        team_found = {"data": {"team": {"id": "team-123", "name": "Engineering"}}}
        with patched_urlopen([team_found]):
            _validate_team(api_key=API_KEY, team_id="team-123")  # must not raise


class TestCredentialNeverLeaks:
    """T009 (FR-006): the API key must never appear in any raised exception's
    message, across all four error types."""

    def test_key_absent_from_every_exception_message(self, patched_urlopen) -> None:
        from agile_metrics.linear_client import (
            LinearAPIUnavailableError,
            LinearAuthenticationError,
            LinearRateLimitedError,
            LinearTeamNotFoundError,
            _fetch_all_completed_at,
            _validate_team,
        )

        cases: list[tuple[Exception | dict[str, object], Exception, Callable[[], object]]] = [
            (
                http_error(401, "AUTHENTICATION_ERROR", "Authentication required"),
                LinearAuthenticationError,
                lambda: _fetch_all_completed_at(API_KEY, "team-123", "2026-01-01"),
            ),
            (
                http_error(400, "RATELIMITED", "Rate limit exceeded"),
                LinearRateLimitedError,
                lambda: _fetch_all_completed_at(API_KEY, "team-123", "2026-01-01"),
            ),
            (
                URLError("connection refused"),
                LinearAPIUnavailableError,
                lambda: _fetch_all_completed_at(API_KEY, "team-123", "2026-01-01"),
            ),
            (
                {"data": {"team": None}},
                LinearTeamNotFoundError,
                lambda: _validate_team(API_KEY, "team-123"),
            ),
        ]
        for response, expected_exception_type, call in cases:
            with patched_urlopen([response]), pytest.raises(expected_exception_type) as excinfo:
                call()
            assert API_KEY not in str(excinfo.value)


class TestBucketing:
    """T011: completedAt timestamps -> ThroughputHistory (data-model.md's bucket formula)."""

    _TODAY = date(2026, 10, 5)
    _WEEK = timedelta(days=7)

    def test_buckets_one_issue_per_period_in_order(self) -> None:
        from agile_metrics.linear_client import _bucket_completed_at

        values = [
            "2026-09-10T00:00:00Z",  # bucket 0: [09-07, 09-14)
            "2026-09-16T00:00:00Z",  # bucket 1: [09-14, 09-21)
            "2026-09-25T00:00:00Z",  # bucket 2: [09-21, 09-28)
            "2026-10-01T00:00:00Z",  # bucket 3 (most recent): [09-28, 10-05)
        ]
        counts = _bucket_completed_at(
            values, periods=4, period_duration=self._WEEK, today=self._TODAY
        )
        assert counts == [1, 1, 1, 1]

    def test_multiple_issues_in_the_same_period_are_summed(self) -> None:
        from agile_metrics.linear_client import _bucket_completed_at

        values = ["2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z", "2026-10-03T00:00:00Z"]
        counts = _bucket_completed_at(
            values, periods=4, period_duration=self._WEEK, today=self._TODAY
        )
        assert counts == [0, 0, 0, 3]

    def test_zero_completed_issues_raises_the_existing_all_zero_validation_error(self) -> None:
        from agile_metrics.linear_client import fetch_linear_throughput

        with pytest.raises(ValidationError, match="all zero"):
            with (
                patch("agile_metrics.linear_client._fetch_all_completed_at", return_value=[]),
                patch("agile_metrics.linear_client._validate_team", return_value=None),
            ):
                fetch_linear_throughput(
                    api_key=API_KEY, team_id="team-123", period_duration=self._WEEK, periods=6
                )

    def test_too_few_periods_raises_the_existing_minimum_periods_error(self) -> None:
        from agile_metrics.linear_client import fetch_linear_throughput

        with pytest.raises(ValidationError, match="at least"):
            with (
                patch(
                    "agile_metrics.linear_client._fetch_all_completed_at",
                    return_value=["2026-10-01T00:00:00Z"],
                ),
                patch("agile_metrics.linear_client._validate_team", return_value=None),
            ):
                fetch_linear_throughput(
                    api_key=API_KEY, team_id="team-123", period_duration=self._WEEK, periods=3
                )

    def test_fetch_linear_throughput_returns_a_valid_throughput_history(self) -> None:
        from agile_metrics.linear_client import fetch_linear_throughput

        # periods=6 (MIN_HISTORICAL_PERIODS) so this exercises the real
        # happy path, not the too-few-periods validator from the test above.
        completed = ["2026-09-10T00:00:00Z", "2026-09-16T00:00:00Z", "2026-09-25T00:00:00Z"] + [
            "2026-10-01T00:00:00Z"
        ] * 3
        with (
            patch("agile_metrics.linear_client._fetch_all_completed_at", return_value=completed),
            patch("agile_metrics.linear_client._validate_team", return_value=None),
            patch("agile_metrics.linear_client.date") as mock_date,
        ):
            mock_date.today.return_value = self._TODAY
            history = fetch_linear_throughput(
                api_key=API_KEY, team_id="team-123", period_duration=self._WEEK, periods=6
            )

        assert history.completed_per_period == [0, 0, 1, 1, 1, 3]
        assert history.period_duration == self._WEEK
