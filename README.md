# Agile Metrics

A Monte Carlo forecasting tool for agile teams: given a history of completed work, it
answers the two questions teams ask most — **"when will this backlog be done?"** and
**"how much will be done by this date?"** — as a range of outcomes with confidence levels,
not a single promised number.

It covers similar ground to tools like [predictability-engine](https://github.com/cbroult/predictability-engine),
but is an independent, clean-room implementation — see the project constitution for why.

## Status

Six features are implemented, tested, and passing the full constitution Quality Gate
suite: the throughput-forecasting library (`forecast_by_items`/`forecast_by_date`), a CLI +
Docker image wrapping it, a React web UI + FastAPI JSON API as a second presentation layer
over the same library, a Tailwind CSS visual redesign of that UI, four forecast charts
(distribution, probability curve, burn-up, throughput run chart) built from the library's
output, and Linear as an alternative, automatic source for the history both surfaces
consume. See:

- [`.specify/memory/constitution.md`](.specify/memory/constitution.md) — project principles, tech stack, and workflow rules
- [`specs/001-throughput-forecast/`](specs/001-throughput-forecast/) — spec, plan, research, and data model for the forecasting library
- [`specs/002-forecast-cli/`](specs/002-forecast-cli/) — spec, plan, and contracts for the CLI and container image
- [`specs/003-forecast-web-ui/`](specs/003-forecast-web-ui/) — spec, plan, and contracts for the web UI
- [`specs/004-web-ui-styling/`](specs/004-web-ui-styling/) — spec, plan, and design tokens for the Tailwind CSS redesign
- [`specs/005-forecast-charts/`](specs/005-forecast-charts/) — spec, plan, research, and data model for the forecast charts
- [`specs/006-linear-integration/`](specs/006-linear-integration/) — spec, plan, research, and data model for Linear as a data source

## How it works

Rather than extrapolating a single average velocity, a forecast is produced by repeatedly
resampling your historical throughput (with replacement) thousands of times to simulate
many possible futures, then reporting outcomes at the 50th/70th/85th/95th percentiles. No
assumption is made about the shape of your team's throughput distribution.

## Usage

### Command line

```bash
uv sync
uv run agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --backlog-size 20 --seed 42
# Forecast (10000 trials, 8 historical periods):
#   50% confidence: 2026-11-06
#   70% confidence: 2026-11-13
#   85% confidence: 2026-11-13
#   95% confidence: 2026-11-20

uv run agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --target-date 2026-12-01 --seed 42
```

`--history` can be replaced with a [Linear](https://linear.app) personal API key and team,
so the history is fetched automatically from completed issues instead of typed in — see
[Linear integration](#linear-integration) below.

### Container

No local Python installation needed — only a container runtime:

```bash
docker build -t agile-metrics .
docker run --rm agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --backlog-size 20 --seed 42
```

See [`specs/002-forecast-cli/quickstart.md`](specs/002-forecast-cli/quickstart.md) and
[`specs/002-forecast-cli/contracts/cli-interface.md`](specs/002-forecast-cli/contracts/cli-interface.md)
for the full flag/exit-code/output contract.

### Web UI

Backend (serves the API, and the built frontend once `frontend/dist/` exists):

```bash
uv sync
uv run uvicorn agile_metrics.web:app --reload
```

Frontend, for local development (hot-reloads, proxies `/api` to the backend above):

```bash
cd frontend
npm ci
npm run dev
```

Or build everything into the same Docker image the CLI uses, which bundles both the API
and the static frontend — the image's default `ENTRYPOINT` is still the CLI (spec 002's
contract), so the web server needs an explicit override:

```bash
docker build -t agile-metrics .
docker run --rm -p 8000:8000 --entrypoint uvicorn agile-metrics \
  agile_metrics.web:app --host 0.0.0.0 --port 8000
```

If the backend's request/response shapes change, regenerate the frontend's TypeScript
types from its OpenAPI schema and commit the result:

```bash
cd frontend
npm run generate-types
```

See [`specs/003-forecast-web-ui/quickstart.md`](specs/003-forecast-web-ui/quickstart.md) and
[`specs/003-forecast-web-ui/contracts/forecast-api.md`](specs/003-forecast-web-ui/contracts/forecast-api.md)
for the full request/response contract.

After a successful forecast, the web UI also renders four charts built entirely from that
response (no extra request, no re-simulation): an outcome distribution histogram, a
cumulative probability curve, a burn-up with a forecast fan, and a throughput run chart. See
[`specs/005-forecast-charts/`](specs/005-forecast-charts/) for the data model and contract
delta.

### Linear integration

Instead of pasting throughput by hand, both the CLI and the web UI can fetch it
automatically from [Linear](https://linear.app): completed issues in a team are bucketed
into per-period counts (26 periods by default) and fed into the same
`forecast_by_items`/`forecast_by_date` functions, producing identical output to manual
paste. Needs only a personal API key (Linear → Settings → Security & Access → Personal API
keys) — no OAuth app registration.

CLI:

```bash
export AGILE_METRICS_LINEAR_API_KEY=lin_api_...
uv run agile-metrics --linear-team <team-id> --period-days 7 --backlog-size 20
# --linear-periods <n> overrides the 26-period default lookback window
```

`--linear-api-key` is also accepted as a flag directly, instead of the environment
variable; exactly one of `--history` or (`--linear-api-key` and `--linear-team`) is
required.

Web UI: switch the "Data source" toggle on the form from "Manual paste" to "Linear" and
enter the API key and team — the same four confidence levels and charts render afterward.

See [`specs/006-linear-integration/`](specs/006-linear-integration/) for the full request/
response contract and error-message table (invalid credential, inaccessible team, rate
limiting, and API unavailability each produce a distinct, actionable message).

### Library

```python
from datetime import timedelta, date
from agile_metrics import forecast_by_items, forecast_by_date
from agile_metrics.models import ThroughputHistory

history = ThroughputHistory(
    completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3],  # 8 weeks of history
    period_duration=timedelta(days=7),
)

# "When will 20 remaining items be done?"
result = forecast_by_items(history, backlog_size=20, seed=42)
print(result.outcomes)  # {50: date(...), 70: date(...), 85: date(...), 95: date(...)}

# "How many items will be done by December 1st?"
result = forecast_by_date(history, target_date=date(2026, 12, 1), seed=42)
print(result.outcomes)  # {50: int, 70: int, 85: int, 95: int}
```

`ForecastResult` also carries `reference_date`, `distribution` (the simulated outcomes,
grouped for charting), and `projection` (cumulative future items per period at each
confidence level) — all derived from the same simulation run as `outcomes`, for presentation
layers that want more than the four headline numbers (e.g. the web UI's charts above).

See [`specs/001-throughput-forecast/quickstart.md`](specs/001-throughput-forecast/quickstart.md)
for the full walkthrough, including how invalid input is rejected.

## Tech stack

Python 3.11+, managed with [`uv`](https://github.com/astral-sh/uv); `numpy` for simulation,
`pydantic` for data models, `typer` for the CLI, `fastapi`/`uvicorn` for the web API;
`ruff` + `mypy --strict` + `pytest` + `hypothesis` for quality and statistical validation.
Frontend: React + TypeScript + Vite, with request/response types generated from the
backend's own OpenAPI schema (never hand-written, to avoid drift); Tailwind CSS for styling,
Recharts for the forecast charts; `eslint` + `vitest` for its own quality gates. A
multi-stage Dockerfile builds both sides into one container image.
Full details in the constitution's Technology Stack & Quality Gates sections.

## Contributing

This project follows a spec-driven workflow (see `.specify/`) and a project constitution
that governs coding standards, testing requirements, and the git/PR workflow. Read
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) before contributing.

## License

[MIT](LICENSE)
