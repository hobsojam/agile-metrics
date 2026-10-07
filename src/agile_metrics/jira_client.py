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


def _detect_done_statuses(connection: JiraConnection) -> list[str]:
    """Names of every status whose category is `done` in this project (research §3).

    A name counts as done if any of the project's issue types classifies it that
    way, so one type's classification cannot hide a done status from another.
    """
    path = f"/rest/api/3/project/{connection.project_key}/statuses"
    try:
        issue_types = _jira_get_list(connection, path)
    except (_HttpNotFound, _HttpForbidden):
        raise JiraProjectNotFoundError(connection.project_key) from None
    done = {
        status["name"]
        for issue_type in issue_types
        for status in issue_type.get("statuses", [])
        if status.get("statusCategory", {}).get("key") == "done"
    }
    if not done:
        raise JiraNoDoneStatusesError(connection.project_key)
    return sorted(done)


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
    completion_dates: list[date | None],
    *,
    periods: int,
    period_days: int,
    today: date,
) -> list[int]:
    """Count completions per period, using the same today-anchored convention as
    the CSV and Linear sources (`csv_item_import._bucket_items`).

    Takes already-resolved `date` objects, not raw timestamp strings (fix,
    2026-10-07): parsing and UTC conversion (clarification Q5) now happen once, in
    `_resolve_issue_completion`, since a completion date can come from either
    `resolutiondate` or a changelog entry - this function just buckets whatever it's
    given.
    """
    counts = [0] * periods
    for completion_date in completion_dates:
        if completion_date is None:
            continue
        periods_ago = (today - completion_date).days // period_days
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
) -> list[dict[str, Any]]:
    """Every issue currently in a done-category status, across all pages (research
    §1, §5; corrected 2026-10-07 - see below).

    No `resolved >=` window filter at the JQL level any more. Live testing against
    a real Jira Cloud trial found that `resolutiondate` is not reliably set just
    because an issue's status category became `done` - a plain drag-and-drop move
    on a team-managed Kanban board (Jira's own default new-project type) can leave
    it null, with no "Resolution" field even exposed in that board's issue view to
    set it manually. Filtering on that field at query time would silently exclude
    exactly the issues this bug affects. Every currently-done issue is fetched
    instead (no date filter), and the caller (`fetch_jira_throughput`) resolves
    each one's actual completion date itself (`_resolve_issue_completion`) before
    bucketing - the window exclusion then happens naturally in `_bucket_resolved`.
    """
    statuses = ", ".join('"' + name.replace('"', '\\"') + '"' for name in done_statuses)
    jql = f'project = "{connection.project_key}" AND status in ({statuses})'
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


def _fetch_issue_changelog(connection: JiraConnection, issue_key: str) -> list[dict[str, Any]]:
    """One issue's changelog history entries, for the fallback path when
    `resolutiondate` is absent (fix, 2026-10-07). This endpoint's first page only -
    pagination within one issue's own changelog is a rare-enough edge case (very
    actively re-statused issues) that it's left for live testing to surface if it
    ever matters in practice."""
    payload = _jira_get(connection, f"/rest/api/3/issue/{issue_key}/changelog")
    values = payload.get("values")
    if not isinstance(values, list):
        raise JiraAPIUnavailableError()
    return values


def _resolve_completion_date(
    histories: list[dict[str, Any]], done_statuses: list[str]
) -> date | None:
    """The *most recent* changelog entry that transitions the issue's status into
    one of `done_statuses` (fix, 2026-10-07 - confirmed with the user: most recent,
    not first, so a status moved to the wrong column by mistake and later
    corrected doesn't permanently fix the completion date to the wrong moment).
    `None` when no such entry exists."""
    done = set(done_statuses)
    latest: date | None = None
    for entry in histories:
        for item in entry.get("items", []):
            if item.get("field") != "status":
                continue
            if item.get("toString") not in done:
                continue
            entry_date = _parse_jira_timestamp(entry["created"]).astimezone(UTC).date()
            if latest is None or entry_date > latest:
                latest = entry_date
    return latest


def _resolve_issue_completion(
    connection: JiraConnection, issue: dict[str, Any], done_statuses: list[str]
) -> date | None:
    """`resolutiondate` when Jira set it (cheap - no extra request, the common
    case for projects whose workflow does set it); the changelog's most recent
    done-transition otherwise (fix, 2026-10-07)."""
    resolution_raw = issue["fields"].get("resolutiondate")
    if resolution_raw is not None:
        return _parse_jira_timestamp(resolution_raw).astimezone(UTC).date()
    histories = _fetch_issue_changelog(connection, issue["key"])
    return _resolve_completion_date(histories, done_statuses)


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
    issues = _fetch_resolved_issues(connection, done_statuses)
    counted = [issue for issue in issues if _counts_toward_throughput(issue)]
    completion_dates = [
        _resolve_issue_completion(connection, issue, done_statuses) for issue in counted
    ]
    counts = _bucket_resolved(
        completion_dates,
        periods=connection.periods,
        period_days=connection.period_days,
        today=anchor,
    )
    history = ThroughputHistory(
        completed_per_period=counts,
        period_duration=timedelta(days=connection.period_days),
    )
    return JiraThroughput(history=history, done_statuses=done_statuses)
