# Feature Specification: Forecast CLI

**Feature Branch**: `002-forecast-cli`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "A command-line interface for the throughput forecast
library: lets a user supply historical throughput data and either a backlog size or a
target date, and prints the resulting Monte Carlo forecast. Include Docker support so the
CLI can be built and run as a container, not just via a local Python install."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a completion-date forecast from the command line (Priority: P1)

A user who is not a programmer has their team's historical throughput and a backlog size.
They run a single command, supplying their data and backlog size, and get back a forecast
of likely completion dates at standard confidence levels — without writing any code.

**Why this priority**: This is the entire reason the CLI exists — it's the only way most
users can reach the forecasting capability built in the underlying library feature. Without
it, the forecasting logic is reachable only by writing Python.

**Independent Test**: Can be fully tested by invoking the CLI with a sample historical
throughput input and a backlog size, and verifying the printed output contains completion
dates at all four confidence levels.

**Acceptance Scenarios**:

1. **Given** a valid historical throughput input and a backlog size, **When** the user runs
   the CLI, **Then** it prints a completion-date forecast at all four confidence levels to
   the screen.
2. **Given** the same input, backlog size, and an explicit seed, **When** the command is run
   twice, **Then** both runs print identical output.
3. **Given** invalid input (e.g., a backlog size of zero), **When** the user runs the CLI,
   **Then** it prints a clear, human-readable error message and exits with a non-zero status
   — never a raw stack trace.

---

### User Story 2 - Get an items-completed forecast from the command line (Priority: P2)

A user has a target date (e.g., a release date) and wants to know how many items are likely
to be done by then. They run the CLI with their historical data and the target date instead
of a backlog size.

**Why this priority**: The inverse question to User Story 1, and the second most valuable
capability, but the CLI delivers its core value without it.

**Independent Test**: Can be fully tested by invoking the CLI with a sample historical
throughput input and a target date, and verifying the printed output contains item-count
forecasts at all four confidence levels.

**Acceptance Scenarios**:

1. **Given** a valid historical throughput input and a future target date, **When** the user
   runs the CLI, **Then** it prints an items-completed forecast at all four confidence
   levels.
2. **Given** a target date that is not in the future, **When** the user runs the CLI,
   **Then** it prints a clear error message and exits with a non-zero status.

---

### User Story 3 - Run the tool without installing Python or any dependencies (Priority: P3)

A user has Docker (or an equivalent container runtime) but does not want to install Python,
a package manager, or any dependencies on their machine — or wants to run the tool as a
consistent step in an automated pipeline. They build and run the tool as a container image
instead.

**Why this priority**: Removes an installation barrier and enables consistent automated use,
but is a distribution convenience — the CLI already delivers its full value to anyone
willing to install Python locally, per User Stories 1 and 2.

**Independent Test**: Can be fully tested by building the container image, running it with
the same input and arguments used in User Story 1 or 2, and verifying the output is
identical to running the CLI locally — with no local Python installation involved.

**Acceptance Scenarios**:

1. **Given** the container image has been built, **When** it is run with a valid historical
   throughput input and a backlog size or target date, **Then** it prints the same forecast
   a local run would produce for the same input.
2. **Given** the container is run with invalid or missing input, **When** it exits, **Then**
   it prints a clear error message and exits with a non-zero status, the same as a local
   run — it does not hang or fail silently.

### Edge Cases

- What happens when required input is missing entirely (no backlog size and no target
  date supplied)? The CLI MUST print usage help and a clear error, and exit non-zero.
- What happens when both a backlog size and a target date are supplied? The CLI MUST print
  a clear error explaining that exactly one is required, and exit non-zero (surfacing the
  underlying library's own rule).
- What happens when the supplied historical data fails the underlying library's validation
  (too few periods, all-zero history, negative or non-whole values)? The CLI MUST surface
  that specific validation message to the user, not a raw exception trace.
- What happens when the container is run with no input supplied at all (e.g., no file
  mounted)? The CLI MUST print the same clear usage error as the local case, not hang.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a command-line entry point that accepts a historical
  throughput series and its period duration as input.
- **FR-002**: System MUST accept exactly one of a backlog size or a target date as input,
  selecting the corresponding forecast mode, and MUST reject input that supplies both or
  neither with a clear error (mirroring the underlying library's FR-011).
- **FR-003**: System MUST print the resulting forecast to the screen in a human-readable
  format that shows all four confidence levels — never a single point estimate.
- **FR-004**: System MUST accept an optional random seed so that runs are reproducible.
- **FR-005**: System MUST translate every validation failure from the underlying
  forecasting library (insufficient history, all-zero history, invalid backlog size or
  target date, etc.) into a clear, human-readable error message and a non-zero exit status
  — never an unhandled exception trace.
- **FR-006**: System MUST provide a help/usage message describing how to invoke it and what
  input it expects.
- **FR-007**: System MUST be packaged as a container image that can be built and run with no
  local Python installation or dependency setup required.
- **FR-008**: Running the containerized form with the same input and arguments as a local
  run MUST produce identical output.

### Key Entities

- **CLI Invocation**: The user-supplied command-line arguments and historical throughput
  input for a single run — maps onto the underlying library's `ThroughputHistory` and
  `ForecastRequest`.
- **CLI Output**: The human-readable rendering of the underlying library's
  `ForecastResult` printed to the screen.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can get a completion-date forecast using only the tool's
  built-in help text, with no outside documentation, in a single command.
- **SC-002**: A first-time user can get an items-completed forecast the same way.
- **SC-003**: 100% of invalid-input cases produce a human-readable error message and a
  non-zero exit status — none produce a raw stack trace.
- **SC-004**: A user with a container runtime but no local Python installation can build and
  run the tool successfully, getting output identical to a local Python run given the same
  input.
- **SC-005**: Repeating an identical command with an explicit seed produces byte-identical
  output 100% of the time.

## Assumptions

- The exact shape of the historical-data input (a file format, stdin, or individual
  command-line arguments) is an implementation decision for the planning phase, not a
  user-facing scope question — any form satisfying FR-001 is acceptable here.
- The forecasting behavior, validation rules, and result invariants are inherited unchanged
  from the `001-throughput-forecast` library feature; this spec defines only the interface
  (CLI and container packaging) around it, not new forecasting logic.
- Standard CLI conventions apply: exit code 0 on success, non-zero on any error, `--help`
  available.
- The container image's base image, registry, and build details are implementation-plan
  decisions, not user-facing scope.
