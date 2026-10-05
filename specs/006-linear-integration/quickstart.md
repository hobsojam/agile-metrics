# Quickstart: Linear Integration

Validates that Linear-backed forecasting works end-to-end, without regressing the existing
manual-paste path. Needs a real Linear workspace with a personal API key and at least one
team with completed issues spanning a few periods to fully exercise — scenarios 1-3 use a
mocked HTTP layer and need no real Linear access; scenarios 6-7 do.

## Prerequisites

- `uv sync` at the repo root; `npm ci` in `frontend/`
- For scenarios 6-7 only: a real Linear personal API key (Linear → Settings → Security &
  Access → Personal API keys) and a team id

## 1. Query shape and pagination (mocked)

```bash
uv run pytest tests/test_linear_client.py -k "query or pagination" -v
```

Expected: the built query matches research.md §2's shape, and a multi-page mocked response
(`hasNextPage: true` then `false`) is fully concatenated — no issues dropped (FR-009).

## 2. Error classification (mocked)

```bash
uv run pytest tests/test_linear_client.py -k "error" -v
```

Expected: a mocked 401/`AUTHENTICATION_ERROR` response raises `LinearAuthenticationError`; a
mocked `RATELIMITED` response (HTTP 400 — research.md §3) raises `LinearRateLimitedError`; a
mocked team-not-found response raises `LinearTeamNotFoundError`; a simulated connection
failure raises `LinearAPIUnavailableError`. None of these exceptions' messages contain the
API key used in the mocked call (FR-006).

## 3. Reuses existing validation for zero/sparse history (mocked)

```bash
uv run pytest tests/test_linear_client.py -k "all_zero or too_few" -v
```

Expected: a mocked response with zero completed issues raises `pydantic.ValidationError`
with the *same* message `test_models.py` already pins for an all-zero manually-entered
history — not a new, Linear-specific error (FR-010).

## 4. CLI, Linear mode (mocked)

```bash
uv run pytest tests/test_cli.py -k linear -v
```

Expected: `agile-metrics --linear-api-key ... --linear-team ... --backlog-size 20` prints
the same output format as manual-paste mode, with the HTTP layer mocked to return a known
set of completion dates.

## 5. Web API, Linear mode (mocked)

```bash
uv run pytest tests/test_web.py -k linear -v
```

Expected: `POST /api/forecast` with `linear_api_key`/`linear_team_id` instead of `history`
returns the same 200 response shape as manual paste, with the HTTP layer mocked.

## 6. Real Linear API, CLI (needs a real key + team)

```bash
export AGILE_METRICS_LINEAR_API_KEY=lin_api_...
uv run agile-metrics --linear-team <team-id> --period-days 7 --backlog-size 20
```

Expected: a real forecast, populated from your team's actual completed issues — compare it
by eye against `https://linear.app` to sanity-check the throughput numbers look right.

## 7. Real Linear API, web UI (needs a real key + team)

```bash
uv run uvicorn agile_metrics.web:app --reload
cd frontend && npm run dev
```

Switch the form to Linear mode, enter the key and team, submit, and confirm a forecast
renders exactly like the manual-paste path does — plus the same four charts from spec 005,
unmodified by this feature.

## 8. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
cd frontend && npm run lint && npm run typecheck && npm test && npm audit
```

Expected: everything passes.
