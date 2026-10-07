# Quickstart: Cycle Time Scatterplot with Percentile Lines

All scenarios run with no network access needed - this feature adds no new Jira API
calls (research.md confirms the percentile computation is pure arithmetic over data
spec 011 already fetches), so there is no live-Jira gate like specs 010/011 needed.
Scenario 6 is a manual visual check instead, since a chart's readability can't be
asserted in a unit test.

## Prerequisites

- `uv sync` at the repo root.
- `cd frontend && npm ci` for the frontend scenarios.

## 1. Percentile computation matches `np.percentile` exactly

```bash
uv run pytest tests/test_jira_client.py -k "cycle_time_percentile" -v
```

Expected: for a known, hand-computed set of cycle-time values, `compute_jira_flow_metrics`'s
`cycle_time_percentiles` matches `np.percentile(values, [50, 70, 85, 95])` to the same
rounding (research.md §1) - not an approximation or a different interpolation method.

## 2. The 5-item minimum sample size

```bash
uv run pytest tests/test_jira_client.py -k "percentile_sample_size or percentile_omitted" -v
```

Expected: with 4 or fewer resolved entries, `cycle_time_percentiles` is `None`; with 5
or more, it's populated with all four levels (never a partial dict) (research.md §2, FR-006).

## 3. `FlowMetrics` validation

```bash
uv run pytest tests/test_models.py -k "cycle_time_percentiles" -v
```

Expected: a `FlowMetrics` with non-monotonic percentile values (e.g. `85` less than
`70`) is rejected; one with fewer than four keys when not `None` is rejected
(data-model.md).

## 4. API contract

```bash
uv run pytest tests/test_web.py -k "cycle_time_percentiles" -v
```

Expected: `flow_metrics.cycle_time_percentiles` appears in the JSON response for a
Jira request with 5+ resolved issues, is `null` for fewer, and is absent entirely
(because `flow_metrics` itself is `null`) for manual/Linear/CSV requests - unchanged
from spec 011's existing conditions.

## 5. Frontend data shaping

```bash
cd frontend && npm test -- -t "toCycleTimeScatter or agingWipThreshold"
```

Expected: `toCycleTimeScatter` produces one point per `cycle_time` entry and a marker
per percentile level (empty marker list when `cycle_time_percentiles` is `null`);
`agingWipThreshold` returns the 85th-percentile value styled with
`CONFIDENCE_LEVEL_STYLES[85]`, or `null` when there isn't one.

## 6. Chart rendering

```bash
cd frontend && npm test -- -t "CycleTimeChart or AgingWipChart"
```

Expected: `CycleTimeChart` renders a scatter point per resolved issue and up to four
labeled horizontal reference lines; with `cycle_time_percentiles` absent, it still
renders the points with no lines, not an error or empty state (FR-001, FR-006, Edge
Cases). `AgingWipChart` renders its existing per-item bars, now with the item(s)
exceeding the threshold visually distinguished, and the threshold reference line
only when a threshold is available.

## 7. Manual visual check

```bash
uv run uvicorn agile_metrics.web:app --reload &
cd frontend && npm run dev
```

Run a Jira-sourced forecast (real site or any mocked/manual data that produces
`flow_metrics` with 5+ resolved issues and at least one in-progress issue) and open
the result in a browser. Confirm:
- the four percentile lines on the Cycle Time scatterplot are legible, not clipped or
  overlapping at the chart edges (the same clipping class of bug fixed for
  `DistributionChart` in PR #382 - verify this chart didn't inherit it);
- the Aging WIP threshold line and any flagged bar are visually distinct from the
  unflagged bars, readable without relying on color alone (constitution/spec 005
  research.md §7's colorblind-safe precedent).

## 8. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
uv run pip-audit && uv run bandit -c pyproject.toml -r src/
cd frontend && npm run lint && npm run typecheck && npm test && npm audit
cd frontend && npm run generate-types && git diff --exit-code frontend/src/api-types.ts frontend/openapi.json
```

Expected: everything passes, and the generated-types freshness check (constitution
Quality Gates) produces no diff once `FlowMetrics.cycle_time_percentiles` is committed
on both sides.
