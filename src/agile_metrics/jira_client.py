"""Jira Cloud integration: fetch a project's resolved-issue throughput as a
`ThroughputHistory` (spec 010), so the web UI and CLI can forecast from Jira
data through the same `forecast_by_items`/`forecast_by_date` path already used
for manual, Linear, and CSV history (Constitution Principle II).

Uses only the standard library for HTTP (research.md §8) - no new runtime
dependency.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, NoReturn
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agile_metrics.models import ThroughputHistory

__all__ = [
    "DEFAULT_LOOKBACK_PERIODS",
    "JiraAPIUnavailableError",
    "JiraAuthenticationError",
    "JiraConnection",
    "JiraIntegrationError",
    "JiraNoDoneStatusesError",
    "JiraProjectNotFoundError",
    "JiraRateLimitedError",
    "JiraSiteUnreachableError",
    "JiraThroughput",
    "fetch_jira_throughput",
]

DEFAULT_LOOKBACK_PERIODS = 26


class JiraIntegrationError(Exception):
    """Base class for every Jira-side failure. `str()` is the final user-facing
    text (contracts/jira-errors.md); it never includes the API token (FR-008)."""


class JiraAuthenticationError(JiraIntegrationError):
    def __init__(self) -> None:
        super().__init__("Jira authentication failed - check the email and API token")


class JiraSiteUnreachableError(JiraIntegrationError):
    def __init__(self, site: str) -> None:
        super().__init__(f"Could not reach a Jira site at '{site}' - check the site address")


class JiraProjectNotFoundError(JiraIntegrationError):
    def __init__(self, project_key: str) -> None:
        super().__init__(
            f"Jira project '{project_key}' was not found or is not visible to this account"
        )


class JiraRateLimitedError(JiraIntegrationError):
    def __init__(self, retry_after: int | None) -> None:
        if retry_after is None:
            message = "Jira is rate-limiting requests - try again later"
        else:
            message = f"Jira is rate-limiting requests - try again in {retry_after} seconds"
        super().__init__(message)


class _HttpForbidden(JiraIntegrationError):
    """Internal marker: a 403 from one request. Callers map it to the category
    that fits (authentication for /myself, not-found for a project call -
    FR-007), so it never reaches a user directly."""


class _HttpNotFound(JiraIntegrationError):
    """Internal marker: a 404 from one request. Callers map it (see above)."""


class JiraAPIUnavailableError(JiraIntegrationError):
    def __init__(self) -> None:
        super().__init__("Jira API is currently unavailable - try again later")


class JiraNoDoneStatusesError(JiraIntegrationError):
    def __init__(self, project_key: str) -> None:
        super().__init__(f"Jira project '{project_key}' has no statuses in the Done category")


@dataclass(frozen=True)
class JiraConnection:
    """Everything one Jira request needs (data-model.md).

    `api_token` is excluded from `repr` (and therefore `str`) so it cannot leak
    into logs or tracebacks by accident (FR-008, research.md §7).
    """

    site: str
    email: str
    api_token: str = field(repr=False)
    project_key: str
    period_days: int
    periods: int = DEFAULT_LOOKBACK_PERIODS

    def __post_init__(self) -> None:
        if not self.site or "://" in self.site or "/" in self.site:
            raise ValueError(
                f"site must be a bare host such as 'acme.atlassian.net', got {self.site!r}"
            )
        if not self.api_token:
            raise ValueError("api_token must not be empty")
        if not self.email or not self.project_key:
            raise ValueError("email and project_key must not be empty")


_TIMEOUT_SECONDS = 30


def _auth_header(connection: JiraConnection) -> str:
    raw = f"{connection.email}:{connection.api_token}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _retry_after(exc: HTTPError) -> int | None:
    value = exc.headers.get("Retry-After") if exc.headers else None
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _map_http_error(connection: JiraConnection, exc: HTTPError) -> NoReturn:
    if exc.code == 401:
        raise JiraAuthenticationError() from None
    if exc.code == 403:
        raise _HttpForbidden() from None
    if exc.code == 404:
        raise _HttpNotFound() from None
    if exc.code == 429:
        raise JiraRateLimitedError(retry_after=_retry_after(exc)) from None
    raise JiraAPIUnavailableError() from None


def _jira_request(
    connection: JiraConnection, method: str, path: str, body: dict[str, Any] | None = None
) -> Any:
    """One authenticated request, returning the decoded JSON value (object or array).

    Every failure is mapped to a Jira exception and raised `from None`, so neither the
    token nor the underlying URLError text can appear in what the caller sees (FR-008).
    """
    data = json.dumps(body).encode() if body is not None else None
    request = Request(
        f"https://{connection.site}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": _auth_header(connection),
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        # The scheme is always https and the site was validated as a bare host in
        # JiraConnection, so this URL cannot be redirected to an arbitrary scheme.
        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310  # nosec B310
            raw = response.read()
    except HTTPError as exc:
        _map_http_error(connection, exc)
    except URLError:
        raise JiraSiteUnreachableError(connection.site) from None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        raise JiraAPIUnavailableError() from None


def _expect_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JiraAPIUnavailableError()
    return value


def _jira_get(connection: JiraConnection, path: str) -> dict[str, Any]:
    return _expect_object(_jira_request(connection, "GET", path))


def _jira_post(connection: JiraConnection, path: str, body: dict[str, Any]) -> dict[str, Any]:
    return _expect_object(_jira_request(connection, "POST", path, body))


_SEARCH_PAGE_SIZE = 100
_SEARCH_FIELDS = ["resolutiondate", "issuetype", "status"]


def _fetch_status_categories(connection: JiraConnection) -> dict[str, str]:
    """Every status name in this project mapped to its category key (`new`,
    `indeterminate`, or `done`) - one call, shared by `_detect_done_statuses` and
    `_detect_in_progress_statuses` (spec 011 research §2). A name appearing in more
    than one issue type keeps whichever category it's classified as (in practice
    the same category every time - Jira's status categories are per-status, not
    per-issue-type)."""
    path = f"/rest/api/3/project/{connection.project_key}/statuses"
    try:
        issue_types = _jira_get_list(connection, path)
    except (_HttpNotFound, _HttpForbidden):
        raise JiraProjectNotFoundError(connection.project_key) from None
    categories: dict[str, str] = {}
    for issue_type in issue_types:
        for status in issue_type.get("statuses", []):
            name = status["name"]
            key = status.get("statusCategory", {}).get("key", "")
            # "done" wins over a conflicting classification elsewhere, preserving
            # _detect_done_statuses' original OR semantics (a name is done if ANY
            # issue type classifies it that way - spec 010 research §3).
            if categories.get(name) != "done":
                categories[name] = key
    return categories


def _detect_done_statuses(connection: JiraConnection) -> list[str]:
    """Names of every status whose category is `done` in this project (research §3).

    A name counts as done if any of the project's issue types classifies it that
    way, so one type's classification cannot hide a done status from another.
    """
    categories = _fetch_status_categories(connection)
    done = sorted(name for name, key in categories.items() if key == "done")
    if not done:
        raise JiraNoDoneStatusesError(connection.project_key)
    return done


def _detect_in_progress_statuses(connection: JiraConnection) -> list[str]:
    """Names of every status whose category is `indeterminate` (Jira's "in progress"
    category) in this project (spec 011). Unlike `_detect_done_statuses`, an empty
    result is not an error - a project with no in-progress statuses still has a
    perfectly good throughput forecast, just nothing to show in the flow-metrics
    views."""
    categories = _fetch_status_categories(connection)
    return sorted(name for name, key in categories.items() if key == "indeterminate")


def _jira_get_list(connection: JiraConnection, path: str) -> list[dict[str, Any]]:
    """GET for an endpoint that returns a JSON array rather than an object."""
    value = _jira_request(connection, "GET", path)
    if not isinstance(value, list):
        raise JiraAPIUnavailableError()
    return value


def _parse_jira_timestamp(value: str) -> datetime:
    """Jira writes offsets as +0000 (no colon) and fractional seconds; accept both
    that and the colon form, with or without fractions."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(value)


