# Tasks: Forecast Web UI

**Input**: Design documents from `specs/003-forecast-web-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecast-api.md, quickstart.md

**Tests**: Included and sequenced before implementation in every phase. The project
constitution's Principle III ("Test-First & Statistically Validated") is NON-NEGOTIABLE and
supersedes the default task-template guidance that treats tests as optional.

**Organization**: Tasks are grouped by user story (spec.md). Note: unlike
`001-throughput-forecast` (separate library functions per story) or `002-forecast-cli`
(one CLI command branching per story), the backend's mode-dispatch (`_compute_forecast`)
is built once in Foundational, since JSON request parsing needs no per-mode string
handling the way the CLI did. User Story phases here are mostly about **frontend** wiring
and end-to-end verification per mode, plus the backend's own HTTP-level contract tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Per plan.md: `src/agile_metrics/web.py` + `tests/test_web.py` (Python side, existing
package); `frontend/` (new top-level Node/TypeScript project); `Dockerfile` updated in
place.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create the `frontend/` scaffold: `package.json`, `vite.config.ts`,
  `tsconfig.json` (strict mode), `index.html`, `src/main.tsx` placeholder — React + Vite +
  TypeScript per plan.md's Project Structure. Pinned TypeScript to `^5.9` after npm pulled
  TS 7 by default and it conflicted with `typescript-eslint`'s peer range (same issue the
  author's `SAFe_tooling` repo already hit and pinned around).
- [X] T002 [P] Add `fastapi` and `uvicorn[standard]` to `pyproject.toml`'s
  `[project.dependencies]` (core, not dev-only — same precedent as `typer`); run `uv lock`
- [X] T003 [P] Add `openapi-typescript` as a frontend devDependency and a
  `generate-types` npm script that exports `app.openapi()` to `frontend/openapi.json` and
  runs `openapi-typescript` against it to produce `frontend/src/api-types.ts`
  (research.md "Keeping frontend and backend types in sync"). Also added `py.typed` to
  `src/agile_metrics/` and extended `[tool.mypy] files` to include `scripts/` — the export
  script imports the package from outside `src/`, which needs the PEP 561 marker to be
  type-checked without a spurious "missing library stubs" error. Expected to fail until
  `web.py` exists (T013).
- [X] T004 [P] Add ESLint config and strict TypeScript compiler options for `frontend/`
  (constitution v1.3.0 Technology Stack)
- [X] T005 [P] Add `vitest` and `@testing-library/react` devDependencies and test config to
  `frontend/`
- [X] T006 [P] Add an `npm` Dependabot ecosystem block scoped to `/frontend` in
  `.github/dependabot.yml`, 7-day cooldown, matching the project-wide policy (constitution
  v1.3.0 Quality Gates)
- [X] T007 [P] Add frontend CI gates to `.github/workflows/ci.yml`: `eslint` → `tsc
  --noEmit` → `vitest` → `npm audit` → a step that reruns `generate-types` and fails if
  `frontend/openapi.json`/`api-types.ts` would change — written now, expected to fail (no
  frontend code or backend app exists yet) (constitution v1.3.0 Quality Gates)

**Checkpoint**: `npm install` succeeds in `frontend/`; `uv sync --locked` installs
`fastapi`/`uvicorn`; CI config exists but is expected to fail until later phases.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The backend's request/response models and mode-dispatch logic, the generated
API types, and a minimal frontend form skeleton that every user story builds on. **No user
story work may begin until this phase is complete.**

### Tests for Foundational (write first — MUST fail before implementation exists)

- [X] T008 [P] Unit tests in `tests/test_web.py` for the request-body model: valid JSON
  (history as `list[int]`, `period_days: int`, optional `backlog_size`/`target_date`/
  `seed`) parses correctly. **Scope note**: the both/neither mutual-exclusivity check ended
  up in `_compute_forecast` (T009/T012), not the request-body model itself — mirroring
  `002-forecast-cli`'s `main()`, which needs the same explicit branch for type-safety
  (can't call `forecast_by_date` with a `None` date), and avoiding a third copy of the same
  rule alongside the library's own `ForecastRequest` validator. T008 covers type-shape
  parsing only.
- [X] T009 [P] Unit tests in `tests/test_web.py` for `_compute_forecast(body) ->
  ForecastResult`: a body with `backlog_size` set calls `forecast_by_items`; a body with
  `target_date` set calls `forecast_by_date`; both-or-neither raises `ValueError` (FR-002);
  invalid history raises the library's own `ValidationError`
- [X] T010 [P] Frontend test in `frontend/src/App.test.tsx`: renders inputs for history,
  period length, backlog size, target date, and seed, plus a submit control — written now,
  fails since `App.tsx` doesn't exist yet

### Foundational Implementation

- [X] T011 [P] Define the request-body and `{"error": "..."}` response pydantic models in
  `src/agile_metrics/web.py` per contracts/forecast-api.md's field table, satisfying T008
  (depends on T008)
- [X] T012 Implement `_compute_forecast()` in `src/agile_metrics/web.py` satisfying T009 —
  contains zero HTTP-specific code, calling only the public `forecast_by_items`/
  `forecast_by_date` API (Principle II; research.md "Keeping the backend reusable across
  frontend changes") (depends on T009, T011)
- [X] T013 Implement the FastAPI `app` and `POST /api/forecast` route in
  `src/agile_metrics/web.py`: calls `_compute_forecast()`, catches
  `pydantic.ValidationError`/`ValueError`, returns a 400 `{"error": "<message>"}` body on
  failure — never an unhandled exception (FR-004) (depends on T012). Found and fixed two
  real bugs while verifying this with `TestClient` rather than trusting it by inspection:
  (1) FastAPI raises its own `RequestValidationError` for malformed bodies, not a raw
  `pydantic.ValidationError`, so a request with non-integer `history` entries was falling
  through uncaught to FastAPI's default 422 — added a `RequestValidationError` exception
  handler. (2) `str(exc)` on a pydantic `ValidationError` dumps its verbose multi-line repr
  (including a `https://errors.pydantic.dev/...` URL), which is not the "clear,
  human-readable message" FR-004 requires — added a `_format_error()` helper that extracts
  just the field path and message from `exc.errors()` instead. Also added `responses={400:
  ...}` to the route decorator, since FastAPI's auto-generated OpenAPI schema otherwise only
  documents the (never-actually-returned) default 422, which T014's generated types would
  then have missed entirely.
