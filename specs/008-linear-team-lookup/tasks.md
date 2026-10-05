---

description: "Task list for Linear team lookup by name or key (008-linear-team-lookup)"
---

# Tasks: Linear Team Lookup by Name or Key

**Input**: Design documents from `specs/008-linear-team-lookup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/linear-errors.md, quickstart.md

**Tests**: Included and placed before implementation in every phase (Constitution
Principle III). The HTTP layer is mocked throughout (no real network calls in CI), same
pattern as 006 - only quickstart.md's Scenario 5 uses a real Linear API key, and that's a
manual verification step, not part of the automated suite.

**Organization**: This feature is entirely internal to `linear_client.py` - no CLI, web, or
frontend file changes at all, since `--linear-team`/`linear_team_id` keep their existing
`str` type and the resolution happens inside `fetch_linear_throughput`'s own body
(data-model.md). Foundational builds the three new pieces (format detection, team-listing
pagination, name/key matching + error classification); each user story phase then verifies
one already-wired behavior end-to-end through the public `fetch_linear_throughput`
function, rather than adding new implementation of its own - US1/US2/US3 are almost
entirely verification phases, mirroring how 006/007's US3 phases usually found no gaps.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Per plan.md: every change lives inside the existing `src/agile_metrics/linear_client.py`
and `tests/test_linear_client.py` - no new files, no new top-level structure.

---

## Phase 1: Setup

- [X] T001 Add `LinearTeamAmbiguousError` to the exception hierarchy in
  `src/agile_metrics/linear_client.py`, alongside the existing `LinearAuthenticationError`/
  `LinearTeamNotFoundError`/`LinearRateLimitedError`/`LinearAPIUnavailableError`. MUST carry
  its final, user-facing message as the exception's own `str()` (data-model.md): `"Linear
  team '{value}' matches more than one team: {candidates as 'name (key)', comma-separated}
  - use a more specific value or the team's ID"`.

**Checkpoint**: Exception type exists; no detection, listing, or matching logic yet.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: `_resolve_team_id()` end-to-end - this is the one function
`fetch_linear_throughput()` calls first (US1/US2/US3 all depend on it).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### UUID-format detection

- [X] T002 Write failing tests in `tests/test_linear_client.py` for
  `_looks_like_linear_id()`: a UUID-shaped string (e.g.
  `"a1b2c3d4-e5f6-7890-abcd-ef1234567890"`) returns `True`; a team name (`"Engineering"`),
  a team key (`"ENG"`), and an empty string all return `False` (research.md §1).
- [X] T003 Implement `_looks_like_linear_id(value: str) -> bool` in `linear_client.py`
  satisfying T002, using the regex `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-
  [0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`.

### Team-listing pagination

- [X] T004 Write failing tests for `_fetch_all_teams()`: given two mocked pages
  (`hasNextPage: true` with an `endCursor`, then `hasNextPage: false`), confirm every
  `(id, name, key)` tuple across **both** pages is collected - none dropped (FR-008),
  mirroring 006's `_fetch_all_completed_at` pagination test exactly.
- [X] T005 Implement `_build_teams_query(after)` and `_fetch_all_teams(api_key)` in
  `linear_client.py` satisfying T004, reusing `_post_graphql` exactly as
  `_fetch_all_completed_at` already does (research.md §2).

### Matching and error classification

- [ ] T006 Write failing tests for `_resolve_team_id()`: an exact, case-insensitive match
  on a team's `name` resolves to its `id`; an exact, case-insensitive match on a team's
  `key` resolves to its `id`; zero matches raises the *existing* `LinearTeamNotFoundError`
  with its unchanged message (research.md §3 - not a new error); more than one match raises
  `LinearTeamAmbiguousError` naming every candidate as `"name (key)"`; a UUID-shaped value
  returns unchanged with **zero** calls to `_fetch_all_teams` (confirms the format-detection
  short-circuit, not just the matching logic).
- [ ] T007 Implement `_resolve_team_id(api_key: str, value: str) -> str` in
  `linear_client.py` satisfying T006.

**Checkpoint**: `_resolve_team_id()` is complete and fully tested in isolation. Each user
story phase below only needs to confirm it's wired in and reachable end-to-end.

---

## Phase 3: User Story 1 - Forecast using a team's name or key instead of hunting for its ID (Priority: P1) 🎯 MVP

**Goal**: A name or key value, passed through the existing `--linear-team`/
`linear_team_id` (no new flag/field), produces the same forecast as the team's raw ID.

**Independent Test**: Call `fetch_linear_throughput()` with a team's name or key (HTTP
layer mocked) and confirm it returns the identical `ThroughputHistory` supplying that
team's raw ID would.

- [ ] T008 [US1] Write a failing test in `tests/test_linear_client.py`:
  `fetch_linear_throughput()` called with a team's name (and, separately, its key) resolves
  and fetches throughput identically to calling it with that team's raw ID - same mocked
  issues, same resulting `ThroughputHistory`.
- [ ] T009 [US1] Implement the wiring in `fetch_linear_throughput()`: call
  `team_id = _resolve_team_id(api_key, team_id)` as its first line, before
  `_validate_team()`, satisfying T008. No change to the function's signature
  (data-model.md) - `cli.py`/`web.py` need no changes at all.
- [ ] T010 [US1] Run quickstart.md Scenarios 1-4 and confirm they pass.

