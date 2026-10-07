# Quickstart: Jira Flow Metrics

Scenarios 1-5 run with the HTTP layer mocked, no network access needed. Scenario 6 needs a
real Jira Cloud site and is the gate that catches schema mismatches mocks cannot - the same
role quickstart Scenario 5 played in spec 010.

## Prerequisites

- `uv sync` at the repo root.
- For Scenario 6 only: a Jira Cloud site, account email, API token, and a project with a
  mix of resolved, in-progress, and never-started issues.

## 1. Start-date detection from the changelog

```bash
uv run pytest tests/test_jira_client.py -k "start_date or changelog" -v
```

Expected: an issue's first transition into an in-progress-category status is its start
date, even when it later left and re-entered progress (research.md §1, spec Edge Cases); an
issue with no such transition is excluded, not guessed.

## 2. One query, one universe

```bash
uv run pytest tests/test_jira_client.py -k "flow_issues" -v
```

Expected: the JQL fetch returns resolved-in-window issues and all currently-in-progress
issues in one call (research.md §2); an issue resolved without ever being in progress is
absent from both the cycle-time and aging results.

## 3. The three views and their shared invariant

```bash
uv run pytest tests/test_jira_client.py tests/test_models.py -k "flow" -v
```

Expected: `compute_jira_flow_metrics` returns cycle-time entries only for resolved issues
with a known start; WIP snapshots only for currently-in-progress issues; and
`flow_state_counts` where, for every day, `not_started + in_progress + done ==
len(cycle_time) + len(wip)` (data-model.md's validator, SC-003). A project with more than
500 eligible issues reports the overflow in `capped_count`, distinct from `excluded_count`.

## 4. Web and CLI surfaces

```bash
uv run pytest tests/test_cli.py tests/test_web.py -k "flow_metrics" -v
```

Expected: `flow_metrics` appears in the JSON response only for Jira requests, `null`
otherwise; the CLI prints the one-line summary only for Jira; manual, Linear, and CSV
responses are unchanged.

## 5. Frontend

```bash
npm test -- -t "flow metrics"
```

Expected: the three new views render only when `result.flow_metrics` is present, alongside
the existing four forecast charts, not instead of them (FR-007); a project with no
in-progress issues shows the plain "nothing in progress" state, not an empty chart.

## 6. Live check against a real Jira Cloud site (gate)

```bash
uv run agile-metrics --jira-site acme.atlassian.net --jira-email you@example.com \
  --jira-project ENG --period-days 7 --backlog-size 50 --seed 42
```

(with `AGILE_METRICS_JIRA_API_TOKEN` exported in your own shell beforehand - see the
Secrets note below)

Expected:
- the new `Flow metrics:` summary line appears, with numbers that agree with a manual
  spot-check of a few issues in Jira itself;
- confirms whether `expand=changelog` on `/rest/api/3/search/jql` actually bundles each
  issue's changelog in the same response (research.md §1) - if the changelog is missing or
  shaped differently than expected, this is where that surfaces, not in production;
- an issue known to have skipped "in progress" entirely is confirmed absent from the
  cycle-time/aging/CFD views, with the exclusion count matching.

**Secrets note**: export the token in your own shell, not via a command whose literal text
would be echoed back into this conversation - see the global "Secrets and the `!` Prefix"
guidance.

## 7. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
uv run pip-audit && uv run bandit -c pyproject.toml -r src/
cd frontend && npm run lint && npm run typecheck && npm test && npm audit
```

Expected: everything passes.