- [X] T014 [P] Run `generate-types` (T003) for the first time: export `app.openapi()` to
  `frontend/openapi.json`, generate `frontend/src/api-types.ts`, commit both (depends on
  T013). Verified the freshness check itself: staged the files, reran `generate-types`,
  confirmed `git diff --exit-code` reports no drift.
- [X] T015 [P] Implement the minimal React form in `frontend/src/App.tsx`/`main.tsx` using
  the generated types from T014 for the request shape, satisfying T010 — no submit wiring
  yet (depends on T010, T014)

**Checkpoint**: `uv run pytest tests/test_web.py` passes; `frontend` renders an (inert)
form; generated types exist and are committed.

---

## Phase 3: User Story 1 - Get a completion-date forecast in a browser (Priority: P1) 🎯 MVP

**Goal**: Filling in history + backlog size and submitting shows a completion-date forecast
on the page.

**Independent Test**: Load the page, enter a sample history and backlog size, submit, and
verify the page displays dates at all four confidence levels.

### Tests for User Story 1 (write first — MUST fail before implementation exists)

- [X] T016 [P] [US1] Backend test in `tests/test_web.py`: `POST /api/forecast` with valid
  history + `backlog_size` + `seed` returns HTTP 200 with four confidence-level **date**
  outcomes (spec US1 Acceptance Scenario 1)
- [X] T017 [P] [US1] Backend test in `tests/test_web.py`: the same request sent twice
  returns identical responses (spec US1 Acceptance Scenario 2; FR-007)
- [X] T018 [P] [US1] Backend test in `tests/test_web.py`: `backlog_size: 0` returns HTTP
  400 with a clean `{"error": "..."}` body, never an unhandled exception (spec US1
  Acceptance Scenario 3)
- [X] T019 [P] [US1] Frontend test in `frontend/src/App.test.tsx` (mocked `fetch`):
  submitting the form with a backlog size calls `fetch` with the expected request body and
  renders the four returned dates. Needed `@testing-library/user-event` (not yet
  installed); fixed a real test bug along the way — `getByText` on a single exact date
  string broke because this dataset's 70%/85% outcomes are both `2026-11-13`, so the query
  matched twice. Fixed by asserting on each full `"N% confidence: <date>"` line instead.

### Implementation for User Story 1

