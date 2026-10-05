# Research: CSV Item Import

## 1. CSV parsing

**Decision**: Python's standard library `csv` module (`csv.DictReader`), not a new
dependency.

**Rationale**: `DictReader` already gives header-name-keyed row dicts for free, which
directly satisfies two spec requirements with no extra code: matching columns by header
name rather than position (Edge Cases), and ignoring extra, unrecognized columns (Edge
Cases — they simply end up as unused dict keys). No new dependency to justify in the
implementing PR (constitution: "prefer the standard library... before adding new deps").

**Alternatives considered**: `pandas.read_csv` — rejected; pandas is an existing dependency
for *tabular metrics data handling* (constitution Technology Stack), but pulling in a
DataFrame for row-by-row validation with per-row, per-field error messages (FR-007) is a
worse fit than the stdlib's row-dict iteration, and would be the first use of pandas
anywhere in the codebase for a feature that doesn't need vectorized operations.

## 2. Web transport: multipart endpoint

**Decision**: A new `POST /api/forecast/csv` endpoint, `multipart/form-data`, accepting:

- `csv_file`: `UploadFile | None` — an uploaded file
- `csv_text`: `str | None` — pasted CSV text (so the web UI's "paste" option and "upload"
  option both reach the same endpoint; exactly one of the two must be present, same
  "exactly one of" pattern already used for `backlog_size`/`target_date` and
  `history`/`linear_*`)
- `period_days`, `backlog_size`, `target_date`, `seed` — the same fields
  `ForecastRequestBody` already has, as individual FastAPI `Form(...)` parameters (FastAPI
  has no native multipart support for a single nested JSON body field, so these travel as
  sibling form fields rather than a nested object)

The existing `POST /api/forecast` (JSON) endpoint is completely unchanged — no `csv_*`
fields are added to it, and CSV is not a third arm of its `history`/`linear_*` check.

**Rationale**: confirmed decision (plan.md "Decisions confirmed before implementation" §1).
Keeps file bytes out of a JSON body and gives CSV import its own explicit contract, at the
cost of a second request shape — accepted because file upload is a genuinely different kind
of request than the existing JSON-only API has needed so far.

**Alternatives considered**: a single `csv_text` field on the existing `ForecastRequestBody`
(frontend reads an uploaded file into text client-side via `File.text()` before sending
JSON) — this was the recommended option; not chosen.

## 3. Module placement

**Decision**: A single new module, `src/agile_metrics/csv_item_import.py` — not a new
package, mirroring `linear_client.py`'s precedent (006 research.md §6).

**Rationale**: Constitution Principle V — no speculative structure ahead of a second,
actually-demonstrated need. If a future `integrations/`-style package becomes warranted once
Jira (#180) or item-level flow metrics also need shared structure, that is the point to
introduce it, not now.

**Public surface**: two functions, both pure (no I/O):

- `parse_items_csv(csv_text: str) -> list[Item]` — parses and validates row-by-row,
  raising a `CsvImportError` subclass naming the specific row/column/column-set problem.
- `bucket_items_to_throughput(items: list[Item], period_duration: timedelta) ->
  ThroughputHistory` — derives the period count from the data itself (§4) and buckets
  completed items' `end_date` values into it.

The CLI and web layers call both in sequence, then proceed exactly as manual paste and
Linear import already do (FR-004; Principle II unaffected).

## 4. Deriving the period count from the data

**Decision**: Unlike Linear (a fixed period count, default 26), a CSV has no separate
"lookback periods" concept (spec Assumptions) — the period count is derived entirely from
the completed items' `end_date` values, anchored so the most recent period ends today (the
same anchoring convention manual paste and Linear already use):

```
completed = [item.end_date for item in items if item.end_date is not None]
if not completed:
    periods = MIN_HISTORICAL_PERIODS   # 6 - produces an all-zero history
else:
    earliest = min(completed)
    periods = (today - earliest).days // period_duration.days + 1
```

The resulting `completed_per_period` list is then built the same way Linear's bucketing
does: bucket `k` (0 = oldest) covers `[today - (periods-k)*period_duration, today -
(periods-k-1)*period_duration)`. An `end_date` that falls outside this computed range
(e.g., a future-dated completion) is silently excluded from bucketing rather than clamped
into the wrong bucket — the same defensive behavior `linear_client.py`'s bucketing already
has for its own out-of-range case.

**Rationale**: this formula is what makes the two "no valid completion data" shapes in the
spec land on the *correct*, *different* existing messages without any new error-handling
code:

- **Zero items have any `end_date` at all** (spec Edge Cases / Acceptance Scenario 4) →
  `periods = MIN_HISTORICAL_PERIODS` exactly, all-zero → `ThroughputHistory`'s existing
  all-zero validator fires, matching manual paste's and Linear's message for the same case.
- **Some items have an `end_date`, but they only span a few periods** (spec Acceptance
  Scenario 3) → `periods` is computed as that smaller number, with *no* clamping up to the
  minimum → `ThroughputHistory`'s existing too-few-periods validator fires instead,
  correctly distinct from the all-zero case.

Clamping the derived count up to `MIN_HISTORICAL_PERIODS` in *all* cases was considered and
rejected specifically because it would make the too-few-periods case (Acceptance Scenario 3)
unreachable — every CSV would always produce at least 6 padded (mostly-zero) periods,
silently hiding genuinely sparse data instead of naming the problem.

**Alternatives considered**: requiring the user to additionally specify a period count or
date range for CSV import, mirroring Linear's `--linear-periods` — rejected; a CSV is
already a complete, bounded dataset (unlike an open-ended API fetch), so asking the user to
redundantly bound it again adds a parameter spec's Assumptions explicitly says this feature
doesn't need.

## 5. Row-level validation and error messages

**Decision**:

- **Required columns** (FR-008): all five of `id, type, title, start_date, end_date` MUST
  appear as header names (case-sensitive, matching the spec's exact names) before any row is
  read. Missing any → immediate rejection naming the missing column(s), no row-level
  parsing attempted.
- **Per-row requiredness** (FR-007, FR-010): only `id` must be non-blank on every row — a
  blank `id` is "missing a required field." `start_date` and `end_date` may each be blank
  independently (an item can have an unknown start, be not-yet-completed, or both); a
  *non-blank* `start_date`/`end_date` that fails to parse as `YYYY-MM-DD` is "malformed," not
  "missing." `type` and `title` are free text with no required/format constraint — a blank
  value is stored as an empty string, never an error.
- **Row numbering**: error messages count data rows only, starting at 1 for the first row
  after the header — e.g. "row 1" is the CSV's first item, independent of the header
  occupying its own line. Chosen to match how a user counting down their own data (ignoring
  the header) would expect rows to be numbered, since the header is a fixed, known line, not
  itself a candidate for "which row is wrong."
- **Duplicate `id` values, extra columns, out-of-order columns** (spec Edge Cases): none of
  these are errors — `id` is an opaque passthrough label with no uniqueness constraint
  enforced here, and `csv.DictReader` already matches by header name regardless of column
  order or extra columns (§1).

**Rationale**: this gives FR-007's "row number and field" error text exactly one case per
failure mode (missing `id`, malformed `start_date`, malformed `end_date`) with no ambiguity
about whether a given blank value is an error — directly testable per row, matching the
precision Linear's error-classification table (006 research.md §3) already established as
this project's bar for "clear, specific" errors (spec FR-007 explicitly asks for the same
standard).
