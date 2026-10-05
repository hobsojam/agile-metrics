import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DistributionChart } from "./DistributionChart";
import { toDistributionSeries } from "./chartData";
import type { components } from "../api-types";

type ForecastResult = components["schemas"]["ForecastResponseBody"];

const backlogResult: ForecastResult = {
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
};

describe("DistributionChart", () => {
  it("renders a figure with a visible title and a caption explaining how to read it", () => {
    render(<DistributionChart series={toDistributionSeries(backlogResult)} />);
    const figure = screen.getByRole("figure", { name: /outcome distribution/i });
    expect(figure).toBeInTheDocument();
    expect(screen.getByText(/bar.*simulated future/i)).toBeInTheDocument();
  });

  it("includes a text alternative listing all four levels and their outcomes", () => {
    render(<DistributionChart series={toDistributionSeries(backlogResult)} />);
    expect(screen.getByText(/50%.*2026-11-06/)).toBeInTheDocument();
    expect(screen.getByText(/70%.*2026-11-13/)).toBeInTheDocument();
    expect(screen.getByText(/85%.*2026-11-13/)).toBeInTheDocument();
    expect(screen.getByText(/95%.*2026-11-20/)).toBeInTheDocument();
  });

  it("never shows an 'average' or 'expected' value", () => {
    render(<DistributionChart series={toDistributionSeries(backlogResult)} />);
    expect(screen.queryByText(/average/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/expected/i)).not.toBeInTheDocument();
  });
});
