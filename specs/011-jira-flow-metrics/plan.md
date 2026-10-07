# Implementation Plan: Cycle-Time, Aging-WIP, and Cumulative-Flow Metrics for Jira

**Branch**: `011-jira-flow-metrics` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-jira-flow-metrics/spec.md`

## Summary

Add `compute_jira_flow_metrics()` to `jira_client.py`. It reuses the project-statuses
payload spec 010 already fetches to detect both `done` and `indeterminate` (in-progress)
status categories, fetches resolved-in-window and currently-in-progress issues in one JQL
query, resolves each issue's start date from its changelog's first transition into an
in-progress status, and shapes the result into three source-agnostic models (cycle-time
entries, WIP snapshots, daily flow-state counts). Wired into the CLI (a one-line summary)
and the web UI (three new charts) only for Jira-sourced requests. The forecasting library
is untouched.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript + React 19 (frontend). Both sides
change, additive only.

**Primary Dependencies**: None new (research.md §6) - reuses `jira_client.py`'s existing
HTTP seam and `recharts`, already a frontend dependency since spec 005.

**Storage**: N/A.

**Testing**: `pytest` with the HTTP seam mocked, no real network in CI; `vitest` for the
three new chart components. A live Jira check (quickstart Scenario 6) is a manual
pre-merge gate, not part of CI - it is the only way to confirm whether `expand=changelog`
bundles on the new `/search/jql` endpoint (research.md §1).

**Target Platform**: Same as every prior feature - one container serving the API, static
frontend, and CLI.

**Project Type**: Web application + CLI, unchanged structure.

**Performance Goals**: One flow-metrics request = one statuses call (shared with
throughput, not duplicated) + one paginated JQL fetch with changelog bundled, if confirmed
live; the per-request cost of changelog data is the reason for the scale decision below.

**Constraints**: No change to `ForecastResult`, `ForecastRequest`, `ThroughputHistory`, or
the simulation core (Principle II). No new user-facing input (spec Assumptions). The
existing manual, Linear, and CSV paths are unaffected.

**Scale/Scope**: Three new models (`CycleTimeEntry`, `WipSnapshot`, `FlowStateCount`) plus
a container (`FlowMetrics`) in `models.py`; one new function in `jira_client.py`; additive
changes to `cli.py`, `web.py`, and the frontend; no new files beyond tests and three new
chart components.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | Built from Atlassian's public changelog documentation and community write-ups (research.md header) - no comparable flow-metrics code was studied or copied. | PASS |
| II. Library-First Simulation Core | `compute_jira_flow_metrics()` never touches `forecast_by_items`/`forecast_by_date`; it is a sibling read of the same Jira project, not a forecasting-library change. | PASS |
| III. Test-First & Statistically Validated | No new randomness. Test-first applies to start-date detection, the shared-universe exclusion rule, and the three views' outputs, all with mocked HTTP. | PASS |
| IV. Transparent Assumptions | Strengthened: `excluded_count` makes exclusions visible (FR-002, SC-004) rather than a silent gap, extending the same transparency spec 010's `done_statuses` established. | PASS |
| V. Simplicity & Incremental Scope | Jira only, by explicit user decision (2026-10-07) - CSV and Linear are named, not built, here. Simplified three-band cumulative-flow, not a full workflow-state diagram, because nothing in this system tracks that history (research.md, spec Assumptions). | PASS |
| Tech constraints | New models are `pydantic`, consistent with "pydantic is the one source of truth for data shapes." `mypy --strict`, ruff, bandit, pip-audit apply. | PASS |
| Workflow | `tasks.md` -> GitHub issues `[011-jira-flow-metrics] T0NN: ...` before implementation. README updated in the implementing PR. | PASS (action noted) |
| Secrets (Development Workflow) | Unaffected - no new credential; reuses the Jira token already handled by spec 010 (never logged, never persisted). | PASS |

**Post-design re-check** (after research.md, data-model.md, contracts/): unchanged, all PASS.

## Decisions needing confirmation before implementation

Per the constitution's "ask before implementing" for API shape and data modeling:

1. **Changelog-fetch scale cap** (research.md §4) - RESOLVED 2026-10-07: capped at 500
   issues (resolved-in-window + currently-in-progress, combined). Issues beyond the cap are
   skipped for flow metrics specifically; the existing throughput forecast is unaffected,
   since it never needs a changelog. The response reports how many were skipped
   (`capped_count`, data-model.md), so the cap is visible, not silent (Principle IV).
2. **CLI output shape**: a one-line summary (median cycle time, WIP count and oldest age,
   excluded count), not a full per-item dump - following the established "charts are
   web-only" precedent (spec 005 Assumptions, unchanged across 006/007/009/010). Flagged
   here for visibility, not because it seems contested.

## Project Structure

### Documentation (this feature)

```text
specs/011-jira-flow-metrics/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── forecast-api.md  # Phase 1 - request/response/CLI/web delta
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 (/speckit-tasks) - NOT created here
```

### Source Code (repository root)

```text
src/agile_metrics/
├── models.py           # + CycleTimeEntry, WipSnapshot, FlowStateCount, FlowMetrics
├── jira_client.py      # + compute_jira_flow_metrics(), + changelog fetch, + in-progress
│                        #   category detection (reuses the existing statuses call)
├── cli.py               # + one-line flow-metrics summary for Jira results
├── web.py                 # + flow_metrics field on ForecastResponseBody
└── (forecast.py, simulation.py, linear_client.py, csv_item_import.py unchanged)

tests/
├── test_jira_client.py  # + changelog/start-date, flow-issue fetch, three-view tests
├── test_models.py         # + FlowMetrics validator tests
├── test_cli.py               # + flow-metrics summary line tests
└── test_web.py                 # + flow_metrics response field tests

frontend/src/
├── charts/
│   ├── CycleTimeChart.tsx         # NEW
│   ├── AgingWipChart.tsx            # NEW
│   └── CumulativeFlowChart.tsx        # NEW
├── charts/ForecastCharts.tsx            # + renders the three new charts when present
└── App.tsx                                 # unchanged beyond passing the field through
frontend/openapi.json                         # regenerated
frontend/src/api-types.ts                       # regenerated
```

**Structure Decision**: New models live in `models.py` (source-agnostic, per research.md
§5's forward note for the Linear follow-up), but all fetching/computation logic stays
inside `jira_client.py` - no new top-level module, consistent with spec 010's own
structure decision.

## Complexity Tracking

*No entries - Constitution Check reported no violations.*
