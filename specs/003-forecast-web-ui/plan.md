# Implementation Plan: Forecast Web UI

**Branch**: `003-forecast-web-ui` | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-forecast-web-ui/spec.md`

## Summary

A React single-page form over a FastAPI JSON API: the user pastes/uploads historical
throughput, picks a backlog size or target date, and sees the Monte Carlo forecast rendered
client-side. The backend is a third thin presentation layer over the existing
`agile_metrics` library (same pattern as the CLI); no server-rendered templates — the user
explicitly chose a real React frontend over a Jinja2 one after discussing the effort
tradeoff.

## Technical Context

**Language/Version**: Backend: Python 3.11+ (unchanged). Frontend: TypeScript, Node.js
(current LTS) for the build toolchain only — nothing Node-based ships at runtime.

**Primary Dependencies**: Backend: `fastapi`, `uvicorn[standard]` (new core dependencies,
same precedent as adding `typer` for the CLI). Frontend: `react`, `vite` (build tool),
`openapi-typescript` (dev dependency, codegen only — generates request/response types from
the backend's own OpenAPI schema instead of hand-written duplicates); no routing library,
no state-management library, no HTTP client library (native `fetch`) — all rejected as
unneeded for one form hitting one endpoint.

**Storage**: N/A — stateless (spec FR-005)

**Testing**: Backend: `pytest` + FastAPI's `TestClient`, testing the JSON contract directly
(mirrors the CLI's `CliRunner` tests). Frontend: `vitest` + `@testing-library/react`,
testing form submission/rendering with a mocked `fetch`.

**Target Platform**: Any modern browser; same container-based deployment as the CLI (one
Docker image serving both the API and the built static frontend)

**Project Type**: Web application — a genuine split from the existing single-package
structure, since the frontend is a different language/toolchain entirely (see Project
Structure below)

**Performance Goals**: Forecast appears within 5 seconds of submission (inherited from
library SC-004), with visible in-progress feedback if it takes any noticeable time (spec
SC-004)

**Constraints**: Stateless; no accounts; the backend route handler MUST separate "compute
the result" from "shape the HTTP response" so business-logic tests don't depend on the HTTP
layer and survive any future frontend change

**Scale/Scope**: Single-user-at-a-time, one page, one API endpoint — same scope as the CLI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | API contract, component structure, and Docker build designed from scratch below | PASS |
| II. Library-First Simulation Core | The FastAPI route only calls `forecast_by_items`/`forecast_by_date` — a third thin presentation layer over the same unchanged library, exactly as Principle II anticipated ("CLI today, a dashboard tomorrow") | PASS |
| III. Test-First & Statistically Validated | Backend API tests and frontend component tests both written and confirmed failing before implementation, in every phase | PASS |
| IV. Transparent Assumptions | API response always includes all four confidence levels plus `trials_run`/`periods_used`; the React component renders all of them, never a subset | PASS |
| V. Simplicity & Incremental Scope | See Complexity Tracking below — introducing a full React/npm toolchain for a single-form page is more machinery than a server-rendered template would need | FLAGGED, justified |

**Gap requiring a companion constitution amendment**: the existing Quality Gates section
already says "Dependabot MUST be configured for this repository (pip/uv and github-actions
ecosystems)" and specifies a fixed Python-only CI gate order. Neither covers a
frontend/npm toolchain at all. Introducing `frontend/` without updating that MUST clause
would put this feature in violation of the constitution from the moment `package.json`
exists. This is being resolved via a separate constitution amendment (not part of this
feature branch, per the project's own convention for non-Spec-Kit governance work),
addressed alongside this plan rather than left as a known gap.

## Project Structure

### Documentation (this feature)

```text
specs/003-forecast-web-ui/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── forecast-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/agile_metrics/
├── __init__.py       # existing, unchanged
├── models.py          # existing, unchanged
├── simulation.py       # existing, unchanged
├── forecast.py          # existing, unchanged
├── cli.py                # existing, unchanged
└── web.py                 # NEW: FastAPI app. POST /api/forecast; separates
                             # _compute_forecast() (testable without HTTP) from the
                             # route handler that shapes the HTTP response; serves
                             # frontend/dist/ as static files in production

tests/
├── ... (existing)
└── test_web.py          # NEW: FastAPI TestClient tests against the JSON contract

frontend/                 # NEW: separate Node/TypeScript project (own toolchain,
                            # own Dependabot ecosystem - matches the frontend+server
                            # split already used in the author's other repos)
├── package.json
├── vite.config.ts
├── tsconfig.json
├── openapi.json            # generated from the backend's app.openapi(), committed
├── src/
│   ├── main.tsx
│   ├── App.tsx            # the single form + result display
│   ├── App.test.tsx        # vitest + React Testing Library
│   └── api-types.ts        # generated by openapi-typescript from ../openapi.json,
│                             # committed; `npm run generate-types` regenerates both,
│                             # a CI step fails if that would change either file
└── dist/                    # build output (gitignored), copied into the Docker image
```

**Structure Decision**: The Python side stays a single package — `web.py` is a sibling
presentation module to `cli.py`, not a separate `backend/` directory, since nothing about
it needs its own dependency/build setup beyond what `pyproject.toml` already manages. The
frontend genuinely is a separate toolchain (different language, own `package.json`,
Dependabot ecosystem, CI gates), so it gets its own top-level `frontend/` directory rather
than forcing it under `src/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Full React/Vite/npm toolchain (build step, second test stack, second Dependabot ecosystem, second set of CI gates) for a single-form page | Explicit, informed user decision after discussing the effort tradeoff against a server-rendered Jinja2 template; not a speculative or hypothetical need | A server-rendered HTML form was the lower-effort option and was proposed, but the user found no value in it for this project and wants to invest in a real frontend now rather than migrate later |