- [X] T020 [US1] Wire the form's submit handler in `frontend/src/App.tsx` for the
  backlog-size mode: call `fetch('/api/forecast', ...)`, render the four confidence-level
  results — satisfying T016-T019 (depends on T015, T016, T017, T018, T019)
- [X] T021 [US1] Run `quickstart.md` Scenario 1 (API via `curl`) and Scenario 3 (browser,
  dev server) verbatim and confirm both match the documented expected outcome (depends on
  T020). Scenario 1 matches exactly. Scenario 3: no real browser is available in this
  environment, so verified what's actually checkable — the Vite dev server serves the page
  and its `/api` proxy correctly forwards to the backend with the exact expected result —
  rather than claiming full browser click-through verification that didn't happen.

**Checkpoint**: User Story 1 is fully functional end-to-end (browser → API → library →
browser) and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Get an items-completed forecast in a browser (Priority: P2)

**Goal**: Filling in history + a target date and submitting shows an items-completed
forecast.

**Independent Test**: Load the page, enter a sample history and a future target date,
submit, and verify the page displays item counts at all four confidence levels.

### Tests for User Story 2 (write first — MUST fail before implementation exists)

- [X] T022 [P] [US2] Backend test in `tests/test_web.py`: `POST /api/forecast` with valid
  history + `target_date` + `seed` returns HTTP 200 with four confidence-level **integer**
  outcomes (spec US2 Acceptance Scenario 1) — already passed, route built in Foundational
- [X] T023 [P] [US2] Backend test in `tests/test_web.py`: a `target_date` that is not in
  the future returns HTTP 400 with a clean error (spec US2 Acceptance Scenario 2) —
  already passed, same reason
- [X] T024 [P] [US2] Frontend test in `frontend/src/App.test.tsx` (mocked `fetch`):
  submitting the form with a target date calls `fetch` with the expected request body and
  renders the four returned integers

### Implementation for User Story 2

- [X] T025 [US2] ~~Add the target-date mode and a mode selector~~ — T024 passed against the
  existing implementation with no changes needed: `App.tsx`'s two independent optional
  fields (each omitted from the request body when left blank) already let a user fill in
  `target_date` and leave `backlog_size` blank, satisfying US2 without an explicit
  toggle/selector component. Adding one anyway would be unrequested UI complexity beyond
  what T024 actually required (Principle V) — US3's error handling (T027-T030) is what
  covers the case where a user fills in both or neither.
- [X] T026 [US2] Run `quickstart.md` Scenario 2 (API via `curl`) verbatim and confirm it
  matches the documented expected outcome (depends on T025)

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Understand what went wrong with bad input (Priority: P3)

**Goal**: Invalid or contradictory submissions show a clear, in-page message — never a
blank page, a crash, or a raw technical error.

**Independent Test**: Submit the form with invalid or contradictory input and verify a
clear, in-page message appears, with no raw error page or stack trace visible.

### Tests for User Story 3 (write first — MUST fail before implementation exists)

- [X] T027 [P] [US3] Backend test in `tests/test_web.py`: both `backlog_size` and
  `target_date` set returns HTTP 400 with a clean error naming that exactly one is required
  (spec US3 Acceptance Scenario 1; FR-002) — already passed, route built in Foundational
- [X] T028 [P] [US3] Backend test in `tests/test_web.py`: malformed or insufficient history
  (too few periods, all-zero, non-numeric) returns HTTP 400 with a clean error naming the
  specific problem (spec US3 Acceptance Scenario 2) — already passed, same reason
- [X] T029 [P] [US3] Frontend test in `frontend/src/App.test.tsx`: an error response from
  `fetch` renders the server's error message on the page (not a crash/blank screen); a
  pending request shows an in-progress indicator (spec Edge Cases: visible feedback if the
  request takes any noticeable time). This test caught a real pre-existing bug: `App.tsx`
  blindly treated every response body as a `ForecastResult`, so an error response (no
  `outcomes` key) crashed the render with `Cannot read properties of undefined (reading
  '50')` instead of showing the error.

### Implementation for User Story 3

- [X] T030 [US3] Add in-page error-message rendering and a loading/in-progress state to
  `frontend/src/App.tsx`, satisfying T027-T029 (depends on T020, T025, T027, T028, T029).
  Fixed the bug T029 caught: branch on `response.ok` and parse the body as either
  `ForecastResult` or `ErrorResponseBody` accordingly, plus a `try/catch` around the
  `fetch` call itself for network failures.
