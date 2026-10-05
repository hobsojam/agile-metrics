# Implementation Plan: Forecast Precision Warning

**Branch**: `009-forecast-precision-warning` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-forecast-precision-warning/spec.md`

## Summary

Add a `precision_warning: PrecisionWarning | None` field to `ForecastResult`, computed
once in `forecast_by_items`/`forecast_by_date` from the ratio between the 50%-to-95%
outcome spread and the median outcome itself (research.md §1) — a unit-invariant,
mode-agnostic measure of "how much wider is the worst-case tail than the typical case."
Because every presentation layer (CLI, web UI, JSON API) already consumes `ForecastResult`
as the single source of truth, this one library-level change propagates everywhere
automatically except for the CLI's text renderer and the web UI's display, which need an
explicit line/banner added.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript + React 19 (frontend) — this
feature touches both, since the web UI needs a visible warning banner, but introduces no
new dependency on either side

**Primary Dependencies**: None new. The ratio is computed from values `forecast_by_items`/
`forecast_by_date` already have in hand (`outcomes`, `reference_date`) — no new numpy
operations beyond what's already there

**Storage**: N/A

**Testing**: `pytest` with deterministic seeded simulations for the threshold boundary
(same pattern every other forecast-output test in `test_forecast.py` already uses);
`vitest` + Testing Library for the new frontend banner

**Target Platform**: Same as every prior feature — one container serving the API, static
frontend, and CLI

**Project Type**: Web application (library + FastAPI + React SPA) + CLI, unchanged
structure — a new field on an existing model, consumed by all three existing surfaces

**Performance Goals**: The computation is a handful of scalar arithmetic operations on
values already computed — no measurable cost added to any forecast request

**Constraints**: MUST NOT change `outcomes`, `distribution`, `projection`, or any other
existing `ForecastResult` field (spec FR-004 - purely additive). MUST NOT introduce a
hard gate that suppresses or refuses a forecast (spec Assumptions). MUST produce the
identical warning for the same underlying `outcomes`/`reference_date` regardless of data
source, forecast mode, or presentation surface (spec FR-005/FR-006/FR-007) — trivially true
once computed once in the library, since no presentation layer recomputes it

**Scale/Scope**: One new `pydantic` model (`PrecisionWarning`), one new field on
`ForecastResult`, one new private helper function in `forecast.py`, a CLI render-line
addition, a web UI banner addition, no new files beyond tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | A simple ratio computed from this project's own existing outcome values — no comparable code exists to study or avoid. | PASS |
| II. Library-First Simulation Core | Computed entirely inside `forecast_by_items`/`forecast_by_date`, the library's only two public entry points — no presentation layer computes or duplicates this logic. | PASS |
| III. Test-First & Statistically Validated | No new randomness - the computation is deterministic given `outcomes`. Test-first still applies: seeded simulations with known-wide and known-narrow historical throughput confirm the warning fires/doesn't fire as expected. | PASS |
| IV. Transparent Assumptions | This feature exists *specifically* to strengthen this principle - surfacing when the existing confidence-level transparency isn't enough on its own because the spread is too wide to be practically useful. The warning is strictly additive (FR-004); nothing is ever hidden. | PASS |
| V. Simplicity & Incremental Scope | No new dependency; no new module (lives inside the existing `forecast.py`/`models.py`); one small helper function, not a new "data quality" subsystem. | PASS |
| Tech constraints | `PrecisionWarning` is a `pydantic` model, consistent with "pydantic is the one source of truth for data shapes." `mypy --strict` and existing lint rules apply. | PASS |
| Workflow | `tasks.md` → GitHub Issues titled `[009-forecast-precision-warning] T00x: …` before implementation, with `Closes #N` for every one of them in the completing PR. README updated in the completing PR. | PASS (action noted) |
| Secrets (Development Workflow) | Unaffected — no credential involved. | PASS |

**Post-design re-check** (after research.md, data-model.md, contracts/): unchanged, all PASS.

## Decisions needing confirmation before implementation

Per the constitution's "ask before implementing" for API shape and data modeling:

1. **Warning threshold**: the ratio `(p95_outcome - p50_outcome) / max(p50_outcome, 1)`
   (research.md §1) needs a cutoff above which the warning fires. This is a product
   judgment call with no objectively "correct" value — a planning-phase decision, not a
   hard requirement, same category as 006's 26-period Linear lookback default.

## Project Structure

### Documentation (this feature)

```text
specs/009-forecast-precision-warning/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md         # Phase 1
├── quickstart.md          # Phase 1
├── contracts/
│   └── forecast-api.md      # Phase 1 (new precision_warning field on the existing response)
├── checklists/
│   └── requirements.md
└── tasks.md                  # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/agile_metrics/
├── models.py            # + PrecisionWarning model, + ForecastResult.precision_warning
├── forecast.py            # + _compute_precision_warning(), called from both
│                          #   forecast_by_items and forecast_by_date
├── cli.py                  # + _render_result prints the warning line when present
├── web.py                    # unchanged - ForecastResponseBody(ForecastResult) inherits
│                             #   the new field automatically, same as every prior field
├── linear_client.py            # unchanged
└── csv_item_import.py            # unchanged

tests/
├── test_models.py        # + PrecisionWarning validation
├── test_forecast.py        # + threshold-boundary tests (wide vs narrow seeded simulations)
└── test_cli.py                # + render test for the warning line

frontend/
├── openapi.json                  # regenerated (new precision_warning field)
└── src/
    ├── api-types.ts              # regenerated
    └── App.tsx                    # + a visible warning banner when
                                    #   result.precision_warning is present
```

**Structure Decision**: No new files beyond tests - the warning lives entirely inside
existing modules (`models.py`, `forecast.py`), consumed automatically by `web.py` through
inheritance and explicitly rendered by `cli.py` and `App.tsx` (research.md §2, mirroring
prior features' "no speculative structure" precedent).

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
