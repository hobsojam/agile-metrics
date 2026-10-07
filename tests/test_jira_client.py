"""Tests for the Jira Cloud adapter (spec 010). The HTTP layer is mocked throughout."""

import base64
import io
import json
from datetime import date, timedelta
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from agile_metrics import jira_client
from agile_metrics.jira_client import JiraConnection
from agile_metrics.models import ThroughputHistory


def _connection(**overrides: object) -> JiraConnection:
    fields: dict[str, object] = {
        "site": "acme.atlassian.net",
        "email": "dev@example.com",
        "api_token": "secret-token-123",
        "project_key": "ENG",
        "period_days": 7,
    }
    fields.update(overrides)
    return JiraConnection(**fields)  # type: ignore[arg-type]


class TestJiraConnection:
    def test_exposes_the_supplied_fields(self) -> None:
        connection = _connection()
        assert connection.site == "acme.atlassian.net"
        assert connection.email == "dev@example.com"
        assert connection.api_token == "secret-token-123"
        assert connection.project_key == "ENG"
        assert connection.period_days == 7
        assert connection.periods == 26

    def test_repr_and_str_never_contain_the_api_token(self) -> None:
        connection = _connection()
        assert "secret-token-123" not in repr(connection)
        assert "secret-token-123" not in str(connection)

    def test_rejects_a_site_with_a_scheme(self) -> None:
        with pytest.raises(ValueError, match="site"):
            _connection(site="https://acme.atlassian.net")

    def test_rejects_a_site_with_a_path(self) -> None:
        with pytest.raises(ValueError, match="site"):
            _connection(site="acme.atlassian.net/jira")

    def test_rejects_an_empty_api_token(self) -> None:
        with pytest.raises(ValueError, match="api_token"):
            _connection(api_token="")


class TestJiraErrors:
    """T004: each contract category is its own type with the exact contract message."""

    def test_authentication_error_message(self) -> None:
        err = jira_client.JiraAuthenticationError()
        assert str(err) == "Jira authentication failed - check the email and API token"

    def test_site_unreachable_error_names_the_site(self) -> None:
        err = jira_client.JiraSiteUnreachableError("acme.atlassian.net")
        assert str(err) == (
            "Could not reach a Jira site at 'acme.atlassian.net' - check the site address"
        )

    def test_project_not_found_error_message(self) -> None:
        err = jira_client.JiraProjectNotFoundError("ENG")
        assert str(err) == "Jira project 'ENG' was not found or is not visible to this account"

    def test_rate_limited_error_with_retry_after(self) -> None:
        err = jira_client.JiraRateLimitedError(retry_after=30)
        assert str(err) == "Jira is rate-limiting requests - try again in 30 seconds"

    def test_rate_limited_error_without_retry_after(self) -> None:
        err = jira_client.JiraRateLimitedError(retry_after=None)
        assert str(err) == "Jira is rate-limiting requests - try again later"

    def test_api_unavailable_error_message(self) -> None:
        err = jira_client.JiraAPIUnavailableError()
        assert str(err) == "Jira API is currently unavailable - try again later"

    def test_no_done_statuses_error_names_the_project(self) -> None:
        err = jira_client.JiraNoDoneStatusesError("ENG")
        assert str(err) == "Jira project 'ENG' has no statuses in the Done category"

    def test_every_category_subclasses_one_base(self) -> None:
        base = jira_client.JiraIntegrationError
        for cls in (
            jira_client.JiraAuthenticationError,
            jira_client.JiraSiteUnreachableError,
            jira_client.JiraProjectNotFoundError,
            jira_client.JiraRateLimitedError,
            jira_client.JiraAPIUnavailableError,
            jira_client.JiraNoDoneStatusesError,
        ):
            assert issubclass(cls, base)


def _response(payload: object) -> MagicMock:
    mock = MagicMock()
    mock.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return mock