def _bucket_resolved(
    resolution_dates: list[str | None],
    *,
    periods: int,
    period_days: int,
    today: date,
) -> list[int]:
    """Count resolutions per period, using the same today-anchored convention as the
    CSV and Linear sources (`csv_item_import._bucket_items`). The date that decides a
    bucket is the UTC date of the timestamp (clarification Q5)."""
    counts = [0] * periods
    for value in resolution_dates:
        if value is None:
            continue
        utc_day = _parse_jira_timestamp(value).astimezone(UTC).date()
        periods_ago = (today - utc_day).days // period_days
        if periods_ago < 0:
            continue
        bucket_index = periods - 1 - periods_ago
        if 0 <= bucket_index < periods:
            counts[bucket_index] += 1
    return counts


def _counts_toward_throughput(issue: dict[str, Any]) -> bool:
    """Epics (hierarchy level 1 and above) and sub-tasks do not count (FR-002, Q1).
    Structural fields are used rather than issue-type names, which are localized and
    customizable (research §4)."""
    issue_type = issue["fields"]["issuetype"]
    if issue_type.get("subtask"):
        return False
    return int(issue_type.get("hierarchyLevel", 0)) < 1


def _fetch_resolved_issues(
    connection: JiraConnection,
    done_statuses: list[str],
    *,
    today: date,
) -> list[dict[str, Any]]:
    """Every issue resolved in the widened window, across all pages (research §1, §5).

    The window is one period wider than the lookback on the old side, because JQL date
    comparisons use the API user's Jira timezone; the exact UTC check happens in
    `_bucket_resolved`.
    """
    window_start = today - timedelta(days=(connection.periods + 1) * connection.period_days)
    statuses = ", ".join('"' + name.replace('"', '\\"') + '"' for name in done_statuses)
    jql = (
        f'project = "{connection.project_key}" AND status in ({statuses}) '
        f'AND resolved >= "{window_start.isoformat()}"'
    )
    issues: list[dict[str, Any]] = []
    next_token: str | None = None
    while True:
        body: dict[str, Any] = {
            "jql": jql,
            "fields": _SEARCH_FIELDS,
            "maxResults": _SEARCH_PAGE_SIZE,
        }
        if next_token is not None:
            body["nextPageToken"] = next_token
        page = _jira_post(connection, "/rest/api/3/search/jql", body)
        if "issues" not in page:
            raise JiraAPIUnavailableError()
        issues.extend(page["issues"])
        next_token = page.get("nextPageToken")
        if page.get("isLast", next_token is None) or next_token is None:
            return issues


