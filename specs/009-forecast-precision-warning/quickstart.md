# Quickstart: Forecast Precision Warning

Validates that the precision warning fires correctly on wide forecasts and stays silent on
tight ones, without changing any existing forecast output. Every scenario is
self-contained — no external service or network access needed.

## Prerequisites

- `uv sync` at the repo root; `npm ci` in `frontend/` (for scenario 4 only)

## 1. The spread-ratio computation

```bash
uv run pytest tests/test_forecast.py -k "precision_warning" -v
```

Expected: a seeded simulation producing a wide spread (ratio > 1.0) returns a
`ForecastResult` with `precision_warning` set, naming the computed ratio; a seeded
simulation producing a tight spread (ratio ≤ 1.0) returns `precision_warning=None`. Both
date-mode (`forecast_by_items`) and count-mode (`forecast_by_date`) are covered.

## 2. No change to existing forecast output

```bash
uv run pytest tests/test_forecast.py tests/test_models.py -v
```

Expected: every pre-existing test (outcomes, distribution, projection, trials_run,
periods_used) still passes unmodified — this feature is purely additive.

## 3. CLI renders the warning line

```bash
uv run pytest tests/test_cli.py -k "precision_warning" -v
```

Expected: `_render_result` includes the warning message when present, and omits it
entirely (no blank line, no placeholder) when absent.

## 4. Web UI shows the warning banner

```bash
cd frontend && npm test -- -t "precision"
```

Expected: a visible, distinctly-styled banner renders when `result.precision_warning` is
present; no banner renders when it's absent. The existing four confidence-level outcomes
and charts render unchanged either way.

## 5. Manual end-to-end check

```bash
uv run agile-metrics --history "1,0,2,0,1,0" --period-days 7 --backlog-size 50 --seed 42
```

Expected: a sparse, mostly-zero 6-period history forecasting a comparatively large backlog
should produce a wide spread and trigger the warning line. Compare against:

```bash
uv run agile-metrics --history "8,9,7,8,10,9,8,7" --period-days 7 --backlog-size 10 --seed 42
```

Expected: a consistent, ample history forecasting a small backlog should produce a tight
spread and show no warning.

## 6. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
cd frontend && npm run lint && npm run typecheck && npm test && npm audit
```

Expected: everything passes.
