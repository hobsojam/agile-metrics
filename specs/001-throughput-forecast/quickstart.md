# Quickstart: Throughput-Based Monte Carlo Forecast

Validates the feature end-to-end once implemented. See `data-model.md` for field details and
`contracts/forecasting-api.md` for the full function signatures.

## Prerequisites

- Python 3.11+ environment with the project installed (`uv sync`)

## Scenario 1 — "When will this backlog be done?" (User Story 1)

```python
from datetime import timedelta
from agile_metrics import forecast_by_items
from agile_metrics.models import ThroughputHistory

history = ThroughputHistory(
    completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3],  # 8 weeks of history
    period_duration=timedelta(days=7),
)

result = forecast_by_items(history, backlog_size=20, seed=42)

print(result.outcomes)  # {50: date(...), 70: date(...), 85: date(...), 95: date(...)}
print(result.trials_run)  # 10000
print(result.periods_used)  # 8
```

**Expected outcome**: four dates, non-decreasing as confidence rises (SC-001, SC-005).
Running this exact snippet twice produces identical `outcomes` (SC-003).

## Scenario 2 — "How much will be done by this date?" (User Story 2)

```python
from datetime import date, timedelta
from agile_metrics import forecast_by_date
from agile_metrics.models import ThroughputHistory

history = ThroughputHistory(
    completed_per_period=[3, 5, 4, 6, 2, 5, 4, 3],
    period_duration=timedelta(days=7),
)

result = forecast_by_date(history, target_date=date(2026, 12, 1), seed=42)

print(result.outcomes)  # {50: int, 70: int, 85: int, 95: int}, non-increasing as confidence rises
```

**Expected outcome**: four item counts (SC-002, SC-005).

## Scenario 3 — Rejecting bad input (edge cases / SC-006)

```python
import pytest
from pydantic import ValidationError

# Too little history (fewer than 6 periods) -> rejected
with pytest.raises(ValidationError):
    ThroughputHistory(completed_per_period=[1, 2, 3], period_duration=timedelta(days=7))

# All-zero history -> rejected
with pytest.raises(ValidationError):
    ThroughputHistory(completed_per_period=[0, 0, 0, 0, 0, 0], period_duration=timedelta(days=7))
```

**Expected outcome**: both raise `ValidationError` with a message naming which rule was
violated — no forecast is silently produced from insufficient or all-zero data.

## Running it for real

```bash
uv run pytest tests/test_forecast.py -v
```

All three scenarios above are expected to exist as cases in `test_forecast.py` once
implemented (see `tasks.md`, generated separately by `/speckit-tasks`).
