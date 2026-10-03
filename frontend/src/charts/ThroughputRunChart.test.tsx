import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ThroughputRunChart } from "./ThroughputRunChart";
import { toRunChartSeries } from "./chartData";

describe("ThroughputRunChart", () => {
  const series = toRunChartSeries([3, 5, 4, 6, 2, 5, 4, 3], "2026-10-01", 7);

  it("renders a figure with a title and a caption", () => {
    render(<ThroughputRunChart series={series} />);
    expect(screen.getByRole("figure", { name: /throughput history/i })).toBeInTheDocument();
    expect(screen.getAllByText(/median/i).length).toBeGreaterThan(0);
  });

  it("includes a text alternative stating the period count, median, min, and max", () => {
    render(<ThroughputRunChart series={series} />);
    expect(screen.getByText(/8 historical periods/i)).toBeInTheDocument();
    expect(screen.getByText(/median.*4/i)).toBeInTheDocument();
    expect(screen.getByText(/min.*2/i)).toBeInTheDocument();
    expect(screen.getByText(/max.*6/i)).toBeInTheDocument();
  });
});
