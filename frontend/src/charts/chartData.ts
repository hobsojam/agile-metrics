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

export interface ProbabilityCurvePoint {
  label: string;
  probability: number;
}

export interface ProbabilityMarker {
  level: ConfidenceLevel;
  label: string;
  color: string;
  outcomeLabel: string;
  probability: number;
}

export interface ProbabilityCurveSeries {
  points: ProbabilityCurvePoint[];
  markers: ProbabilityMarker[];
  mode: "backlog" | "target-date";
  xAxisLabel: string;
}

export function toProbabilityCurve(result: ForecastResult): ProbabilityCurveSeries {
  const dateMode = isDateMode(result);
  const buckets = result.distribution;
  const trialsRun = result.trials_run;

  let points: ProbabilityCurvePoint[];
  let mode: "backlog" | "target-date";

  if (dateMode) {
    // "Done on or before the bucket's last date" - accumulate ascending,
    // ending at 1 once every trial is accounted for (research.md §4).
    let runningTotal = 0;
    points = buckets.map((bucket) => {
      runningTotal += bucket.trials;
      return { label: String(bucket.upper), probability: runningTotal / trialsRun };
    });
    mode = "backlog";
  } else {
    // "At least the bucket's lower count" - accumulate from the highest
    // bucket down (a higher value's trials also satisfy a lower "at least"
    // threshold), then present ascending so the curve reads left-to-right:
    // the lowest item count starts at 1, since every trial reaches at least
    // the minimum observed value (research.md §4).
    let runningTotal = 0;
    const descending = [...buckets].reverse().map((bucket) => {
      runningTotal += bucket.trials;
      return { label: String(bucket.lower), probability: runningTotal / trialsRun };
    });
    points = descending.reverse();
    mode = "target-date";
  }

  const pointByLabel = new Map(points.map((point) => [point.label, point]));
  const markers: ProbabilityMarker[] = CONFIDENCE_LEVELS.map((level) => {
    const outcome = result.outcomes[String(level) as "50" | "70" | "85" | "95"];
    const style = CONFIDENCE_LEVEL_STYLES[level];
    const point = pointByLabel.get(String(outcome));
    return {
      level,
      label: style.label,
      color: style.color,
      outcomeLabel: String(outcome),
      probability: point?.probability ?? 0,
    };
  });

  return {
    points,
    markers,
    mode,
    xAxisLabel: dateMode ? "Completion date" : "Items completed",
  };
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
