"""Pydantic models for the throughput forecasting library.

No raw dicts cross a module boundary — every input and output is one of the
three models below (Constitution: Technology Stack & Constraints).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MIN_HISTORICAL_PERIODS = 6
DEFAULT_TRIALS = 10_000


class ThroughputHistory(BaseModel):
    """A team's historical throughput: items completed per equal-length period."""

    completed_per_period: list[int]
    period_duration: timedelta

    @field_validator("completed_per_period")
    @classmethod
    def _validate_periods(cls, value: list[int]) -> list[int]:
        if len(value) < MIN_HISTORICAL_PERIODS:
            raise ValueError(
                f"at least {MIN_HISTORICAL_PERIODS} historical periods are required, "
                f"got {len(value)}"
            )
        if any(count < 0 for count in value):
            raise ValueError("completed_per_period must not contain negative values")
        if all(count == 0 for count in value):
            raise ValueError(
                "completed_per_period must not be all zero — no completion can be projected"
            )
        return value

    @field_validator("period_duration")
    @classmethod
    def _validate_duration(cls, value: timedelta) -> timedelta:
        if value <= timedelta(0):
            raise ValueError("period_duration must be positive")
        return value


class ForecastRequest(BaseModel):
    """A request for either a completion-date forecast or an items-completed forecast.

    Exactly one of backlog_size / target_date must be set.
    """

    history: ThroughputHistory
    backlog_size: int | None = None
    target_date: date | None = None
    seed: int | None = None
    reference_date: date = Field(default_factory=date.today)
    trials: int = DEFAULT_TRIALS

    @model_validator(mode="after")
    def _validate_exactly_one_mode(self) -> ForecastRequest:
        if (self.backlog_size is None) == (self.target_date is None):
            raise ValueError(
                "exactly one of backlog_size or target_date is required, not both or neither"
            )
        if self.backlog_size is not None and self.backlog_size <= 0:
            raise ValueError("backlog_size must be a positive whole number")
        if self.target_date is not None and self.target_date <= self.reference_date:
            raise ValueError("target_date must be strictly after the reference date")
        return self


class ForecastResult(BaseModel):
    """The outcome of a forecast request: outcomes at four confidence levels, plus basis.

    `outcomes` always carries all four confidence levels — never a bare point
    estimate (Constitution Principle IV).
    """

    outcomes: dict[Literal[50, 70, 85, 95], date | int]
    trials_run: int
    periods_used: int
