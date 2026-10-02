# Implementation Plan: Throughput-Based Monte Carlo Forecast

**Branch**: `001-throughput-forecast` | **Date**: 2026-10-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-throughput-forecast/spec.md`

## Summary

Given a team's historical throughput (items completed per equal-length period, plus the
real-world duration of one period) and either a backlog size or a target date, produce a
Monte Carlo forecast — by resampling the historical series with replacement thousands of
times — expressed as outcomes at the 50/70/85/95% confidence levels, never a single point
estimate. Delivered as a standalone, seedable Python library (no CLI/dashboard in this
slice), per the constitution's library-first and transparency principles.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `numpy` (vectorized resampling and percentile calculation),
`pydantic` v2 (boundary models for `ThroughputHistory`, `ForecastRequest`, `ForecastResult`)

**Storage**: N/A — the library is pure in-memory computation; it reads no files and has no
persistence of its own

**Testing**: `pytest` + `pytest-cov`; `hypothesis` for the statistical-validation tests
required by Constitution Principle III (convergence and distribution-shape checks)

**Target Platform**: Any platform running Python 3.11+ (no OS-specific behavior)

**Project Type**: Single library project (no frontend/mobile component)

**Performance Goals**: A forecast over a typical historical series (12–26 periods) completes
in under 5 seconds (spec SC-004)

**Constraints**: Fully deterministic given the same inputs and seed (spec FR-009); no
network or filesystem I/O inside the library

**Scale/Scope**: Single-invocation, single-team use; historical series on the order of tens
of periods, not large-scale data processing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | Resampling approach, module layout, and naming designed from scratch below (Phase 0); nothing copied from predictability-engine or similar tools | PASS |
| II. Library-First Simulation Core | Entire feature lives in `src/agile_metrics/` with no CLI/dashboard dependency; the public functions in `contracts/forecasting-api.md` are the only surface a future CLI/dashboard would call | PASS |
| III. Test-First & Statistically Validated | Tests written first (tasks phase will order them before implementation); `hypothesis`-based convergence/distribution tests planned alongside example-based tests; all randomness goes through a seeded `numpy.random.Generator` | PASS |
| IV. Transparent Assumptions | `ForecastResult` always carries all four confidence levels plus trial count and periods-used — spec FR-004/FR-005 enforce this; no code path can return a bare point estimate | PASS |
| V. Simplicity & Incremental Scope | Single package, 3 modules, no `scipy` (numpy's percentile/RNG suffice), no persistence layer, no CLI — only what User Stories 1–3 require | PASS |

No violations. Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-throughput-forecast/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── forecasting-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── agile_metrics/
    ├── __init__.py       # Public re-exports: forecast_by_items, forecast_by_date
    ├── models.py          # Pydantic models: ThroughputHistory, ForecastRequest, ForecastResult
    ├── simulation.py       # Pure Monte Carlo core: seeded resampling, trial-array generation
    └── forecast.py          # Orchestration: validates request, runs simulation, maps to ForecastResult

tests/
├── conftest.py
├── test_models.py         # FR-001, FR-006, FR-007, FR-008, FR-010, FR-011 validation rules
├── test_simulation.py      # FR-003, FR-009: resampling behavior, seeded reproducibility
├── test_statistical.py      # Principle III: hypothesis-based convergence/distribution checks
└── test_forecast.py         # End-to-end acceptance scenarios from spec User Stories 1-3
```

**Structure Decision**: Single project (library), per Constitution Principle II. No
`backend/`/`frontend` split and no `cli/` module — this feature's scope is the forecasting
capability itself; a CLI or dashboard consuming it is explicitly out of scope per the spec's
Assumptions and would be planned as its own future feature.

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
