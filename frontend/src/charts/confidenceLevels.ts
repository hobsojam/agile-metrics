/**
 * Shared confidence-level label and color, imported by every chart (FR-010)
 * so users can match a level between charts. No other module defines these.
 *
 * Colors are one hue (004's primary blue) at increasing strength for higher
 * confidence, using the exact oklch values Tailwind v4 generates for its
 * `blue-*` utilities (so chart colors match the rest of the page exactly,
 * not just visually). Each level is also labelled, so the distinction
 * doesn't rely on color alone for colour-blind users (research.md §7).
 */

export const CONFIDENCE_LEVELS = [50, 70, 85, 95] as const;

export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];

interface ConfidenceLevelStyle {
  readonly label: string;
  readonly color: string;
}

export const CONFIDENCE_LEVEL_STYLES: Readonly<Record<ConfidenceLevel, ConfidenceLevelStyle>> = {
  50: { label: "50%", color: "oklch(80.9% 0.105 251.813)" }, // blue-300
  70: { label: "70%", color: "oklch(62.3% 0.214 259.815)" }, // blue-500
  85: { label: "85%", color: "oklch(48.8% 0.243 264.376)" }, // blue-700
  95: { label: "95%", color: "oklch(37.9% 0.146 265.522)" }, // blue-900
};
