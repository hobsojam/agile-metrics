# Research: Throughput-Based Monte Carlo Forecast

## Resolved ambiguity: calendar dates require a period duration

**Decision**: `ThroughputHistory` carries an explicit real-world period duration
(`datetime.timedelta`), in addition to the ordered per-period item counts.

**Rationale**: The spec's User Story 1 requires actual completion *dates*, not a count of
periods. "N periods from now" can only become a calendar date if the real-world length of
one period is known (e.g., 6 periods × 7 days/period = 42 days from today). The original
spec draft treated periods as fully opaque, which made FR-002(a) unsatisfiable. Resolved by
amending FR-001 and the Throughput History entity (see spec.md) to require the duration,
while still not requiring calendar alignment of period boundaries (e.g., which weekday a
period starts on) — only its length matters.

**Alternatives considered**: Requiring the caller to pass an explicit list of calendar dates
per period — rejected as unnecessary ceremony; a single shared duration plus "today" as the
reference point is sufficient for every requirement in the spec and keeps the input shape
simple (Principle V).

## Resampling method

**Decision**: Bootstrap resampling — draw a value with replacement from the historical
throughput array for each simulated future period, accumulate, repeat for many independent
trials.

**Rationale**: Makes no assumption about the shape of the team's throughput distribution
(no Poisson/negative-binomial fitting), which matches real agile teams whose throughput is
rarely a clean textbook distribution. It is also the simplest technique that satisfies
FR-003's requirement to simulate "possible future outcomes" rather than extrapolate a single
average rate, consistent with Principle V.

**Alternatives considered**: Fitting a parametric distribution (e.g., Poisson) to the
historical data and sampling from that — rejected because it assumes a distribution shape
that may not hold, and because clean-room independence (Principle I) favors the simpler,
assumption-free technique over reproducing a specific modeling choice from existing tools.

## Trial count and performance

**Decision**: Default to 10,000 trials per forecast, generated as a single vectorized numpy
operation (not a Python-level loop), with the exact count returned in `ForecastResult` per
FR-004. The trial count is a documented constant, not required user input (per spec
Assumptions).

**Rationale**: 10,000 trials gives stable 50th/70th/85th/95th percentile estimates while
running in well under the 5-second budget (SC-004) even for the largest typical input
(26 periods) — vectorized numpy resampling of this size is a sub-second operation on
ordinary hardware, leaving comfortable headroom.

**Alternatives considered**: 1,000 trials — rejected as too coarse for a stable 95th
percentile estimate; 100,000 trials — rejected as unnecessary precision for the marginal
compute cost, and against Principle V.

## Random number generation

**Decision**: `numpy.random.Generator` (PCG64 bit generator), seeded from the optional
user-supplied integer seed (FR-009). When no seed is supplied, a fresh OS-seeded generator
is used.

**Rationale**: `Generator` is numpy's modern RNG API (successor to the legacy
`RandomState`), supports fast vectorized sampling, and accepting a seed makes repeated runs
byte-for-byte reproducible, satisfying FR-009 and Principle III directly.

**Alternatives considered**: Python's standard-library `random` module — rejected as it
cannot vectorize sampling across trials as efficiently as numpy, which matters for the
5-second performance budget.

## Percentile calculation

**Decision**: `numpy.percentile` (linear interpolation) over the array of simulated trial
outcomes.

**Rationale**: Built into the `numpy` dependency already required for resampling; no
additional dependency needed.

**Alternatives considered**: `scipy.stats` percentile utilities — rejected; would add a
second numerical dependency for no capability `numpy.percentile` doesn't already provide
(Principle V, and the constitution's "justify new dependencies" rule).

## Statistical validation strategy (Constitution Principle III)

**Decision**: In addition to example-based `pytest` tests, use `hypothesis` to
property-test: (a) seeded reproducibility (same seed + inputs ⇒ identical output, across
randomly generated valid inputs), and (b) convergence (as trial count increases, the
simulated percentiles for a known synthetic throughput series converge toward the
analytically-computable percentiles of resampling that series).

**Rationale**: Principle III requires simulation correctness to be validated against known
statistical properties, not just example assertions. Property-based testing is the
standard way to check a property holds across a wide input space rather than a handful of
hand-picked examples.

**Alternatives considered**: Example-based tests only — rejected as insufficient to satisfy
Principle III's explicit requirement.

## Minimum historical periods (FR-006)

**Decision**: Require at least 6 historical periods to produce a forecast.

**Rationale**: Below ~6 data points, a bootstrap resample mostly reproduces the same handful
of values and its percentile spread is not a meaningful reflection of real variability.
6 is a clean, defensible minimum for a first slice; it is a documented constant
(`agile_metrics.models.MIN_HISTORICAL_PERIODS`), not user-facing configuration, and can be
revisited with evidence later without a spec change.

**Alternatives considered**: No minimum (let any non-empty series through) — rejected, as it
directly contradicts FR-006 and SC-006, which require refusing to produce a misleading
forecast from too little data.
