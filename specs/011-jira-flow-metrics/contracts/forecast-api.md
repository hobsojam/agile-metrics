# Contract Delta: Jira Flow Metrics

Describes only what changes relative to the existing forecast contracts (specs 006, 007,
009, 010). No request shape changes at all - this adds one optional response field,
populated for Jira-sourced requests only.

## Web response: `ForecastResponseBody`

```json
{
  "...existing fields unchanged...": "",
  "done_statuses": ["Done", "Released"],
  "flow_metrics": {
    "cycle_time": [
      { "key": "ENG-101", "started_at": "2026-09-01", "resolved_at": "2026-09-05" }
    ],
    "wip": [
      { "key": "ENG-150", "started_at": "2026-09-20", "age_days": 17 }
    ],
    "flow_state_counts": [
      { "day": "2026-09-01", "not_started": 4, "in_progress": 2, "done": 0 }
    ],
    "excluded_count": 3,
    "capped_count": 0
  }
}
```

`flow_metrics` is `null` for manual paste, Linear, and CSV requests (FR-005), and for a
Jira request where no issue has a known in-progress transition (the cycle-time/aging/CFD
"not enough data" states - rendered as plain messages, not an error, per the spec's Edge
Cases).

## CLI

No new flags (same as spec 010's own `Done statuses:` line, no new user-facing input per
this spec's Assumptions). Per the established "charts are web-only" precedent (spec 005
Assumptions, unchanged since), the CLI prints a short summary rather than every entry,
after the `Done statuses:` line, only for a Jira source with flow metrics available:

```text
Flow metrics: 42 resolved with known start (median cycle time 4.5 days), 6 in progress
(oldest 17 days), 3 excluded (no start signal)
```

When the 500-issue changelog cap (research.md §4) is reached, the summary names it
separately, e.g. `..., 128 skipped (changelog cap reached)` - never folded silently into
the "excluded" count, since it's a different kind of omission (unknown, not absent).

## Web UI

Three new views, rendered only when `result.flow_metrics` is present, alongside (not
replacing) the existing four forecast charts (FR-007):

- **Cycle-time**: a scatter/distribution of `cycle_time` durations.
- **Aging WIP**: a sorted list/bar of `wip` entries, oldest first, with a plain "nothing in
  progress" state when `wip` is empty.
- **Cumulative flow**: a stacked-area chart of `flow_state_counts` over the lookback window.

Each follows the existing chart components' accessibility pattern (`figure`/`figcaption`/
`sr-only` summary, colorblind-safe styling - spec 005 research.md §7).

## Library (`agile_metrics` public API)

New: `agile_metrics.models.CycleTimeEntry`, `WipSnapshot`, `FlowStateCount`, `FlowMetrics`.
New: `agile_metrics.jira_client.compute_jira_flow_metrics(connection, done_statuses, *,
today=None) -> FlowMetrics`. `fetch_jira_throughput`, `forecast_by_items`, and
`forecast_by_date` keep their existing signatures unchanged.
