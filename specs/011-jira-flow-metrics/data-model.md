# Data Model: Cycle-Time, Aging-WIP, and Cumulative-Flow Metrics for Jira

No change to the forecasting library's existing entities (`ThroughputHistory`,
`ForecastRequest`, `ForecastResult`, `PrecisionWarning`) - Principle II, FR-008. These are
new, additive models in `agile_metrics.models`, source-agnostic in shape even though only
Jira populates them in this version (research.md §5 - Linear will reuse them later).

## New models (in `agile_metrics.models`)

### `CycleTimeEntry`

| Field | Type | Meaning |
|---|---|---|
| `key` | `str` | The item's identifier (e.g. `ENG-123`) |
| `started_at` | `date` | First entry into an in-progress status |
| `resolved_at` | `date` | Resolution date |

Validation: `resolved_at >= started_at` (an entry violating this is never constructed - it
is excluded upstream per FR-002, not represented here as an invalid state).

### `WipSnapshot`

| Field | Type | Meaning |
|---|---|---|
| `key` | `str` | The item's identifier |
| `started_at` | `date` | First entry into an in-progress status |
| `age_days` | `int` | `today - started_at`, computed once at fetch time |

Validation: `age_days >= 0`.

### `FlowStateCount`

| Field | Type | Meaning |
|---|---|---|
| `day` | `date` | One day in the lookback window |
| `not_started` | `int` | Items that exist but hadn't started yet as of this day |
| `in_progress` | `int` | Items started but not yet resolved as of this day |
| `done` | `int` | Items resolved on or before this day |

Validation: all three counts `>= 0`.

### `FlowMetrics`

| Field | Type | Meaning |
|---|---|---|
| `cycle_time` | `list[CycleTimeEntry]` | One entry per resolved item with a known start |
| `wip` | `list[WipSnapshot]` | One entry per currently-in-progress item |
| `flow_state_counts` | `list[FlowStateCount]` | One entry per day in the lookback window |
| `excluded_count` | `int` | Items considered but excluded for lacking a start signal (FR-002, SC-004) |
| `capped_count` | `int` | Otherwise-eligible items skipped by the 500-issue changelog cap (research.md §4, plan.md "Decisions" §1) - distinct from `excluded_count`: these had an unknown start, not a missing one, because their changelog was never fetched |

Validation (`@model_validator`, mirroring `ForecastResult`'s own distribution/trials-run
check): for every `FlowStateCount`, `not_started + in_progress + done == len(cycle_time) +
len(wip)` (research.md §3's "one universe" rule, enforced structurally - SC-003).

## Changed model: none

`ForecastResult` is unchanged. `ForecastResponseBody` (web.py) gains one new optional field
(`flow_metrics: FlowMetrics | None = None`), the same additive pattern `done_statuses`
used in spec 010 - empty/`None` for every source except Jira.

## New library function (not a model)

```python
def compute_jira_flow_metrics(
    connection: JiraConnection, done_statuses: list[str], *, today: date | None = None
) -> FlowMetrics:
```

In `jira_client.py`, alongside `fetch_jira_throughput`. Takes the already-detected
`done_statuses` (avoids a second call to the project-statuses endpoint when both throughput
and flow metrics are needed for the same request - research.md §2) and internally detects
the in-progress status set from the same statuses payload.

**Called from**: `cli.py`/`web.py`, immediately after `fetch_jira_throughput`, only when the
source is Jira - never from the forecasting library itself.
