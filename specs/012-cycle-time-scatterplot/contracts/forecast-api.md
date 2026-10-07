# Contract Delta: Cycle Time Scatterplot with Percentile Lines

Describes only what changes relative to the existing forecast contracts (specs 006,
007, 009, 010, 011). No request shape changes. One new optional field on the existing
`FlowMetrics` response object.

## Web response: `ForecastResponseBody.flow_metrics`

```json
{
  "...existing flow_metrics fields unchanged...": "",
  "cycle_time_percentiles": { "50": 2, "70": 4, "85": 7, "95": 12 }
}
```

`cycle_time_percentiles` is `null` when `flow_metrics` itself is `null` (unchanged
conditions from spec 011), and also `null` whenever `flow_metrics` is present but
`cycle_time` has fewer than 5 entries (data-model.md, FR-006) - never a partial object
with fewer than four keys.

## CLI

No change. This feature is explicitly web-only (spec's Assumptions; same "charts are
web-only" precedent spec 011 and spec 005 already established) - the CLI's one-line
flow-metrics summary is unaffected.

## Web UI

Two existing views change shape, both still rendered only when `result.flow_metrics`
is present (unchanged from spec 011):

- **Cycle time**: was a bar per resolved issue; becomes a scatterplot (resolution date
  × cycle-time days) with up to four horizontal percentile reference lines, using the
  same `CONFIDENCE_LEVEL_STYLES` colors/labels the forecast Distribution view already
  uses. No lines (not an error state - just no lines) when `cycle_time_percentiles`
  is `null`.
- **Aging WIP**: unchanged bar-per-item shape, gains one horizontal reference line at
  the 85th-percentile value and distinguishes any bar whose `age_days` exceeds it.
  No line and no distinguishing style when `cycle_time_percentiles` is `null`.

The **Cumulative flow** view (spec 011) is unaffected by this feature.

## Library (`agile_metrics` public API)

Changed: `agile_metrics.models.FlowMetrics` gains `cycle_time_percentiles:
dict[Literal[50, 70, 85, 95], int] | None`. `agile_metrics.jira_client.compute_jira_flow_metrics`
keeps its existing signature; its return value now populates the new field.
`CycleTimeEntry`, `WipSnapshot`, `FlowStateCount` are unchanged (FR-008).
`fetch_jira_throughput`, `forecast_by_items`, and `forecast_by_date` are unaffected.
