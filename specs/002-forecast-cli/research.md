# Research: Forecast CLI

## CLI framework

**Decision**: `typer`.

**Rationale**: Type-hint-driven argument parsing fits a codebase that already runs
`mypy --strict` everywhere; it reduces boilerplate versus hand-rolling `argparse`, and
matches the pattern in the author's other recent Python CLI tools (`water-margin`,
`slopify` both use `typer`).

**Alternatives considered**: `click` (what `test-analysis` uses) — typer is itself built on
click and gives the same capability with less boilerplate, so there's no reason to drop to
the lower-level API here. `argparse` (stdlib, zero dependency) — rejected because it is
substantially more verbose for the same mutually-exclusive-flag validation this CLI needs,
and the constitution already accepts justified new dependencies.

## Input format for historical data

**Decision**: Plain CLI flags — `--history "3,5,4,6,2,5,4,3"` (comma-separated integers)
and `--period-days 7` — rather than a file format.

**Rationale**: The library's own spec assumes historical series on the order of 12-26
periods; typing that as one flag is perfectly usable and means `/speckit-plan`'s "try it in
one command" success criterion (spec SC-001) is trivially met with no file to prepare first.

**Alternatives considered**: A JSON or CSV input file — rejected as unnecessary ceremony for
this input size (Principle V/YAGNI). If a real need for file-driven or larger input emerges,
that's a future, demonstrated-need addition, not something to pre-build now.

## Forecast mode selection

**Decision**: `--backlog-size INTEGER` and `--target-date YYYY-MM-DD` as separate optional
flags on the same command; the command body constructs the library's `ForecastRequest`
either way, which already enforces "exactly one of the two" (spec 001 FR-011). The CLI does
not duplicate that check — it only needs to catch the resulting `ValidationError` and format
it (see Error handling below).

**Rationale**: Avoids re-implementing a validation rule the library already owns; keeps the
CLI a thin pass-through, consistent with Principle II.

**Alternatives considered**: A single `--mode`/`--value` pair, or two separate subcommands
(`forecast by-items` / `forecast by-date`) — both rejected as more ceremony than two plain
flags for a tool with exactly two mutually exclusive inputs.

## Error handling

**Decision**: Catch `pydantic.ValidationError` and `ValueError` (the latter for CLI-level
parsing mistakes, e.g. a malformed `--history` string) at the top of the command function,
print a single clean `Error: <message>` line to stderr, and exit via `raise typer.Exit(1)`.

**Rationale**: Directly satisfies FR-005/SC-003 — a user must never see a raw Python
traceback. Catching at one place keeps the mapping consistent across both forecast modes.

**Alternatives considered**: Letting typer/click's default exception handling take over —
rejected, as its default behavior prints a traceback for unhandled exception types.

## Output format

**Decision**: Plain formatted text via f-strings/`print`, no table-rendering dependency.

**Rationale**: The output is small and fixed-shape (four confidence levels plus two
metadata fields) — nowhere near complex enough to justify a dependency like `rich` just for
table drawing (Principle V).

**Alternatives considered**: `rich` tables — rejected as an unneeded dependency for this
amount of output; can be revisited if a real formatting need (e.g., a future `--json` output
mode) emerges.

## Docker image

**Decision**: Multi-stage `Dockerfile`. Stage `builder` uses a `python:3.11-slim` base with
`uv` installed, runs `uv sync --locked --no-dev` (installing only `[project.dependencies]` —
`numpy`, `pydantic`, `typer` — never the dev/test extras) into `/app/.venv`. Stage `runtime`
starts from a fresh `python:3.11-slim`, copies only `/app/.venv` and `src/` from the builder
stage, and sets `ENTRYPOINT` to the installed console-script entry point.

**Rationale**: Keeps the shipped image free of build tools and every dev/test dependency
(pytest, mypy, ruff, bandit, hypothesis, pre-commit, pip-audit) — smaller image, smaller
attack surface. `--locked` matches the same supply-chain hardening already applied to CI
(spec 001's CI work): the image is built from exactly the reviewed, committed lockfile.

**Alternatives considered**: A single-stage image installing the full `dev` extra —
rejected; it would ship an image several times larger with tooling that serves no purpose
at runtime.

## CI coverage for the container

**Decision**: Add a CI step that builds the Docker image and runs it against a fixed sample
input, asserting a zero exit code and an expected substring in the output — exercising
spec 001-level FR-008 ("containerized form produces identical output to a local run")
automatically rather than leaving it to manual verification.

**Rationale**: FR-008 is a testable requirement; per Principle III's test-first ethos, a
testable requirement should have an automated check, not just a `quickstart.md` instruction
a human might forget to run.

**Alternatives considered**: Documenting the check in `quickstart.md` only, with no CI
coverage — rejected, since that allows the container form to silently drift from the local
CLI's behavior with no automated signal.
