# Implementation Plan: Cycle Time Scatterplot with Percentile Lines

**Branch**: `012-cycle-time-scatterplot` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-cycle-time-scatterplot/spec.md`

## Summary

Redesign the Cycle Time flow-metrics view as a scatterplot (resolution date × cycle
time in days) with the same 50/70/85/95% percentile reference lines already used on
the forecast Distribution view, and overlay the 85th-percentile value as an at-risk
threshold on the Aging WIP view. Percentiles are computed server-side with `np.percentile`
— the same function and semantics the Monte Carlo forecast already uses for its
confidence-level outcomes (research.md §1) — and returned as one new optional field on
the existing `FlowMetrics` response, rather than reimplemented in the frontend. Both
charts stay presentation-only consumers of pre-computed data, matching how every other
chart in this app already works.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.x / React 19 (frontend) — unchanged, no new language/runtime

**Primary Dependencies**: `numpy` (`np.percentile`, already a dependency), `pydantic`, `fastapi` (backend, all existing); `recharts` (frontend, already used by every other chart) — no new runtime dependency on either side

**Storage**: N/A (stateless computation from each request's already-fetched Jira data, same as spec 011)

**Testing**: `pytest` (backend: percentile correctness, sample-size threshold, field presence/absence), `vitest` + `@testing-library/react` (frontend: chart data-shaping functions and component rendering)

**Target Platform**: Linux server (backend), browser (frontend) — unchanged

**Project Type**: Web application (existing `src/agile_metrics/` backend + `frontend/` — Option 2 structure, already in place since spec 003)

**Performance Goals**: N/A beyond existing flow-metrics request (spec 011) — percentile computation is O(n log n) on at most 500 cycle-time entries (the existing changelog cap), negligible next to the Jira network calls already dominating that request

**Constraints**: Percentile values MUST come from exactly one computation (FR-003) — no parallel frontend reimplementation of `np.percentile`'s interpolation method. `CycleTimeEntry`/`WipSnapshot` contracts stay unchanged (FR-008); only `FlowMetrics` gains a field.

**Scale/Scope**: Two chart components changed (`CycleTimeChart.tsx`, `AgingWipChart.tsx`), one shared frontend data-shaping module extended (`chartData.ts`), one backend field added (`FlowMetrics.cycle_time_percentiles`) and populated in `compute_jira_flow_metrics`. No new files beyond tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Clean-room)**: N/A — no external tool's design is being studied or mirrored; this redesigns an internal chart using patterns already established within this codebase (`DistributionChart`'s percentile-marker convention). PASS.
- **Principle II (Library-first simulation core)**: Percentile computation is added to `compute_jira_flow_metrics` (the existing Jira flow-metrics library function, `src/agile_metrics/jira_client.py`), not to a chart component or the web layer — charts remain pure presentation, consuming a pre-computed field exactly as `DistributionChart` already consumes `result.outcomes`. PASS.
- **Principle III (Test-first & statistically validated)**: Percentile computation is deterministic (not randomized), so no seed is needed, but it still requires tests asserting exact values against known small datasets (comparable to how `np.percentile` is already tested indirectly via `forecast.py`'s existing tests) and a test for the <5-item omission boundary (FR-006). Tests are written first, per Principle III. PASS.
- **Principle IV (Transparent assumptions)**: Directly served by this feature — it exists to surface a sample-size-backed threshold instead of a bare number, and explicitly withholds that threshold when the sample is too small to trust (FR-006) rather than showing a misleading value. PASS.
- **Principle V (Simplicity/YAGNI)**: One new optional field, no new abstractions, no new dependencies; reuses the existing `CONFIDENCE_LEVELS`/`CONFIDENCE_LEVEL_STYLES` frontend module and the existing `np.percentile` backend pattern rather than inventing new ones. PASS.

No violations — Complexity Tracking section omitted.

## Project Structure

### Documentation (this feature)

```text
specs/012-cycle-time-scatterplot/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/agile_metrics/
├── models.py            # FlowMetrics gains cycle_time_percentiles field
├── jira_client.py        # compute_jira_flow_metrics computes + populates it
└── web.py                # unchanged — ForecastResponseBody already embeds FlowMetrics

frontend/src/
├── charts/
│   ├── confidenceLevels.ts    # unchanged — reused as-is (CONFIDENCE_LEVELS, CONFIDENCE_LEVEL_STYLES)
│   ├── chartData.ts           # gains cycle-time-scatter and WIP-threshold shaping functions
│   ├── CycleTimeChart.tsx     # BarChart -> ScatterChart + horizontal ReferenceLines
│   └── AgingWipChart.tsx      # adds one ReferenceLine + per-bar at-risk coloring
└── api-types.ts          # regenerated (openapi.json freshness gate) once FlowMetrics changes

tests/
├── test_models.py              # FlowMetrics.cycle_time_percentiles validation
└── test_jira_client.py         # percentile computation + <5-item omission

frontend/src/charts/
├── chartData.test.ts
├── CycleTimeChart.test.tsx
└── AgingWipChart.test.tsx
```

**Structure Decision**: No new top-level directories. This feature extends the existing
web-application layout (`src/agile_metrics/` backend, `frontend/` frontend) established
since spec 003, touching exactly the files listed above.
