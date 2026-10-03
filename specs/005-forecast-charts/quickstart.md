# Quickstart: Validating Forecast Charts

These are end-to-end checks that the feature works once implemented. Shapes and rules are
in [data-model.md](./data-model.md) and [contracts/forecast-api.md](./contracts/forecast-api.md).

## Prerequisites

- Spec 004 (styling) merged to `main`, and this branch rebased on it
- `uv sync` at the repo root; `npm ci` in `frontend/`

## 1. Existing behaviour is untouched (SC-006)

```bash
uv run agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --backlog-size 20 --seed 42
```

Expected: the same four dates as the README example, with identical formatting. The
regression test that pins pre-feature outcome values for fixed seeds passes:

```bash
uv run pytest -k regression
```

## 2. Library returns chart data

```bash
uv run python -c "
from datetime import timedelta, date
from agile_metrics import forecast_by_date
from agile_metrics.models import ThroughputHistory
h = ThroughputHistory(completed_per_period=[3,5,4,6,2,5,4,3], period_duration=timedelta(days=7))
r = forecast_by_date(h, date(2026,11,14), seed=42, reference_date=date(2026,10,3))
print(sum(b.trials for b in r.distribution) == r.trials_run)
print(r.projection[-1].cumulative == r.outcomes)
"
```

Expected: `True` and `True`.

## 3. API returns the new fields

```bash
uv run uvicorn agile_metrics.web:app &
curl -s localhost:8000/api/forecast -H 'Content-Type: application/json' \
  -d '{"history":[3,5,4,6,2,5,4,3],"period_days":7,"backlog_size":20,"seed":42}' \
  | python -m json.tool
```

Expected: `outcomes`, `trials_run` and `periods_used` as before, plus `reference_date`,
`distribution` (at most 60 buckets, with date bounds) and `projection`.

## 4. Generated types are fresh

```bash
cd frontend && npm run generate-types && git diff --exit-code openapi.json src/api-types.ts
```

Expected: no diff, because the regenerated files were committed with the model change.

## 5. Charts in the browser

Start the backend (step 3) and `cd frontend && npm run dev`, then:

| Do | Expect |
|---|---|
| History `3,5,4,6,2,5,4,3`, period 7, backlog 20, seed 42 → submit | The four confidence results as before, **plus** four charts below them |
| Look at the distribution | One bar per completion date. Labelled 50/70/85/95% markers at exactly the listed dates |
| Hover the probability curve at a date between two markers | Tooltip shows "x% of simulations done by \<date\>" |
| Look at the burn-up | The history line rises over 8 weeks to the reference date. The fan widens from there. A horizontal line marks history total + 20. Each level's line meets it at (or within one week of) its listed date |
| Look at the run chart | 8 bars in input order (oldest left), median line at 4 |
| Switch to target date `2026-11-14` → submit | The distribution is in items. The curve reads "at least N items". The fan ends at the target date with values equal to the listed counts |
| Enter history `5,5,5,5,5,5` → submit | A single distribution bar with all four markers on it, still readable |
| Submit invalid input (backlog 0) | The error message as before, no charts |
| Narrow the window to about 400px | Charts shrink to fit, with no horizontal page scroll |
| Tab through the page with a screen reader | Each chart is announced with its title, caption and a text summary of the four confidence values |

## 6. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
cd frontend && npm run lint && npm run typecheck && npm test && npm audit
```

Expected: everything passes.
