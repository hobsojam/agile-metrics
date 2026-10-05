# Data Model: Linear Team Lookup by Name or Key

No new `pydantic` models. `ThroughputHistory`, `ForecastRequest`, `ForecastResult`,
`ForecastRequestBody`, and `Item` are all **unchanged** — this feature's only job is
resolving a `str` to another `str` before the existing flow runs.

## New exception: `LinearTeamAmbiguousError`

Joins `LinearIntegrationError`'s existing hierarchy (006 data-model.md) alongside
`LinearAuthenticationError`, `LinearTeamNotFoundError`, `LinearRateLimitedError`,
`LinearAPIUnavailableError`.

| Field | Type | Meaning |
|---|---|---|
| `value` | `str` | The ambiguous value the user supplied |
| `candidates` | `list[tuple[str, str]]` | Every matching team's `(name, key)`, in the order returned by the team-listing query |

**Message**: `"Linear team '{value}' matches more than one team: {candidates formatted as
'name (key)', comma-separated} - use a more specific value or the team's ID"`.

**Not** a new exception: zero matches raises the *existing* `LinearTeamNotFoundError`
unchanged (research.md §3).

## New functions (not models): `linear_client` module

### `_looks_like_linear_id(value: str) -> bool`

Pure regex match against the UUID shape (research.md §1). No I/O.

### `_build_teams_query(after: str | None) -> dict[str, object]`

One page of the team-listing query (research.md §2), mirroring
`_build_issues_query`'s shape exactly.

### `_fetch_all_teams(api_key: str) -> list[tuple[str, str, str]]`

Every team accessible to the key, across every page — `(id, name, key)` tuples, in the
same "nothing silently dropped" spirit as `_fetch_all_completed_at` (spec FR-008).

### `_resolve_team_id(api_key: str, value: str) -> str`

- If `_looks_like_linear_id(value)`: returns `value` unchanged — **no API call**, no
  resolution attempted at all. (The caller's existing `_validate_team` call immediately
  afterward is what actually confirms it against the live API, exactly as today.)
- Otherwise: calls `_fetch_all_teams`, matches case-insensitively against each team's
  `name`/`key` (research.md §3), and returns the single match's `id`.
- **Raises**: the *existing* `LinearTeamNotFoundError(value)` for zero matches, or the new
  `LinearTeamAmbiguousError(value, candidates)` for more than one.

## Changed function (behavior, not signature): `fetch_linear_throughput`

Signature is **unchanged** — still `fetch_linear_throughput(api_key, team_id,
period_duration, periods=DEFAULT_LOOKBACK_PERIODS) -> ThroughputHistory`. Its body now
calls `team_id = _resolve_team_id(api_key, team_id)` as its first line, before
`_validate_team` — a UUID-shaped `team_id` passes through this call as a no-op (no API
call), so the rest of the function, and every caller in `cli.py`/`web.py`, is unaffected
(spec FR-003/US3, FR-010).

## CLI / web changes

**None.** `--linear-team` and `linear_team_id` keep their exact existing type, help text,
and validation (spec FR-010) — this feature is entirely internal to
`fetch_linear_throughput`'s implementation.