def _http_error(code: int, headers: dict[str, str] | None = None) -> HTTPError:
    return HTTPError(
        url="https://acme.atlassian.net/x",
        code=code,
        msg="err",
        hdrs=headers or {},  # type: ignore[arg-type]
        fp=io.BytesIO(b""),
    )


class TestHttpSeam:
    """T006: request shape and HTTP-status mapping, with urlopen mocked."""

    def test_get_sends_basic_auth_and_decodes_json(self) -> None:
        connection = _connection()
        with patch("agile_metrics.jira_client.urlopen", return_value=_response({"ok": True})) as m:
            result = jira_client._jira_get(connection, "/rest/api/3/myself")
        request = m.call_args.args[0]
        expected = base64.b64encode(b"dev@example.com:secret-token-123").decode()
        assert request.get_header("Authorization") == f"Basic {expected}"
        assert request.full_url == "https://acme.atlassian.net/rest/api/3/myself"
        assert result == {"ok": True}

    def test_post_sends_a_json_body(self) -> None:
        connection = _connection()
        body: dict[str, Any] = {"jql": "project = ENG"}
        with patch(
            "agile_metrics.jira_client.urlopen", return_value=_response({"issues": []})
        ) as m:
            jira_client._jira_post(connection, "/rest/api/3/search/jql", body)
        request = m.call_args.args[0]
        assert request.method == "POST"
        assert json.loads(request.data) == body

    def test_url_error_raises_site_unreachable(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=URLError("no route")):
            with pytest.raises(jira_client.JiraSiteUnreachableError, match="acme.atlassian.net"):
                jira_client._jira_get(_connection(), "/rest/api/3/myself")

    def test_401_raises_authentication_error(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(401)):
            with pytest.raises(jira_client.JiraAuthenticationError):
                jira_client._jira_get(_connection(), "/rest/api/3/myself")

    def test_403_raises_the_forbidden_marker_for_callers_to_map(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(403)):
            with pytest.raises(jira_client._HttpForbidden):
                jira_client._jira_get(_connection(), "/rest/api/3/project/ENG/statuses")

    def test_404_raises_the_not_found_marker_for_callers_to_map(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(404)):
            with pytest.raises(jira_client._HttpNotFound):
                jira_client._jira_get(_connection(), "/rest/api/3/project/ENG/statuses")

    def test_429_raises_rate_limited_with_retry_after(self) -> None:
        error = _http_error(429, {"Retry-After": "30"})
        with patch("agile_metrics.jira_client.urlopen", side_effect=error):
            with pytest.raises(jira_client.JiraRateLimitedError, match="30 seconds"):
                jira_client._jira_get(_connection(), "/rest/api/3/myself")

    def test_429_without_retry_after_says_try_later(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(429)):
            with pytest.raises(jira_client.JiraRateLimitedError, match="try again later"):
                jira_client._jira_get(_connection(), "/rest/api/3/myself")

    def test_5xx_raises_api_unavailable(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(503)):
            with pytest.raises(jira_client.JiraAPIUnavailableError):
                jira_client._jira_get(_connection(), "/rest/api/3/myself")

    def test_non_json_body_raises_api_unavailable(self) -> None:
        mock = MagicMock()
        mock.__enter__.return_value.read.return_value = b"<html>not json</html>"
        with patch("agile_metrics.jira_client.urlopen", return_value=mock):
            with pytest.raises(jira_client.JiraAPIUnavailableError):
                jira_client._jira_get(_connection(), "/rest/api/3/myself")


class TestTokenNeverLeaks:
    """T008: the token is absent from str() of every raised error, even when the
    underlying network error text contains it (FR-008)."""

    @pytest.mark.parametrize(
        "side_effect",
        [
            URLError("connection failed carrying secret-token-123"),
            _http_error(401),
            _http_error(403),
            _http_error(404),
            _http_error(429),
            _http_error(500),
        ],
    )
    def test_token_absent_from_raised_message(self, side_effect: BaseException) -> None:
        connection = _connection(api_token="secret-token-123")
        with patch("agile_metrics.jira_client.urlopen", side_effect=side_effect):
            with pytest.raises(jira_client.JiraIntegrationError) as info:
                jira_client._jira_get(connection, "/rest/api/3/myself")
        assert "secret-token-123" not in str(info.value)
        assert info.value.__cause__ is None
        assert info.value.__suppress_context__ is True


