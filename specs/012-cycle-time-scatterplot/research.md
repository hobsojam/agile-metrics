# Phase 0 Research: Cycle Time Scatterplot with Percentile Lines

## §1. Where does percentile computation already live, and should this feature reuse it directly?

**Decision**: Compute the new percentiles server-side, in `compute_jira_flow_metrics`
(`src/agile_metrics/jira_client.py`), using `np.percentile` — the exact function
`forecast.py` already uses for the Monte Carlo forecast's 50/70/85/95% confidence-level
outcomes (`forecast.py:52`, `:94`, `:217`). Store the result as a new field on
`FlowMetrics` (`cycle_time_percentiles`), populated once per request and consumed as-is
by both the Cycle Time scatterplot and the Aging WIP threshold line.

**Rationale**: Inspecting `frontend/src/charts/chartData.ts` confirmed the frontend
*never* recomputes percentiles today — `DistributionChart`'s four reference lines and
`ProbabilityCurveChart`'s markers both read pre-computed values straight out of
`result.outcomes`, which `forecast.py` populates via `np.percentile`. There is no
existing client-side percentile implementation to "reuse" in the literal sense; the
only way to satisfy FR-003 ("same method... numerically consistent") without a second,
independent implementation is to compute it the same way, in the same layer, and let
the frontend render it exactly as it already renders every other percentile-derived
value.

**Alternatives considered**:
- *Compute percentiles client-side in TypeScript from the `CycleTimeEntry` list
  already returned.* Rejected: `np.percentile`'s interpolation method (linear by
  default) would need to be reimplemented in JS to match exactly, including edge
  cases (ties, small N, the exact interpolation fraction). A second implementation
  of the same statistic is exactly the kind of duplicated-source-of-truth problem
  this project already gates against elsewhere (the generated-API-types freshness
  check exists for the same reason — one source of truth, drift caught in CI). It
  would also split "where does a confidence level come from" across two languages
  for no benefit, working against Principle II's intent that forecasting/statistical
  logic lives in one library layer.
- *Export `forecast.py`'s private `_CONFIDENCE_LEVELS` tuple and call a shared
  percentile helper from `jira_client.py`.* Considered, but `jira_client.py` and
  `forecast.py` are currently independent modules with no import relationship (by
  design — Jira integration and the forecasting core are separate concerns per
  Principle II). Importing a forecast-module private constant into the Jira client
  for a four-element literal tuple `(50, 70, 85, 95)` adds a cross-module coupling
  for negligible duplication risk (it's a fixed set of levels, not an algorithm).
  Decision: duplicate the small literal tuple locally in `jira_client.py`; the actual
  statistical method (`np.percentile`'s interpolation) is what must match, and does,
  because both call sites use the same numpy function the same way.

## §2. Minimum sample size before showing a percentile-based threshold

**Decision**: 5 resolved items (`len(flow_metrics.cycle_time) < 5` → `cycle_time_percentiles = None`).

**Rationale**: Below 5 points, percentiles (especially the 95th) frequently coincide
with the single maximum or minimum observed value, which reads as spuriously precise
and can mislead more than it helps (Principle IV — transparent assumptions, not a
single point estimate presented as certain). 5 is also the smallest N where an 85th
percentile isn't trivially identical to the max of the sample under `np.percentile`'s
default linear interpolation for the datasets this feature will typically see. No
existing convention in this codebase sets a different threshold, so this is a new,
explicitly-documented default (recorded in spec.md's Assumptions) rather than a
previously-established constant being reused.

**Alternatives considered**: A lower bound of 1 (always compute something) — rejected,
directly conflicts with FR-006 and Principle IV. A statistically "ideal" minimum (e.g.
30, per common sampling-theory rules of thumb) — rejected as unnecessarily strict for
a small-team, low-volume Jira project where 30 resolved issues could take months to
accumulate; 5 was chosen as a practical floor against the most misleading degenerate
cases, not a rigorous confidence-interval guarantee.

## §3. Chart library mechanics: horizontal reference lines and per-point/per-bar styling

**Decision**: `CycleTimeChart` switches from Recharts' `BarChart`/`Bar` to
`ScatterChart`/`Scatter`, with `XAxis dataKey="resolved_at" type="category"` (consistent
with every other chart's category-axis convention — no chart in this app currently uses
a continuous time scale) and up to four `<ReferenceLine y={...} .../>` elements (horizontal,
since the percentile values are cycle-time days, the *Y* axis here — unlike
`DistributionChart`, where the measured quantity is the X axis and its markers are
vertical `x=` lines). `AgingWipChart` keeps `BarChart`/`Bar` and adds one horizontal
`ReferenceLine` plus per-bar conditional coloring via `<Cell>` children (Recharts' standard
mechanism for per-datum bar styling, not used elsewhere in this codebase yet but a
first-party, no-new-dependency Recharts feature).

**Rationale**: Recharts (the only charting library this project uses, already a
dependency since spec 005) supports both `ScatterChart` and per-`Cell` bar coloring
natively. No new dependency, no new charting approach — this is applying existing
library features already available, just not yet used in a scatter or
conditionally-colored-bar shape.

**Alternatives considered**: A continuous/numeric date axis (`type="number"` with a
time scale) for a "real" time-proportional X axis. Rejected for this iteration: every
existing chart in this app uses evenly-spaced category ticks, and matching that
convention keeps the new chart visually consistent with its siblings; a proportional
time axis is a plausible future enhancement but out of scope here (Principle V — no
speculative scope beyond what FR-001 asks for).

## §4. Reuse of existing percentile styling

**Decision**: Reuse `CONFIDENCE_LEVELS` and `CONFIDENCE_LEVEL_STYLES` from
`frontend/src/charts/confidenceLevels.ts` unchanged, for both the four scatterplot
reference lines and the single Aging WIP threshold line (styled with the existing
85th-percentile color, `CONFIDENCE_LEVEL_STYLES[85]`).

**Rationale**: That module's own docstring already states its purpose: "imported by
every chart... so users can match a level between charts." This feature is exactly
that reuse case, and introducing a second color/label convention for the same four
levels would directly undermine the stated purpose of the shared module.

**Alternatives considered**: None seriously considered — this is the one module this
project already built for exactly this purpose.
