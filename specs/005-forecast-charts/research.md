# Research: Forecast Charts

Phase 0 decisions for [spec.md](./spec.md). Each section: Decision / Rationale /
Alternatives considered.

## 1. One simulation feeds the outcomes, the distribution, and the projection (FR-004, SC-006)

**Decision**: Add one internal function to `simulation.py`. It draws the
`(trials, horizon)` resampling matrix and returns its row-wise cumulative sum (the
**cumulative paths**). Both existing simulation functions are re-expressed on top of it:

- `periods_to_complete` becomes "first column where the cumulative path reaches the
  backlog", computed on the same paths it already builds today.
- `items_completed_after` becomes "the last column of the cumulative paths".

`forecast.py` then calls the cumulative-paths function once per request and derives all
three outputs from that one matrix: the four outcomes (unchanged formulas), the
distribution, and the projection.

**Rationale**: Today's functions call `rng.choice(historical, size=(trials, horizon))`
exactly once each, with the same generator, seed and shape. Keeping that one call with the
same arguments means the random stream, and therefore every existing outcome value, is
byte-for-byte unchanged (SC-006). This must be pinned by a regression test that records
current outputs for fixed seeds *before* the refactor (Principle III: the test fails first
if the refactor drifts). A single matrix also guarantees the distribution and fan describe
the same simulated futures as the four headline numbers.

**Alternatives considered**:
- *Run a second simulation for chart data.* Rejected because the charts could then disagree
  with the headline numbers (violates FR-004) and it doubles compute.
- *Return the raw `trials × horizon` matrix to presentation layers.* Rejected because it
  would be tens of MB of JSON. FR-009 needs summaries, not raw trials.

**Pre-existing cost noted, not changed here**: backlog mode allocates a
`trials × max(50·backlog, 500)` matrix (about 80 MB at backlog 20 with default trials).
This feature adds no extra allocation, since percentiles are read from a column slice of
the existing matrix. The cost itself is worth a separate GitHub issue, filed when
implementation starts (constitution: issues are filed for problems found).

## 2. How projection lines are defined, and how exactly they match the outcomes

**Decision**: For future period *t* (1-based) and confidence level *L*, the projection
value is `int(np.percentile(cumulative[:, t-1], 100 - L))`. That is the item count reached
or exceeded in *L*% of simulated futures, using the same mirrored-percentile reading the
existing items mode already uses.

- **Target-date mode**: the projection's last column *is* the `items` array the existing
  outcome is read from, with the identical formula. So each line's final value equals the
  listed outcome **exactly**, by construction.
- **Backlog mode**: because the paths never decrease, "finished by period *t*" is the same
  event as "cumulative at *t* ≥ backlog". So the fan line and the date outcome describe the
  same probability. However, the existing date outcome is
  `round(np.percentile(periods, L))` with linear interpolation, and that rounding can't
  change (SC-006). A seeded experiment (400 random histories × 4 levels = 1,600 cases,
  2,000 trials each) found the line's first crossing differed from the listed date in
  **7 of 1,600 cases (0.4%), never by more than one period**. The spec's SC-003 and
  User Story 3 now state a one-period tolerance for backlog mode.

**Rationale**: This is the honest definition of a probabilistic fan. It needs no new
statistics, and it shares the existing items-mode convention, so "85%" means the same
thing on every chart (FR-010).

**Alternatives considered**:
- *Switch outcomes to a non-interpolating percentile so the match is exact.* Rejected
  because it changes existing outputs (violates FR-003 and SC-006).
- *Bend the fan lines to pass through the listed dates.* Rejected because the fan would
  no longer be an honest percentile of the simulated futures.

## 3. Distribution grouping (FR-005)

**Decision**: Group outcome values into equal-width groups (buckets) of whole numbers,
with at most 60 buckets.

- Outcome values are whole numbers: periods-to-complete in backlog mode, items completed
  in target-date mode.
- Let `span = max − min + 1`. If `span ≤ 60`, use one bucket per value. Otherwise use
  `width = ceil(span / 60)`, with buckets `[min + k·width, min + (k+1)·width − 1]`
  (inclusive bounds).
- Count with `np.bincount` on `(value − min) // width`, so counts always add up to
  `trials_run` (SC-002).
- In backlog mode, the bucket bounds are reported as **dates** (period count × period
  length + reference date). That's the same mapping the outcomes use, so markers line up
  with bars (SC-001). Trials that hit the simulation horizon land in the final bucket, as
  today.

**Rationale**: Integer bounds avoid the floating-point edges of `np.histogram`. Ordinary
forecasts get one bar per possible date, which is the most readable form.

**Alternatives considered**: `np.histogram(bins="auto")`, rejected because it gives float
bin edges and an unpredictable number of bars. Sending raw value counts with no cap was
also rejected, because wide spreads would mean hundreds of bars.

## 4. Probability curve data (User Story 2)

**Decision**: There is **no new API field**. The web UI accumulates the distribution's
bucket counts into a cumulative curve. In backlog mode that's P(done on or before the
bucket's last date). In items mode, accumulating from the high end gives P(at least the
bucket's first count). Resolution therefore matches the distribution: exact per period or
item when there are 60 or fewer distinct values, otherwise per bucket.

