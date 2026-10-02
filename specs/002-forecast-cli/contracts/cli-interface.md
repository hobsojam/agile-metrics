# Contract: Forecast CLI interface

This is the user-facing contract both the local CLI and the Docker container form must
satisfy identically (spec FR-008).

## Invocation

```text
agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --backlog-size 20 [--seed 42]
agile-metrics --history "3,5,4,6,2,5,4,3" --period-days 7 --target-date 2026-12-01 [--seed 42]
```

| Flag | Required | Notes |
|---|---|---|
| `--history` | yes | Comma-separated non-negative integers |
| `--period-days` | yes | Positive integer |
| `--backlog-size` | exactly one of this or `--target-date` | Positive integer |
| `--target-date` | exactly one of this or `--backlog-size` | `YYYY-MM-DD`, must be in the future |
| `--seed` | no | Integer; omit for a fresh random forecast each run |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Forecast computed and printed successfully |
| 1 | Any invalid input (CLI-level parsing failure or a library validation rejection) — a clean one-line `Error: ...` message is printed to stderr, never a stack trace |

## Output (stdout, on success)

```text
Forecast (<trials_run> trials, <periods_used> historical periods):
  50% confidence: <value>
  70% confidence: <value>
  85% confidence: <value>
  95% confidence: <value>
```

`<value>` is a date (`YYYY-MM-DD`) when `--backlog-size` was used, or an integer item count
when `--target-date` was used.

## Container equivalence

Running the same flags via the Docker image MUST produce byte-identical stdout and the same
exit code as running the local CLI directly — this is the specific behavior spec FR-008 and
SC-004 require, and what the CI Docker smoke test (research.md) checks automatically.
