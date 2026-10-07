# Agile Metrics

A Monte Carlo forecasting tool for agile teams: given a history of completed work, it
answers the two questions teams ask most — **"when will this backlog be done?"** and
**"how much will be done by this date?"** — as a range of outcomes with confidence levels,
not a single promised number.

It covers similar ground to tools like [predictability-engine](https://github.com/cbroult/predictability-engine),
but is an independent, clean-room implementation — see the project constitution for why.

## Status

Ten features are implemented, tested, and passing the full constitution Quality Gate
suite: the throughput-forecasting library (`forecast_by_items`/`forecast_by_date`), a CLI +
Docker image wrapping it, a React web UI + FastAPI JSON API as a second presentation layer
over the same library, a Tailwind CSS visual redesign of that UI, four forecast charts
(distribution, probability curve, burn-up, throughput run chart) built from the library's
output, Linear as an alternative, automatic source for the history both surfaces consume
(with a team identifiable by name or key, not just its raw ID), CSV import as a third,
zero-integration source for the same history, a Jira Cloud source that counts resolved work
from a project's own workflow, a precision warning that flags forecasts whose confidence
interval is too wide to plan against, regardless of data source or mode, and three
diagnostic flow-metrics views (cycle time, aging WIP, cumulative flow) for Jira-sourced
forecasts. See:

- [`.specify/memory/constitution.md`](.specify/memory/constitution.md) — project principles, tech stack, and workflow rules
- [`specs/001-throughput-forecast/`](specs/001-throughput-forecast/) — spec, plan, research, and data model for the forecasting library
- [`specs/002-forecast-cli/`](specs/002-forecast-cli/) — spec, plan, and contracts for the CLI and container image
- [`specs/003-forecast-web-ui/`](specs/003-forecast-web-ui/) — spec, plan, and contracts for the web UI
- [`specs/004-web-ui-styling/`](specs/004-web-ui-styling/) — spec, plan, and design tokens for the Tailwind CSS redesign
- [`specs/005-forecast-charts/`](specs/005-forecast-charts/) — spec, plan, research, and data model for the forecast charts
- [`specs/006-linear-integration/`](specs/006-linear-integration/) — spec, plan, research, and data model for Linear as a data source
- [`specs/007-csv-item-import/`](specs/007-csv-item-import/) — spec, plan, research, and data model for CSV item import
- [`specs/008-linear-team-lookup/`](specs/008-linear-team-lookup/) — spec, plan, research, and data model for Linear team lookup by name or key
- [`specs/009-forecast-precision-warning/`](specs/009-forecast-precision-warning/) — spec, plan, research, and data model for the forecast precision warning
- [`specs/010-jira-integration/`](specs/010-jira-integration/) — spec, plan, research, and contracts for Jira Cloud as a data source
- [`specs/011-jira-flow-metrics/`](specs/011-jira-flow-metrics/) — spec, plan, research, and contracts for cycle-time, aging-WIP, and cumulative-flow metrics
- [`specs/012-cycle-time-scatterplot/`](specs/012-cycle-time-scatterplot/) — spec, plan, research, and contracts for the cycle-time scatterplot and the aging-WIP risk threshold

## How it works

Rather than extrapolating a single average velocity, a forecast is produced by repeatedly
resampling your historical throughput (with replacement) thousands of times to simulate
many possible futures, then reporting outcomes at the 50th/70th/85th/95th percentiles. No
assumption is made about the shape of your team's throughput distribution.

If the 50%-to-95% spread of those outcomes is wide enough that the result isn't practically
useful for planning (for example, years apart for a date-based forecast), every surface -
CLI, web UI, and JSON API - adds a plain-language warning naming how much wider the
pessimistic case is than the typical one, right alongside the four confidence levels. This
is advisory only: the full forecast is always computed and shown, never hidden or gated,
and there's nothing to configure - it's derived entirely from the forecast's own output.

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
[Linear integration](#linear-integration) below. It can also be replaced with a local CSV
file via `--csv-file items.csv` — see [CSV import](#csv-import) below.

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

`--linear-team`/the web UI's Linear team field also accepts a team's **name** (e.g.
`Engineering`) or short **key** (e.g. `ENG`) instead of its raw ID — resolved
automatically, case-insensitively. A value matching more than one team names every
candidate so you can pick a more specific one; a raw ID always continues to work exactly as
before. See [`specs/008-linear-team-lookup/`](specs/008-linear-team-lookup/) for details.

`--linear-api-key` is also accepted as a flag directly, instead of the environment
variable; exactly one of `--history` or (`--linear-api-key` and `--linear-team`) is
required.

Web UI: switch the "Data source" toggle on the form from "Manual paste" to "Linear" and
enter the API key and team — the same four confidence levels and charts render afterward.

See [`specs/006-linear-integration/`](specs/006-linear-integration/) for the full request/
response contract and error-message table (invalid credential, inaccessible team, rate
limiting, and API unavailability each produce a distinct, actionable message).

### CSV import

A third way to populate the history, with no live integration at all: a CSV of per-item
records (`id, type, title, start_date, end_date` — matching
[predictability-engine](https://github.com/cbroult/predictability-engine)'s format for easy
comparison data). Only `end_date` is used for forecasting today; `start_date` is accepted
and retained for a future item-level flow-metrics feature (cycle time, aging WIP, CFD) to
reuse without a CSV-shape change.

CLI:

```bash
uv run agile-metrics --csv-file items.csv --period-days 7 --backlog-size 20
```

Web UI: switch the "Data source" toggle to "CSV" and either upload a file or paste CSV
text — both reach the same `POST /api/forecast/csv` endpoint (a dedicated
`multipart/form-data` endpoint, separate from the JSON `POST /api/forecast` the other two
data sources use, so a real file upload needs no client-side text conversion).

An item still in progress (a blank `end_date`) is accepted, not rejected — it's simply
excluded from the throughput count. A row with a missing required column, a blank `id`, or
a malformed date produces an error naming the specific row and column at fault. See
[`specs/007-csv-item-import/`](specs/007-csv-item-import/) for the full contract.

### Jira integration

Jira Cloud can be used as a data source, so the history is read from a project's resolved
issues instead of being typed in. Authentication is an Atlassian account email plus an API
token (create one at <https://id.atlassian.com/manage-profile/security/api-tokens>). Jira
Server and Data Center are not supported yet.

```bash
export AGILE_METRICS_JIRA_API_TOKEN=...   # keep the token out of shell history
uv run agile-metrics --jira-site acme.atlassian.net --jira-email you@example.com \
  --jira-project ENG --period-days 7 --backlog-size 50 --seed 42
```

- Counts resolved issues in the project over the lookback window (`--jira-periods`, default 26).
- Done statuses are read from the project's own workflow, so custom completion statuses count.
  The output names the statuses that were used.
- Epics and sub-tasks are not counted. Each issue is counted in the UTC period of its
  resolution date.
- The token is used only for the request. It is never stored, logged, or echoed in an error.

See [`specs/010-jira-integration/`](specs/010-jira-integration/) for the full contract.

Jira forecasts also get three flow-metrics views, alongside the existing throughput
forecast and its four charts - diagnostic, retrospective views of the team's actual flow,
not a replacement for the forecast:

- **Cycle time**: a scatterplot of every resolved issue's cycle time (resolution date
  against days from when it first entered an in-progress status), with reference lines
  at the historical 50/70/85/95% confidence levels - the same levels, computed the same
  way, as the forecast's own outcomes - so a service-level expectation can be read
  directly off the chart.
- **Aging work in progress**: every issue currently in progress, oldest first, with the
  historical 85th-percentile cycle time overlaid as a threshold - any item that's already
  taken longer than that is visually flagged as at risk.
- **Cumulative flow**: how many issues were not started, in progress, and done each day
  over the lookback window (a simplified three-band view, not a full multi-state workflow
  diagram - nothing in this system tracks that history).

"In progress" is detected the same way "done" is - from the project's own workflow status
categories, not a hard-coded name. An issue that was never in progress before resolution is
excluded from these views, and the response/CLI output say so. At most 500 issues are
fetched for flow metrics per request (the changelog lookup behind cycle time is
significantly more expensive than the throughput fetch); any excess is reported, not
silently dropped. The percentile lines and threshold are only shown once there are at
least 5 resolved issues to compute them from - below that, cycle time still plots every
point, just without a misleadingly precise line. CSV and Linear support are planned,
incremental follow-ups, not available yet. See
[`specs/011-jira-flow-metrics/`](specs/011-jira-flow-metrics/) and
[`specs/012-cycle-time-scatterplot/`](specs/012-cycle-time-scatterplot/) for the full
contract.

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