_TODAY = date(2026, 10, 6)


def _statuses_payload(*categories: tuple[str, str]) -> list[dict[str, Any]]:
    """Shape of GET /rest/api/3/project/{key}/statuses: a list of issue types, each
    with its statuses and their statusCategory keys."""
    statuses = [{"name": name, "statusCategory": {"key": key}} for name, key in categories]
    return [{"id": "10001", "name": "Story", "statuses": statuses}]


def _issue(
    resolved: str | None,
    *,
    subtask: bool = False,
    hierarchy_level: int = 0,
) -> dict[str, Any]:
    return {
        "key": "ENG-1",
        "fields": {
            "resolutiondate": resolved,
            "issuetype": {"name": "Story", "subtask": subtask, "hierarchyLevel": hierarchy_level},
            "status": {"name": "Done"},
        },
    }


class TestDetectDoneStatuses:
    """T009: done statuses come from each status's category key, per project (research §3)."""

    def test_returns_only_names_whose_category_is_done(self) -> None:
        payload = _statuses_payload(
            ("To Do", "new"), ("In Progress", "indeterminate"), ("Done", "done")
        )
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            result = jira_client._detect_done_statuses(_connection())
        assert result == ["Done"]

    def test_a_name_done_in_one_issue_type_counts_as_done(self) -> None:
        payload = [
            {
                "name": "Story",
                "statuses": [{"name": "Released", "statusCategory": {"key": "done"}}],
            },
            {
                "name": "Bug",
                "statuses": [{"name": "Released", "statusCategory": {"key": "indeterminate"}}],
            },
        ]
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            assert jira_client._detect_done_statuses(_connection()) == ["Released"]

    def test_project_with_no_done_statuses_raises(self) -> None:
        payload = _statuses_payload(("To Do", "new"), ("In Progress", "indeterminate"))
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            with pytest.raises(jira_client.JiraNoDoneStatusesError, match="ENG"):
                jira_client._detect_done_statuses(_connection())

    def test_403_on_statuses_is_reported_as_project_not_found(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(403)):
            with pytest.raises(jira_client.JiraProjectNotFoundError):
                jira_client._detect_done_statuses(_connection())

    def test_404_on_statuses_is_reported_as_project_not_found(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(404)):
            with pytest.raises(jira_client.JiraProjectNotFoundError):
                jira_client._detect_done_statuses(_connection())


class TestBucketing:
    """T010: UTC bucketing against a today-anchored window (research §5, clarification Q5)."""

    def test_timestamp_is_bucketed_by_its_utc_date_not_its_local_date(self) -> None:
        # 2026-09-29 23:30 at UTC-02:00 is 2026-09-30 01:30 UTC: 6 days before _TODAY.
        # Its local date (29th) would be 7 days before, which is the previous bucket.
        counts = jira_client._bucket_resolved(
            ["2026-09-29T23:30:00.000-0200"], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 0, 1]

    def test_issue_exactly_one_period_back_lands_in_the_previous_bucket(self) -> None:
        counts = jira_client._bucket_resolved(
            ["2026-09-29T12:00:00.000+0000"], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 1, 0]

    def test_issue_without_resolution_date_is_excluded(self) -> None:
        counts = jira_client._bucket_resolved([None], periods=4, period_days=7, today=_TODAY)
        assert counts == [0, 0, 0, 0]

    def test_issue_older_than_the_window_is_excluded(self) -> None:
        counts = jira_client._bucket_resolved(
            ["2026-07-01T12:00:00.000+0000"], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 0, 0]

    def test_issue_resolved_after_today_is_excluded(self) -> None:
        counts = jira_client._bucket_resolved(
            ["2026-10-07T12:00:00.000+0000"], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 0, 0]


