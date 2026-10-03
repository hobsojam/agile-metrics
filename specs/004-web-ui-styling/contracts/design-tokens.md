# Design Tokens Contract

This is the fixed visual vocabulary every styled element in `frontend/src/App.tsx` MUST draw
from (spec FR-009: one cohesive design, not independently-styled pieces). Implementation tasks
MUST use only the Tailwind utility classes listed here for color, spacing, and type — not other
shades/steps from Tailwind's full default scale — so nothing drifts by accident.

All values below are Tailwind v4 default-scale utility classes (no custom `@theme` overrides
needed — the defaults already provide a sufficient, consistent subset).

## Color

| Role | Utility classes | Used for |
|------|------------------|----------|
| Primary / brand | `bg-blue-600`, `text-blue-600`, `hover:bg-blue-700`, `focus-visible:ring-blue-500` | Submit button, primary call-to-action (FR-002) |
| Neutral text (body) | `text-slate-900` | Labels, body text, result values |
| Neutral text (muted) | `text-slate-500` | Supporting context: trial count, periods used (FR-004) |
| Neutral surface | `bg-white`, `border-slate-200` | Form and results containers |
| Neutral page background | `bg-slate-50` | Page `<body>`/root background |
| Error | `text-red-700`, `bg-red-50`, `border-red-200` | Error message (FR-006) — distinct from neutral/primary so it cannot be confused with a successful result |
| Focus ring (all interactive elements) | `focus-visible:ring-2 focus-visible:ring-offset-2` | Keyboard focus visibility (accessibility baseline, research.md §4) |

## Spacing

| Step | Utility classes | Used for |
|------|------------------|----------|
| Tight | `gap-2` / `p-2` (0.5rem / 8px) | Space between a label and its input |
| Standard | `gap-4` / `p-4` (1rem / 16px) | Space between form fields; internal card padding |
| Section | `gap-6` / `p-6` (1.5rem / 24px) | Space between the form, results, and error/loading sections |
| Page margin | `p-8` (2rem / 32px) | Outer page padding around the whole layout |

## Typography

| Role | Utility classes | Used for |
|------|------------------|----------|
| Page title | `text-2xl font-semibold` | "Agile Metrics Forecast" heading |
| Section label | `text-sm font-medium` | Form field labels |
| Body | `text-base` | Input values, result values |
| Supporting/muted | `text-sm text-slate-500` | Trial count, periods used (FR-004) |

## Layout

- Form and results render as visually distinct `bg-white` cards (`rounded-lg border
  border-slate-200 p-6`) on the `bg-slate-50` page background, satisfying FR-001's "clear visual
  grouping" and SC-001's "identify which part is for input vs. output within 5 seconds."
- A single-column flex/stack layout (`flex flex-col gap-6`) is sufficient — no CSS grid needed
  for this page's content (one form, one results area, stacked).
- Minimum content width target: readable without horizontal scrolling or overlap down to
  1024px container width (FR-008, SC-004); use `max-w-xl` (or similar) on the centered content
  column rather than a fixed pixel width, so it scales naturally between 1024px and 1280px+.
