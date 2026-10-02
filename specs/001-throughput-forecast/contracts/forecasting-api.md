# Contract: `agile_metrics` public forecasting API

Per Constitution Principle II, this is the *only* surface any future CLI, dashboard, or
other presentation layer may depend on — it must not reach into `simulation.py` or
`models.py` internals directly.

## `forecast_by_items`

```python
def forecast_by_items(
    history: ThroughputHistory,
    backlog_size: int,
    *,
    seed: int | None = None,
    reference_date: date | None = None,
) -> ForecastResult:
    """Forecast completion dates for a backlog of `backlog_size` remaining items.

    Raises pydantic.ValidationError if `history` or `backlog_size` violate any
    rule in data-model.md (FR-006, FR-007, FR-008, FR-010).
    """
```

Corresponds to spec User Story 1 / FR-002(a). `ForecastResult.outcomes` values are `date`.

## `forecast_by_date`

```python
def forecast_by_date(
    history: ThroughputHistory,
    target_date: date,
    *,
    seed: int | None = None,
    reference_date: date | None = None,
) -> ForecastResult:
    """Forecast how many items will be completed by `target_date`.

    Raises pydantic.ValidationError if `history` or `target_date` violate any
    rule in data-model.md (FR-006, FR-007, FR-008, FR-010).
    """
```

Corresponds to spec User Story 2 / FR-002(b). `ForecastResult.outcomes` values are `int`.

## Notes

- Both functions are thin wrappers that construct a `ForecastRequest` (triggering its
  FR-011 mutual-exclusivity validation implicitly, since each function only exposes one of
  the two fields) and delegate to the shared simulation core in `forecast.py`.
- Neither function performs I/O; callers are responsible for however they obtain
  `completed_per_period`/`period_duration` and for displaying the `ForecastResult` (CLI
  output, a file, a future dashboard — out of scope per spec Assumptions).
- `trials_run` and `periods_used` are always present on the result (User Story 3 / FR-004),
  regardless of which function was called.