_FLOW_SEARCH_FIELDS = ["resolutiondate", "issuetype", "status", "created"]


def _build_flow_jql(
    connection: JiraConnection,
    done_statuses: list[str],
    in_progress_statuses: list[str],
    *,
    today: date,
) -> str:
    """Resolved-in-window issues, plus every currently-in-progress issue regardless
    of age (research §2) - an issue stuck for months is exactly what the aging-WIP
    view exists to surface, so it isn't bounded by the lookback window."""
    window_start = today - timedelta(days=(connection.periods + 1) * connection.period_days)
    done = ", ".join('"' + name.replace('"', '\\"') + '"' for name in done_statuses)
    resolved_clause = f'(status in ({done}) AND resolved >= "{window_start.isoformat()}")'
    if not in_progress_statuses:
        clause = resolved_clause
    else:
        in_progress = ", ".join(
            '"' + name.replace('"', '\\"') + '"' for name in in_progress_statuses
        )
        clause = f"({resolved_clause} OR status in ({in_progress}))"
    return f'project = "{connection.project_key}" AND {clause}'


def _fetch_flow_issues(
    connection: JiraConnection,
    done_statuses: list[str],
    in_progress_statuses: list[str],
    *,
    today: date,
) -> list[dict[str, Any]]:
    """Every issue this feature needs, across all pages (research §2) - cheap: plain
    fields only, no changelog. `_fetch_changelogs` fetches the expensive part
    separately, for at most the first `_FLOW_ISSUE_CAP` of these (research §4)."""
    jql = _build_flow_jql(connection, done_statuses, in_progress_statuses, today=today)
    issues: list[dict[str, Any]] = []
    next_token: str | None = None
    while True:
        body: dict[str, Any] = {
            "jql": jql,
            "fields": _FLOW_SEARCH_FIELDS,
            "maxResults": _SEARCH_PAGE_SIZE,
        }
        if next_token is not None:
            body["nextPageToken"] = next_token
        page = _jira_post(connection, "/rest/api/3/search/jql", body)
        if "issues" not in page:
            raise JiraAPIUnavailableError()
        issues.extend(page["issues"])
        next_token = page.get("nextPageToken")
        if page.get("isLast", next_token is None) or next_token is None:
            return issues


