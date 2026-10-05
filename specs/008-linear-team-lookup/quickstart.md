# Quickstart: Linear Team Lookup by Name or Key

Validates that name/key resolution works end-to-end, without regressing raw-ID usage.
Scenarios 1-4 use a mocked HTTP layer and need no real Linear access; scenario 5 does, and
specifically closes the gap research.md §2 flags (the team-listing query's shape was not
independently re-confirmed via live introspection — this is exactly the kind of assumption
that produced this project's two real-API bugs so far, so don't skip this scenario).

## Prerequisites

- `uv sync` at the repo root
- For scenario 5 only: a real Linear personal API key and a workspace with at least one
  team whose name or key you know

## 1. UUID-format detection

```bash
uv run pytest tests/test_linear_client.py -k "looks_like_linear_id" -v
```

Expected: a UUID-shaped string is detected as a raw ID; a team name, a team key, and an
empty string are not.

## 2. Team-listing pagination

```bash
uv run pytest tests/test_linear_client.py -k "fetch_all_teams" -v
```

Expected: a multi-page mocked response (`hasNextPage: true` then `false`) is fully
concatenated — no teams dropped (FR-008), mirroring 006's issues-pagination guarantee.

## 3. Name/key matching and error classification

```bash
uv run pytest tests/test_linear_client.py -k "resolve_team_id" -v
```

Expected: an exact case-insensitive match on a team's name or key resolves to its ID; zero
matches raises the *existing* `LinearTeamNotFoundError` message unchanged; more than one
match raises `LinearTeamAmbiguousError` naming every candidate as `"name (key)"`.

## 4. Raw-ID path is untouched

```bash
uv run pytest tests/test_linear_client.py -k "unchanged_for_a_raw_id" -v
```

Expected: a UUID-shaped `team_id` reaches `_validate_team` with **zero** team-listing calls
made first — confirms US3's "exact same code path, not just equivalent behavior" guarantee.

## 5. Real Linear API: resolve by name and by key

```bash
export AGILE_METRICS_LINEAR_API_KEY=lin_api_...
uv run agile-metrics --linear-team "<a real team's exact name>" --period-days 7 --backlog-size 20
uv run agile-metrics --linear-team "<that same team's key>" --period-days 7 --backlog-size 20
```

Expected: both commands produce the identical forecast you'd get from
`--linear-team <that team's raw ID>` (spec SC-001/SC-002). This is the first live exercise
of the team-listing query's actual shape — if it fails with a schema-validation error
(matching the same failure pattern that originally motivated this feature's parent bug
fixes), treat that as a real finding, not a flake, and fix the query shape before merging.

## 6. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
```

Expected: everything passes.
