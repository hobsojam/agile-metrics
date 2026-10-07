# Phase 1 Data Model: Cycle Time Scatterplot with Percentile Lines

## `FlowMetrics` (extended)

`src/agile_metrics/models.py` — one field added to the existing model (spec 011);
`CycleTimeEntry` and `WipSnapshot` are unchanged (FR-008).

| Field                    | Type                                     | Notes |
|---------------------------|-------------------------------------------|-------|
| `cycle_time_percentiles`  | `dict[Literal[50, 70, 85, 95], int] \| None` | Cycle time in days at each confidence level, computed from `cycle_time` via `np.percentile` (research.md §1). `None` when `len(cycle_time) < 5` (research.md §2, FR-006) — never a partial dict. |

Validation:
- When not `None`, MUST contain exactly the four keys `50, 70, 85, 95` (mirrors
  `ForecastResult.outcomes`'s existing "always all four levels" invariant,
  `models.py:104`).
- Each value MUST be `>= 0` (a cycle time in days can't be negative — same invariant
  `CycleTimeEntry` already enforces via `_validate_resolved_not_before_started`).
- Values MUST be non-decreasing across ascending levels (`[50] <= [70] <= [85] <= [95]`)
  — a direct property of `np.percentile` on any level ordering, enforced as a model
  validator for the same reason `FlowMetrics._validate_flow_state_counts_sum` exists:
  catching a computation bug at the data-model boundary, not just trusting the caller.

## Computation (in `compute_jira_flow_metrics`, `src/agile_metrics/jira_client.py`)

```text
cycle_time_days = [(entry.resolved_at - entry.started_at).days for entry in cycle_time]
cycle_time_percentiles = (
    None
    if len(cycle_time_days) < 5
    else {level: int(p) for level, p in zip((50, 70, 85, 95), np.percentile(cycle_time_days, [50, 70, 85, 95]), strict=True)}
)
```

No new entity. This is a derived, read-only summary of the already-computed
`cycle_time` list — the same relationship `excluded_count`/`capped_count` already
have to the rest of `FlowMetrics`.

## Frontend shaping (`frontend/src/charts/chartData.ts`, extended)

No new wire type beyond the regenerated `api-types.ts` (`FlowMetrics.cycle_time_percentiles`).
Two new pure functions, following this file's existing "API response -> chart-ready
series" pattern:

- `toCycleTimeScatter(flowMetrics: FlowMetrics): CycleTimeScatterSeries` — one point
  per `CycleTimeEntry` (`resolved_at`, cycle-time days, `key`), plus up to four
  `ReferenceLine`-ready markers built from `cycle_time_percentiles` and
  `CONFIDENCE_LEVEL_STYLES` (empty marker list when `cycle_time_percentiles` is `null`).
- `agingWipThreshold(flowMetrics: FlowMetrics): { days: number; color: string; label: string } | null`
  — `null` when `cycle_time_percentiles` is `null`, otherwise built from
  `cycle_time_percentiles[85]` and `CONFIDENCE_LEVEL_STYLES[85]`.

Both are pure functions over already-fetched data (no new request), matching this
module's existing docstring contract ("no re-simulation, no extra request").
