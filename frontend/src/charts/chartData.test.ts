import { describe, expect, it } from "vitest";
import { toDistributionSeries } from "./chartData";
import type { components } from "../api-types";

type ForecastResult = components["schemas"]["ForecastResult"];

function backlogResult(overrides: Partial<ForecastResult> = {}): ForecastResult {
  return {
    outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
    trials_run: 10000,
    periods_used: 8,
    reference_date: "2026-10-01",
    distribution: [
      { lower: "2026-10-30", upper: "2026-10-30", trials: 1000 },
      { lower: "2026-11-06", upper: "2026-11-06", trials: 4000 },
      { lower: "2026-11-13", upper: "2026-11-13", trials: 3800 },
      { lower: "2026-11-20", upper: "2026-11-20", trials: 1200 },
    ],
    projection: [
      { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
    ],
    ...overrides,
  };
}

function targetDateResult(overrides: Partial<ForecastResult> = {}): ForecastResult {
  return {
    outcomes: { "50": 24, "70": 22, "85": 21, "95": 19 },
    trials_run: 10000,
    periods_used: 8,
    reference_date: "2026-10-01",
    distribution: [
      { lower: 19, upper: 19, trials: 1200 },
      { lower: 21, upper: 21, trials: 3800 },
      { lower: 22, upper: 22, trials: 4000 },
      { lower: 24, upper: 24, trials: 1000 },
    ],
    projection: [
      {
        period: 1,
        period_end: "2026-10-08",
        cumulative: { "50": 24, "70": 22, "85": 21, "95": 19 },
      },
    ],
    ...overrides,
  };
}

describe("toDistributionSeries", () => {
  it("returns one bar per bucket, in order, with the bucket's trial count", () => {
    const series = toDistributionSeries(backlogResult());
    expect(series.bars).toHaveLength(4);
    expect(series.bars.map((bar) => bar.trials)).toEqual([1000, 4000, 3800, 1200]);
  });

  it("labels a single-value backlog-mode bucket with its date", () => {
    const series = toDistributionSeries(backlogResult());
    expect(series.bars[0].label).toBe("2026-10-30");
  });

  it("labels a grouped bucket with a lower–upper range", () => {
    const series = toDistributionSeries(
      backlogResult({
        distribution: [{ lower: "2026-10-30", upper: "2026-11-06", trials: 10000 }],
      })
    );
    expect(series.bars[0].label).toBe("2026-10-30–2026-11-06");
  });

  it("places one marker per confidence level, on the bucket containing that outcome", () => {
    const series = toDistributionSeries(backlogResult());
    expect(series.markers).toHaveLength(4);
    const byLevel = Object.fromEntries(series.markers.map((m) => [m.level, m.barIndex]));
    expect(byLevel).toEqual({ 50: 1, 70: 2, 85: 2, 95: 3 });
  });

  it("uses 'Completion date' as the x-axis label in backlog mode", () => {
    expect(toDistributionSeries(backlogResult()).xAxisLabel).toBe("Completion date");
  });

  it("uses 'Items completed' as the x-axis label in target-date mode", () => {
    expect(toDistributionSeries(targetDateResult()).xAxisLabel).toBe("Items completed");
  });

  it("places all four markers on the single bar for a constant history (edge case)", () => {
    const series = toDistributionSeries(
      backlogResult({
        outcomes: {
          "50": "2026-10-30",
          "70": "2026-10-30",
          "85": "2026-10-30",
          "95": "2026-10-30",
        },
        distribution: [{ lower: "2026-10-30", upper: "2026-10-30", trials: 10000 }],
      })
    );
    expect(series.markers.every((m) => m.barIndex === 0)).toBe(true);
  });

  it("labels a grouped target-date-mode bucket with an item-count range", () => {
    const series = toDistributionSeries(
      targetDateResult({ distribution: [{ lower: 19, upper: 24, trials: 10000 }] })
    );
    expect(series.bars[0].label).toBe("19–24");
  });
});
