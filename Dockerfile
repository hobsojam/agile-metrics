# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.12.21 AS uv

FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
# --ignore-scripts: none of our dependencies need install-time lifecycle
# scripts (verified: `npm run build`/test/lint all succeed without them),
# so skip them rather than letting a compromised package run arbitrary code
# at install time.
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS builder
# Copying the pinned uv binary from Astral's official image, rather than
# `pip install uv` with no version pin, keeps the build reproducible and
# lets Dependabot's docker ecosystem track version bumps for this image
# reference the same way it already does for the python base image.
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY README.md ./
# --locked: build from exactly the reviewed, committed lockfile (same
# supply-chain hardening as CI). --no-dev: never ship pytest/mypy/ruff/
# bandit/hypothesis/pre-commit/pip-audit in the production image.
#
# --no-build (forbid building any dependency from a source distribution)
# IS used here, unlike CI's equivalent uv sync: verified with podman that
# every dependency in this --no-dev set (including fastapi/uvicorn's own
# C-extension transitive deps like uvloop/websockets - re-checked after
# adding them, not just assumed from the smaller CLI-only set this
# comment originally covered) already resolves to a wheel, so nothing
# changes today. This is the artifact that actually ships, not a
# disposable CI sandbox, so the malicious-build-hook risk --no-build
# guards against is worth the same future-Dependabot-bump brittleness
# that argued against it in CI.
RUN uv sync --locked --no-dev --no-build

FROM python:3.11-slim AS runtime
# The base image defaults to root; this tool is stateless (no files to
# write, no privileged ports), so there is no reason to run as root.
RUN groupadd --system appuser && useradd --system --gid appuser --no-create-home appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist /app/frontend/dist
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
# ENTRYPOINT stays the CLI (spec 002's contract) even though the image
# now also bundles the web UI - start the web server by overriding the
# entrypoint: `docker run --entrypoint uvicorn <image> agile_metrics.web:app ...`
ENTRYPOINT ["agile-metrics"]