The same experiment as §2 found the curve, read at each listed outcome, was **≥ L% in all
1,600 cases**. This is pinned as a property test.

**Rationale**: The curve is a pure re-summary of data already in the response. That
satisfies FR-009 (no extra simulation, no extra request) and keeps the API small
(Principle V).

**Alternatives considered**: a separate `cumulative` array in the response. Rejected
because it duplicates information the distribution already carries.

## 5. Projection horizon

**Decision**:
- **Target-date mode**: periods `1 … num_periods`, the existing whole-period floor
  computation with a minimum of 1.
- **Backlog mode**: periods `1 … P95 + 1`, where `P95` is the rounded 95% period count.
  This covers the one-period tolerance from §2 and shows the fan crossing the line.

**Rationale**: This meets User Story 3's acceptance scenario 2 ("continues until at least
the 95% completion date") without rendering a long tail that would squash the
interesting region.

## 6. Charting library for the web UI

**Decision**: **Recharts** `^3.10.1` (React 16.8–19 supported; latest release
2026-09-21, older than the 7-day cooldown), plus its peer dependency `react-is`.

**Rationale**: It's declarative and React-native, so it fits the existing `useState` +
`fetch` app with no imperative DOM code. It covers every chart needed out of the box:
bars (distribution, run chart), lines and stepped lines (probability curve), shaded ranges
between lines (fan), and reference lines (confidence markers, median, backlog line,
target date). It has built-in tooltips (FR-012) and renders SVG, which is accessible and
inspectable in tests. The constitution requires the new dependency to be justified in the
PR description: hand-rolling four interactive, responsive SVG charts with tooltips and
keyboard support is substantially more code to own and test.

**Alternatives considered**:
- *Hand-written SVG*: no dependency, but tooltips, axes, ticks, responsiveness and
  keyboard access for four charts is a large amount of bespoke code.
- *Observable Plot / D3*: excellent statistical charts, but imperative DOM rendering
  inside React effects, and harder to test with Testing Library.
- *Chart.js / ECharts*: canvas output is opaque to jsdom tests and screen readers, and
  ECharts is heavy.
- *Vega-Lite*: avoided partly to keep implementation choices visibly distinct from
  predictability-engine (Principle I), and it's heavyweight for four charts.

**Testing note**: Recharts' `ResponsiveContainer` measures its parent, which is zero-sized
under jsdom. Tests (a) cover the pure data-shaping functions directly, and (b) render chart
components with fixed `width`/`height` or a stubbed `ResizeObserver`, asserting on text
alternatives and captions rather than SVG geometry.

## 7. Frontend structure and coexistence with spec 004 (styling)

**Decision**:
- **Pure data shaping** goes in `frontend/src/charts/chartData.ts`: functions from
  `ForecastResult` (plus the submitted history and period length) to chart-ready series.
  It has no React dependency and is unit-tested exhaustively.
- **One component per chart** in `frontend/src/charts/` (distribution, probability
  curve, burn-up, run chart), plus a `ForecastCharts` wrapper.
- **Shared confidence-level style** in `frontend/src/charts/confidenceLevels.ts`: one
  label and one colour per level, imported by every chart (FR-010).
- **`App.tsx` change is minimal**: render `<ForecastCharts …/>` inside the existing results
  section, and keep the submitted history and period length alongside the result so the
  charts draw what was actually submitted, not later edits to the form.

Spec 004 is restyling `App.tsx` in a parallel session and isn't merged. Implementation of
this feature waits until 004 merges and rebases on it. Keeping chart code in its own
directory limits the conflict to a few lines in `App.tsx`. Chart colours and type follow
004's design-token contract (slate neutrals, blue primary). The confidence palette uses
one hue at four strengths (darker = higher confidence), which stays readable for
colour-blind users because each level is also labelled.

**Open layout point**: 004's contract caps the content column at `max-w-xl` (~576px),
which is narrow for a 60-bar histogram and a burn-up. The plan widens only the results
area that holds the charts (e.g. `max-w-4xl`) and leaves the form column as 004 defines
it. Because this touches 004's layout decision, it's raised for confirmation (see
plan.md).

## 8. Accessibility (FR-011, FR-012, FR-013)

**Decision**: Each chart is a `<figure>` containing:
- a visible title,
- a `<figcaption>` with a one-sentence plain-language explanation of how to read it,
- the SVG chart, marked `aria-hidden`,
- a visually hidden text summary listing the values the chart marks. For example: "50%:
  6 Nov 2026; 70%: 13 Nov 2026 …" or "Median throughput: 4 items per period".

Tooltips show on hover and on keyboard focus (Recharts `accessibilityLayer`, which is on
by default in v3).

**Rationale**: The existing results list stays as the primary text answer. The charts add
to it and never replace it (FR-007), so screen-reader users lose nothing.

## 9. Clean-room note (Principle I)

These chart types (outcome histogram, cumulative probability curve, burn-up fan, run
chart) are general Monte Carlo and Kanban forecasting practice described in public
literature. No predictability-engine code, file layout, naming or documentation was
consulted beyond its README's feature list. All names here are this project's own.
