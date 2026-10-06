---

description: "Task list for Jira integration (010-jira-integration)"
---

# Tasks: Jira Integration - Import Throughput from Resolved Issues

**Input**: Design documents from `specs/010-jira-integration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/forecast-api.md,
contracts/jira-errors.md, quickstart.md

**Tests**: Included and placed before implementation in every phase (Constitution Principle
III). The HTTP layer is mocked throughout; no network calls in CI. quickstart.md Scenario 5
(real Jira Cloud site) is a manual pre-merge gate, tracked in Polish.

**Organization**: One new backend module (`jira_client.py`) holds all the adapter logic. Each
user story phase adds one behavior and wires it through the public `fetch_jira_throughput()`
function. CLI and web changes are split per story so each stays independently verifiable.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Per plan.md: `src/agile_metrics/jira_client.py` (new), `src/agile_metrics/cli.py` and
`src/agile_metrics/web.py` (additive), `tests/test_jira_client.py` (new), `tests/test_cli.py`,
`tests/test_web.py`, `frontend/src/App.tsx`, `frontend/src/App.test.tsx`.

---

## Phase 1: Setup

- [ ] T001 Create `src/agile_metrics/jira_client.py` with a module docstring describing the
  Jira Cloud adapter (spec 010) and empty `__all__ = []`, and create `tests/test_jira_client.py`
  with its module docstring only. No logic yet.

**Checkpoint**: Both files exist and import cleanly (`uv run python -c "import agile_metrics.jira_client"`).

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Connection value type, error taxonomy, and the HTTP seam every later task uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Connection type and token masking

- [ ] T002 Write failing tests in `tests/test_jira_client.py` for `JiraConnection` (research
  §7, data-model.md): a connection built with `site="acme.atlassian.net"`, `email`,
  `api_token="secret-token-123"`, `project_key="ENG"`, `periods=26`, `period_days=7` exposes
  those fields; `repr()` and `str()` of the connection do **not** contain `secret-token-123`;
  `site` containing a scheme (`https://...`) or a path is rejected with `ValueError`; an empty
  `api_token` is rejected.
- [ ] T003 Implement `JiraConnection` as a frozen dataclass in
  `src/agile_metrics/jira_client.py`, with a `__repr__` that masks `api_token` (e.g.
  `api_token='***'`), and validation in `__post_init__` for the site format and non-empty
  required fields, satisfying T002.

### Error taxonomy

- [ ] T004 Write failing tests in `tests/test_jira_client.py` that each category in
  `contracts/jira-errors.md` is its own exception type, subclassing one shared
  `JiraIntegrationError`, and that its `str()` equals the exact message in the contract
  (for example `Jira project 'ENG' was not found or is not visible to this account`). Cover
  all seven: authentication, site not Jira, project not found, rate limited (with and without
  a retry-after value), API unavailable, no done statuses.
- [ ] T005 Implement the exception classes in `src/agile_metrics/jira_client.py` satisfying
  T004. Message text is passed in by the raising code; the classes add no secrets.

### HTTP seam

- [ ] T006 Write failing tests for `_jira_get(connection, path)` and `_jira_post(connection,
  path, body)` in `tests/test_jira_client.py` with `urllib.request.urlopen` patched: the
  `Authorization` header is `Basic base64(email:api_token)`; the URL is
  `https://<site>` + `path`; a JSON body is decoded; a `URLError` raises the site-not-Jira error;
  a 401/403 raises the authentication error; a 429 raises the rate-limited error with the
  `Retry-After` value when present; a 5xx raises the API-unavailable error.
- [ ] T007 Implement `_jira_get` and `_jira_post` in `src/agile_metrics/jira_client.py` with
  `urllib.request` and `base64`, using a 30-second timeout, satisfying T006. Map HTTP errors to
  the T005 exception types; never include the header or token in any message.
- [ ] T008 Write a failing test asserting the API token does not appear in `str()` of any
  exception raised by T007's paths, including a forced `URLError` whose reason string contains
  the token text. Implement the scrubbing in T007 to make it pass.

**Checkpoint**: Connection, errors, and HTTP seam are complete and tested in isolation. No
user story has been started; every story below calls these.

---

## Phase 3: User Story 1 - Forecast from a Jira project's throughput instead of pasting it (Priority: P1) 🎯 MVP

**Goal**: `fetch_jira_throughput(connection)` returns a `ThroughputHistory` whose per-period
counts equal the number of resolved, non-epic, non-sub-task issues in each UTC period of the
lookback window, with done statuses detected from the project's workflow.

