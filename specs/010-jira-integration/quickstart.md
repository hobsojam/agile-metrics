# Quickstart: Jira Integration

Validates the Jira source end to end. Scenarios 1-4 run with the HTTP layer mocked and need no
network access. Scenario 5 needs a real Jira Cloud site and is the gate that catches schema
mismatches mocks cannot (the lesson from spec 006's live-testing bugs).

## Prerequisites

- `uv sync` at the repo root.
- For Scenario 5 only: a Jira Cloud site, an account email, an API token
  (https://id.atlassian.com/manage-profile/security/api-tokens), and a project key with some
  resolved issues in the last 26 weeks.

## 1. Pure logic: UTC bucketing, lookback window, issue-type exclusion, done-status mapping

```bash
uv run pytest tests/test_jira_client.py -k "bucket or window or excluded or done_status" -v
```

Expected: an issue resolved at 23:30 UTC on a boundary lands in the later period; epics and
sub-tasks are excluded; an issue with no `resolutiondate` is excluded; only statuses whose
category key is `done` count.

## 2. Pagination

```bash
uv run pytest tests/test_jira_client.py -k "pagination" -v
```

Expected: a two-page mocked response (first page with a `nextPageToken`, second with
`isLast: true`) yields every issue across both pages - none dropped.

## 3. Error categories

```bash
uv run pytest tests/test_jira_client.py -k "error" -v
```

Expected: each category in contracts/jira-errors.md raises its own exception type with its own
message; no message contains the API token.

## 4. Source selection and web/CLI surfaces

```bash
uv run pytest tests/test_cli.py tests/test_web.py -k "jira" -v
```

Expected: partial Jira credentials name the missing field; exactly-one-of-four is enforced;
`done_statuses` appears in the web response and the CLI prints the `Done statuses:` line for
Jira only; the manual, Linear, and CSV paths are unchanged.

## 5. Live check against a real Jira Cloud site (gate)

```bash
uv run agile-metrics \
  --jira-site acme.atlassian.net \
  --jira-email you@example.com \
  --jira-project ENG \
  --period-days 7 \
  --backlog-size 50 \
  --seed 42
```

(with `AGILE_METRICS_JIRA_API_TOKEN` exported, so the token is not in shell history)

Expected:
- a forecast is printed, with a `Done statuses:` line listing real status names for the project;
- the throughput counts agree with a manual count: open the project's issue search,
  `project = ENG AND resolved >= -26w AND issuetype not in (Epic, Sub-task)`, and compare its
  count with the sum of the per-period counts in the web UI's history chart (the CLI prints
  only the forecast, so use the web UI for this comparison);
- a deliberately wrong token gives the authentication message, not a stack trace.

If `issuetype.subtask` or `issuetype.hierarchyLevel` is absent from the real response, Scenario
5 fails here - that is the point of running it before merge.

## 6. Quality gates

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src
uv run pytest --cov
uv run pip-audit && uv run bandit -c pyproject.toml -r src/
cd frontend && npm run lint && npm run typecheck && npm test && npm audit
```

Expected: everything passes.
