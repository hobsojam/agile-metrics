"""Linear integration: fetch a team's completed-issue throughput as a
`ThroughputHistory` (spec 006), so the web UI and CLI can forecast from
Linear data through the exact same `forecast_by_items`/`forecast_by_date`
path already used for manually-entered history (Constitution Principle II).

Uses only the standard library for HTTP (research.md §5) - no new runtime
dependency for the one kind of call this needs.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agile_metrics.models import ThroughputHistory

_ENDPOINT = "https://api.linear.app/graphql"
_PAGE_SIZE = 100

_LINEAR_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

#: ~6 months at weekly granularity - a comfortable margin above
#: MIN_HISTORICAL_PERIODS so a handful of slow periods don't trip
#: ThroughputHistory's own validators by accident (research.md §7).
DEFAULT_LOOKBACK_PERIODS = 26


class LinearIntegrationError(Exception):
    """Base class for every Linear-side failure this module can raise.

    Each subclass's message is the final, user-facing text (data-model.md) -
    callers render `str(exc)` directly, the same pattern already used for
    `ValueError` in `cli.py`/`web.py`. Never includes the API key used for
    the request (FR-006).
    """


class LinearAuthenticationError(LinearIntegrationError):
    def __init__(self) -> None:
        super().__init__("Linear API key is invalid or expired")


class LinearTeamNotFoundError(LinearIntegrationError):
    def __init__(self, team_id: str) -> None:
        super().__init__(
            f"Linear team '{team_id}' was not found or is not accessible with this API key"
        )


class LinearTeamAmbiguousError(LinearIntegrationError):
    def __init__(self, value: str, candidates: list[tuple[str, str]]) -> None:
        formatted = ", ".join(f"{name} ({key})" for name, key in candidates)
        super().__init__(
            f"Linear team '{value}' matches more than one team: {formatted} - "
            f"use a more specific value or the team's ID"
        )


class LinearRateLimitedError(LinearIntegrationError):
    def __init__(self) -> None:
        super().__init__("Linear API rate limit exceeded - try again later")


class LinearAPIUnavailableError(LinearIntegrationError):
    def __init__(self) -> None:
        super().__init__("Linear API is currently unavailable - try again later")


def _looks_like_linear_id(value: str) -> bool:
    """A value shaped like a UUID is treated as a raw Linear team ID and
    skips name/key resolution entirely (research.md §1, 008) - no API call,
    no behavior change for an already-working raw-ID request."""
    return _LINEAR_ID_PATTERN.match(value) is not None


_TEAM_QUERY = """
query($teamId: String!) {
  team(id: $teamId) {
    id
    name
  }
}
"""

_ISSUES_QUERY = """
query($teamId: ID!, $since: DateTimeOrDuration!, $after: String) {
  issues(
    filter: { team: { id: { eq: $teamId } }, completedAt: { gte: $since, null: false } }
    first: 100
    after: $after
  ) {
    nodes {
      completedAt
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

_TEAMS_QUERY = """
query($after: String) {
  teams(first: 100, after: $after) {
    nodes {
      id
      name
      key
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


def _build_team_query(team_id: str) -> dict[str, object]:
    """Validate a team exists and is accessible, before spending a paginated
    fetch on it (research.md §2)."""
    return {"query": _TEAM_QUERY, "variables": {"teamId": team_id}}


def _build_issues_query(team_id: str, since: str, after: str | None) -> dict[str, object]:
    """One page of a team's completed issues, filtered server-side
    (research.md §2)."""
    return {
        "query": _ISSUES_QUERY,
        "variables": {"teamId": team_id, "since": since, "after": after},
    }


def _build_teams_query(after: str | None) -> dict[str, object]:
    """One page of every team accessible to the API key (008 research.md §2)."""
    return {"query": _TEAMS_QUERY, "variables": {"after": after}}


def _post_graphql(api_key: str, body: dict[str, object]) -> dict[str, object]:
    """POST one GraphQL request to Linear, classifying any failure into one
    of the four `LinearIntegrationError` subclasses (research.md §3)."""
    request = Request(
        _ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": api_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 # nosec B310 - fixed https:// endpoint above
            payload: dict[str, object] = json.loads(response.read())
    except HTTPError as exc:
        _raise_for_http_error(exc)
    except URLError as exc:
        raise LinearAPIUnavailableError() from exc

    # A 200 response is not a guarantee of usable data - Linear (like other
    # GraphQL servers) can return `"data": null` alongside a populated
    # `"errors"` array for some failure classes instead of a non-2xx status
    # (contrast with the HTTP-level 400s _raise_for_http_error classifies).
    # Every caller assumes payload["data"][...] is safely subscriptable, so
    # that invariant is enforced once, here, rather than letting a raw
    # TypeError escape from each call site individually.
    if payload.get("data") is None:
        raise LinearAPIUnavailableError()
    return payload


def _raise_for_http_error(exc: HTTPError) -> NoReturn:
    """Classify an HTTP-level failure by Linear's documented error codes
    (research.md §3), confirmed live against the real API. Any status/code
    combination not explicitly recognized falls back to
    `LinearAPIUnavailableError` - from the user's perspective, an
    unrecognized Linear-side failure is still "try again later", not a
    problem with their key or team."""
    if exc.code == 401:
        raise LinearAuthenticationError() from exc
    try:
        payload = json.loads(exc.read())
        code = payload["errors"][0]["extensions"]["code"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        code = None
    if exc.code == 400 and code == "RATELIMITED":
        raise LinearRateLimitedError() from exc
    raise LinearAPIUnavailableError() from exc


def _validate_team(api_key: str, team_id: str) -> None:
    """Confirm the team exists and is accessible with this key, before
    spending a paginated fetch on it (research.md §2)."""
    payload = _post_graphql(api_key, _build_team_query(team_id))
    if payload["data"]["team"] is None:  # type: ignore[index]
        raise LinearTeamNotFoundError(team_id)


def _fetch_all_completed_at(api_key: str, team_id: str, since: str) -> list[str]:
    """Every completed issue's `completedAt` for a team, across every page
    (FR-009/FR-010/SC-004 - nothing silently dropped)."""
    completed_at_values: list[str] = []
    after: str | None = None
    while True:
        body = _build_issues_query(team_id, since, after)
        payload = _post_graphql(api_key, body)
        issues = payload["data"]["issues"]  # type: ignore[index]
        completed_at_values.extend(node["completedAt"] for node in issues["nodes"])
        page_info = issues["pageInfo"]
        if not page_info["hasNextPage"]:
            return completed_at_values
        after = page_info["endCursor"]


def _fetch_all_teams(api_key: str) -> list[tuple[str, str, str]]:
    """Every team accessible to the API key, across every page (008 FR-008 -
    nothing silently dropped), as `(id, name, key)` tuples."""
    teams: list[tuple[str, str, str]] = []
    after: str | None = None
    while True:
        payload = _post_graphql(api_key, _build_teams_query(after))
        result = payload["data"]["teams"]  # type: ignore[index]
        teams.extend((node["id"], node["name"], node["key"]) for node in result["nodes"])
        page_info = result["pageInfo"]
        if not page_info["hasNextPage"]:
            return teams
        after = page_info["endCursor"]


def _bucket_completed_at(
    completed_at_values: list[str],
    periods: int,
    period_duration: timedelta,
    today: date,
) -> list[int]:
    """Bucket `k` (0 = oldest) covers `[today - (periods-k)*period_duration,
    today - (periods-k-1)*period_duration)` (data-model.md). A value outside
    `[0, periods)` periods ago is dropped - it's outside the requested
    window (shouldn't normally happen, since the fetch itself is bounded by
    the same window, but a boundary value right at the cutoff could land
    just outside after rounding)."""
    period_days = period_duration.days
    counts = [0] * periods
    for value in completed_at_values:
        completed_date = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        periods_ago = (today - completed_date).days // period_days
        bucket_index = periods - 1 - periods_ago
        if 0 <= bucket_index < periods:
            counts[bucket_index] += 1
    return counts


def fetch_linear_throughput(
    api_key: str,
    team_id: str,
    period_duration: timedelta,
    periods: int = DEFAULT_LOOKBACK_PERIODS,
) -> ThroughputHistory:
    """Fetch `team_id`'s completed issues from Linear and shape them into a
    `ThroughputHistory` - the same type manual paste already produces
    (FR-003). `ThroughputHistory`'s own validators (not duplicated here)
    reject an all-zero or too-short result exactly as they already do for
    manually-entered history (FR-004/FR-010)."""
    _validate_team(api_key, team_id)
    today = date.today()
    since = f"{(today - periods * period_duration).isoformat()}T00:00:00Z"
    completed_at_values = _fetch_all_completed_at(api_key, team_id, since)
    counts = _bucket_completed_at(completed_at_values, periods, period_duration, today)
    return ThroughputHistory(completed_per_period=counts, period_duration=period_duration)
