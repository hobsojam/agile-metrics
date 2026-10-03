# Data Model: Web UI Visual Styling

No new or changed data entities. This feature is presentation-only (spec FR-007): it does not
touch `ThroughputHistory`, `ForecastRequest`, `ForecastResult`, or any other `pydantic` model
from spec 001/003, and introduces no new request/response shape.

The one new "vocabulary" this feature introduces — a small set of design tokens (colors,
spacing, type scale) — is a visual/CSS concern, not a data model, and is documented instead in
[`contracts/design-tokens.md`](./contracts/design-tokens.md).
