# Research: Forecast Web UI

## Backend framework

**Decision**: `FastAPI` + `uvicorn[standard]`.

**Rationale**: Our pydantic models already serialize to/from JSON natively; FastAPI is
built directly on pydantic for request/response validation, so there is no translation
layer to write by hand. It also matches the constitution's existing "pydantic everywhere"
mandate without any new design pattern.

**Alternatives considered**: Flask — would need a separate, hand-rolled JSON
(de)serialization layer on top of pydantic; rejected as pure extra work. Django — far
heavier (ORM, admin, templating) than a single stateless JSON endpoint needs; rejected per
Simplicity.

## Frontend framework/tooling

**Decision**: React + Vite + TypeScript.

**Rationale**: User's explicit choice over a server-rendered template. Vite is the current
lightweight standard for a React app with no routing/SSR needs — minimal config, fast dev
server, produces a plain static `dist/` the backend can serve. TypeScript (not plain JS)
matches the project's existing strict-typing ethos (`mypy --strict` on the Python side).

**Alternatives considered**: Next.js — its file-based routing and SSR/SSG machinery solve
problems this single-page form doesn't have; rejected per Simplicity. Create React App —
unmaintained; rejected regardless of this project's choices.

## State management / data fetching

**Decision**: React's built-in `useState` only; native `fetch` for the one API call.

**Rationale**: One form, one submit action, one result view. No caching, no retries, no
shared state across routes/components to justify Redux/Zustand/React Query/axios.

**Alternatives considered**: React Query, axios — rejected as unneeded machinery for a
single POST request with no caching semantics worth having.

## API contract shape

**Decision**: A single `POST /api/forecast` endpoint. Request body carries the history as a
native JSON array of integers (not a comma-separated string — unlike the CLI, JSON doesn't
need that workaround), period length, exactly one of `backlog_size`/`target_date`, and an
optional seed. Response is either the forecast result (confidence-level outcomes, trial
count, periods used) on success, or a structured `{"error": "<message>"}` body with a
4xx status on validation failure.

**Rationale**: Mirrors the CLI's contract/data-model one-for-one, just with JSON-native
types instead of CLI-string parsing. Keeps the request/response shape obvious from the
pydantic models alone.

**Alternatives considered**: Separate endpoints per forecast mode (`/forecast/by-items`,
`/forecast/by-date`) — rejected; one endpoint with a mode discriminator matches the
library's own `ForecastRequest` shape more directly and avoids duplicating the
mutual-exclusivity validation across two routes.

## Keeping the backend reusable across frontend changes

**Decision**: The route handler does exactly two things: parse the request body and call a
separate `_compute_forecast(...)` function; catch what it raises and shape the HTTP
response. `_compute_forecast` itself only calls the public `forecast_by_items`/
`forecast_by_date` API (Principle II) and contains zero HTTP-specific code, so it is
unit-testable without an HTTP client at all.

**Rationale**: This is what keeps a future frontend swap cheap — business-logic tests
target `_compute_forecast` and the JSON contract, not rendered markup, so they survive
unchanged regardless of what consumes the API.

**Alternatives considered**: Inlining validation/dispatch directly in the route function
(as the CLI's `main()` does) — rejected here specifically because a web backend is far more
likely to gain a second consumer (future mobile client, a different frontend) than a CLI
is; the extra function boundary costs nothing and pays for exactly this.

## Serving the frontend

**Decision**: Vite builds the React app to static files; FastAPI mounts and serves that
`dist/` directory alongside the `/api/forecast` route. One container, one port, one
deployable artifact.

**Rationale**: Matches the "one Docker image" simplicity already established for the CLI;
avoids the operational overhead of running and coordinating two separate services for what
is still a small, single-page tool.

**Alternatives considered**: Separate frontend-hosting and backend-API services (e.g. a
static host plus an API server) — rejected as unnecessary operational complexity at this
scale; nothing about this feature needs independent scaling or deployment of the two
halves.

## Docker build

**Decision**: Add a `frontend-builder` stage (`node:22-slim`, `npm ci`, `npm run build`)
alongside the existing Python `builder` stage; the final `runtime` stage copies both the
Python venv and the frontend's `dist/` output. Non-root `appuser`, pinned `uv` image, and
`--locked --no-build` all carry over unchanged from the CLI's Dockerfile.

**Rationale**: Keeps the "single image, built from pinned/locked inputs, runs as non-root"
properties the CLI feature already established, extended to cover the new build stage
rather than treated as a special case.

**Alternatives considered**: None specific to this decision beyond what's already covered
above (serving strategy, backend framework).

## Keeping frontend and backend types in sync

**Decision**: Generate the frontend's TypeScript request/response types from the backend's
own OpenAPI schema, rather than hand-writing a parallel set of interfaces. Concretely:

1. A small script exports `app.openapi()` (FastAPI builds this from the pydantic models
   automatically — no separate schema to maintain) to a static `openapi.json`, without
   needing a running server.
2. `openapi-typescript` (frontend dev dependency) generates `frontend/src/api-types.ts`
   from that file.
3. Both `openapi.json` and `api-types.ts` are **committed**, generated via an
   `npm run generate-types` script — not generated fresh on every build.
4. A frontend CI step re-runs generation and fails if the committed files would change
   ("types are stale — run `npm run generate-types` and commit the result").

**Rationale**: The pydantic models are already this project's single source of truth for
data shapes (constitution: "no raw dicts crossing boundaries"); this extends that same
principle across the language boundary instead of hand-maintaining a second copy of the
shape in TypeScript that can silently drift (rename a field in FastAPI, nothing catches the
frontend still expecting the old name until a user hits it at runtime). Committing the
generated files, with a CI freshness check, mirrors exactly how this project already treats
`uv.lock` — a committed, pinned artifact whose staleness is caught by a gate (`--locked`)
rather than by regenerating it on every build. That keeps the Docker build graph simple (no
cross-stage dependency forcing the frontend-builder stage to wait on a Python stage) and
means a frontend-only contributor doesn't need a Python environment just to get types.

**Alternatives considered**: Hand-written TypeScript interfaces — rejected; this is exactly
the drift risk described above, for an API with two field-level discriminators
(`backlog_size`/`target_date`) that are easy to get subtly wrong by hand. A full
client generator (`orval`, `openapi-generator`) producing fetch wrappers, not just types —
rejected as more than one endpoint needs; only types are generated, the one `fetch` call is
still hand-written (per the State management decision above). Regenerating at build time
instead of committing — rejected; it would couple the frontend build to having a Python
environment available, and add cross-stage ordering to the Dockerfile for no benefit over
a CI freshness check.

## Frontend quality gates

**Decision**: ESLint + TypeScript's own compiler (`tsc --noEmit`) for linting/type
checking; `vitest` for tests; `npm audit` for dependency vulnerabilities — the npm-ecosystem
equivalents of `ruff`/`mypy --strict`/`pytest`/`pip-audit` on the Python side. A Dependabot
`npm` ecosystem block (7-day cooldown, matching the project-wide policy) is added for
`frontend/`.

**Rationale**: Parity with the existing Python Quality Gates, rather than leaving the new
language/toolchain without equivalent coverage. This is addressed via a companion
constitution amendment (see plan.md's Constitution Check) rather than silently expanding
scope without updating the governing document.

**Alternatives considered**: Skipping frontend-specific gates since it's "just a small UI"
— rejected; the constitution's existing Quality Gates section already mandates Dependabot
coverage for every ecosystem in the repo, and introducing one without updating that
commitment would make this feature non-compliant from day one.