**Independent Test**: Mock the Jira responses for a project with known resolved issues; confirm
the returned `completed_per_period` matches the hand-computed counts, and that the done-status
set reflects the project's `done` categories.

### Tests for User Story 1 ⚠️ (write first, confirm failing)

- [ ] T009 [P] [US1] Write failing tests in `tests/test_jira_client.py` for the done-status
  mapping (research §3): given a mocked `GET /rest/api/3/project/ENG/statuses` response with
  issue types whose statuses carry `statusCategory.key` values `done`, `indeterminate`, and
  `new`, `_detect_done_statuses()` returns exactly the names whose category is `done`; a name
  classified `done` in one issue type and not another counts as done; a project with zero
  `done` statuses raises the "no done statuses" error.
- [ ] T010 [P] [US1] Write failing tests for the bucketing and window rules (research §5,
  spec FR-003, clarification Q5): an issue with `resolutiondate` `2026-09-30T23:30:00-02:00`
  (which is 01:30 UTC on 2026-10-01) counts in the UTC period starting 2026-10-01; an issue with
  no `resolutiondate` is excluded; an issue outside the lookback window is excluded even when the
  widened JQL window returned it.
- [ ] T011 [P] [US1] Write failing tests for issue-type exclusion (research §4, FR-002,
  clarification Q1): an issue whose `issuetype.subtask` is `true` is excluded; an issue whose
  `issuetype.hierarchyLevel` is the epic level is excluded; stories, tasks, and bugs are kept.
- [ ] T012 [P] [US1] Write failing tests for cursor pagination (research §1): a mocked
  `POST /rest/api/3/search/jql` sequence (first page with `nextPageToken` and `isLast: false`,
  second page with `isLast: true`) yields every issue across both pages in order, and the second
  request carries the first response's `nextPageToken`. A response missing `issues` raises the
  API-unavailable error (research §6 hardening).
- [ ] T013 [US1] Write a failing end-to-end test in `tests/test_jira_client.py`:
  `fetch_jira_throughput(connection)` with the HTTP layer mocked (identity call, statuses call,
  two issue pages) returns a `ThroughputHistory` whose `completed_per_period` equals the
  hand-computed counts, and whose done-status set is available to the caller.

### Implementation for User Story 1

- [ ] T014 [P] [US1] Implement `_detect_done_statuses(connection) -> set[str]` in
  `src/agile_metrics/jira_client.py` calling `GET /rest/api/3/project/{key}/statuses`, satisfying
  T009. Raise the no-done-statuses error when the set is empty.
- [ ] T015 [P] [US1] Implement `_bucket_resolved(issues, periods, period_days, today)` in
  `src/agile_metrics/jira_client.py`, reusing the bucket formula from
  `csv_item_import._bucket_items` / `linear_client._bucket_completed_at` (same convention, not a
  copy-paste - a shared helper is extracted only if the three become identical), satisfying T010.
  Convert `resolutiondate` to UTC before bucketing.
- [ ] T016 [US1] Implement issue-type filtering in `src/agile_metrics/jira_client.py` inside the
  fetch loop (exclude `subtask` and epic-level issue types), satisfying T011.
- [ ] T017 [US1] Implement `_fetch_resolved_issues(connection, done_statuses, window_start,
  window_end)` in `src/agile_metrics/jira_client.py`: a JQL query for `project = <key> AND
  status in (<done statuses>) AND resolved >= <window_start - 1 period> AND resolved <=
  <window_end + 1 period>`, paged with `nextPageToken` until `isLast`, satisfying T012.
- [ ] T018 [US1] Implement `fetch_jira_throughput(connection: JiraConnection) ->
  ThroughputHistory` in `src/agile_metrics/jira_client.py`: identity check, done-status
  detection, paged fetch, issue-type filter, UTC bucketing, then construct `ThroughputHistory`
  (reusing its existing validators for too-few-periods and all-zero), satisfying T013.

**Checkpoint**: The adapter works end to end through the public function with mocked HTTP.
User Story 1 is independently testable at the library level.

### CLI and web wiring for User Story 1

- [ ] T019 [US1] Write failing tests in `tests/test_cli.py` for the four Jira options
  (`--jira-site`, `--jira-email`, `--jira-api-token`, `--jira-project`, `--jira-periods`, default
  26) and the `AGILE_METRICS_JIRA_API_TOKEN` env fallback (contracts/forecast-api.md): with all
  four given and `fetch_jira_throughput` mocked, the forecast prints and the `Done statuses:`
  line lists the mocked done statuses.
