"""Web API for agile_metrics.

Per Constitution Principle II, `_compute_forecast` only calls the public
`forecast_by_items`/`forecast_by_date` API - never `simulation.py` internals. It contains
no HTTP-specific code so it is unit-testable without an HTTP client (research.md "Keeping
the backend reusable across frontend changes").
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from agile_metrics import forecast_by_date, forecast_by_items
from agile_metrics.linear_client import LinearIntegrationError, fetch_linear_throughput
from agile_metrics.models import ForecastResult, ThroughputHistory

app = FastAPI(title="Agile Metrics Forecast API")


class ForecastRequestBody(BaseModel):
    """The JSON body `POST /api/forecast` accepts (contracts/forecast-api.md).

    `history` is optional - exactly one of it, or both `linear_api_key` and
    `linear_team_id`, is required (spec 006; enforced in `_compute_forecast`,
    matching the existing `backlog_size`/`target_date` "exactly one of"
    pattern rather than a separate pydantic validator)."""

    history: list[int] | None = None
    period_days: int
    backlog_size: int | None = None
    target_date: date | None = None
    seed: int | None = None
    linear_api_key: str | None = None
    linear_team_id: str | None = None
    linear_periods: int | None = None


class ErrorResponseBody(BaseModel):
    """The JSON body returned on any validation failure."""

    error: str


class ForecastResponseBody(ForecastResult):
    """`ForecastResult`'s fields plus the actual per-period history used -
    whether typed in manually or fetched from Linear - so presentation
    layers (the web UI's charts, spec 005) can draw the burn-up/run charts
    without already knowing the counts client-side. Linear mode never gives
    the frontend the raw counts the way manual paste does (spec 006), so
    they're echoed back here instead. No change to `ForecastResult` itself
    (Constitution Principle II) - this is a web-layer-only addition."""

    history: list[int]


def _format_error(
    exc: ValidationError | RequestValidationError | ValueError | LinearIntegrationError,
) -> str:
    """Render an exception as a clean, human-readable message (FR-004) - never
    pydantic's verbose multi-line repr, which includes a "For further information
    visit https://errors.pydantic.dev/..." URL and reads like a technical dump."""
    if isinstance(exc, LinearIntegrationError):
        return str(exc)
    if isinstance(exc, ValueError) and not isinstance(exc, ValidationError):
        return str(exc)
    parts = []
    for error in exc.errors():
        loc = ".".join(str(segment) for segment in error["loc"] if segment != "body")
        parts.append(f"{loc}: {error['msg']}" if loc else error["msg"])
    return "; ".join(parts)


def _build_history(body: ForecastRequestBody) -> ThroughputHistory:
    """Exactly one of `history` or both Linear fields is required (spec 006) -
    same "exactly one of" pattern as `backlog_size`/`target_date` below, not a
    separate pydantic validator."""
    has_linear = body.linear_api_key is not None and body.linear_team_id is not None
    if body.history is not None and not has_linear:
        return ThroughputHistory(
            completed_per_period=body.history,
            period_duration=timedelta(days=body.period_days),
        )
    elif has_linear and body.history is None:
        kwargs: dict[str, object] = {
            "api_key": body.linear_api_key,
            "team_id": body.linear_team_id,
            "period_duration": timedelta(days=body.period_days),
        }
        if body.linear_periods is not None:
            kwargs["periods"] = body.linear_periods
        return fetch_linear_throughput(**kwargs)  # type: ignore[arg-type]
    else:
        raise ValueError(
            "exactly one of history or (linear_api_key and linear_team_id) is required, "
            "not both or neither"
        )


def _compute_forecast(body: ForecastRequestBody) -> ForecastResponseBody:
    """Build the request's history, dispatch to the right forecast mode, or raise."""
    history = _build_history(body)

    if body.backlog_size is not None and body.target_date is None:
        result = forecast_by_items(history, body.backlog_size, seed=body.seed)
    elif body.target_date is not None and body.backlog_size is None:
        result = forecast_by_date(history, body.target_date, seed=body.seed)
    else:
        raise ValueError(
            "exactly one of backlog_size or target_date is required, not both or neither"
        )
    return ForecastResponseBody(**result.model_dump(), history=history.completed_per_period)


@app.post(
    "/api/forecast",
    response_model=ForecastResponseBody,
    responses={400: {"model": ErrorResponseBody, "description": "Invalid input"}},
)
def post_forecast(body: ForecastRequestBody) -> ForecastResponseBody | JSONResponse:
    try:
        return _compute_forecast(body)
    except (ValidationError, ValueError, LinearIntegrationError) as exc:
        return JSONResponse(
            status_code=400, content=ErrorResponseBody(error=_format_error(exc)).model_dump()
        )


@app.exception_handler(RequestValidationError)
def _request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Malformed request bodies (e.g. non-integer history entries) are caught by
    FastAPI itself as a RequestValidationError before the route body ever runs -
    this re-shapes that into the same {"error": "..."} contract as every other
    failure (contracts/forecast-api.md), instead of FastAPI's default 422 body."""
    return JSONResponse(
        status_code=400, content=ErrorResponseBody(error=_format_error(exc)).model_dump()
    )


_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
