import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProbabilityCurveChart } from "./ProbabilityCurveChart";
import { toProbabilityCurve } from "./chartData";
import type { components } from "../api-types";

type ForecastResult = components["schemas"]["ForecastResult"];

const backlogResult: ForecastResult = {
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
};

const targetDateResult: ForecastResult = {
  outcomes: { "50": 24, "70": 22, "85": 21, "95": 19 },
  trials_run: 10000,
  periods_used: 8,
  reference_date: "2026-10-01",
  distribution: [
    { lower: 17, upper: 17, trials: 500 },
    { lower: 19, upper: 19, trials: 1000 },
    { lower: 21, upper: 21, trials: 1500 },
    { lower: 22, upper: 22, trials: 2000 },
    { lower: 24, upper: 24, trials: 5000 },
  ],
  projection: [
    { period: 1, period_end: "2026-10-08", cumulative: { "50": 24, "70": 22, "85": 21, "95": 19 } },
  ],
};

describe("ProbabilityCurveChart", () => {
  it("renders a figure with a title and a caption for backlog (date) mode", () => {
    render(<ProbabilityCurveChart series={toProbabilityCurve(backlogResult)} />);
    expect(screen.getByRole("figure", { name: /likelihood of finishing/i })).toBeInTheDocument();
    expect(screen.getByText(/how likely you are to be done by a date/i)).toBeInTheDocument();
  });

  it("renders a caption for target-date (items) mode", () => {
    render(<ProbabilityCurveChart series={toProbabilityCurve(targetDateResult)} />);
    expect(screen.getByText(/to complete at least/i)).toBeInTheDocument();
  });

  it("includes a text alternative with the likelihood at each listed outcome", () => {
    render(<ProbabilityCurveChart series={toProbabilityCurve(backlogResult)} />);
    expect(screen.getByText(/50%.*2026-11-06.*50%/)).toBeInTheDocument();
    expect(screen.getByText(/95%.*2026-11-20.*100%/)).toBeInTheDocument();
  });
});
