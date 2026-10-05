# Quickstart: CSV Item Import

Validates that CSV-backed forecasting works end-to-end, without regressing the existing
manual-paste or Linear-import paths. Every scenario below is self-contained — no external
service, API key, or network access needed (unlike Linear's scenarios 6-7).

## Prerequisites

- `uv sync` at the repo root; `npm ci` in `frontend/`

## 1. CSV parsing and row-level validation

```bash
uv run pytest tests/test_csv_item_import.py -k "parse" -v
```

Expected: a well-formed CSV produces one `Item` per data row, matched by header name
regardless of column order (research.md §1); a CSV missing a required column is rejected
before any row is read; a row with a blank `id` or an unparsable `start_date`/`end_date` is
rejected naming the specific row number and column (research.md §5); a row with a blank
`end_date` is accepted, not rejected (FR-010).

## 2. Bucketing and period-count derivation

```bash
uv run pytest tests/test_csv_item_import.py -k "bucket" -v
```

Expected: items' `end_date` values are bucketed the same way Linear's are, anchored to
today; a CSV where every item lacks an `end_date` produces the *existing* all-zero
validation message (not a new error); a CSV whose completions span fewer than
`MIN_HISTORICAL_PERIODS` produces the *existing* too-few-periods message — the two cases are
distinct (research.md §4).

## 3. CLI, CSV mode

```bash
uv run pytest tests/test_cli.py -k csv -v
```

Expected: `agile-metrics --csv-file items.csv --period-days 7 --backlog-size 20` prints the
same output format as manual-paste mode, derived from the file's completion dates.

## 4. Web API, CSV mode

```bash
uv run pytest tests/test_web.py -k csv -v
```

Expected: `POST /api/forecast/csv` (multipart, either `csv_file` or `csv_text`) returns the
same 200 response shape as `POST /api/forecast` with manually-entered history covering the
same underlying per-period counts.

## 5. Manual end-to-end check, CLI

```bash
cat > /tmp/items.csv <<'EOF'
id,type,title,start_date,end_date
1,story,First item,2026-08-01,2026-08-05
2,story,Second item,2026-08-03,2026-08-12
3,bug,Third item,2026-08-10,2026-08-19
4,story,Fourth item,2026-08-15,2026-08-26
5,bug,Fifth item,2026-09-01,2026-09-02
6,story,Sixth item,2026-09-10,2026-09-16
7,story,Still open,2026-09-20,
EOF
uv run agile-metrics --csv-file /tmp/items.csv --period-days 7 --backlog-size 20 --seed 42
```

Expected: a forecast with all four confidence levels, computed from the six completed
items' `end_date` values (the seventh, still-open item is accepted but excluded from
bucketing).

## 6. Manual end-to-end check, web UI

```bash
uv run uvicorn agile_metrics.web:app --reload
cd frontend && npm run dev
```

Switch the form's "Data source" to CSV, paste the same CSV content from scenario 5 (or
upload it as a file), submit, and confirm a forecast renders exactly like the manual-paste
path does — plus the same four charts from spec 005, unmodified by this feature.

## 7. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
cd frontend && npm run lint && npm run typecheck && npm test && npm audit
```

Expected: everything passes.
