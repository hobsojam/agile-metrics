# Agile Metrics

A Monte Carlo forecasting tool for agile teams: given a history of completed work, it
answers the two questions teams ask most — **"when will this backlog be done?"** and
**"how much will be done by this date?"** — as a range of outcomes with confidence levels,
not a single promised number.

It covers similar ground to tools like [predictability-engine](https://github.com/cbroult/predictability-engine),
but is an independent, clean-room implementation — see the project constitution for why.

## Status

Two features are implemented, tested, and passing the full constitution Quality Gate
suite: the throughput-forecasting library (`forecast_by_items`/`forecast_by_date`) and a
CLI + Docker image wrapping it. See:

- [`.specify/memory/constitution.md`](.specify/memory/constitution.md) — project principles, tech stack, and workflow rules
- [`specs/001-throughput-forecast/`](specs/001-throughput-forecast/) — spec, plan, research, and data model for the forecasting library
- [`specs/002-forecast-cli/`](specs/002-forecast-cli/) — spec, plan, and contracts for the CLI and container image

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

### Container

No local Python installation needed — only a container runtime:

```bash
docker build -t agile-metrics .
docker run --rm agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --backlog-size 20 --seed 42
```

See [`specs/002-forecast-cli/quickstart.md`](specs/002-forecast-cli/quickstart.md) and
[`specs/002-forecast-cli/contracts/cli-interface.md`](specs/002-forecast-cli/contracts/cli-interface.md)
for the full flag/exit-code/output contract.

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

See [`specs/001-throughput-forecast/quickstart.md`](specs/001-throughput-forecast/quickstart.md)
for the full walkthrough, including how invalid input is rejected.

## Tech stack

Python 3.11+, managed with [`uv`](https://github.com/astral-sh/uv); `numpy` for simulation,
`pydantic` for data models, `typer` for the CLI; `ruff` + `mypy --strict` + `pytest` +
`hypothesis` for quality and statistical validation; a multi-stage Dockerfile for the
container image. Full details in the constitution's Technology Stack & Quality Gates
sections.

## Contributing

This project follows a spec-driven workflow (see `.specify/`) and a project constitution
that governs coding standards, testing requirements, and the git/PR workflow. Read
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) before contributing.

## License

[MIT](LICENSE)