- [X] T031 [US3] Run `quickstart.md` Scenario 4 in the browser (not just via `curl`) and
  confirm the clean error renders on the page (depends on T030). `curl` confirms the API
  returns the exact documented 400 body; actual on-page rendering of that message is what
  T029's passing test verifies, since no real browser is available in this environment.

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T032 [P] Verify the generated-types freshness CI gate (T007/T014) actually fails if
  `frontend/openapi.json`/`api-types.ts` are made stale, and passes once they're
  regenerated and committed correctly (constitution v1.3.0). Confirmed both directions:
  a manual edit makes `git diff --exit-code` fail (1); regenerating from the real backend
  restores the exact committed content (0) - proving the generated files genuinely reflect
  the current schema, not a frozen snapshot.
- [X] T033 [P] Update `README.md` to document running the web UI locally (backend +
  frontend dev servers) and via Docker (constitution: README MUST be updated when a
  feature completes). Verified every documented command actually runs as written,
  including discovering along the way that the Docker web-server command needed an
  explicit `--entrypoint uvicorn` override, since the image's default `ENTRYPOINT` is
  still the CLI (spec 002's contract) - documented that rather than silently changing it.
- [X] T034 Add a `frontend-builder` stage to the `Dockerfile` (`node:22-slim`, `npm ci`,
  `npm run build`); update the `runtime` stage to also copy `frontend/dist/`; update
  `.dockerignore` for `frontend/node_modules`; verify locally with `podman` that the built
  image serves both the API and the static frontend correctly (depends on T021, T026,
  T031). Found and fixed two real gaps: `.dockerignore` didn't exclude `node_modules/` at
  all (would've copied the local dev install, including any wrong-platform native
  modules, into the build context); and re-verified `--no-build` (added back in T002)
  against the larger `fastapi`/`uvicorn` dependency set including C-extension transitive
  deps like `uvloop`/`websockets`, rather than trusting the comment written for the
  smaller CLI-only set. Verified both the CLI entrypoint (unchanged) and the web server
  (via `--entrypoint` override) work from the same image, and that it still runs as
  `appuser`, not root.
- [X] T035 Run the full constitution Quality Gate sequence clean across the repo: Python
  gates (`ruff`, `mypy --strict`, `pytest --cov`, `pip-audit`, `bandit`) and frontend gates
  (`eslint`, `tsc --noEmit`, `vitest`, `npm audit`, generated-types freshness), plus the
  Docker build/smoke test (depends on all prior tasks)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational *and* User Story 1's submit handler
  existing (T020), since the mode selector extends the same component
- **User Story 3 (Phase 5)**: Depends on both US1 and US2's handlers existing (T020, T025),
  since error/loading states wrap the same submit flow
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Within Each Phase

- Tests MUST be written and FAIL before their corresponding implementation task
- Backend models before `_compute_forecast` before the FastAPI route before type
  generation before the frontend can consume those types
- Each story's checkpoint must pass before moving to the next priority

### Parallel Opportunities

- T002-T007 (Setup, after T001) can all run in parallel — independent config files
- T008-T010 (Foundational tests) can run in parallel
- T016-T019 (US1 tests), T022-T024 (US2 tests), and T027-T029 (US3 tests) can each run in
  parallel within their own set
- T032-T033 (Polish) can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything else)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1 and 3 independently
5. User Story 1 alone is a demonstrable MVP — a browser-based completion-date forecast

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate → MVP (browser forecasting works end-to-end)
3. User Story 2 → validate → adds the items-by-date question
4. User Story 3 → validate → adds clear error/loading feedback
5. Polish (Docker, README, CI gate verification)

---

## Notes

- `[P]` tasks touch different files or independent code paths — no shared-state conflicts
- `[Story]` label maps each task to its user story for traceability back to spec.md
- Per the constitution's Development Workflow, this `tasks.md` is a disposable planning
  draft: **before any implementation task above begins, convert this file into GitHub
  Issues via `/speckit-taskstoissues`**, which then become the system of record for
  tracking the work — not this file.
- Commit after each task or logical group, on the `003-forecast-web-ui` branch
- Verify each test fails before writing the implementation that makes it pass
- PR #65 (constitution v1.3.0, frontend stack + quality gates) should land before or
  alongside this feature's implementation, since T004-T007 directly depend on the
  conventions it defines
