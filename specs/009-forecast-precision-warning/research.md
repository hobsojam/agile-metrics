# Research: Forecast Precision Warning

## 1. The spread-ratio metric

**Decision**:

```
p50 = outcomes[50]
p95 = outcomes[95]

if p50 is a date:
    center = (p50 - reference_date).days
    spread = (p95 - p50).days          # p95 >= p50 always (later = higher confidence)
    ratio = spread / max(center, 1)
else:
    spread = p50 - p95                  # p95 <= p50 always (fewer items = higher confidence)
    ratio = spread / max(p95, 1)        # correction below - NOT max(p50, 1)

warns if ratio > 1.0                    # confirmed decision, plan.md §"Decisions"
```

**Correction (2026-10-05, found via live arithmetic check before writing tests, not from a
unit test)**: the count-mode branch originally divided by `max(p50, 1)` (mirroring the
date-mode denominator exactly). That's unit-invariant but wrong: item counts are bounded
below by zero, so `p95 >= 0` always, which caps `spread = p50 - p95` at `p50` and therefore
caps `ratio` at exactly `1.0` - reachable only when `p95 == 0`, never exceedable. Confirmed
empirically against the real simulation (sparse history, 5-year target → outcomes `{50: 5,
70: 4, 85: 3, 95: 2}` → `ratio = 0.6`; sparse history, 30-day target → outcomes all `0` →
`ratio = 0.0`): no real `forecast_by_date` output can ever cross the threshold with the
original formula, silently violating FR-006 ("the warning MUST apply identically to both
forecast modes"). Date-mode has no equivalent bound - future dates are unbounded, so its
tail can exceed its center freely. Count-mode's tail (the pessimistic *few-items* outcome)
shares the same floor as the metric's own denominator, which date-mode's tail (the
pessimistic *far-future* outcome) does not share with its denominator (today). Dividing by
`max(p95, 1)` instead - comparing the shortfall to the pessimistic floor rather than to the
median - removes the bound (`3 / max(2, 1) = 1.5` for the 5-year-target example above,
correctly warning) while still producing `0` for a tight, consistent forecast. This means
the two modes no longer share one literal formula (the earlier "unit-invariant, no
mode-specific casing" framing below is now inaccurate for the denominator choice, though
each mode's own formula is still unit-invariant on its own terms) - the branch was already
required to pick date vs. int paths, so this is a different per-branch calculation, not a
new code path.

**Rationale**: this ratio is dimensionless and unit-invariant — `period_duration` cancels
out of the division (both `center` and `spread` scale by the same factor), so there's no
need to convert into "periods" at all; raw day/item differences work identically. It
directly measures "how much wider is the worst-realistic-case tail than the typical case,"
which is exactly spec FR-002's requirement: based on the *computed outcome spread*, not an
input characteristic like `periods_used` considered in isolation. This is also why the
edge cases in spec.md resolve correctly without any special-casing:

- **Few periods, but consistent** (spec Edge Cases): a tight simulated distribution
  produces a small `ratio` regardless of how few periods fed it — not flagged.
- **Many periods, but inconsistent**: a wide simulated distribution produces a large
  `ratio` regardless of how much data fed it — flagged.
- **Count-based (target-date) mode**: the mirrored-percentile convention
  (`forecast_by_date`'s existing `100 - level` read-off, data-model.md's invariant that
  higher confidence means a *lower* item count) is handled by computing `spread` as
  `p50 - p95` instead of `p95 - p50` for the int case, **and** dividing by `max(p95, 1)`
  instead of `max(center, 1)` (per the correction above) — same threshold, correct sign
  either way, but a mode-specific denominator rather than one literal shared formula.

**`max(center, 1)` / `max(p95, 1)` floor**: guards division-by-zero when the denominator
would otherwise be zero - date-mode's `center` is zero when the median outcome is
`reference_date` itself (an already-at-or-past-target forecast); count-mode's `p95` is zero
when the pessimistic case is "nothing completed at all." Neither zero denominator means
"infinitely imprecise" on its own - it means the typical (or pessimistic) case is
"immediately" / "nothing" - so clamping to 1
avoids a crash while still letting a large absolute `spread` produce a large (if somewhat
extreme) ratio in that case, which is the correct behavior: a forecast that's "done
immediately at the median, but years away at the 95th percentile" genuinely is exactly the
kind of imprecise result this feature exists to flag.

**Alternatives considered**:

- **A composite metric using all four confidence levels** (not just 50/95) — rejected;
  the 50-to-95 gap is literally the full range already displayed on screen (the first and
  last numbers a user sees), so flagging based on it is immediately, visibly verifiable by
  the user without needing to understand a more complex formula (Principle IV - transparent
  assumptions means the *trigger* should be transparent too, not just the output).
- **Basing the warning on `periods_used` or a zero-count fraction of the input history**
  directly — rejected per FR-002's explicit requirement; these are plausible *causes* of a
  wide spread, not the spread itself, and checking them directly would flag/miss exactly
  the two edge cases above incorrectly (few-but-consistent periods would false-positive;
  many-but-bursty periods could false-negative depending on the exact check chosen).
- **Using the full `distribution` histogram** (up to 60 buckets) instead of just the two
  named outcome values — rejected for this version; richer, but harder to explain to a user
  in a single plain-language sentence tied to numbers they can already see, and the
  two-outcome ratio already satisfies every spec requirement and edge case.

## 2. Threshold value

**Decision**: `ratio > 1.0` — confirmed (plan.md "Decisions needing confirmation" §1).

**Rationale**: "the worst-realistic-case tail is at least as far out as the typical case
itself" is an intuitive, easy-to-explain line: beyond this point, the forecast is telling
the user "it could very plausibly take twice as long (or more) as the headline median
suggests," which is a meaningfully different message than "it'll be done around date X."
Confirmed against the feature's own motivating real-world example (a Linear-backed
forecast with p50 ≈ 2035 and p95 ≈ 2049, roughly 9 years out at the median and 14 years of
additional spread beyond that → ratio ≈ 1.6, comfortably above the threshold) and a
plausible "tight" counter-example (p50 10 weeks out, p95 13 weeks out → ratio 0.3, well
below it).

**Alternatives considered**: 1.5x and 2.0x (more conservative, fewer false positives at
the cost of under-flagging moderately-wide-but-still-impractical forecasts) — not chosen.

## 3. Module placement

**Decision**: `_compute_precision_warning(outcomes, reference_date) -> PrecisionWarning |
None` as a new private function in `forecast.py`, called from both `forecast_by_items` and
`forecast_by_date` right before each constructs its `ForecastResult`. `PrecisionWarning`
itself is a new model in `models.py`, alongside `ForecastResult`.

**Rationale**: mirrors this project's existing pattern exactly — `forecast.py` already
has per-mode private helpers (`_build_distribution_dates`/`_build_distribution_ints`,
`_build_projection`) that both public functions call into; this is one more such helper,
not a new module or subsystem (Principle V).

## 4. Message content

**Decision**: a single `message: str` field on `PrecisionWarning` (no severity levels, no
structured reason codes) — plain text naming the actual computed ratio, e.g. "This
forecast's range is very wide: the 95% outcome is roughly {ratio:.1f}x further from the
median than the median itself is from today. Treat these numbers as a rough risk range,
not a committed plan." (exact wording is an implementation-time detail, not fixed here).

**Rationale**: spec FR-003 asks for a plain-language explanation of *why*, not a
machine-readable taxonomy of causes — and per research.md §1, the tool doesn't actually
diagnose a root cause (sparse data vs. bursty data vs. something else); it only measures
the symptom. Describing the symptom precisely, with the actual numbers behind it, is both
simpler to implement and more directly verifiable by the user than inventing categories
for causes the computation never actually determines.

**Alternatives considered**: a structured `reason: Literal[...]` field distinguishing
"insufficient data" from "highly inconsistent throughput" — rejected; would require
additional computation on the raw `ThroughputHistory` (period count, zero-count fraction)
that research.md §1 specifically avoided needing, and risks guessing at a cause the
symptom-only computation can't actually distinguish.
