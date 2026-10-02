# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY README.md ./
# --locked: build from exactly the reviewed, committed lockfile (same
# supply-chain hardening as CI). --no-dev: never ship pytest/mypy/ruff/
# bandit/hypothesis/pre-commit/pip-audit in the production image.
RUN uv sync --locked --no-dev

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["agile-metrics"]
