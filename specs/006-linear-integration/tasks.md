---

description: "Task list for Linear integration (006-linear-integration)"
---

# Tasks: Linear Integration

**Input**: Design documents from `specs/006-linear-integration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecast-api.md, quickstart.md

**Tests**: Included and placed before implementation in every phase (Constitution
Principle III). The Linear HTTP layer is mocked throughout (no real network calls in CI) -
only quickstart.md's scenarios 6-7 use a real Linear API key, and those are manual
verification steps, not part of the automated suite.

**Organization**: `linear_client.py` (query building, pagination, bucketing, error
classification) is needed by both the web UI (US1) and the CLI (US2), so it's built once in
Foundational. Each story then wires its own surface (web request body / CLI flags) on top
of the same shared function. US3 (error clarity) is mostly verification that Foundational +
US1 + US2 already produce the right distinct messages, not new production code - the
exceptions carry their final user-facing message text themselves (data-model.md), so
"surfacing" them is one `except` clause per surface, already added in US1/US2.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Per plan.md: one new backend module (`src/agile_metrics/linear_client.py`), additive
changes to `src/agile_metrics/cli.py` and `src/agile_metrics/web.py`, additive changes to
`frontend/src/App.tsx`. No new top-level directories.

---

## Phase 1: Setup

- [X] T001 Create `src/agile_metrics/linear_client.py` with the exception hierarchy:
  `LinearIntegrationError` (base), `LinearAuthenticationError`, `LinearTeamNotFoundError`,
  `LinearRateLimitedError`, `LinearAPIUnavailableError`. Each MUST carry its final,
  user-facing message as the exception's own `str()` (data-model.md) - no new message
  formatting needed later in the CLI/web layers, same pattern as the existing `ValueError`
  handling.
- [X] T002 [P] Create `tests/test_linear_client.py` with a reusable test helper that mocks
  `urllib.request.urlopen` to return a given status code + JSON body, for use by every
  later test task in this file (plan.md Testing: the HTTP layer is the only thing that
  needs mocking - query-building/bucketing is otherwise pure).

**Checkpoint**: Module and test scaffolding exist; no HTTP or business logic yet.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: `fetch_linear_throughput()` end-to-end - this is the one function both US1 and
US2 call.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Query building and pagination

- [X] T003 Write failing tests in `tests/test_linear_client.py` for the two query shapes
  from research.md §2: the team-validation query (`team(id: $teamId) { id name }`) and the
  paginated issues query (`issues(filter: { team: { id: { eq: $teamId } }, completedAt: {
  gte: $since, null: false } }, first: 100, after: $after) { nodes { completedAt }
  pageInfo { hasNextPage endCursor } }`). Assert on the built query string/variables, no
  network.
- [X] T004 Implement the query-building functions in `linear_client.py` satisfying T003.
- [X] T005 Write failing tests for pagination: given two mocked pages (`hasNextPage: true`
  with an `endCursor`, then `hasNextPage: false`), confirm every `completedAt` value across
  **both** pages is collected - none dropped (FR-009/FR-010/SC-004).
- [X] T006 Implement the paginated-fetch loop in `linear_client.py`, looping on
  `pageInfo.hasNextPage` satisfying T005.

### Error classification

- [X] T007 Write failing tests for each detection rule in research.md §3: HTTP 401 with
  `errors[].extensions.code == "AUTHENTICATION_ERROR"` raises `LinearAuthenticationError`;
  HTTP 400 with `errors[].extensions.code == "RATELIMITED"` raises
  `LinearRateLimitedError`; a simulated connection error or any 5xx raises
  `LinearAPIUnavailableError`; a team-validation response with `data.team == null` raises
  `LinearTeamNotFoundError`.
- [X] T008 Implement the error classification satisfying T007, wired into the fetch loop
  from T006 and the team-validation call.
- [X] T009 Write a failing test asserting the API key used in a mocked call never appears
  in any of the four exceptions' `str()` representation (FR-006; plan.md's Secrets gate).
- [X] T010 Fix T009 if it fails (expected to pass already, since the key is never
  interpolated into any exception message by construction - this task exists to make the
  check explicit, not because a fix is anticipated).

### Bucketing and the public entrypoint

- [X] T011 Write failing tests for bucketing: given a fixed set of mocked `completedAt`
  values, `periods`, and `period_duration`, confirm bucket `k` (0 = oldest) covers `[today -
  (periods - k) * period_duration, today - (periods - k - 1) * period_duration)` exactly
  (data-model.md's formula) and the result is a valid `ThroughputHistory`. Include: a case
  with zero completed issues in range - confirm it raises `pydantic.ValidationError` with
  the *existing* all-zero message already pinned in `test_models.py`, not a new error
  (FR-010); and a case producing fewer than `MIN_HISTORICAL_PERIODS` buckets - confirm the
  *existing* too-few-periods message (FR-004).
- [X] T012 Implement the bucketing logic and the public `fetch_linear_throughput(api_key,
  team_id, period_duration, periods=26)` entrypoint in `linear_client.py`, wiring together
  team validation (T008), the paginated fetch (T006/T008), and bucketing - returning a
  `ThroughputHistory` or propagating one of the four `LinearIntegrationError` subclasses or
  the *existing* `ThroughputHistory` validators unchanged, satisfying T011.

**Checkpoint**: `fetch_linear_throughput()` is complete and fully tested in isolation. Both
user story phases below only need to call it.

---

## Phase 3: User Story 1 - Forecast from Linear in the web UI (Priority: P1) 🎯 MVP

**Goal**: A user can get a forecast through the web UI using Linear import instead of
manual paste.

**Independent Test**: `POST /api/forecast` with `linear_api_key`/`linear_team_id` (HTTP
layer mocked) instead of `history` returns the same 200 response shape as manual paste.

### Backend

- [X] T013 [US1] Write a failing test in `tests/test_web.py`: `ForecastRequestBody` accepts
  `linear_api_key: str | None`, `linear_team_id: str | None`, `linear_periods: int | None`,
  and `history` is now optional; constructing it with neither `history` nor both Linear
  fields, or with both groups present, raises the "exactly one of" `ValueError`
  (contracts/forecast-api.md).
- [X] T014 [US1] Update `ForecastRequestBody` in `web.py`: `history: list[int] | None =
  None`, add the three new optional fields, satisfying T013.
- [X] T015 [US1] Write a failing test: `_compute_forecast` with Linear fields set (mocked
  `fetch_linear_throughput`) builds the same kind of `ThroughputHistory` manual paste would,
  then proceeds through the unchanged `forecast_by_items`/`forecast_by_date` call (FR-003).
- [X] T016 [US1] Implement the branch in `_compute_forecast` (`web.py`): call
  `fetch_linear_throughput` when Linear fields are present instead of `history`, applying
  the "exactly one of" check first, satisfying T015.
- [X] T017 [US1] Write a failing test: `POST /api/forecast` in Linear mode (HTTP layer
  mocked) returns the identical 200 response shape manual-paste mode already returns for
  the same underlying per-period counts.
- [X] T018 [US1] Catch `LinearIntegrationError` alongside the existing
  `ValidationError`/`ValueError` in `post_forecast` (`web.py`), rendering `str(exc)` through
  the existing 400 `{"error": "..."}` path - no new formatting code (contracts/forecast-api.md).

### Frontend

- [X] T019 [US1] Regenerate `frontend/openapi.json` and `frontend/src/api-types.ts`
  (`npm run generate-types`) now that `ForecastRequestBody` has changed, and commit both.
- [X] T020 [US1] Write a failing test in `frontend/src/App.test.tsx`: a data-source toggle
  ("Manual paste" / "Linear") shows the history textarea in manual mode and the API-key/
  team/periods fields in Linear mode, never both at once.
- [X] T021 [US1] Implement the toggle and the three new fields in `frontend/src/App.tsx`,
  satisfying T020 - the API-key field MUST use `type="password"` (never logged to the
  console, never written to any persisted state - FR-005/FR-006 applied client-side).
- [X] T022 [US1] Write a failing test: submitting the form in Linear mode (mocked `fetch`)
  sends `linear_api_key`/`linear_team_id`/`linear_periods` instead of `history` in the
  POST body, and renders the same four-confidence-level results and charts (spec 005,
  unmodified) as the manual-paste success path already does.
- [X] T023 [US1] Implement the submit-handler changes in `frontend/src/App.tsx` satisfying
  T022.
- [X] T024 [US1] Run quickstart.md Scenarios 1-3 and 5 and confirm they pass.

**Checkpoint**: MVP. A user can get a Linear-backed forecast through the web UI.

---

## Phase 4: User Story 2 - Use Linear import from the CLI (Priority: P2)

**Goal**: The same Linear-backed forecast is available from the command line.

**Independent Test**: Running the CLI with `--linear-api-key`/`--linear-team` (HTTP layer
mocked) instead of `--history` prints the same output format as manual-paste mode.

- [X] T025 [US2] Write a failing test in `tests/test_cli.py`: `--history` is optional; new
  `--linear-api-key`, `--linear-team`, `--linear-periods` (default 26) options exist;
  `--linear-api-key` is also readable from the `AGILE_METRICS_LINEAR_API_KEY` environment
  variable when the flag is omitted.
- [X] T026 [US2] Update `cli.py`: make `--history` optional, add the three new Typer
  options (`--linear-api-key` with `envvar="AGILE_METRICS_LINEAR_API_KEY"`,
  `--linear-team`, `--linear-periods` defaulting to 26), satisfying T025.
- [X] T027 [US2] Write a failing test: running the CLI in Linear mode (HTTP layer mocked)
  prints the identical output `_render_result` already produces for manual-paste mode with
  the same underlying per-period counts.
- [X] T028 [US2] Implement the branch in the CLI's `main()`: build `ThroughputHistory` from
  `--history` OR `fetch_linear_throughput(...)`, same "exactly one of" validation as the web
  layer (T016), satisfying T027.
- [X] T029 [US2] Catch `LinearIntegrationError` in the CLI's existing exception handling,
  rendering the same `Error: <message>` on stderr / exit code 1 pattern already used for
  `ValueError`/`ValidationError` - no new formatting code.
- [X] T030 [US2] Run quickstart.md Scenario 4 and confirm it passes.

**Checkpoint**: User Stories 1 AND 2 both independently complete - Linear-backed
forecasting works from both the web UI and the CLI.

---

## Phase 5: User Story 3 - Clear errors when Linear access fails (Priority: P3)

**Goal**: Every distinct Linear-side failure produces its own specific, actionable message,
through both surfaces.

**Independent Test**: Submitting a forecast with an invalid key, then an inaccessible team,
then a team with zero completed issues, produces three distinct, correct messages - via
both the web API and the CLI.

- [X] T031 [US3] Write failing end-to-end tests (web **and** CLI, HTTP layer mocked) for
  each of the four `LinearIntegrationError` cases from contracts/forecast-api.md's error
  table: invalid/expired credential, inaccessible team, rate-limited, API unavailable -
  asserting the exact message text from the error table appears, distinct per case.
- [X] T032 [US3] Write failing end-to-end tests (web and CLI) for the two cases that reuse
  *existing* validators: zero completed issues and fewer-than-minimum periods - asserting
  the *existing* all-zero/too-few-periods message appears unchanged, confirming no
  Linear-specific duplicate error was introduced (FR-010).
- [X] T033 [US3] Fix any gap T031/T032 surface. Expected to be none - Foundational (T001-T012)
  already defines the exact message text, and US1/US2's `except LinearIntegrationError`
  clauses (T018, T029) already surface it unchanged on both surfaces. This task makes the
  verification-and-fix step explicit rather than assuming it. No gaps found - all 18 new
  tests passed on first run.

**Checkpoint**: All three user stories independently complete and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T034 [P] Update `README.md`: document Linear-backed forecasting (the
  `AGILE_METRICS_LINEAR_API_KEY` environment variable, the new CLI flags, the web UI
  toggle), and link `specs/006-linear-integration/` from the Status section (constitution:
  README updated in the completing PR).
- [ ] T035 Run quickstart.md Scenarios 6 and 7 (real Linear API key + team) manually and
  confirm the forecast looks correct against the real workspace.
- [ ] T036 Run the full constitution Quality Gate sequence clean across the repo: `ruff`,
  `mypy --strict`, `pytest --cov`, `pip-audit`, `bandit`, `eslint`, `tsc --noEmit`,
  `vitest`, `npm audit`, and the generated-types freshness check.
- [ ] T037 Write the PR description: confirm no new runtime dependency was introduced
  (research.md §5 - nothing to justify), and the constitution principles touched
  (plan.md's Constitution Check table).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. **Blocks both US1 and US2** - neither story
  can call `fetch_linear_throughput()` before it exists and is tested.
- **User Stories (Phase 3-4)**: Both depend on Foundational only, not on each other - US1
  and US2 touch disjoint files (web.py+frontend vs. cli.py) and could be done in either
  order or in parallel by different people.
- **US3 (Phase 5)**: Depends on US1 **and** US2 - it verifies both surfaces.
- **Polish (Phase 6)**: Depends on all three user stories.

### Within Each Phase

- Tests before implementation, confirmed failing (Principle III).
- Foundational: query-building -> pagination -> error classification -> bucketing ->
  public entrypoint (each layer builds on the last).
- Each story: backend test -> backend implementation -> (US1 only) frontend test ->
  frontend implementation -> quickstart verification.

### Parallel Opportunities

- T002 can run alongside T001 (different files).
- Once Foundational (T001-T012) is done, User Story 1 (T013-T024) and User Story 2
  (T025-T030) touch no shared files and could proceed in parallel.
- T034 (README) can run in parallel with T035/T036 once all three stories are done.

---

## Implementation Strategy

### MVP First

1. Phase 1 -> Phase 2 (the shared `fetch_linear_throughput()`, fully tested in isolation).
2. Phase 3 (US1): Linear-backed forecasting works end-to-end through the web UI.
3. **STOP and VALIDATE** with quickstart.md Scenarios 1-3 and 5. Demo it.

### Incremental Delivery

1. Setup + Foundational -> the adapter function exists and is trustworthy on its own.
2. US1 (web) -> validate -> demo (MVP!).
3. US2 (CLI) -> validate -> demo.
4. US3 -> confirms both surfaces fail clearly, not just succeed clearly.
5. Polish (README, full quality gates, PR description) -> ready to merge.

---

## Notes

- `[P]` = different files, no dependency on incomplete tasks.
- Commit after each task or logical group.
- Clean-room (Principle I): this adapter is built from Linear's own public, documented
  GraphQL schema (confirmed via live introspection during planning) - no comparable code
  exists in predictability-engine to consult or avoid.
