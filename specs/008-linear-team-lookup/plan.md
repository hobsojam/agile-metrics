# Implementation Plan: Linear Team Lookup by Name or Key

**Branch**: `008-linear-team-lookup` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-linear-team-lookup/spec.md`

## Summary

Let a value that doesn't look like a Linear team ID be resolved to one by listing every
team accessible to the API key and matching its name or key (case-insensitive, exact)
before the existing team-validation/throughput-fetch flow runs unchanged. A value that
does look like a Linear ID (UUID format) skips resolution entirely and goes straight
through today's unmodified `_validate_team`/`fetch_linear_throughput` path — zero new code
runs for an already-working raw-ID request (spec FR-003/US3).

## Technical Context

**Language/Version**: Python 3.11+ (backend only) — this feature touches
`linear_client.py` exclusively; no CLI/web/frontend request or response shape changes at
all, since `--linear-team`/`linear_team_id` keep their existing `str` type

**Primary Dependencies**: None new. Format detection uses the standard library's `re`
module (a UUID-shape regex); the team-listing query reuses the exact same
`urllib.request`/pagination pattern `_fetch_all_completed_at` already established in 006

**Storage**: N/A — resolution happens once per request, nothing persisted or cached
between requests (spec Assumptions)

**Testing**: `pytest` with the Linear HTTP layer mocked, extending `test_linear_client.py`'s
existing `patched_urlopen` fixture — no new test infrastructure needed

**Target Platform**: Same as 006/007 — one container serving the API, static frontend, CLI

**Project Type**: Web application (library + FastAPI + React SPA) + CLI, unchanged
structure — this feature is entirely internal to one existing backend module

**Performance Goals**: A UUID-shaped value costs exactly what it costs today (one
team-validation call, no change). A name/key value costs one additional paginated
team-listing fetch before validation — bounded by the workspace's team count, not its issue
count, so cheap even for a large workspace

**Constraints**: No change to `ForecastRequestBody`/CLI flags (spec FR-010). No change to
period handling, lookback window, or any other part of the Linear integration (spec FR-002,
FR-010). Raw-ID requests MUST take the exact same code path as before this feature (spec
FR-003/US3) — not just equivalent behavior, the literal same function call unconditionally

**Scale/Scope**: One new internal function (`_resolve_team_id` or similar) plus one new
query-building function and one new exception type in `linear_client.py`; no new files, no
new top-level structure

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | Another plain query against Linear's own public, documented schema — no comparable code exists to study or avoid. | PASS |
| II. Library-First Simulation Core | Unaffected — this feature is entirely upstream of `ThroughputHistory` construction; `fetch_linear_throughput`'s own body and the simulation core are untouched. | PASS |
| III. Test-First & Statistically Validated | No new randomness — nothing here needs statistical validation. Test-first still applies to format detection, team-listing pagination, and name/key matching (ordinary unit tests, HTTP layer mocked, same pattern as 006). | PASS |
| IV. Transparent Assumptions | Unaffected — no change to any forecast output. | PASS |
| V. Simplicity & Incremental Scope | No new dependency; no new module or package (research.md §2); the "no match" case reuses the *existing* `LinearTeamNotFoundError` instead of inventing a parallel error (research.md §3). | PASS |
| Tech constraints | No new data shape crossing a boundary — `_resolve_team_id` takes/returns plain `str`, same as today's `team_id` parameter. `mypy --strict` and existing lint rules apply. | PASS |
| Workflow | `tasks.md` → GitHub Issues titled `[008-linear-team-lookup] T00x: …` before implementation, with `Closes #N` for every one of them in the completing PR (per PR #221's `/speckit-implement` fix). README updated in the completing PR. | PASS (action noted) |
| Secrets (Development Workflow) | Unaffected — no new credential handling; the API key is used exactly as it already is for every other Linear call. | PASS |

**Post-design re-check** (after research.md, data-model.md, contracts/): unchanged, all PASS.

## Decisions confirmed before implementation

Per the constitution's "ask before implementing" for API shape and data modeling:

1. **Resolution strategy**: detect Linear's ID format (UUID) up front via regex. A
   UUID-shaped value skips resolution entirely and goes through today's unmodified
   `_validate_team` path unconditionally. A non-UUID-shaped value skips the direct lookup
   entirely and goes straight to listing teams and matching by name/key — never attempts
   the (futile) direct lookup first. Confirmed over the alternative (always try the direct
   lookup first, fall back to name/key search only on "not found") specifically to avoid a
   wasted round-trip for values that obviously aren't IDs.

No second decision needed for the ambiguous-match message format (research.md §4) — listing
each candidate as `"name (key)"` is the only format that directly helps the user pick a
more specific value (the key), so there's no genuine alternative worth presenting.

## Project Structure

### Documentation (this feature)

```text
specs/008-linear-team-lookup/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md         # Phase 1
├── quickstart.md          # Phase 1
├── contracts/
│   └── linear-errors.md    # Phase 1 (new ambiguous-match error; everything else unchanged)
├── checklists/
│   └── requirements.md
└── tasks.md               # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/agile_metrics/
├── linear_client.py  # + _looks_like_linear_id(), _build_teams_query(),
│                      #   _fetch_all_teams(), _resolve_team_id(), LinearTeamAmbiguousError;
│                      #   _validate_team()/fetch_linear_throughput() call the new resolver
│                      #   first, otherwise unchanged
├── cli.py              # unchanged - --linear-team keeps its existing str type and help text
├── web.py                # unchanged - linear_team_id keeps its existing str type
├── csv_item_import.py     # unchanged
├── models.py                # unchanged
└── forecast.py                # unchanged

tests/
└── test_linear_client.py  # + format detection, team-listing pagination, name/key
                             #   matching (unique/none/ambiguous), raw-ID-path-unchanged
                             #   regression test

frontend/
└── (no changes - linear_team_id's type and the request/response shapes are identical)
```

**Structure Decision**: No new files, no new top-level structure — every change lives
inside the existing `linear_client.py` (research.md §2, mirroring 006/007's "no
speculative package" precedent). No frontend changes at all, since the web UI's
`linear_team_id` field already accepts free text and the resolution is entirely
server-side.

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