class TestIssueTypeExclusion:
    """T011: epics (hierarchy level 1 and above) and sub-tasks are excluded (FR-002, Q1)."""

    def test_sub_tasks_are_excluded(self) -> None:
        assert (
            jira_client._counts_toward_throughput(
                _issue("2026-10-01T00:00:00.000+0000", subtask=True)
            )
            is False
        )

    def test_epics_are_excluded(self) -> None:
        epic = _issue("2026-10-01T00:00:00.000+0000", hierarchy_level=1)
        assert jira_client._counts_toward_throughput(epic) is False

    def test_stories_tasks_and_bugs_are_kept(self) -> None:
        story = _issue("2026-10-01T00:00:00.000+0000", hierarchy_level=0)
        assert jira_client._counts_toward_throughput(story) is True


class TestPagination:
    """T012: cursor pagination over POST /rest/api/3/search/jql (research §1)."""

    def test_follows_next_page_token_until_is_last(self) -> None:
        first = {
            "issues": [_issue("2026-10-01T00:00:00.000+0000")],
            "nextPageToken": "tok-2",
            "isLast": False,
        }
        second = {"issues": [_issue("2026-10-02T00:00:00.000+0000")], "isLast": True}
        with patch(
            "agile_metrics.jira_client.urlopen", side_effect=[_response(first), _response(second)]
        ) as m:
            issues = jira_client._fetch_resolved_issues(_connection(), ["Done"], today=_TODAY)
        assert len(issues) == 2
        second_request_body = json.loads(m.call_args_list[1].args[0].data)
        assert second_request_body["nextPageToken"] == "tok-2"

    def test_missing_issues_key_raises_api_unavailable(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", return_value=_response({"isLast": True})):
            with pytest.raises(jira_client.JiraAPIUnavailableError):
                jira_client._fetch_resolved_issues(_connection(), ["Done"], today=_TODAY)

    def test_query_restricts_to_project_done_statuses_and_widened_window(self) -> None:
        page = {"issues": [], "isLast": True}
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(page)) as m:
            jira_client._fetch_resolved_issues(
                _connection(periods=4), ["Done", "Released"], today=_TODAY
            )
        jql = json.loads(m.call_args.args[0].data)["jql"]
        assert 'project = "ENG"' in jql
        assert 'status in ("Done", "Released")' in jql
        # Widened by one period on the lookback side: 4 periods + 1 = 5 weeks back.
        assert 'resolved >= "2026-09-01"' in jql


class TestFetchJiraThroughputEndToEnd:
    """T013: the public function, HTTP mocked, returns counts and done statuses."""

    def test_returns_history_and_done_statuses(self) -> None:
        identity = {"accountId": "abc"}
        statuses = _statuses_payload(("Done", "done"), ("In Progress", "indeterminate"))
        page = {
            "issues": [
                _issue("2026-10-05T12:00:00.000+0000"),
                _issue("2026-10-05T13:00:00.000+0000"),
                _issue("2026-09-29T12:00:00.000+0000", subtask=True),
                _issue(None),
            ],
            "isLast": True,
        }
        responses = [_response(identity), _response(statuses), _response(page)]
        connection = _connection(period_days=7, periods=6)
        with patch("agile_metrics.jira_client.urlopen", side_effect=responses):
            result = jira_client.fetch_jira_throughput(connection, today=_TODAY)
        assert result.history == ThroughputHistory(
            completed_per_period=[0, 0, 0, 0, 0, 2], period_duration=timedelta(days=7)
        )
        assert result.done_statuses == ["Done"]


