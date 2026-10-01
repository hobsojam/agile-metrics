# Data Model: Throughput-Based Monte Carlo Forecast

All three entities are `pydantic` v2 models (Constitution: "no raw dicts crossing
boundaries"). Validation rules make invalid states unrepresentable at construction time
rather than checked later in a separate function.

## ThroughputHistory

Represents the historical record a forecast is based on (spec: Key Entities — Throughput
History).

| Field | Type | Rules |
|---|---|---|
| `completed_per_period` | `list[int]` | Each element ≥ 0 (FR-010). At least `MIN_HISTORICAL_PERIODS` (6) elements (FR-006). Not all elements may be 0 (FR-007). |
| `period_duration` | `timedelta` | Must be positive. Shared real-world length of every period (FR-001; see research.md). |

**Derived**: `len(completed_per_period)` is "the number of historical periods used," surfaced
in `ForecastResult` per FR-004/User Story 3.

## ForecastRequest

Represents a single forecast ask — either mode from FR-002, mutually exclusive per FR-011.

| Field | Type | Rules |
|---|---|---|
| `history` | `ThroughputHistory` | Required. |
| `backlog_size` | `int \| None` | If set, must be a positive whole number (FR-008). Mode (a): forecast completion dates. |
| `target_date` | `date \| None` | If set, must be strictly after the reference date (FR-008). Mode (b): forecast items completed. |
| `seed` | `int \| None` | Optional. When supplied, forecast is fully deterministic (FR-009). |
| `reference_date` | `date` | Defaults to the date the forecast is run (spec Assumptions: "today"). |

**Validation rule (FR-011)**: exactly one of `backlog_size` / `target_date` MUST be set —
enforced by a model validator, not left to caller discipline.

## ForecastResult

Represents the outcome of a `ForecastRequest` (spec: Key Entities — Forecast Result;
Constitution Principle IV: never a bare point estimate).

| Field | Type | Rules |
|---|---|---|
| `outcomes` | `dict[Literal[50, 70, 85, 95], date \| int]` | One entry per confidence level (FR-005). Value type is `date` for mode (a), `int` for mode (b) — matches the request mode. |
| `trials_run` | `int` | Number of simulation trials executed (FR-004). |
| `periods_used` | `int` | Number of historical periods the forecast was based on (FR-004, User Story 3). |

**Invariant**: for mode (a), `outcomes[50] <= outcomes[70] <= outcomes[85] <= outcomes[95]`
(higher confidence ⇒ later or equal date). For mode (b), the inequality direction is
reversed: `outcomes[50] >= outcomes[70] >= outcomes[85] >= outcomes[95]` (higher confidence
⇒ fewer or equal items guaranteed done). Both directions are asserted by the acceptance-scenario
tests in `test_forecast.py`.

## Validation error shape

All rejections (FR-006, FR-007, FR-008, FR-010, FR-011) surface as `pydantic.ValidationError`
raised during model construction, with a message naming the specific violated rule — there is
no separate "error result" type; invalid input never reaches the simulation core.