def _fetch_issue_changelog(connection: JiraConnection, issue_key: str) -> list[dict[str, Any]]:
    """Fallback for one issue whose search result didn't carry a bundled changelog
    (research §1). This endpoint's first page only - pagination within one issue's
    own changelog is a rare-enough edge case (very actively re-statused issues) that
    it's left for the live gate (quickstart Scenario 6) to surface if it matters."""
    payload = _jira_get(connection, f"/rest/api/3/issue/{issue_key}/changelog")
    values = payload.get("values")
    if values is None:
        raise JiraAPIUnavailableError()
    return values


def _fetch_changelogs(
    connection: JiraConnection, issue_keys: list[str]
) -> dict[str, list[dict[str, Any]]]:
    """Changelog history entries for each key, preferring one bundled search request
    (`expand: ["changelog"]`) and falling back to a per-issue GET only for a result
    that lacks it (research §1 - the bundling behavior on the new `/search/jql`
    endpoint is unconfirmed until quickstart Scenario 6, so both paths matter)."""
    if not issue_keys:
        return {}
    histories: dict[str, list[dict[str, Any]]] = {}
    quoted_keys = ", ".join(f'"{key}"' for key in issue_keys)
    jql = f"key in ({quoted_keys})"
    next_token: str | None = None
    while True:
        body: dict[str, Any] = {
            "jql": jql,
            "fields": ["key"],
            "expand": ["changelog"],
            "maxResults": _SEARCH_PAGE_SIZE,
        }
        if next_token is not None:
            body["nextPageToken"] = next_token
        page = _jira_post(connection, "/rest/api/3/search/jql", body)
        if "issues" not in page:
            raise JiraAPIUnavailableError()
        for issue in page["issues"]:
            key = issue["key"]
            changelog = issue.get("changelog")
            if changelog is not None:
                histories[key] = changelog.get("histories", [])
            else:
                histories[key] = _fetch_issue_changelog(connection, key)
        next_token = page.get("nextPageToken")
        if page.get("isLast", next_token is None) or next_token is None:
            return histories


@dataclass(frozen=True)
class JiraThroughput:
    """The result of one Jira fetch: the history the forecast consumes, plus the
    done statuses it was built from, so the caller can report them (clarification Q3)."""

    history: ThroughputHistory
    done_statuses: list[str]


def fetch_jira_throughput(
    connection: JiraConnection, *, today: date | None = None
) -> JiraThroughput:
    """Fetch resolved-issue throughput for one project (spec 010).

    `today` is injectable for deterministic tests; it defaults to the current UTC date.
    """
    anchor = today if today is not None else datetime.now(UTC).date()
    try:
        _jira_get(connection, "/rest/api/3/myself")
    except _HttpForbidden:
        raise JiraAuthenticationError() from None
    done_statuses = _detect_done_statuses(connection)
    issues = _fetch_resolved_issues(connection, done_statuses, today=anchor)
    counted = [issue for issue in issues if _counts_toward_throughput(issue)]
    resolution_dates = [issue["fields"].get("resolutiondate") for issue in counted]
    counts = _bucket_resolved(
        resolution_dates,
        periods=connection.periods,
        period_days=connection.period_days,
        today=anchor,
    )
    history = ThroughputHistory(
        completed_per_period=counts,
        period_duration=timedelta(days=connection.period_days),
    )
    return JiraThroughput(history=history, done_statuses=done_statuses)
