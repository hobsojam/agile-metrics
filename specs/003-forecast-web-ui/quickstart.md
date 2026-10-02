# Quickstart: Forecast Web UI

Validates the feature end-to-end once implemented. See `contracts/forecast-api.md` for the
full request/response contract.

## Prerequisites

- Backend: Python 3.11+ environment with the project installed (`uv sync`)
- Frontend: Node.js (current LTS) with dependencies installed (`cd frontend && npm ci`)

## Scenario 1 — Completion-date forecast via the API (User Story 1)

```bash
uv run uvicorn agile_metrics.web:app --reload &
curl -s -X POST http://localhost:8000/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"history": [3,5,4,6,2,5,4,3], "period_days": 7, "backlog_size": 20, "seed": 42}'
```

**Expected outcome**: HTTP 200; JSON body with four confidence-level dates, matching
`specs/001-throughput-forecast/quickstart.md` Scenario 1's values for the same input/seed.

## Scenario 2 — Items-completed forecast via the API (User Story 2)

```bash
curl -s -X POST http://localhost:8000/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"history": [3,5,4,6,2,5,4,3], "period_days": 7, "target_date": "2026-12-01", "seed": 42}'
```

**Expected outcome**: HTTP 200; JSON body with four confidence-level item counts, matching
`specs/001-throughput-forecast/quickstart.md` Scenario 2's values.

## Scenario 3 — In the browser, end to end (User Stories 1-2)

```bash
cd frontend && npm run dev
```

Open the dev server URL, paste `3,5,4,6,2,5,4,3` as the history, enter `7` as the period
length, enter `20` as the backlog size, submit.

**Expected outcome**: the page displays the same four dates as Scenario 1, with the trial
count and periods-used metadata visible, no page reload/navigation required.

## Scenario 4 — Rejecting bad input (edge cases / SC-003)

```bash
curl -s -X POST http://localhost:8000/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"history": [3,5,4,6,2,5,4,3], "period_days": 7}'
```

**Expected outcome**: HTTP 400; `{"error": "..."}` body explaining that exactly one of
`backlog_size`/`target_date` is required. In the browser, submitting the form the same way
must show this message on the page, not a blank screen or a browser-level network error.

## Running it for real

```bash
uv run pytest tests/test_web.py -v
cd frontend && npm test
```
