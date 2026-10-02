# Implementation Plan: Forecast CLI

**Branch**: `002-forecast-cli` | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-forecast-cli/spec.md`

## Summary

A thin command-line interface over the existing `agile_metrics` library: parses historical
throughput and a backlog size or target date from CLI flags, calls the library's public
`forecast_by_items`/`forecast_by_date`, and prints the result in human-readable form with a
clean error/exit-code contract. Packaged as a multi-stage Docker image so it can run with no
local Python installation, built from the same `uv.lock` the library already uses.

## Technical Context

**Language/Version**: Python 3.11+ (unchanged from the library)

**Primary Dependencies**: `typer` (CLI framework, new); reuses the existing `agile_metrics`
public API (`forecast_by_items`, `forecast_by_date`, `ThroughputHistory`) — no new
dependency for the forecasting logic itself

**Storage**: N/A

**Testing**: `pytest` + `typer.testing.CliRunner` (built on `click`'s runner) for in-process
CLI invocation tests; a Docker build-and-run smoke test in CI for the container form

**Target Platform**: Same as the library (any Python 3.11+ platform) for the local CLI, plus
a Linux container image for the Docker form

**Project Type**: Single project — adds a `cli.py` module to the existing `agile_metrics`
package, plus a repository-root `Dockerfile`/`.dockerignore`

**Performance Goals**: Dominated by the underlying library's existing 5-second budget
(spec 001 SC-004); CLI argument parsing and output formatting are negligible by comparison

**Constraints**: The container image MUST NOT require a local Python install to run it,
and MUST exclude dev/test dependencies (pytest, mypy, ruff, bandit, hypothesis,
pre-commit, pip-audit) from what ships in the image

**Scale/Scope**: Single-invocation, single-user CLI tool — same scope as the library it wraps

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Original, Clean-Room Design | CLI argument shape, error handling, and Dockerfile designed from scratch below (Phase 0) | PASS |
| II. Library-First Simulation Core | `cli.py` only imports the public `agile_metrics` API (`forecast_by_items`, `forecast_by_date`, `ThroughputHistory`) — never reaches into `simulation.py` internals | PASS |
| III. Test-First & Statistically Validated | CLI tests (argument parsing, mutual-exclusivity, error mapping, output shape) written and confirmed failing before `cli.py` exists; the Docker smoke test is written as a CI step before the Dockerfile that makes it pass | PASS |
| IV. Transparent Assumptions | CLI output always prints all four confidence levels plus `trials_run`/`periods_used` — no code path can print a bare number | PASS |
| V. Simplicity & Incremental Scope | One new dependency (`typer`); no new output-formatting dependency (`rich` rejected, see research.md); input stays CLI flags, no new file-format parser | PASS |

No violations. Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-forecast-cli/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── cli-interface.md
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
└── cli.py                # NEW: typer app - parses args, calls forecast_by_items/
                            # forecast_by_date, formats output, maps validation
                            # errors to clean messages + non-zero exit codes

tests/
├── ... (existing)
└── test_cli.py          # NEW: CliRunner-based tests for all 3 user stories + edge cases

Dockerfile                # NEW: multi-stage uv build -> slim runtime image
.dockerignore              # NEW
```

**Structure Decision**: Single project, extending the existing `agile_metrics` package with
one new module (`cli.py`) rather than a separate package — the CLI has no state or
structure of its own beyond argument parsing and output formatting, so a second package
would be unjustified ceremony (Principle V). The Dockerfile lives at the repository root per
convention.

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
