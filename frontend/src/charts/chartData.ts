/**
 * Pure data-shaping functions: ForecastResult (+ submitted inputs) -> chart-ready
 * series. No React import (plan.md Project Structure) - testable in isolation,
 * and the single place that reads the API response shape for charts (FR-009:
 * no re-simulation, no extra request).
 */
import type { components } from "../api-types";
import { CONFIDENCE_LEVELS, CONFIDENCE_LEVEL_STYLES, type ConfidenceLevel } from "./confidenceLevels";

type ForecastResult = components["schemas"]["ForecastResult"];
type OutcomeBucket = components["schemas"]["OutcomeBucket"];

function isDateMode(result: ForecastResult): boolean {
  return typeof result.outcomes["50"] === "string";
}

function bucketLabel(bucket: OutcomeBucket): string {
  return bucket.lower === bucket.upper ? String(bucket.lower) : `${bucket.lower}–${bucket.upper}`;
}

export interface DistributionBar {
  label: string;
  trials: number;
}

export interface DistributionMarker {
  level: ConfidenceLevel;
  label: string;
  color: string;
  barIndex: number;
  outcomeLabel: string;
}

export interface DistributionSeries {
  bars: DistributionBar[];
  markers: DistributionMarker[];
  xAxisLabel: string;
}

export function toDistributionSeries(result: ForecastResult): DistributionSeries {
  const dateMode = isDateMode(result);
  const bars: DistributionBar[] = result.distribution.map((bucket) => ({
    label: bucketLabel(bucket),
    trials: bucket.trials,
  }));

  const markers: DistributionMarker[] = CONFIDENCE_LEVELS.map((level) => {
    const outcome = result.outcomes[String(level) as "50" | "70" | "85" | "95"];
    const barIndex = result.distribution.findIndex(
      (bucket) => bucket.lower <= outcome && outcome <= bucket.upper
    );
    const style = CONFIDENCE_LEVEL_STYLES[level];
    return {
      level,
      label: style.label,
      color: style.color,
      barIndex,
      outcomeLabel: String(outcome),
    };
  });

  return {
    bars,
    markers,
    xAxisLabel: dateMode ? "Completion date" : "Items completed",
  };
}
