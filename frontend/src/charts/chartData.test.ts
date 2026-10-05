import { describe, expect, it } from "vitest";
import {
  outcomeLabels,
  toBurnUpSeries,
  toDistributionSeries,
  toProbabilityCurve,
  toRunChartSeries,
} from "./chartData";
import type { components } from "../api-types";

type ForecastResult = components["schemas"]["ForecastResponseBody"];

function backlogResult(overrides: Partial<ForecastResult> = {}): ForecastResult {
  return {
    outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
    trials_run: 10000,
    periods_used: 8,
    reference_date: "2026-10-01",
    history: [3, 5, 4, 6, 2, 5, 4, 3],
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
    history: [3, 5, 4, 6, 2, 5, 4, 3],
    // Trial counts chosen so cumulative-from-the-top matches each outcome's
    // confidence level exactly: P(>=24)=50%, P(>=22)=70%, P(>=21)=85%,
    // P(>=19)=95% (the remaining 500 trials fall below 19, in a 5th bucket).
    distribution: [
      { lower: 17, upper: 17, trials: 500 },
      { lower: 19, upper: 19, trials: 1000 },
      { lower: 21, upper: 21, trials: 1500 },
      { lower: 22, upper: 22, trials: 2000 },
      { lower: 24, upper: 24, trials: 5000 },
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

describe("toProbabilityCurve", () => {
  it("backlog mode: accumulates ascending by date, ending at 1", () => {
    const curve = toProbabilityCurve(backlogResult());
    expect(curve.points.map((p) => p.label)).toEqual([
      "2026-10-30",
      "2026-11-06",
      "2026-11-13",
      "2026-11-20",
    ]);
    expect(curve.points.map((p) => p.probability)).toEqual([0.1, 0.5, 0.88, 1]);
    expect(curve.mode).toBe("backlog");
  });

  it("target-date mode: ascending by item count, starting at 1", () => {
    const curve = toProbabilityCurve(targetDateResult());
    expect(curve.points.map((p) => p.label)).toEqual(["17", "19", "21", "22", "24"]);
    // At the lowest count (17), every trial achieved at least that many.
    expect(curve.points[0].probability).toBe(1);
    // At the highest count (24), only the top bucket's own trials qualify.
    expect(curve.points[4].probability).toBeCloseTo(5000 / 10000);
    // Monotonically non-increasing as the "at least" threshold rises.
    for (let i = 1; i < curve.points.length; i++) {
      expect(curve.points[i].probability).toBeLessThanOrEqual(curve.points[i - 1].probability);
    }
  });

  it("gives a single step for a constant history (edge case)", () => {
    const curve = toProbabilityCurve(
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
    expect(curve.points).toHaveLength(1);
    expect(curve.points[0].probability).toBe(1);
  });

  it("reports a probability at or above each level at that level's outcome", () => {
    const backlogCurve = toProbabilityCurve(backlogResult());
    for (const marker of backlogCurve.markers) {
      expect(marker.probability).toBeGreaterThanOrEqual(marker.level / 100 - 1e-9);
    }
    const targetCurve = toProbabilityCurve(targetDateResult());
    for (const marker of targetCurve.markers) {
      expect(marker.probability).toBeGreaterThanOrEqual(marker.level / 100 - 1e-9);
    }
  });
});

describe("toBurnUpSeries", () => {
  const history = [3, 5, 4, 6, 2, 5, 4, 3]; // sum = 32

  it("starts historical points at 0 at the start of the oldest period", () => {
    const series = toBurnUpSeries(backlogResult(), history, 7, {
      kind: "backlog",
      backlogSize: 20,
    });
    expect(series.historical[0]).toEqual({ label: "2026-08-06", value: 0 });
  });

  it("gives one historical point per period, ending at the reference date with the running total", () => {
    const series = toBurnUpSeries(backlogResult(), history, 7, {
      kind: "backlog",
      backlogSize: 20,
    });
    expect(series.historical).toHaveLength(history.length + 1);
    expect(series.historical.map((p) => p.value)).toEqual([0, 3, 8, 12, 18, 20, 25, 29, 32]);
    expect(series.historical.at(-1)).toEqual({ label: "2026-10-01", value: 32 });
  });

  it("shows a zero-throughput period as a flat segment (no increase)", () => {
    const series = toBurnUpSeries(backlogResult(), [3, 0, 4], 7, {
      kind: "backlog",
      backlogSize: 20,
    });
    expect(series.historical.map((p) => p.value)).toEqual([0, 3, 3, 7]);
  });

  it("fan points add the historical total to each projection point's cumulative", () => {
    const series = toBurnUpSeries(backlogResult(), history, 7, {
      kind: "backlog",
      backlogSize: 20,
    });
    expect(series.fan).toEqual([
      { label: "2026-10-08", cumulative: { 50: 36, 70: 36, 85: 35, 95: 34 } },
    ]);
  });

  it("backlog mode: the target is a horizontal line at historical total + backlog size", () => {
    const series = toBurnUpSeries(backlogResult(), history, 7, {
      kind: "backlog",
      backlogSize: 20,
    });
    expect(series.target).toEqual({ kind: "backlog", value: 52 });
  });

  it("target-date mode: the target is a vertical marker at the target date", () => {
    const series = toBurnUpSeries(targetDateResult(), history, 7, {
      kind: "target-date",
      targetDate: "2026-11-14",
    });
    expect(series.target).toEqual({ kind: "target-date", label: "2026-11-14" });
  });
});

describe("toRunChartSeries", () => {
  it("returns one bar per period, oldest first, with the entered heights", () => {
    const series = toRunChartSeries([3, 5, 4, 6, 2, 5, 4, 3], "2026-10-01", 7);
    expect(series.bars.map((b) => b.value)).toEqual([3, 5, 4, 6, 2, 5, 4, 3]);
    expect(series.bars[0].label).toBe("2026-08-13"); // oldest period end
    expect(series.bars.at(-1)?.label).toBe("2026-10-01"); // most recent, = reference date
  });

  it("keeps zero-throughput periods as zero-value bars, not omitted", () => {
    const series = toRunChartSeries([3, 0, 4, 0, 5, 2], "2026-10-01", 7);
    expect(series.bars.map((b) => b.value)).toEqual([3, 0, 4, 0, 5, 2]);
  });

  it("computes the median for an odd-length history", () => {
    expect(toRunChartSeries([3, 5, 4, 6, 2], "2026-10-01", 7).median).toBe(4);
  });

  it("computes the median for an even-length history", () => {
    expect(toRunChartSeries([3, 5, 4, 6, 2, 5, 4, 3], "2026-10-01", 7).median).toBe(4);
  });
});

describe("outcomeLabels", () => {
  it("formats each outcome as a string, keyed by level", () => {
    expect(outcomeLabels(backlogResult())).toEqual({
      50: "2026-11-06",
      70: "2026-11-13",
      85: "2026-11-13",
      95: "2026-11-20",
    });
  });
});
