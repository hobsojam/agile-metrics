# Quickstart: Web UI Visual Styling

Validates that the restyled forecast web UI satisfies spec `004-web-ui-styling`'s acceptance
scenarios, without regressing spec `003-forecast-web-ui`'s existing functional behavior.

## Prerequisites

- `uv sync` (backend) and, inside `frontend/`, `npm ci` (frontend) have been run.
- Node 22 (the version pinned in CI/Dockerfile) — if your local Node is older, run frontend
  commands inside a `node:22-slim` container (as used throughout this project's CI/Docker
  verification) to match CI exactly.

## Scenario 1 — Automated checks still pass (regression guard)

```bash
cd frontend
npm run lint
npm run typecheck
npm test
```

**Expected outcome**: all three pass unchanged. `App.test.tsx`'s existing assertions (roles,
text content, mocked `fetch` behavior) are unaffected by styling-only changes — if any of these
fail, the restyle has accidentally changed behavior or markup semantics, not just appearance.

## Scenario 2 — Form visual grouping (User Story 1, FR-001, FR-002, SC-001)

```bash
cd frontend
npm run dev
```

Open the printed local URL in a browser. **Expected outcome**:
- The five form fields (history, period length, backlog size, target date, seed) are visually
  grouped with consistent spacing and legible labels (design-tokens.md "Spacing"/"Typography").
- The submit button is visually distinct as the primary action (design-tokens.md "Color" →
  Primary/brand).
- Resize the browser window between roughly 1024px and 1280px+ wide: the form remains legible
  with no overlapping or cut-off elements (FR-008).

## Scenario 3 — Results visual hierarchy (User Story 2, FR-003, FR-004, SC-002)

With the dev server from Scenario 2 still running, submit a valid forecast (e.g. history
`3,5,4,6,2,5,4,3`, period length `7`, backlog size `20`).

**Expected outcome**:
- The four confidence-level outcomes (50/70/85/95%) are presented with clear visual separation
  from each other and from the form (design-tokens.md "Layout" → distinct cards).
- The trial count and historical-periods-used context are visibly present but visually
  de-emphasized (design-tokens.md "Typography" → Supporting/muted) relative to the confidence
  outcomes.

## Scenario 4 — Loading and error states (User Story 3, FR-005, FR-006)

- Submit a request with an invalid value (e.g. clear a required field) and confirm the error
  message renders styled consistently with the rest of the page (design-tokens.md "Color" →
  Error) while remaining clearly marked as an error — not confusable with a result.
- Submit a valid request and observe the brief loading state before the result renders;
  confirm it is visually styled consistently with the rest of the page, not plain text.

## Scenario 5 — Full-stack smoke test (Docker/podman, consistent with how 003 was verified)

```bash
docker build -t agile-metrics .
docker run --rm -p 8000:8000 --entrypoint uvicorn agile-metrics \
  agile_metrics.web:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` and repeat Scenarios 2–4 against the built, served frontend (not
just the Vite dev server) to confirm the production build renders identically.

## Scenario 6 — Bundle size constraint (Technical Context)

```bash
cd frontend
npm run build
```

**Expected outcome**: the reported gzip sizes for `dist/assets/*.js` and `dist/assets/*.css`
combined stay under 100 kB (plan.md Technical Context constraint).
