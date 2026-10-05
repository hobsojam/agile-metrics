# Implementation Plan: Linear Integration

**Branch**: `006-linear-integration` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-linear-integration/spec.md`

## Summary

Add a new `fetch_linear_throughput()` function that queries Linear's GraphQL API for a
team's completed issues, buckets completion dates into periods, and returns an existing
`ThroughputHistory` — the exact same type manual paste already produces. The CLI and web
layers gain an alternate way to populate that one value; neither the simulation core nor
`forecast_by_items`/`forecast_by_date` change at all.

## Technical Context

**Language/Version**: Python 3.11+ (backend, unchanged); TypeScript + React 19 (frontend,
unchanged) — this feature touches both, but introduces no new dependency on either side

**Primary Dependencies**: None new. The Linear HTTP calls use the Python standard library
(`urllib.request` + `json` — research.md §5); the frontend sends the credential through the
existing `fetch("/api/forecast", ...)` call with new optional body fields, so it never
needs its own HTTP client for Linear (Linear is called server-side only)

**Storage**: N/A — the API key is used for exactly one request and never persisted
(spec FR-005), consistent with the tool's existing stateless design

**Testing**: `pytest` with the Linear HTTP layer mocked (no real network calls in CI — a
thin seam around `urllib.request.urlopen` is the only thing that needs mocking, since the
query-building/pagination/bucketing logic is otherwise pure); `vitest` + Testing Library for
the new frontend form fields, same pattern as the existing manual-paste form

**Target Platform**: Same as specs 002/003 — one container serving the API, static
frontend, and CLI; any modern browser for the web UI

**Project Type**: Web application (library + FastAPI + React SPA) + CLI, unchanged
structure — one new backend module, additive changes to existing CLI/web/frontend files

**Performance Goals**: A single team's throughput fetch (one team-lookup query + a handful
of paginated 100-issue pages) completes well within normal request-timeout expectations for
realistic team sizes (research.md §4 — nowhere near Linear's rate/complexity limits)

**Constraints**: No change to `ForecastResult`, `ForecastRequest`, `ThroughputHistory`, or
the simulation core (Principle II). No credential persistence (FR-005). No logging/printing
of the credential anywhere (FR-006). The existing manual-paste path is untouched (FR-008).

**Scale/Scope**: One new backend module (`linear_client.py`), additive changes to
`cli.py`/`web.py`, additive changes to the frontend form, no new dependencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | Querying a documented public GraphQL API by its own published schema is not "copying" anything — there is no comparable Linear-integration code in predictability-engine to study or avoid (it integrates Jira, not Linear). | PASS |
| II. Library-First Simulation Core | `fetch_linear_throughput()` only ever produces a `ThroughputHistory`; the CLI and web layers still only call `forecast_by_items`/`forecast_by_date`. The simulation core is untouched. | PASS |
| III. Test-First & Statistically Validated | No new randomness/simulation logic — nothing here needs statistical validation. Test-first still applies to the adapter's query-building, pagination, and bucketing logic (ordinary unit tests, HTTP layer mocked). | PASS |
| IV. Transparent Assumptions | Unaffected — `ForecastResult` and its four confidence levels are unchanged; this feature only changes how `ThroughputHistory` gets populated. | PASS |
| V. Simplicity & Incremental Scope | No new dependency (research.md §5); no new package structure ahead of actual need (research.md §6); the "zero completed issues" and "too few periods" cases reuse existing validators instead of duplicating them (research.md §3). | PASS |
| Tech constraints | `ThroughputHistory` (existing `pydantic` model) is still the one source of truth for this data shape — the Linear adapter produces it, nothing new is hand-rolled. `mypy --strict` and existing lint rules apply to the new module. | PASS |
| Workflow | `tasks.md` → GitHub Issues titled `[006-linear-integration] T00x: …` before implementation. README updated in the implementing PR. | PASS (action noted) |
| Secrets (Development Workflow) | The credential is never logged, printed, or committed (FR-006) — verified by a test asserting it doesn't appear in any raised exception's message or `str()` representation. | PASS (to be verified by test) |

**Post-design re-check** (after research.md, data-model.md, contracts/): unchanged, all PASS.

## Decisions needing confirmation before implementation

Per the constitution's "ask before implementing" for API shape and data modeling:

1. **Request shape**: `ForecastRequestBody.history` becomes optional (`list[int] | None`),
   with three new optional fields (`linear_api_key`, `linear_team_id`, `linear_periods`) —
   exactly one of `history` or (`linear_api_key` + `linear_team_id`) must be present. This
   changes an existing field from required to optional.
2. **CLI flag shape**: `--history` becomes optional; new `--linear-api-key` (also readable
   from an `AGILE_METRICS_LINEAR_API_KEY` environment variable, so the key need not appear
   literally in shell history), `--linear-team`, `--linear-periods` (default 12).
3. **Lookback default**: 12 periods by default (research.md §7) — a planning-phase number,
   not a hard product requirement, but worth confirming before it's load-bearing in tests.

## Project Structure

### Documentation (this feature)

```text
specs/006-linear-integration/
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
├── linear_client.py   # NEW: fetch_linear_throughput() + LinearIntegrationError subclasses
├── cli.py              # + --linear-api-key / --linear-team / --linear-periods; --history
│                       #   becomes optional
├── web.py              # + linear_api_key / linear_team_id / linear_periods on
│                       #   ForecastRequestBody; history becomes optional
├── forecast.py         # unchanged
├── models.py            # unchanged
└── simulation.py        # unchanged

tests/
├── test_linear_client.py   # NEW: query building, pagination, bucketing, error
│                            #   classification - HTTP layer mocked
├── test_cli.py              # + Linear-backed CLI tests
└── test_web.py              # + Linear-backed API tests

frontend/
├── openapi.json              # regenerated (new optional request-body fields)
└── src/
    ├── api-types.ts          # regenerated
    └── App.tsx                # + a data-source toggle (manual paste / Linear) and the
                                #   three new fields, password-style input for the key
```

**Structure Decision**: One new backend module, no new top-level directories or packages
(research.md §6). The frontend gets new form fields in the existing `App.tsx`, not a new
component file — the addition is a handful of conditionally-rendered inputs, not a
distinct UI surface worth its own file yet.

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
