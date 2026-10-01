<!--
Sync Impact Report
Version change: 1.1.1 → 1.1.2
Modified principles: none
Added principles: none
Clarified sections:
  - Development Workflow (branch naming: Spec-Kit-driven feature work uses
    Spec-Kit's own NNN-feature-name branches instead of feat/<description>,
    matching how /speckit-plan and /speckit-tasks already name and locate
    feature branches; feat/ and fix/ are retained for non-Spec-Kit work)
Added sections: none
Removed sections: none
Follow-up TODOs: none
-->

# Agile Metrics Constitution

## Core Principles

### I. Original, Clean-Room Design (NON-NEGOTIABLE)
All algorithms, data models, and code MUST be independently designed and
implemented. Studying existing tools (e.g., predictability-engine and similar
Monte Carlo forecasting tools) for conceptual understanding is permitted, but
copying their code, file structure, naming, or verbatim documentation is
prohibited.
**Rationale**: The explicit goal of this project is to build a tool that
covers similar ground to existing forecasting tools without being a fork or
derivative of any of them.

### II. Library-First Simulation Core
The Monte Carlo simulation and forecasting logic MUST be implemented as a
standalone library with no dependency on any CLI, web, or dashboard layer.
Presentation layers (CLI, dashboard, reports) MUST consume the simulation
core only through a stable, documented public API.
**Rationale**: Keeps the statistical engine independently testable and
reusable across future interfaces (CLI today, a dashboard tomorrow) without
requiring a rewrite.

### III. Test-First & Statistically Validated (NON-NEGOTIABLE)
Test-driven development is mandatory: tests are written before
implementation and MUST fail before the implementation makes them pass.
Beyond conventional unit tests, simulation correctness MUST be validated
against known statistical properties (e.g., convergence of Monte Carlo
estimates, expected distribution shape). Every randomized simulation MUST
accept an explicit seed so that test runs and reported bugs are
deterministically reproducible.
**Rationale**: Unseeded or statistically unvalidated simulations cannot be
verified or debugged, which undermines trust in the numbers this tool exists
to produce.

### IV. Transparent Assumptions
Every forecast or metric MUST surface the inputs, assumptions, sample size,
and confidence interval behind it. A simulated output MUST NOT be presented
as a single point estimate without its uncertainty.
**Rationale**: Agile forecasting tools lose credibility when simulated
outputs are presented as certainties; transparency about assumptions is the
core value proposition versus ad hoc guessing.

### V. Simplicity & Incremental Scope (YAGNI)
Start with the smallest useful feature set (e.g., throughput-based "when
will this be done" forecasting) before adding scope such as multi-team
roll-ups, additional metrics, or third-party integrations. New abstractions
MUST be justified by a current, demonstrated need, not a hypothetical future
one.
**Rationale**: Avoids speculative complexity while the tool's real
requirements are still being discovered.

## Technology Stack & Constraints

- Python 3.11+ is the implementation language, using a `src/` layout with
  `setuptools` as the build backend and `uv` for dependency management and
  lockfile generation.
- Core numerical and simulation work MUST use numpy/scipy for performance
  and correctness; pandas MAY be used for tabular metrics data handling.
- All data crossing a module, CLI, or API boundary MUST be modeled with
  `pydantic` — no raw dicts crossing boundaries.
- Public functions and classes MUST carry type hints; `mypy --strict` MUST
  pass in CI with no untyped definitions. `Any` is permitted only when
  genuinely unavoidable and MUST be accompanied by a comment explaining why.
- `ruff` is the sole linter and formatter (lint + format); no separate
  black/isort/flake8 configuration.
- Tests use `pytest`; coverage is collected with `pytest-cov`. Tests
  requiring external resources or slow paths MUST be marked (e.g.
  `integration`) and excluded from the default fast run.
- New runtime or dev dependencies MUST be justified in the pull request
  description — prefer the standard library or an existing dependency
  first, and use minimum-version bounds (`>=`), never unbounded or wildcard
  specifiers.

## Quality Gates

CI MUST run, in order, on every push and pull request: lint/format check
(`ruff`) → type check (`mypy --strict`) → tests with coverage (`pytest`) →
dependency audit (`pip-audit`) → security static analysis (`bandit`). A
pull request MUST NOT merge if any gate fails.

- Dependabot MUST be configured for this repository (pip/uv and
  github-actions ecosystems) with a 7-day cooldown on version updates, so a
  newly published release has a week to surface problems before it reaches
  this repo. Security updates triggered by the GitHub Advisory Database
  bypass the cooldown.
- Mutation testing (e.g. `mutmut`) is NOT required for the initial project
  scaffold, since there is no simulation logic yet to mutate. It MUST be
  introduced into CI once the simulation core (Principle II) has
  non-trivial branching logic worth mutating — coverage alone does not
  demonstrate that tests catch broken statistical behavior.
- SonarCloud (or equivalent static analysis dashboard) integration SHOULD
  be added once a project token is available, consistent with the author's
  other repositories; it is not a blocker for initial development.

## Development Workflow

- All work happens on feature branches cut from an up-to-date `main`,
  merged via pull request; direct pushes to `main` are prohibited once
  initial history exists. Spec-Kit-driven feature work uses the branch
  name Spec-Kit itself generates (`NNN-feature-name`, matching the
  feature's spec directory, e.g. `001-throughput-forecast`) — do not
  rename it to a `feat/` branch. Non-Spec-Kit work (infra, dependency
  bumps, hotfixes) uses `feat/<short-description>` or
  `fix/<short-description>`.
- Pull `main` before starting new work and before cutting a new branch;
  do not branch from a stale local `main`. Commit and push finished work
  before switching branches — if changes are incomplete or uncertain, ask
  before switching rather than stashing or discarding silently.
- Automated tests, type checks, and all Quality Gates MUST pass in CI
  before merge. Each pull request MUST state which constitution
  principles, if any, it touches or could conflict with.
- **Ask before implementing**: scope, API shape, data modeling, and test
  strategy decisions MUST be confirmed before writing code. Prefer one
  focused question over a long list of options or an unrequested
  implementation.
- Work is tracked in GitHub Issues, not local task files or checklists,
  with one exception: the `spec.md` / `plan.md` / `tasks.md` artifacts
  produced by this project's spec-driven workflow are disposable planning
  drafts, not a parallel task tracker. Before implementation of a feature
  begins, `tasks.md` MUST be converted into GitHub Issues (e.g. via
  `/speckit-taskstoissues`), which then become the system of record for
  tracking that work. Any problem, inconsistency, or improvement noticed
  during work MUST be filed as an issue immediately, even if out of scope
  for the current task — not merely mentioned in conversation or a PR
  description.
- `README.md` MUST be updated in the same pull request whenever a feature
  is completed.
- Secrets (API tokens, credentials) MUST NOT be logged, printed, committed,
  or hardcoded; `.env` files stay out of version control. External input
  (CLI args, file contents, API responses) MUST be validated at the
  boundary via `pydantic` before use elsewhere in the codebase.

## Governance

This constitution supersedes ad hoc practices; where other guidance
conflicts with this document, this document governs. Amendments are made
via the `/speckit-constitution` command and follow semantic versioning:
MAJOR for backward-incompatible principle removal or redefinition, MINOR
for a new or materially expanded principle or section, PATCH for
clarifications and wording fixes. Every pull request MUST be reviewed for
compliance with applicable principles; unjustified complexity or deviation
MUST be fixed or explicitly justified in the pull request description.

**Version**: 1.1.2 | **Ratified**: 2026-09-30 | **Last Amended**: 2026-10-01