**Checkpoint**: MVP. A user can forecast using a Linear team's name or key.

---

## Phase 4: User Story 2 - Clear errors when a name or key doesn't resolve to exactly one team (Priority: P2)

**Goal**: The "no match" and "ambiguous match" errors are reachable end-to-end through the
public `fetch_linear_throughput()` function, not just the internal resolver.

**Independent Test**: Call `fetch_linear_throughput()` with a value matching no team, then
one matching two or more teams (HTTP layer mocked), and confirm each produces the correct,
distinct message.

- [ ] T011 [US2] Write failing end-to-end tests: `fetch_linear_throughput()` with a
  name/key value matching zero teams raises the *existing* `LinearTeamNotFoundError`
  message unchanged; with a value matching two or more teams, raises
  `LinearTeamAmbiguousError` naming every candidate.
- [ ] T012 [US2] Fix any gap T011 surfaces. Expected to be none - Foundational (T001-T007)
  already defines the exact message text and classification; this task makes the
  verification-and-fix step explicit rather than assuming it, same as 006/007's US3
  phases.

**Checkpoint**: User Stories 1 AND 2 both independently complete.

---

## Phase 5: User Story 3 - Existing raw-ID usage keeps working unchanged (Priority: P3)

**Goal**: A UUID-shaped `team_id` takes the exact same code path as before this feature
existed - not just equivalent behavior, zero new calls.

**Independent Test**: Call `fetch_linear_throughput()` with a UUID-shaped `team_id` (HTTP
layer mocked) and confirm **no** team-listing request is made - only the existing
team-validation and issues-fetch calls, exactly as before.

- [ ] T013 [US3] Write a failing test asserting that, for a UUID-shaped `team_id`,
  `_fetch_all_teams` is never called (e.g. via a mock call-count assertion on
  `_post_graphql`/`urlopen` matching exactly today's pre-feature call sequence) - not merely
  that the result is correct, but that no new network activity was introduced for the
  already-working path.
- [ ] T014 [US3] Fix any gap T013 surfaces. Expected to be none - T009's wiring already
  short-circuits via `_looks_like_linear_id` before any team-listing call.

**Checkpoint**: All three user stories independently complete and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T015 [P] Update `README.md`: document that `--linear-team`/the web UI's Linear team
  field now also accepts a team's name or key, not just its raw ID; link
  `specs/008-linear-team-lookup/` from the Status section.
- [ ] T016 Run quickstart.md Scenario 5 against a real Linear workspace (resolve by name,
  then by key, confirm both match the raw-ID forecast) and the full constitution Quality
  Gate sequence (`ruff`, `mypy --strict`, `pytest --cov`, `pip-audit`, `bandit`; no frontend
  changes in this feature, so no frontend gates to re-run).
- [ ] T017 Write the PR description: confirm no new runtime dependency was introduced
  (research.md §2 - nothing to justify), and the constitution principles touched (plan.md's
  Constitution Check table). List `Closes #N` for every per-task tracking issue created by
  `/speckit-taskstoissues` for this feature, per the `/speckit-implement` fix in PR #221.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. **Blocks all three user stories** - none of
  them can call `_resolve_team_id()` before it exists and is tested.
- **User Stories (Phase 3-5)**: All depend on Foundational only. US1 (T008-T009) must land
  before US2/US3 can exercise the wired-in behavior through `fetch_linear_throughput()`
  (T011, T013) - unlike 006/007, these three stories are not independent of each other,
  since they all verify facets of the same single integration point.
- **Polish (Phase 6)**: Depends on all three user stories.

### Within Each Phase

- Tests before implementation, confirmed failing (Principle III).
- Foundational: format detection -> pagination -> matching/error classification (each
  layer builds on the last).
- Each story: write the end-to-end test -> confirm/implement -> quickstart verification.

### Parallel Opportunities

- T002 (format detection tests) and T004 (pagination tests) touch no shared code and could
  be written in parallel, though both block T006/T007.
- T015 (README) can run in parallel with T016/T017 once all three stories are done.

---

## Implementation Strategy

### MVP First

1. Phase 1 -> Phase 2 (`_resolve_team_id()`, fully tested in isolation).
2. Phase 3 (US1): name/key resolution works end-to-end through
   `fetch_linear_throughput()`.
3. **STOP and VALIDATE** with quickstart.md Scenarios 1-4. Demo it.

### Incremental Delivery

1. Setup + Foundational -> the resolver exists and is trustworthy on its own.
2. US1 -> validate -> demo (MVP!).
3. US2 -> confirms the two failure messages are reachable end-to-end, not just
   unit-tested in isolation.
4. US3 -> confirms zero regression/zero new cost for the already-working raw-ID path.
5. Polish (README, real-API quickstart scenario, quality gates, PR description) -> ready
   to merge.

---

## Notes

- `[P]` = different files or independent code paths, no dependency on incomplete tasks.
- Commit after each task or logical group.
- Clean-room (Principle I): another plain query against Linear's own public schema - no
  comparable code exists in predictability-engine to consult or avoid.
- Scenario 5 (real API) matters more than usual for this feature: research.md §2 flags that
  the team-listing query's shape has not been independently re-confirmed via live
  introspection - this feature exists *because* an unverified query shape broke twice
  already (the `$teamId: ID!`/`String!` bug and the null-data crash it masked). Don't treat
  Scenario 5 as optional.
