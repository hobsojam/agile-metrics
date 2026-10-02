# Quickstart: Forecast CLI

Validates the feature end-to-end once implemented. See `contracts/cli-interface.md` for the
full flag/exit-code/output contract.

## Prerequisites

- Local run: Python 3.11+ environment with the project installed (`uv sync`)
- Container run: a container runtime (e.g. Docker) — no local Python needed

## Scenario 1 — Completion-date forecast, local (User Story 1)

```bash
uv run agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --backlog-size 20 --seed 42
```

**Expected outcome**: exit code 0; stdout shows four confidence levels as dates, plus
`trials_run`/`periods_used`, matching `specs/001-throughput-forecast/quickstart.md`
Scenario 1's values for the same input and seed.

## Scenario 2 — Items-completed forecast, local (User Story 2)

```bash
uv run agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --target-date 2026-12-01 --seed 42
```

**Expected outcome**: exit code 0; stdout shows four confidence levels as item counts,
matching `specs/001-throughput-forecast/quickstart.md` Scenario 2's values.

## Scenario 3 — Container run, no local Python (User Story 3)

```bash
docker build -t agile-metrics .
docker run --rm agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --backlog-size 20 --seed 42
```

**Expected outcome**: identical stdout and exit code to Scenario 1 — no Python installation
required on the host, only the container runtime.

## Scenario 4 — Rejecting bad input (edge cases / SC-003)

```bash
uv run agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7
# no --backlog-size or --target-date supplied
```

**Expected outcome**: exit code 1; a single clean `Error: ...` line on stderr — no stack
trace — explaining that exactly one of `--backlog-size`/`--target-date` is required.

## Running it for real

```bash
uv run pytest tests/test_cli.py -v
```

All four scenarios above are expected to exist as cases in `test_cli.py` once implemented
(see `tasks.md`, generated separately by `/speckit-tasks`); Scenario 3 is additionally
exercised by a CI step that builds and runs the Docker image directly.
