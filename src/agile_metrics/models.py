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


class OutcomeBucket(BaseModel):
    """One bar of the outcome distribution (spec 005 data-model.md)."""

    lower: date | int
    upper: date | int
    trials: int = Field(ge=0)


class ProjectionPoint(BaseModel):
    """One future period of the burn-up fan (spec 005 data-model.md)."""

    period: int = Field(ge=1)
    period_end: date
    cumulative: dict[Literal[50, 70, 85, 95], int]


class ForecastResult(BaseModel):
    """The outcome of a forecast request: outcomes at four confidence levels, plus basis.

    `outcomes` always carries all four confidence levels — never a bare point
    estimate (Constitution Principle IV).
    """

    outcomes: dict[Literal[50, 70, 85, 95], date | int]
    trials_run: int
    periods_used: int
    reference_date: date
    distribution: list[OutcomeBucket]
    projection: list[ProjectionPoint]

    @model_validator(mode="after")
    def _validate_distribution_and_projection(self) -> ForecastResult:
        total_trials = sum(bucket.trials for bucket in self.distribution)
        if total_trials != self.trials_run:
            raise ValueError(
                f"distribution trials must sum to trials_run ({self.trials_run}), "
                f"got {total_trials}"
            )
        if not 1 <= len(self.distribution) <= 60:
            raise ValueError(
                f"distribution must have 1 to 60 buckets, got {len(self.distribution)}"
            )

        outcomes_are_dates = any(isinstance(value, date) for value in self.outcomes.values())
        previous_upper: date | int | None = None
        for bucket in self.distribution:
            bucket_is_date = isinstance(bucket.lower, date)
            if bucket_is_date != outcomes_are_dates:
                raise ValueError(
                    "distribution bucket bounds must be the same type (date or int) as outcomes"
                )
            if bucket.lower > bucket.upper:  # type: ignore[operator]
                raise ValueError(
                    f"bucket lower ({bucket.lower}) must not exceed upper ({bucket.upper})"
                )
            if previous_upper is not None and bucket.lower <= previous_upper:  # type: ignore[operator]
                raise ValueError("distribution buckets must be in ascending, non-overlapping order")
            previous_upper = bucket.upper

        if not self.projection:
            raise ValueError("projection must not be empty")
        for index, point in enumerate(self.projection, start=1):
            if point.period != index:
                raise ValueError(
                    f"projection periods must run 1, 2, … with no gaps; expected {index}, "
                    f"got {point.period}"
                )
        return self


class Item(BaseModel):
    """A single unit of work parsed from a CSV import (spec 007 data-model.md).

    Not exposed via any API response in this feature - retained so a later
    item-level flow-metrics feature can reuse the same parsed representation
    without a CSV-shape change.
    """

    id: str = Field(min_length=1)
    type: str
    title: str
    start_date: date | None
    end_date: date | None