class TestFailureCategoriesEndToEnd:
    """T025 + T027 (US2): each failure category through the public function, with the
    exact contract text, and the FR-007 non-disclosure rule."""

    def test_identity_401_raises_authentication_error(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(401)):
            with pytest.raises(jira_client.JiraAuthenticationError) as info:
                jira_client.fetch_jira_throughput(_connection(), today=_TODAY)
        assert str(info.value) == "Jira authentication failed - check the email and API token"

    def test_identity_403_is_also_an_authentication_error(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(403)):
            with pytest.raises(jira_client.JiraAuthenticationError):
                jira_client.fetch_jira_throughput(_connection(), today=_TODAY)

    def test_unreachable_site_names_the_site(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=URLError("dns failure")):
            with pytest.raises(jira_client.JiraSiteUnreachableError) as info:
                jira_client.fetch_jira_throughput(_connection(), today=_TODAY)
        assert "acme.atlassian.net" in str(info.value)

    def test_unknown_project_404_gives_the_contract_message(self) -> None:
        responses = [_response({"accountId": "abc"}), _http_error(404)]
        with patch("agile_metrics.jira_client.urlopen", side_effect=responses):
            with pytest.raises(jira_client.JiraProjectNotFoundError) as info:
                jira_client.fetch_jira_throughput(_connection(), today=_TODAY)
        assert (
            str(info.value) == "Jira project 'ENG' was not found or is not visible to this account"
        )

    def test_rate_limit_429_says_how_long_to_wait(self) -> None:
        responses = [_response({"accountId": "abc"}), _http_error(429, {"Retry-After": "30"})]
        with patch("agile_metrics.jira_client.urlopen", side_effect=responses):
            with pytest.raises(jira_client.JiraRateLimitedError) as info:
                jira_client.fetch_jira_throughput(_connection(), today=_TODAY)
        assert str(info.value) == "Jira is rate-limiting requests - try again in 30 seconds"

    def test_api_unavailable_on_search_names_the_problem(self) -> None:
        responses = [
            _response({"accountId": "abc"}),
            _response(_statuses_payload(("Done", "done"))),
            _http_error(503),
        ]
        with patch("agile_metrics.jira_client.urlopen", side_effect=responses):
            with pytest.raises(jira_client.JiraAPIUnavailableError):
                jira_client.fetch_jira_throughput(_connection(), today=_TODAY)


class TestNonDisclosure:
    """T027 (FR-007): a 403 and a 404 on the project call are indistinguishable to the user."""

    def _message(self, status: int) -> str:
        responses = [_response({"accountId": "abc"}), _http_error(status)]
        with patch("agile_metrics.jira_client.urlopen", side_effect=responses):
            with pytest.raises(jira_client.JiraProjectNotFoundError) as info:
                jira_client.fetch_jira_throughput(_connection(), today=_TODAY)
        return str(info.value)

    def test_403_and_404_produce_the_same_message(self) -> None:
        assert self._message(403) == self._message(404)


class TestParityWithManualHistory:
    """T029 + T030 (US3): identical counts give identical forecasts for the same seed."""

    def test_jira_history_forecasts_identically_to_manual_paste(self) -> None:
        from agile_metrics import forecast_by_items

        counts = [3, 5, 4, 6, 2, 5, 4, 3]
        issues = []
        for index, count in enumerate(counts):
            days_ago = (len(counts) - 1 - index) * 7
            resolved = (_TODAY - timedelta(days=days_ago)).isoformat() + "T12:00:00.000+0000"
            issues.extend(_issue(resolved) for _ in range(count))
        responses = [
            _response({"accountId": "abc"}),
            _response(_statuses_payload(("Done", "done"))),
            _response({"issues": issues, "isLast": True}),
        ]
        connection = _connection(periods=len(counts), period_days=7)
        with patch("agile_metrics.jira_client.urlopen", side_effect=responses):
            jira = jira_client.fetch_jira_throughput(connection, today=_TODAY)

        manual = ThroughputHistory(completed_per_period=counts, period_duration=timedelta(days=7))
        assert jira.history.completed_per_period == counts
        jira_result = forecast_by_items(
            jira.history, backlog_size=20, seed=42, reference_date=_TODAY
        )
        manual_result = forecast_by_items(manual, backlog_size=20, seed=42, reference_date=_TODAY)
        assert jira_result.outcomes == manual_result.outcomes
