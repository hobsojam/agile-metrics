/**
 * Pure data-shaping functions: ForecastResult (+ submitted inputs) -> chart-ready
 * series. No React import (plan.md Project Structure) - testable in isolation,
 * and the single place that reads the API response shape for charts (FR-009:
 * no re-simulation, no extra request).
 */
import type { components } from "../api-types";
import { CONFIDENCE_LEVELS, CONFIDENCE_LEVEL_STYLES, type ConfidenceLevel } from "./confidenceLevels";

type ForecastResult = components["schemas"]["ForecastResponseBody"];
type OutcomeBucket = components["schemas"]["OutcomeBucket"];
type OutcomeKey = "50" | "70" | "85" | "95";
type CycleTimeEntry = components["schemas"]["CycleTimeEntry"];
type CycleTimePercentiles = components["schemas"]["FlowMetrics"]["cycle_time_percentiles"];

function cycleTimeDays(entry: CycleTimeEntry): number {
  const ms = new Date(entry.resolved_at).getTime() - new Date(entry.started_at).getTime();
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

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
    const descending = buckets.toReversed().map((bucket) => {
      runningTotal += bucket.trials;
      return { label: String(bucket.lower), probability: runningTotal / trialsRun };
    });
    points = descending.toReversed();
    mode = "target-date";
  }

  const pointByLabel = new Map(points.map((point) => [point.label, point]));
  const markers: ProbabilityMarker[] = CONFIDENCE_LEVELS.map((level) => {
    const outcome = result.outcomes[String(level) as OutcomeKey];
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

export interface CycleTimeScatterPoint {
  key: string;
  date: string;
  days: number;
}

export interface CycleTimeScatterMarker {
  level: ConfidenceLevel;
  label: string;
  color: string;
  days: number;
}

export interface CycleTimeScatterSeries {
  points: CycleTimeScatterPoint[];
  markers: CycleTimeScatterMarker[];
}

/**
 * One point per resolved issue (resolution date x cycle-time days), plus up to
 * four horizontal percentile reference lines (spec 012 FR-001/FR-002). Percentiles
 * come pre-computed from the backend (research.md §1) - `percentiles` is `null`/
 * `undefined` whenever there isn't enough history (FR-006), in which case the
 * points are still returned with an empty marker list, not an empty chart.
 */
export function toCycleTimeScatter(
  entries: CycleTimeEntry[],
  percentiles: CycleTimePercentiles
): CycleTimeScatterSeries {
  const points: CycleTimeScatterPoint[] = entries.map((entry) => ({
    key: entry.key,
    date: entry.resolved_at,
    days: cycleTimeDays(entry),
  }));

  const markers: CycleTimeScatterMarker[] = percentiles
    ? CONFIDENCE_LEVELS.map((level) => {
        const style = CONFIDENCE_LEVEL_STYLES[level];
        return {
          level,
          label: style.label,
          color: style.color,
          days: percentiles[String(level) as OutcomeKey],
        };
      })
    : [];

  return { points, markers };
}

export interface AgingWipThreshold {
  days: number;
  color: string;
  label: string;
}

/**
 * The historical 85th-percentile cycle time, styled for the Aging WIP view's
 * threshold line (spec 012 FR-004) - `null` whenever there isn't enough history
 * to trust a percentile (FR-006), same condition `toCycleTimeScatter` checks.
 */
export function agingWipThreshold(percentiles: CycleTimePercentiles): AgingWipThreshold | null {
  if (!percentiles) return null;
  const style = CONFIDENCE_LEVEL_STYLES[85];
  return { days: percentiles["85" as OutcomeKey], color: style.color, label: style.label };
}

export function outcomeLabels(result: ForecastResult): Record<ConfidenceLevel, string> {
  return Object.fromEntries(
    CONFIDENCE_LEVELS.map((level) => [
      level,
      String(result.outcomes[String(level) as OutcomeKey]),
    ])
  ) as Record<ConfidenceLevel, string>;
}

function addDaysToISODate(iso: string, days: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export interface BurnUpPoint {
  label: string;
  value: number;
}

export interface BurnUpFanPoint {
  label: string;
  cumulative: Record<ConfidenceLevel, number>;
}

export type BurnUpTarget =
  | { kind: "backlog"; value: number }
  | { kind: "target-date"; label: string };

export interface BurnUpSeries {
  historical: BurnUpPoint[];
  fan: BurnUpFanPoint[];
  target: BurnUpTarget;
}

export type BurnUpMode =
  | { kind: "backlog"; backlogSize: number }
  | { kind: "target-date"; targetDate: string };

export function toBurnUpSeries(
  result: ForecastResult,
  history: number[],
  periodDays: number,
  mode: BurnUpMode
): BurnUpSeries {
  const periodCount = history.length;
  const historical: BurnUpPoint[] = [
    { label: addDaysToISODate(result.reference_date, -periodCount * periodDays), value: 0 },
  ];
  let running = 0;
  for (let i = 1; i <= periodCount; i++) {
    running += history[i - 1];
    historical.push({
      label: addDaysToISODate(result.reference_date, -(periodCount - i) * periodDays),
      value: running,
    });
  }
  const historicalTotal = running;

  const fan: BurnUpFanPoint[] = result.projection.map((point) => ({
    label: point.period_end,
    cumulative: Object.fromEntries(
      CONFIDENCE_LEVELS.map((level) => [
        level,
        historicalTotal + point.cumulative[String(level) as OutcomeKey],
      ])
    ) as Record<ConfidenceLevel, number>,
  }));

  const target: BurnUpTarget =
    mode.kind === "backlog"
      ? { kind: "backlog", value: historicalTotal + mode.backlogSize }
      : { kind: "target-date", label: mode.targetDate };

  return { historical, fan, target };
}

export interface RunChartBar {
  label: string;
  value: number;
}

export interface RunChartSeries {
  bars: RunChartBar[];
  median: number;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

export function toRunChartSeries(
  history: number[],
  referenceDate: string,
  periodDays: number
): RunChartSeries {
  const periodCount = history.length;
  const bars: RunChartBar[] = history.map((value, index) => ({
    label: addDaysToISODate(referenceDate, -(periodCount - 1 - index) * periodDays),
    value,
  }));
  return { bars, median: median(history) };
}

export function toDistributionSeries(result: ForecastResult): DistributionSeries {
  const dateMode = isDateMode(result);
  const bars: DistributionBar[] = result.distribution.map((bucket) => ({
    label: bucketLabel(bucket),
    trials: bucket.trials,
  }));

  const markers: DistributionMarker[] = CONFIDENCE_LEVELS.map((level) => {
    const outcome = result.outcomes[String(level) as OutcomeKey];
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
