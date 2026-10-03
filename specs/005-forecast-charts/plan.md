# Implementation Plan: Forecast Charts

**Branch**: `005-forecast-charts` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-forecast-charts/spec.md`

## Summary

Add four charts to the web UI: an outcome distribution histogram, a probability curve, a
burn-up with a forecast fan, and a throughput run chart. All of them are built from data
the forecast already has.

**Library**: `ForecastResult` gains three required fields: `reference_date`,
`distribution` and `projection`. All three come from the same simulation run as the
existing outcomes. The simulation core gets one internal "cumulative paths" function that
both existing modes are re-expressed on. It makes the same single random draw as today,
so existing outcomes stay byte-for-byte identical.

**API and CLI**: The API exposes the new fields automatically through its existing
response model. The CLI is untouched.

**Web UI**: The charts are drawn with Recharts from pure, separately tested data-shaping
functions. Every chart shows the four confidence levels in one shared style and has a
text alternative.

## Technical Context

**Language/Version**: Python 3.11+ (backend/library, unchanged); TypeScript + React 19 (frontend, unchanged)

**Primary Dependencies**: Existing: numpy, pydantic, FastAPI, React, Vite, Tailwind (via 004). **New (frontend runtime)**: `recharts@^3.10.1` and its peer `react-is`. Justification is in research.md §6, to be repeated in the PR description as the constitution requires. No new Python dependencies.

**Storage**: N/A (stateless, unchanged)

**Testing**: pytest + hypothesis (property tests for distribution and projection invariants, plus a seeded regression test pinning pre-feature outcomes); vitest + Testing Library (pure `chartData.ts` functions; chart components through captions and text alternatives)

**Target Platform**: Same as spec 003: one container serving the API and static frontend; any modern browser

**Project Type**: Web application (library + FastAPI + React SPA), unchanged structure

**Performance Goals**: Charts render within 1 s of results (SC-004). Payload grows by at most 60 buckets plus one projection point per period, a few KB in typical cases.

**Constraints**: Existing outputs must be identical (SC-006). No re-simulation or extra requests from the UI (FR-009). Must merge cleanly after spec 004's `App.tsx` restyle.

**Scale/Scope**: One endpoint, four charts, three new model fields, two new models

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | Chart types are general forecasting practice. Only predictability-engine's README feature list was viewed, none of its code. Names and structure are this project's own (research.md §9). | PASS |
| II. Library-First Simulation Core | Chart data is computed in the library (`forecast.py` / `simulation.py`) and exposed through the public `ForecastResult`. The web layer still only calls `forecast_by_items` / `forecast_by_date`. The UI does not simulate. | PASS |
| III. Test-First & Statistically Validated | A regression test pinning current outputs is written **before** the simulation refactor. Hypothesis property tests cover invariants (counts add up to trials, levels ordered, monotone fan, exact target-date match, ±1-period backlog match, curve ≥ L at outcome). Seeds are honoured throughout. | PASS |
| IV. Transparent Assumptions | Every chart shows all four levels, never a single point estimate (FR-008). `reference_date` is now surfaced. Trial count stays visible. | PASS |
| V. Simplicity & Incremental Scope | One new frontend dependency (justified). No new API endpoint. The probability curve is derived client-side rather than adding a field. Item-level and Jira data are deferred to a later feature. | PASS |
| Tech constraints | Pydantic models for all new shapes. `mypy --strict` and `tsc` types. Generated `api-types.ts` regenerated and committed (CI freshness gate). | PASS |
| Workflow | `tasks.md` → GitHub Issues titled `[005-forecast-charts] T00x: …` before implementation. README updated in the implementing PR. A separate issue for the existing backlog-mode memory cost (research.md §1). | PASS (actions noted) |

**Post-design re-check** (after research.md, data-model.md, contracts/): unchanged, all PASS.

## Decisions needing confirmation before implementation

The constitution says "Ask before implementing" for API shape and data modelling. These
are the decisions to confirm:

1. **API shape**: three new *required* fields on `ForecastResult` (`reference_date`,
   `distribution`, `projection`), with the shapes in data-model.md. Two CLI test fixtures
   need the fields added.
2. **Backlog-mode tolerance**: burn-up lines may meet the backlog line one period away from
   the listed date in rare cases (0.4% in testing). The spec was amended to accept this
   rather than change existing outputs (research.md §2).
3. **Layout**: the charts area is wider than spec 004's `max-w-xl` content column
   (research.md §7).

## Project Structure

### Documentation (this feature)

```text
specs/005-forecast-charts/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── forecast-api.md  # Phase 1 (delta over spec 003's contract)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/agile_metrics/
├── models.py        # + OutcomeBucket, ProjectionPoint; ForecastResult gains
│                    #   reference_date, distribution, projection, plus validator
├── simulation.py    # + cumulative-paths function; existing two functions
│                    #   re-expressed on it (same RNG call, so identical output)
├── forecast.py      # derives distribution and projection from the one run;
│                    #   private bucketing and projection helpers
├── web.py           # unchanged (response_model picks up the new fields)
└── cli.py           # unchanged

tests/
├── test_regression.py   # NEW: pins pre-feature outcomes for fixed seeds (written first)
├── test_forecast.py     # + distribution/projection behaviour
├── test_statistical.py  # + property tests for invariants (research.md §2–§4)
├── test_models.py       # + new validator rules
├── test_web.py          # + new fields present in the API response
└── test_cli.py          # fixtures gain the new fields; output assertions unchanged

frontend/
├── package.json         # + recharts, react-is
├── openapi.json         # regenerated
└── src/
    ├── api-types.ts     # regenerated
    ├── App.tsx          # renders <ForecastCharts> in the results section; keeps the
    │                    #   submitted history/period/target alongside the result
    └── charts/          # NEW
        ├── confidenceLevels.ts      # shared label and colour per level (FR-010)
        ├── chartData.ts             # pure: response + inputs → chart series
        ├── chartData.test.ts
        ├── ForecastCharts.tsx       # lays out the four figures
        ├── DistributionChart.tsx
        ├── ProbabilityCurveChart.tsx
        ├── BurnUpChart.tsx
        ├── ThroughputRunChart.tsx
        └── ForecastCharts.test.tsx  # captions, text alternatives, no charts on error
```

**Structure Decision**: Keep the existing layout (single Python package plus a top-level
`frontend/`). The only new directory is `frontend/src/charts/`. It holds the chart code so
`App.tsx` changes by a few lines, which limits merge conflicts with spec 004.

## Sequencing

1. **Library, test-first**: regression pin → cumulative-paths refactor (pin stays green) →
   models plus validator → distribution → projection → property tests.
2. **API**: web test for the new fields, then regenerate `openapi.json` and `api-types.ts`.
3. **Frontend**: *after spec 004 merges and this branch is rebased on it.*
   `chartData.ts` (pure, test-first) → the four chart components in priority order
   (P1 distribution → P2 curve → P3 burn-up → P4 run chart) → wire into `App.tsx`.
4. **Wrap-up**: README update, PR description (dependency justification, principles
   touched).

Steps 1–2 don't touch `frontend/src/App.tsx`, so they could start before 004 merges.

## Complexity Tracking

No constitution violations. Nothing to justify.
