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

    def test_strips_an_https_scheme_from_the_site(self) -> None:
        connection = _connection(site="https://acme.atlassian.net")
        assert connection.site == "acme.atlassian.net"

    def test_strips_an_http_scheme_from_the_site(self) -> None:
        connection = _connection(site="http://acme.atlassian.net")
        assert connection.site == "acme.atlassian.net"

    def test_strips_a_trailing_slash_left_by_a_pasted_browser_url(self) -> None:
        connection = _connection(site="https://acme.atlassian.net/")
        assert connection.site == "acme.atlassian.net"

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
    key: str = "ENG-1",
    status_name: str = "Done",
    created: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "fields": {
            "resolutiondate": resolved,
            "issuetype": {"name": "Story", "subtask": subtask, "hierarchyLevel": hierarchy_level},
            "status": {"name": status_name},
            "created": created,
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


def _flow_issue(
    key: str,
    *,
    status_name: str,
    resolved: str | None,
    histories: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issue = _issue(
        resolved, key=key, status_name=status_name, created="2026-08-01T00:00:00.000+0000"
    )
    return issue, histories


def _status_history(created: str, to_status: str) -> dict[str, Any]:
    return {"created": created, "items": [{"field": "status", "toString": to_status}]}


class TestComputeJiraFlowMetrics:
    """T018 (spec 011): the full orchestration, end to end with HTTP mocked."""

    def _mock_sequence(
        self,
        issues_and_histories: list[tuple[dict[str, Any], list[dict[str, Any]]]],
        in_progress: list[str] = ["In Progress"],  # noqa: B006
    ) -> list[Any]:
        statuses_payload = _statuses_payload(
            ("To Do", "new"), ("In Progress", "indeterminate"), ("Done", "done")
        )
        issues = [pair[0] for pair in issues_and_histories]
        flow_search = _response({"issues": issues, "isLast": True})
        changelog_search = _response(
            {
                "issues": [
                    {"key": issue["key"], "changelog": {"histories": histories}}
                    for issue, histories in issues_and_histories
                ],
                "isLast": True,
            }
        )
        return [_response(statuses_payload), flow_search, changelog_search]

    def test_mixed_resolved_and_in_progress_issues(self) -> None:
        resolved_with_start, h1 = _flow_issue(
            "ENG-1",
            status_name="Done",
            resolved="2026-09-10T00:00:00.000+0000",
            histories=[_status_history("2026-09-01T00:00:00.000+0000", "In Progress")],
        )
        resolved_without_start, h2 = _flow_issue(
            "ENG-2", status_name="Done", resolved="2026-09-11T00:00:00.000+0000", histories=[]
        )
        in_progress_issue, h3 = _flow_issue(
            "ENG-3",
            status_name="In Progress",
            resolved=None,
            histories=[_status_history("2026-09-20T00:00:00.000+0000", "In Progress")],
        )
        sequence = self._mock_sequence(
            [(resolved_with_start, h1), (resolved_without_start, h2), (in_progress_issue, h3)]
        )
        with patch("agile_metrics.jira_client.urlopen", side_effect=sequence):
            result = jira_client.compute_jira_flow_metrics(
                _connection(periods=6), ["Done"], today=_TODAY
            )

        assert len(result.cycle_time) == 1
        assert result.cycle_time[0].key == "ENG-1"
        assert result.cycle_time[0].started_at == date(2026, 9, 1)
        assert result.cycle_time[0].resolved_at == date(2026, 9, 10)
        assert len(result.wip) == 1
        assert result.wip[0].key == "ENG-3"
        assert result.excluded_count == 1  # ENG-2: no in-progress transition
        assert result.capped_count == 0

    def test_wip_is_sorted_oldest_first(self) -> None:
        newer, h1 = _flow_issue(
            "ENG-1",
            status_name="In Progress",
            resolved=None,
            histories=[_status_history("2026-10-01T00:00:00.000+0000", "In Progress")],
        )
        older, h2 = _flow_issue(
            "ENG-2",
            status_name="In Progress",
            resolved=None,
            histories=[_status_history("2026-09-01T00:00:00.000+0000", "In Progress")],
        )
        sequence = self._mock_sequence([(newer, h1), (older, h2)])
        with patch("agile_metrics.jira_client.urlopen", side_effect=sequence):
            result = jira_client.compute_jira_flow_metrics(
                _connection(periods=6), ["Done"], today=_TODAY
            )
        assert [snapshot.key for snapshot in result.wip] == ["ENG-2", "ENG-1"]

    def test_more_than_500_eligible_issues_are_capped(self) -> None:
        pairs = [
            _flow_issue(
                f"ENG-{i}",
                status_name="In Progress",
                resolved=None,
                histories=[_status_history("2026-09-01T00:00:00.000+0000", "In Progress")],
            )
            for i in range(501)
        ]
        statuses_payload = _statuses_payload(
            ("To Do", "new"), ("In Progress", "indeterminate"), ("Done", "done")
        )
        issues = [pair[0] for pair in pairs]
        flow_search = _response({"issues": issues, "isLast": True})
        changelog_search = _response(
            {
                "issues": [
                    {"key": issue["key"], "changelog": {"histories": histories}}
                    for issue, histories in pairs[:500]
                ],
                "isLast": True,
            }
        )
        with patch(
            "agile_metrics.jira_client.urlopen",
            side_effect=[_response(statuses_payload), flow_search, changelog_search],
        ):
            result = jira_client.compute_jira_flow_metrics(
                _connection(periods=6), ["Done"], today=_TODAY
            )
        assert len(result.wip) == 500
        assert result.capped_count == 1

    def test_flow_state_counts_invariant_holds(self) -> None:
        resolved, h1 = _flow_issue(
            "ENG-1",
            status_name="Done",
            resolved="2026-09-10T00:00:00.000+0000",
            histories=[_status_history("2026-09-01T00:00:00.000+0000", "In Progress")],
        )
        in_progress_issue, h2 = _flow_issue(
            "ENG-2",
            status_name="In Progress",
            resolved=None,
            histories=[_status_history("2026-09-20T00:00:00.000+0000", "In Progress")],
        )
        sequence = self._mock_sequence([(resolved, h1), (in_progress_issue, h2)])
        with patch("agile_metrics.jira_client.urlopen", side_effect=sequence):
            result = jira_client.compute_jira_flow_metrics(
                _connection(periods=6), ["Done"], today=_TODAY
            )
        tracked_total = len(result.cycle_time) + len(result.wip)
        for count in result.flow_state_counts:
            assert count.not_started + count.in_progress + count.done == tracked_total


class TestResolveStartDate:
    """T016 (spec 011): the first transition into an in-progress-category status is
    the start date (research §1, spec Edge Cases - "first entry, not most recent")."""

    def _entry(self, created: str, from_status: str, to_status: str) -> dict[str, Any]:
        return {
            "created": created,
            "items": [{"field": "status", "fromString": from_status, "toString": to_status}],
        }

    def test_first_transition_into_in_progress_is_the_start_date(self) -> None:
        histories = [
            self._entry("2026-09-01T00:00:00.000+0000", "To Do", "In Progress"),
            self._entry("2026-09-10T00:00:00.000+0000", "In Progress", "Done"),
        ]
        result = jira_client._resolve_start_date(histories, ["In Progress", "In Review"])
        assert result == date(2026, 9, 1)

    def test_an_issue_that_left_and_re_entered_progress_uses_the_first_entry(self) -> None:
        histories = [
            self._entry("2026-09-01T00:00:00.000+0000", "To Do", "In Progress"),
            self._entry("2026-09-03T00:00:00.000+0000", "In Progress", "To Do"),
            self._entry("2026-09-08T00:00:00.000+0000", "To Do", "In Progress"),
        ]
        result = jira_client._resolve_start_date(histories, ["In Progress"])
        assert result == date(2026, 9, 1)

    def test_a_transition_into_a_different_in_progress_status_name_still_counts(self) -> None:
        histories = [self._entry("2026-09-01T00:00:00.000+0000", "To Do", "In Review")]
        result = jira_client._resolve_start_date(histories, ["In Progress", "In Review"])
        assert result == date(2026, 9, 1)

    def test_no_in_progress_transition_returns_none(self) -> None:
        histories = [self._entry("2026-09-01T00:00:00.000+0000", "To Do", "Done")]
        result = jira_client._resolve_start_date(histories, ["In Progress"])
        assert result is None

    def test_no_history_entries_returns_none(self) -> None:
        assert jira_client._resolve_start_date([], ["In Progress"]) is None

    def test_a_non_status_field_change_is_ignored(self) -> None:
        histories = [
            {"created": "2026-09-01T00:00:00.000+0000", "items": [{"field": "assignee"}]},
        ]
        assert jira_client._resolve_start_date(histories, ["In Progress"]) is None


class TestFetchChangelogs:
    """T012 (spec 011, revised 2026-10-07 - live finding): bundled expand=changelog
    is rejected outright by `/search/jql` with a 400, not a per-issue omission
    within an otherwise-successful response - confirmed live against a real Jira
    Cloud site (research §1's flagged uncertainty resolved: the community reports
    describing bundling were for the older `/search` endpoint, not this one).
    Both the per-issue-omission path (defensive, in case a future API version
    behaves that way) and the whole-request-fails path (the one that actually
    happens today) are covered."""

    def test_empty_keys_makes_no_request(self) -> None:
        with patch("agile_metrics.jira_client.urlopen") as m:
            result = jira_client._fetch_changelogs(_connection(), [])
        assert result == {}
        m.assert_not_called()

    def test_uses_the_bundled_changelog_when_present(self) -> None:
        history_entry = {"created": "2026-09-05T00:00:00.000+0000", "items": []}
        page = {
            "issues": [
                {"key": "ENG-1", "changelog": {"histories": [history_entry]}},
            ],
            "isLast": True,
        }
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(page)) as m:
            result = jira_client._fetch_changelogs(_connection(), ["ENG-1"])
        assert result == {"ENG-1": [history_entry]}
        assert m.call_count == 1  # one search request, nothing per-issue

    def test_requests_changelog_expansion(self) -> None:
        page = {"issues": [{"key": "ENG-1", "changelog": {"histories": []}}], "isLast": True}
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(page)) as m:
            jira_client._fetch_changelogs(_connection(), ["ENG-1"])
        body = json.loads(m.call_args.args[0].data)
        assert body["expand"] == ["changelog"]
        assert "ENG-1" in body["jql"]

    def test_falls_back_to_a_per_issue_call_when_changelog_is_absent(self) -> None:
        search_page = {"issues": [{"key": "ENG-1"}], "isLast": True}  # no "changelog" key
        fallback_entry = {"created": "2026-09-05T00:00:00.000+0000", "items": []}
        fallback = {"values": [fallback_entry], "isLast": True}
        with patch(
            "agile_metrics.jira_client.urlopen",
            side_effect=[_response(search_page), _response(fallback)],
        ) as m:
            result = jira_client._fetch_changelogs(_connection(), ["ENG-1"])
        assert result == {"ENG-1": [fallback_entry]}
        assert m.call_count == 2
        fallback_request = m.call_args_list[1].args[0]
        assert fallback_request.full_url.endswith("/rest/api/3/issue/ENG-1/changelog")

    def test_missing_issues_key_raises_api_unavailable(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", return_value=_response({"isLast": True})):
            with pytest.raises(jira_client.JiraAPIUnavailableError):
                jira_client._fetch_changelogs(_connection(), ["ENG-1"])

    def test_falls_back_to_per_issue_for_every_key_when_the_bundled_request_itself_fails(
        self,
    ) -> None:
        """Live finding, 2026-10-07: the bundled request fails outright (400), not
        a per-issue omission within a 200 - every key falls back individually."""
        fallback_one = {
            "values": [{"created": "2026-09-01T00:00:00.000+0000", "items": []}],
            "isLast": True,
        }
        fallback_two = {
            "values": [{"created": "2026-09-02T00:00:00.000+0000", "items": []}],
            "isLast": True,
        }
        with patch(
            "agile_metrics.jira_client.urlopen",
            side_effect=[_http_error(400), _response(fallback_one), _response(fallback_two)],
        ) as m:
            result = jira_client._fetch_changelogs(_connection(), ["ENG-1", "ENG-2"])
        assert set(result) == {"ENG-1", "ENG-2"}
        assert m.call_count == 3  # 1 failed bundled attempt + 2 per-issue fallbacks
        assert m.call_args_list[1].args[0].full_url.endswith("/rest/api/3/issue/ENG-1/changelog")
        assert m.call_args_list[2].args[0].full_url.endswith("/rest/api/3/issue/ENG-2/changelog")


class TestFetchFlowIssues:
    """T010 (spec 011, revised 2026-10-07): one query covers every currently-done
    issue and every currently-in-progress issue together (research §2). No
    `resolved >=` filter at all now - see `_build_flow_jql`'s docstring for why."""

    def test_query_combines_done_and_in_progress_clauses(self) -> None:
        page = {"issues": [], "isLast": True}
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(page)) as m:
            jira_client._fetch_flow_issues(_connection(periods=4), ["Done"], ["In Progress"])
        jql = json.loads(m.call_args.args[0].data)["jql"]
        assert jql == 'project = "ENG" AND (status in ("Done") OR status in ("In Progress"))'
        assert "resolved" not in jql

    def test_query_omits_the_or_clause_when_no_in_progress_statuses_exist(self) -> None:
        page = {"issues": [], "isLast": True}
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(page)) as m:
            jira_client._fetch_flow_issues(_connection(), ["Done"], [])
        jql = json.loads(m.call_args.args[0].data)["jql"]
        assert jql == 'project = "ENG" AND status in ("Done")'

    def test_requests_the_created_field(self) -> None:
        page = {"issues": [], "isLast": True}
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(page)) as m:
            jira_client._fetch_flow_issues(_connection(), ["Done"], ["In Progress"])
        fields = json.loads(m.call_args.args[0].data)["fields"]
        assert "created" in fields
        assert "resolutiondate" in fields

    def test_follows_next_page_token_until_is_last(self) -> None:
        first = {
            "issues": [_issue("2026-10-01T00:00:00.000+0000")],
            "nextPageToken": "tok-2",
            "isLast": False,
        }
        second = {"issues": [_issue("2026-10-02T00:00:00.000+0000")], "isLast": True}
        with patch(
            "agile_metrics.jira_client.urlopen", side_effect=[_response(first), _response(second)]
        ):
            issues = jira_client._fetch_flow_issues(_connection(), ["Done"], ["In Progress"])
        assert len(issues) == 2

    def test_missing_issues_key_raises_api_unavailable(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", return_value=_response({"isLast": True})):
            with pytest.raises(jira_client.JiraAPIUnavailableError):
                jira_client._fetch_flow_issues(_connection(), ["Done"], ["In Progress"])


class TestFetchStatusCategories:
    """T006 (spec 011): one call returns every status name mapped to its category,
    shared by both _detect_done_statuses and _detect_in_progress_statuses."""

    def test_returns_every_status_mapped_to_its_category(self) -> None:
        payload = _statuses_payload(
            ("To Do", "new"), ("In Progress", "indeterminate"), ("Done", "done")
        )
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            result = jira_client._fetch_status_categories(_connection())
        assert result == {"To Do": "new", "In Progress": "indeterminate", "Done": "done"}

    def test_a_name_appearing_in_two_issue_types_keeps_its_category(self) -> None:
        payload = [
            {"name": "Story", "statuses": [{"name": "Done", "statusCategory": {"key": "done"}}]},
            {"name": "Bug", "statuses": [{"name": "Done", "statusCategory": {"key": "done"}}]},
        ]
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            result = jira_client._fetch_status_categories(_connection())
        assert result == {"Done": "done"}

    def test_403_is_reported_as_project_not_found(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(403)):
            with pytest.raises(jira_client.JiraProjectNotFoundError):
                jira_client._fetch_status_categories(_connection())

    def test_404_is_reported_as_project_not_found(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", side_effect=_http_error(404)):
            with pytest.raises(jira_client.JiraProjectNotFoundError):
                jira_client._fetch_status_categories(_connection())


class TestDetectInProgressStatuses:
    """T008 (spec 011): the indeterminate-category statuses, not an error when absent."""

    def test_returns_only_names_whose_category_is_indeterminate(self) -> None:
        payload = _statuses_payload(
            ("To Do", "new"), ("In Progress", "indeterminate"), ("Done", "done")
        )
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            result = jira_client._detect_in_progress_statuses(_connection())
        assert result == ["In Progress"]

    def test_multiple_names_can_share_the_in_progress_category(self) -> None:
        payload = _statuses_payload(
            ("In Progress", "indeterminate"), ("In Review", "indeterminate"), ("Done", "done")
        )
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            result = jira_client._detect_in_progress_statuses(_connection())
        assert result == ["In Progress", "In Review"]

    def test_no_in_progress_statuses_returns_an_empty_list_not_an_error(self) -> None:
        payload = _statuses_payload(("To Do", "new"), ("Done", "done"))
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(payload)):
            result = jira_client._detect_in_progress_statuses(_connection())
        assert result == []


class TestBucketing:
    """T010 (revised 2026-10-07): pure date-arithmetic bucketing against a
    today-anchored window (research §5, clarification Q5). Parsing and UTC
    conversion now happen in the caller (`_resolve_issue_completion`), not here -
    `_bucket_resolved` takes already-resolved `date` objects (the fix below)."""

    def test_issue_in_the_most_recent_period(self) -> None:
        counts = jira_client._bucket_resolved(
            [date(2026, 9, 30)], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 0, 1]

    def test_issue_exactly_one_period_back_lands_in_the_previous_bucket(self) -> None:
        counts = jira_client._bucket_resolved(
            [date(2026, 9, 29)], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 1, 0]

    def test_issue_without_a_completion_date_is_excluded(self) -> None:
        counts = jira_client._bucket_resolved([None], periods=4, period_days=7, today=_TODAY)
        assert counts == [0, 0, 0, 0]

    def test_issue_older_than_the_window_is_excluded(self) -> None:
        counts = jira_client._bucket_resolved(
            [date(2026, 7, 1)], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 0, 0]

    def test_issue_resolved_after_today_is_excluded(self) -> None:
        counts = jira_client._bucket_resolved(
            [date(2026, 10, 7)], periods=4, period_days=7, today=_TODAY
        )
        assert counts == [0, 0, 0, 0]


class TestResolveCompletionDate:
    """Fix (2026-10-07, found via live testing against a real Jira Cloud trial):
    `resolutiondate` is not reliably set just because an issue's status reached a
    `done` category - a plain drag-and-drop move on a team-managed Kanban board
    (Jira's own default new-project type) can leave it null. The most *recent*
    changelog transition into a done-category status is used instead when needed -
    not the first, so a mistaken move that's later corrected doesn't permanently
    fix the completion date to the wrong moment (user's own reasoning)."""

    def _entry(self, created: str, to_status: str) -> dict[str, Any]:
        return {"created": created, "items": [{"field": "status", "toString": to_status}]}

    def test_most_recent_done_transition_is_used(self) -> None:
        histories = [
            self._entry("2026-09-01T00:00:00.000+0000", "Done"),
            self._entry("2026-09-05T00:00:00.000+0000", "To Do"),  # moved back by mistake
            self._entry("2026-09-10T00:00:00.000+0000", "Done"),  # corrected
        ]
        assert jira_client._resolve_completion_date(histories, ["Done"]) == date(2026, 9, 10)

    def test_no_done_transition_returns_none(self) -> None:
        histories = [self._entry("2026-09-01T00:00:00.000+0000", "In Progress")]
        assert jira_client._resolve_completion_date(histories, ["Done"]) is None

    def test_no_history_entries_returns_none(self) -> None:
        assert jira_client._resolve_completion_date([], ["Done"]) is None


class TestResolveIssueCompletion:
    """The hybrid: `resolutiondate` when Jira set it (cheap, the common case),
    the changelog otherwise (research §1 correction)."""

    def test_uses_resolutiondate_when_present_with_no_extra_request(self) -> None:
        issue = _issue("2026-09-05T12:00:00.000+0000")
        with patch("agile_metrics.jira_client.urlopen") as m:
            result = jira_client._resolve_issue_completion(_connection(), issue, ["Done"])
        assert result == date(2026, 9, 5)
        m.assert_not_called()

    def test_falls_back_to_changelog_when_resolutiondate_is_none(self) -> None:
        issue = _issue(None)
        changelog = {
            "values": [
                {
                    "created": "2026-09-05T00:00:00.000+0000",
                    "items": [{"field": "status", "toString": "Done"}],
                }
            ],
            "isLast": True,
        }
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(changelog)) as m:
            result = jira_client._resolve_issue_completion(_connection(), issue, ["Done"])
        assert result == date(2026, 9, 5)
        request = m.call_args.args[0]
        assert request.full_url.endswith("/rest/api/3/issue/ENG-1/changelog")


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
            issues = jira_client._fetch_resolved_issues(_connection(), ["Done"])
        assert len(issues) == 2
        second_request_body = json.loads(m.call_args_list[1].args[0].data)
        assert second_request_body["nextPageToken"] == "tok-2"

    def test_missing_issues_key_raises_api_unavailable(self) -> None:
        with patch("agile_metrics.jira_client.urlopen", return_value=_response({"isLast": True})):
            with pytest.raises(jira_client.JiraAPIUnavailableError):
                jira_client._fetch_resolved_issues(_connection(), ["Done"])

    def test_query_restricts_to_project_and_done_statuses_only(self) -> None:
        """Fix (2026-10-07): no `resolved >=` clause at all - that field can't be
        trusted for filtering (see TestResolveCompletionDate above), so every
        currently-done issue is fetched and dated by the caller instead."""
        page = {"issues": [], "isLast": True}
        with patch("agile_metrics.jira_client.urlopen", return_value=_response(page)) as m:
            jira_client._fetch_resolved_issues(_connection(periods=4), ["Done", "Released"])
        jql = json.loads(m.call_args.args[0].data)["jql"]
        assert jql == 'project = "ENG" AND status in ("Done", "Released")'
        assert "resolved" not in jql


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
                _issue(None),  # no resolutiondate - falls back to changelog (empty: excluded)
            ],
            "isLast": True,
        }
        changelog_fallback = {"values": [], "isLast": True}
        responses = [
            _response(identity),
            _response(statuses),
            _response(page),
            _response(changelog_fallback),
        ]
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
