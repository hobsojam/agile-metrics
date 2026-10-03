# Data Model: Forecast Charts

Extends the models in `src/agile_metrics/models.py` (spec 001). All new shapes are
`pydantic` models (constitution: no raw dicts across boundaries). They're exposed
unchanged through the web API (see [contracts/forecast-api.md](./contracts/forecast-api.md)).

`ThroughputHistory` and `ForecastRequest` are **unchanged**.

## ForecastResult (existing, extended)

| Field | Type | Status | Meaning |
|---|---|---|---|
| `outcomes` | `dict[Literal[50,70,85,95], date \| int]` | unchanged | Headline answer per confidence level |
| `trials_run` | `int` | unchanged | Number of simulated futures |
| `periods_used` | `int` | unchanged | Number of historical periods resampled |
| `reference_date` | `date` | **new** | The date the forecast starts from (the end of the most recent historical period). It anchors the burn-up's date axis (FR-014) and surfaces an input that was previously implicit (Principle IV). |
| `distribution` | `list[OutcomeBucket]` | **new** | Simulated outcomes grouped for the histogram and probability curve |
| `projection` | `list[ProjectionPoint]` | **new** | Cumulative future items per period at each confidence level, for the burn-up fan |

The new fields are **required**. Every `ForecastResult` is produced by
`forecast_by_items`/`forecast_by_date`, which always fill them in. The only other
constructors are two hand-built fixtures in `tests/test_cli.py`, which get the new fields
added. Making the fields required keeps the generated TypeScript types non-optional, so
the UI never has to handle "charts data missing".

**New validation rules** (model validator, raising `ValueError` like the existing ones):

- `sum(b.trials for b in distribution) == trials_run`
- `1 ≤ len(distribution) ≤ 60`
- Buckets are in ascending order, don't overlap, and each has `lower ≤ upper`. Bucket
  bounds are dates when `outcomes` holds dates, and integers when it holds integers.
- `projection` is non-empty, and `period` runs `1, 2, …, len(projection)` with no gaps.

## OutcomeBucket (new)

One bar of the outcome distribution.

| Field | Type | Meaning |
|---|---|---|
| `lower` | `date \| int` | Smallest outcome in this bucket (inclusive): a completion date in backlog mode, an item count in target-date mode |
| `upper` | `date \| int` | Largest outcome in this bucket (inclusive). Equals `lower` when buckets are one value wide. |
| `trials` | `int` (≥ 0) | Number of simulated futures whose outcome fell in this bucket |

Grouping rule: research.md §3. Empty buckets inside the range are kept, with `trials = 0`,
so the bars show gaps honestly.

## ProjectionPoint (new)

One future period of the burn-up fan.

| Field | Type | Meaning |
|---|---|---|
| `period` | `int` (≥ 1) | Future period number, counted from the reference date |
| `period_end` | `date` | `reference_date + period × period_duration` |
| `cumulative` | `dict[Literal[50,70,85,95], int]` | Items completed from the reference date through this period that were reached or exceeded in L% of simulated futures |

**Invariants** (asserted by property tests rather than the model validator, since they
follow from the maths):

- Higher confidence never means more items: `cumulative[95] ≤ cumulative[85] ≤
  cumulative[70] ≤ cumulative[50]` at every period.
- Each level never decreases over time.
- **Target-date mode**: the last point's `cumulative[L] == outcomes[L]`, exactly.
- **Backlog mode**: the first period where `cumulative[L] ≥ backlog_size` is within one
  period of the period behind `outcomes[L]` (research.md §2).

Horizon (how many points): research.md §5.

## Derived in the web UI (not in the API)

These are computed by pure functions in `frontend/src/charts/chartData.ts`, and so only
from the response plus the history the user submitted (FR-009):

| Series | Derived from |
|---|---|
| Probability curve | Running total of `distribution[].trials ÷ trials_run`. Ascending in backlog mode ("done by"), descending in items mode ("at least") |
| Burn-up history | The submitted history's running total. Period *i* of *n* ends at `reference_date − (n − i) × period_days` |
| Burn-up fan | Historical total + `projection[].cumulative[L]` |
| Burn-up target line | Backlog mode: historical total + backlog size. Target-date mode: a vertical line at the target date |
| Run chart median | Median of the submitted history |
