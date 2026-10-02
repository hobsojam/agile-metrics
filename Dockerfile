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
# The base image defaults to root; this tool is stateless (no files to
# write, no privileged ports), so there is no reason to run as root.
RUN groupadd --system appuser && useradd --system --gid appuser --no-create-home appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
ENTRYPOINT ["agile-metrics"]
