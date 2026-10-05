# Data Model: Forecast Precision Warning

## New model: `PrecisionWarning` (in `agile_metrics.models`)

| Field | Type | Meaning |
|---|---|---|
| `message` | `str` | Plain-language explanation of why this forecast's precision is low (research.md §4) |

No validation rules beyond the inherited `pydantic` non-empty-string-by-default behavior —
`message` is always populated by the library when the field is present at all (there's no
"empty warning" state; absence is modeled as the field being `None`, not an empty message).

## Changed model: `ForecastResult`

One new field, fully optional, purely additive:

```python
class ForecastResult(BaseModel):
    outcomes: dict[Literal[50, 70, 85, 95], date | int]
    trials_run: int
    periods_used: int
    reference_date: date
    distribution: list[OutcomeBucket]
    projection: list[ProjectionPoint]
    precision_warning: PrecisionWarning | None = None  # NEW
```

No existing field's type, meaning, or validation changes (spec FR-004). `ForecastResponseBody(ForecastResult)` in `web.py` inherits this field automatically — no `web.py` change needed for it to appear in the JSON API response.

## New function (not a model): `_compute_precision_warning`

```python
def _compute_precision_warning(
    outcomes: dict[int, date | int], reference_date: date
) -> PrecisionWarning | None:
```

Pure, deterministic given its inputs — no I/O, no randomness (research.md §1). Returns
`None` when the computed ratio is at or below the threshold; returns a `PrecisionWarning`
naming the actual ratio otherwise.

**Called from**: `forecast_by_items` and `forecast_by_date`, immediately before each
constructs its `ForecastResult` — the one and only place either function builds its
`outcomes` dict, so there's exactly one call site per mode (data-model.md's "computed once"
guarantee from spec FR-005/FR-006).

## CLI / web / frontend changes

- **`web.py`**: no change — `precision_warning` flows through `ForecastResponseBody`
  automatically.
- **`cli.py`**: `_render_result` prints an additional line when `result.precision_warning`
  is not `None`, after the four confidence-level lines.
- **`frontend/src/App.tsx`**: a visible warning banner (distinct styling from the existing
  error banner — an amber/warning treatment, not red/error) rendered when
  `result.precision_warning` is present, showing its `message`.
