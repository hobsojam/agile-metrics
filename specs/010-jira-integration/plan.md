# Implementation Plan: Jira Integration

**Branch**: `010-jira-integration` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-jira-integration/spec.md`

## Summary

Add `fetch_jira_throughput()` in a new `jira_client.py` module. It validates the credentials
and project, detects the project's done statuses from its workflow status categories, pages
through resolved issues in a widened JQL window, filters out epics and sub-tasks, buckets each
issue by its UTC resolution date, and returns an existing `ThroughputHistory`. The CLI and web
layers gain a fourth source alongside manual paste, Linear, and CSV. The forecasting library is
untouched, and the response gains one additive `done_statuses` field for transparency.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript + React 19 (frontend). Both sides
change, with additive edits only.

**Primary Dependencies**: None new. HTTP via the standard library (`urllib.request`, `base64`,
`json`), mirroring `linear_client.py` (research §8).

**Storage**: N/A. The API token is used for the request only and never persisted (FR-008).

**Testing**: `pytest` with the HTTP seam mocked (no real network in CI); `vitest` for the new
form fields and the `done_statuses` display. A live Jira check (quickstart Scenario 5) is a
manual pre-merge gate, not part of CI.

**Target Platform**: Same as specs 002/003/006 - one container serving the API, static frontend,
and CLI.

**Project Type**: Web application + CLI, unchanged structure. One new backend module; additive
changes to `cli.py`, `web.py`, and the frontend form.

**Performance Goals**: One fetch = one identity call + one statuses call + a sequence of
cursor pages. Pages are sequential by necessity (cursor pagination). Acceptable for realistic
windows; no fixed issue cap (clarification Q4), with progress reported during long fetches
(SC-005).

**Constraints**: No change to `ForecastResult`, `ForecastRequest`, `ThroughputHistory`, or the
simulation core (Principle II). Token never logged, printed, persisted, or echoed in errors
(FR-008). Existing manual, Linear, and CSV paths unchanged.

**Scale/Scope**: One new module (`jira_client.py`), additive changes to `cli.py` and `web.py`,
additive frontend form fields and a `done_statuses` line, one README section. No new
dependencies.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | Built from Atlassian's public REST documentation and developer-community write-ups (research header). predictability-engine has a Jira integration; it was not consulted for code or structure, and the workflow-mapping approach in issue #180 was not copied. | PASS |
| II. Library-First Simulation Core | The adapter only produces a `ThroughputHistory`; forecasting functions are untouched. `done_statuses` is a web/CLI reporting field, not part of `ForecastResult`. | PASS |
| III. Test-First & Statistically Validated | No simulation logic added. Test-first applies to bucketing, pagination, exclusion, done-status mapping, and error categories, all unit-tested with mocked HTTP. | PASS |
| IV. Transparent Assumptions | Strengthened: the response reports `done_statuses`, so the user sees exactly which statuses were treated as done (clarification Q3, FR-004). | PASS |
| V. Simplicity & Incremental Scope | Cloud only (Server/DC deferred per user decision). No new dependency. Epics/sub-tasks handled by a structural field, not a name list. | PASS |
| Tech constraints | `ThroughputHistory` reused as the single data shape. `mypy --strict`, ruff, bandit, pip-audit apply to the new module. | PASS |
| Workflow | `tasks.md` -> GitHub issues `[010-jira-integration] T0NN: ...` before implementation. README updated in the implementing PR. | PASS (action noted) |
| Secrets (Development Workflow) | Token accepted via env var or request field, never persisted or logged; a test asserts it is absent from every raised error's `str()` and from the `JiraConnection` repr. | PASS (verified by test) |

**Post-design re-check** (after research.md, data-model.md, contracts/): unchanged, all PASS.

## Decisions needing confirmation before implementation

Per the constitution's "ask before implementing" for API shape and data modeling:

1. **Request shape**: four mutually exclusive sources. The existing exactly-one validation
   (`cli.py`'s `_build_throughput_history`, `web.py`'s `_build_history`) extends from three to
   four, and gains partial-credential messages for the Jira fields in the same style as Linear.
2. **Credential transport**: the API token reads from `AGILE_METRICS_JIRA_API_TOKEN` in
   preference to a literal `--jira-api-token` value, so it stays out of shell history
   (same reasoning as the Linear key).
3. **Lookback default**: 26 periods, matching Linear, per clarification Q2.
4. **`done_statuses` in the web response**: additive list field, empty for other sources.
5. **Live-verification gate**: issue-type fields (`subtask`, `hierarchyLevel`) are unverified
   against a real site and must pass quickstart Scenario 5 before merge.

## Project Structure

### Documentation (this feature)

```text
specs/010-jira-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── forecast-api.md  # Phase 1 - request/response/CLI delta
│   └── jira-errors.md   # Phase 1 - error categories and messages
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks) - NOT created here
```

### Source Code (repository root)

```text
src/agile_metrics/
├── jira_client.py       # NEW: JiraConnection, fetch_jira_throughput, error types
├── cli.py               # + four --jira-* options; source selection; Done statuses line
├── web.py               # + jira_* request fields; done_statuses response field; source selection
└── (models.py, forecast.py, simulation.py, linear_client.py, csv_item_import.py unchanged)

tests/
├── test_jira_client.py  # NEW: bucketing, window, exclusion, done statuses, pagination, errors
├── test_cli.py          # + jira source selection and output tests
└── test_web.py          # + jira request/response tests

frontend/src/
├── App.tsx              # + Jira source option, fields, done-statuses line
└── App.test.tsx         # + Jira form tests
frontend/openapi.json    # regenerated
frontend/src/api-types.ts # regenerated
```

**Structure Decision**: One new backend module, mirroring `linear_client.py`. No new package
or layer, consistent with Principle V and with how specs 006 and 007 were structured.

## Complexity Tracking

*No entries - Constitution Check reported no violations.*
