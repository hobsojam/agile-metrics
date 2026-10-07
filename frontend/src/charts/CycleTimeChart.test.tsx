import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { CycleTimeChart } from "./CycleTimeChart";
import type { components } from "../api-types";

type CycleTimeEntry = components["schemas"]["CycleTimeEntry"];
type CycleTimePercentiles = components["schemas"]["FlowMetrics"]["cycle_time_percentiles"];

const entries: CycleTimeEntry[] = [
  { key: "ENG-1", started_at: "2026-09-01", resolved_at: "2026-09-02" },
  { key: "ENG-2", started_at: "2026-09-01", resolved_at: "2026-09-05" },
];

const percentiles: CycleTimePercentiles = { "50": 3, "70": 3, "85": 6, "95": 8 };

describe("CycleTimeChart", () => {
  it("renders a figure with a visible title and a caption explaining how to read it", () => {
    render(<CycleTimeChart entries={entries} percentiles={percentiles} />);
    const figure = screen.getByRole("figure", { name: /cycle time/i });
    expect(figure).toBeInTheDocument();
    expect(screen.getByText(/resolution date.*cycle time/i)).toBeInTheDocument();
  });

  it("includes a text alternative naming the item count and the four percentile levels", () => {
    render(<CycleTimeChart entries={entries} percentiles={percentiles} />);
    expect(screen.getByText(/2 items/i)).toBeInTheDocument();
    expect(screen.getByText(/50%.*3 days/)).toBeInTheDocument();
    expect(screen.getByText(/70%.*3 days/)).toBeInTheDocument();
    expect(screen.getByText(/85%.*6 days/)).toBeInTheDocument();
    expect(screen.getByText(/95%.*8 days/)).toBeInTheDocument();
  });

  it("still plots points with no percentile lines when there isn't enough history", () => {
    render(<CycleTimeChart entries={entries} percentiles={null} />);
    expect(screen.getByRole("figure", { name: /cycle time/i })).toBeInTheDocument();
    expect(screen.getByText(/2 items/i)).toBeInTheDocument();
    expect(screen.getByText(/not enough history/i)).toBeInTheDocument();
    expect(screen.queryByText(/50%/)).not.toBeInTheDocument();
  });

  it("shows a plain not-enough-data state when there are no entries", () => {
    render(<CycleTimeChart entries={[]} percentiles={null} />);
    expect(screen.getByText(/no resolved issues with a known start/i)).toBeInTheDocument();
    expect(screen.queryByRole("figure")).not.toBeInTheDocument();
  });
});
