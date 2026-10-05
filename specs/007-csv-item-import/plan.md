# Implementation Plan: CSV Item Import

**Branch**: `007-csv-item-import` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-csv-item-import/spec.md`

## Summary

Add a new `parse_items_csv()` / `bucket_items_to_throughput()` pair that reads a CSV of
per-item records (`id, type, title, start_date, end_date`), retains them as a list of a new
`Item` model, and buckets completed items' `end_date` values into an existing
`ThroughputHistory` — the exact same type manual paste and Linear import already produce.
The CLI and web layers gain a third way to populate that one value; neither the simulation
core nor `forecast_by_items`/`forecast_by_date` change at all.

## Technical Context

**Language/Version**: Python 3.11+ (backend, unchanged); TypeScript + React 19 (frontend,
unchanged) — this feature touches both, but introduces no new dependency on either side

**Primary Dependencies**: None new. CSV parsing uses the Python standard library's `csv`
module (research.md §1); the web layer gets a second, CSV-dedicated endpoint
(`POST /api/forecast/csv`) accepting `multipart/form-data` via FastAPI's own built-in
`UploadFile`/`Form` support (research.md §2) — no new dependency, but a second request
shape distinct from the existing JSON `POST /api/forecast`

**Storage**: N/A — a submitted CSV is parsed and discarded after the request; nothing is
persisted, consistent with the tool's existing stateless design

**Testing**: `pytest` for CSV parsing, bucketing, and row-level error classification (all
pure string/data-in, model-out logic — no I/O to mock, unlike Linear's HTTP layer);
`vitest` + Testing Library for the new frontend form fields and file-to-text read, same
pattern as the existing manual-paste/Linear form fields

**Target Platform**: Same as specs 002/003/006 — one container serving the API, static
frontend, and CLI; any modern browser for the web UI

**Project Type**: Web application (library + FastAPI + React SPA) + CLI, unchanged
structure — one new backend module, additive changes to existing CLI/web/frontend files

**Performance Goals**: Parsing and bucketing a CSV of thousands of rows completes well
within normal request-timeout expectations — this is in-process string parsing, with no
network calls (unlike Linear's paginated fetch), so it is strictly cheaper

**Constraints**: No change to `ForecastResult`, `ForecastRequest`, `ThroughputHistory`, or
the simulation core (Principle II). The existing manual-paste and Linear-import paths are
untouched (spec FR-009). `Item` records are retained through parsing but not exposed via any
API response in this feature (spec Assumptions: flow metrics are out of scope).

**Scale/Scope**: One new backend module (`csv_item_import.py`), one new pydantic model
(`Item`, in `models.py`), additive changes to `cli.py`/`web.py`, additive changes to the
frontend form, no new dependencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | Parsing a plain CSV by its own documented column names is not "copying" anything — there is no comparable code to study or avoid; the column names happen to match predictability-engine's shape only because the spec explicitly asked for that, for data comparability, not because any code was studied. | PASS |
| II. Library-First Simulation Core | `bucket_items_to_throughput()` only ever produces a `ThroughputHistory`; the CLI and web layers still only call `forecast_by_items`/`forecast_by_date`. The simulation core is untouched. | PASS |
| III. Test-First & Statistically Validated | No new randomness/simulation logic — nothing here needs statistical validation. Test-first still applies to parsing, bucketing, and row-level error classification (ordinary unit tests, no I/O to mock). | PASS |
| IV. Transparent Assumptions | Unaffected — `ForecastResult` and its four confidence levels are unchanged; this feature only changes how `ThroughputHistory` gets populated. | PASS |
| V. Simplicity & Incremental Scope | No new dependency (research.md §1); no new package structure ahead of actual need (research.md §3, mirroring 006's single-module precedent); the "too few periods" and "all-zero" cases reuse existing validators instead of duplicating them (spec FR-005). | PASS |
| Tech constraints | `ThroughputHistory` and the new `Item` model (both `pydantic`) are the one source of truth for these data shapes. `mypy --strict` and existing lint rules apply to the new module. | PASS |
| Workflow | `tasks.md` → GitHub Issues titled `[007-csv-item-import] T00x: …` before implementation, with every per-task issue's number added to the completing PR's `Closes #N` list (per the `/speckit-implement` fix from PR #221) so they close automatically on merge. README updated in the implementing PR. | PASS (action noted) |
| Secrets (Development Workflow) | N/A — no credential is involved in this feature (local file/pasted text only). | PASS |

**Post-design re-check** (after research.md, data-model.md, contracts/): unchanged, all PASS.

## Decisions confirmed before implementation

Per the constitution's "ask before implementing" for API shape and data modeling:

1. **CSV transport (web)**: a dedicated `POST /api/forecast/csv` endpoint accepting
   `multipart/form-data` (a `csv_file` upload plus `period_days`/`backlog_size`/
   `target_date`/`seed` form fields), separate from the existing JSON `POST /api/forecast`.
   The existing endpoint's request/response shape and its two-way `history`/`linear_*`
   "exactly one of" check are completely unchanged — CSV is not a third arm of that check,
   it is simply not reachable from that endpoint at all. The web UI's "paste CSV text"
   option (spec FR-001 also requires pasting, not just file upload) submits the pasted text
   to the same new endpoint as a plain-text form field standing in for the file, so there is
   still only one CSV-handling code path server-side.
2. **CLI transport**: `--csv-file <path>` is a third arm of the CLI's existing single
   "exactly one of" check (alongside `--history` and the `--linear-api-key`+`--linear-team`
   pair) — unlike the web, there is no multipart-vs-JSON concern on the CLI, so splitting it
   into a second command would add structure without a reason (Principle V).
3. **`Item` model placement**: `Item` is a public `pydantic` model in `models.py`, alongside
   `ThroughputHistory`/`ForecastResult` (so a later item-level flow-metrics feature can
   import it directly), but is not added to `ForecastResponseBody` or any API response in
   this feature — `parse_items_csv()` returns `list[Item]`, which is bucketed into a
   `ThroughputHistory` and then discarded at the end of the request, exactly mirroring how
   Linear's fetched `completedAt` values never reach the response today.

## Project Structure

### Documentation (this feature)

```text
specs/007-csv-item-import/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── forecast-api.md  # Phase 1 (new POST /api/forecast/csv endpoint)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/agile_metrics/
├── csv_item_import.py  # NEW: parse_items_csv() + bucket_items_to_throughput() +
│                        #   row-level error classification
├── models.py            # + Item model
├── cli.py                # + --csv-file (third arm of the existing exactly-one-of check)
├── web.py                # + POST /api/forecast/csv (multipart), existing POST
│                         #   /api/forecast unchanged
├── forecast.py            # unchanged
├── linear_client.py        # unchanged
└── simulation.py            # unchanged

tests/
├── test_csv_item_import.py  # NEW: parsing, bucketing, row-level error classification -
│                              #   no I/O to mock, pure string/data-in model-out logic
├── test_cli.py                # + CSV-backed CLI tests
└── test_web.py                 # + CSV-backed API tests (new endpoint)

frontend/
├── openapi.json                # regenerated (new /api/forecast/csv path)
└── src/
    ├── api-types.ts            # regenerated
    └── App.tsx                  # + a third data-source option (CSV), a file input and a
                                  #   textarea for pasted CSV text, submitting via FormData
                                  #   to the new endpoint instead of the existing JSON fetch
```

**Structure Decision**: One new backend module and one new model, no new top-level
directories or packages (research.md §3, mirroring 006's single-module precedent). The
frontend gets a third data-source option and a new submit path in the existing `App.tsx`,
not a new component file — same reasoning as 006's toggle.

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