- [ ] T020 [US1] Add the four `--jira-*` options and the `AGILE_METRICS_JIRA_*` env fallbacks to
  the command in `src/agile_metrics/cli.py`, and route a complete Jira set to
  `fetch_jira_throughput`, satisfying T019.
- [ ] T021 [US1] Write failing tests in `tests/test_cli.py`: after the confidence lines, a
  `Done statuses: <comma-separated>` line is printed only when the source is Jira; manual,
  Linear, and CSV output is unchanged.
- [ ] T022 [US1] Implement the `Done statuses:` line in `src/agile_metrics/cli.py`'s rendering,
  satisfying T021 (source-aware: the renderer receives the done-status list, empty for other
  sources).
- [ ] T023 [US1] Write failing tests in `tests/test_web.py` for the `jira_site`, `jira_email`,
  `jira_api_token`, `jira_project_key`, `jira_periods` request fields: a complete set calls
  `fetch_jira_throughput` (mocked) and the response includes `done_statuses`; the response's
  existing fields are unchanged.
- [ ] T024 [US1] Add the Jira request fields to `ForecastRequestBody` and `done_statuses: list[str]`
  (default `[]`) to `ForecastResponseBody` in `src/agile_metrics/web.py`, and route a complete Jira
  set in `_build_history`, satisfying T023.

**Checkpoint**: User Story 1 is complete through CLI and JSON API. MVP reached.

---

## Phase 4: User Story 2 - Clear, specific errors for authentication and access problems (Priority: P2)

**Goal**: Each failure category reaches the user as its own message through the public function,
the CLI, and the web API.

**Independent Test**: Trigger each category (bad token, bad site, unknown project, rate limit,
unavailable API, no done statuses) and confirm each produces its own message, none containing
the token.

### Tests for User Story 2 ⚠️

- [ ] T025 [P] [US2] Write failing end-to-end tests in `tests/test_jira_client.py`: `401` on
  `/myself` raises the authentication error through `fetch_jira_throughput`; a `URLError` on
  `/myself` raises the site-not-Jira error naming the site; `404` on the statuses call raises the
  project-not-found error with the exact contract text; a `429` with `Retry-After: 30` raises the
  rate-limited error whose message says `30 seconds`.
- [ ] T026 [P] [US2] Write failing tests in `tests/test_web.py` and `tests/test_cli.py`: each
  category surfaces as HTTP 400 `{"error": ...}` (web) and as an error exit with the same text
  (CLI), with the token absent from both.
- [ ] T027 [P] [US2] Write a failing test for the FR-007 non-disclosure rule in
  `tests/test_jira_client.py`: a `403` on the statuses call (project visible to nobody) produces
  the same "not found or not visible" message as a `404`, so the two cannot be distinguished.

### Implementation for User Story 2

- [ ] T028 [US2] Fix any gap T025-T027 surfaces in `src/agile_metrics/jira_client.py` and wire
  the error mapping in `src/agile_metrics/web.py` and `src/agile_metrics/cli.py` if the
  surfaces don't already route `JiraIntegrationError` subclasses. Expected to be small: the
  mapping lives in the exception classes (T005).

**Checkpoint**: User Stories 1 AND 2 independently complete.

---

## Phase 5: User Story 3 - Same forecast regardless of which source supplied the history (Priority: P3)

**Goal**: A Jira-sourced history and a manually pasted history with identical counts produce
identical forecasts for the same seed.

**Independent Test**: Mock a Jira fetch producing counts `[3, 5, 4, 6, 2, 5, 4, 3]`, forecast from
it and from manual paste of the same counts with seed 42, and compare outcomes.

- [ ] T029 [US3] Write a failing test in `tests/test_jira_client.py` (or `tests/test_web.py`):
  the `ThroughputHistory` from a mocked Jira fetch with counts `[3, 5, 4, 6, 2, 5, 4, 3]`,
  passed to `forecast_by_items` with `backlog_size=20, seed=42`, produces the same outcomes as
  `ThroughputHistory(completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3], ...)` passed directly.
- [ ] T030 [US3] Fix any gap T029 surfaces. Expected to be none: the adapter returns the same
  `ThroughputHistory` type, so the forecasting path is identical by construction.

**Checkpoint**: All three user stories independently complete.

---

## Phase 6: Frontend (cross-cutting for the web surface)

- [ ] T031 Write failing tests in `frontend/src/App.test.tsx` for a Jira source option: selecting
  it shows site, email, API token (password input), and project key fields and hides the other
  source fields; submitting sends `jira_site`, `jira_email`, `jira_api_token`, `jira_project_key`
  (and `jira_periods` when set) instead of `history`; the response's `done_statuses` renders as a
  `Done statuses:` line only for Jira results.
- [ ] T032 Regenerate `frontend/openapi.json` and `frontend/src/api-types.ts` (`npm run
  generate-types` in `frontend/`) so the new request and response fields exist in the types.
- [ ] T033 Implement the Jira source option, fields, and `Done statuses:` line in
  `frontend/src/App.tsx`, satisfying T031. Follow the existing Linear/CSV pattern (a small
  per-source helper, no nested ternaries - the Sonar lesson from PR #250).

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T034 [P] Update `README.md`: document the Jira source (site, email, API token and its env
  var, project key, lookback periods, Cloud-only scope); add a Status bullet and link
  `specs/010-jira-integration/`.
- [ ] T035 [P] Extend the "exactly one of" source-selection message in `src/agile_metrics/cli.py`
  and `src/agile_metrics/web.py` to name all four sources, and add partial-credential messages for
  the Jira fields in the same style as the Linear fix (spec 006 follow-up). Tests first.
- [ ] T036 Run the live gate: quickstart.md Scenario 5 against a real Jira Cloud site. Confirm
  `issuetype.subtask` and `issuetype.hierarchyLevel` exist in the real search response and that
  the forecast's counts agree with a manual JQL count. If a field name differs, correct
  `jira_client.py` and its tests before merging (the Linear `$teamId` lesson).
- [ ] T037 Run quickstart.md Scenario 6 quality gates: `ruff check`, `ruff format --check`,
  `mypy --strict src`, `pytest --cov`, `pip-audit`, `bandit -c pyproject.toml -r src/`, and the
  frontend gates (`npm run lint`, `npm run typecheck`, `npm test`, `npm audit`, run in the
  node:22 container).
- [ ] T038 Write the PR description: confirm no new runtime dependency (plan.md Technical Context),
  the constitution principles touched (plan.md Constitution Check), and list `Closes #N` for every
  per-task tracking issue created by `/speckit-taskstoissues` for this feature.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. **Blocks all user stories** - every story calls
  the connection type, the errors, or the HTTP seam.
- **User Story 1 (Phase 3)**: Depends on Foundational. The MVP.
- **User Story 2 (Phase 4)**: Depends on US1's public function (T018) and its CLI/web wiring
  (T020, T024) to have anything to surface.
- **User Story 3 (Phase 5)**: Depends on US1 (T018).
- **Frontend (Phase 6)**: Depends on US1's web wiring (T024).
- **Polish (Phase 7)**: Depends on all of the above. T036 (live gate) must complete before the PR.

### Within Each Phase

- Tests before implementation, confirmed failing (Principle III).
- Foundational: connection (T002-T003) and errors (T004-T005) before the HTTP seam (T006-T008),
  since the seam raises the errors.
- US1: the four helper tests (T009-T012) are independent and marked [P]; T013 (end-to-end) follows
  them; implementation T014-T017 feeds T018.

### Parallel Opportunities

- T009, T010, T011, T012 touch the same test file but independent test functions - write in one
  sitting, or split by class if working in parallel.
- T014 and T015 are different functions in the same module - not truly parallel in one file.
- T034 and T035 touch different files and can run in parallel.

---

## Implementation Strategy

### MVP First

1. Phase 1 -> Phase 2 (connection, errors, HTTP seam, all tested in isolation).
2. Phase 3 (US1): the adapter plus CLI and JSON API wiring.
3. **STOP and VALIDATE** with quickstart.md Scenarios 1-4 (mocked). Demo the mocked path.

### Incremental Delivery

1. Foundational -> the building blocks are trustworthy.
2. US1 -> validate -> MVP.
3. US2 -> every failure is specific and actionable.
4. US3 -> parity guarantee.
5. Frontend, then Polish including the live gate (T036) -> ready to merge.

---

## Notes

- `[P]` = different functions or files with no dependency on an incomplete task.
- Commit after each task or logical group.
- Clean-room (Principle I): built from Atlassian's public REST documentation (research header).
- The live gate T036 matters most for this feature: research §4 flags the issue-type fields as
  unverified against a real response. Do not skip it.
