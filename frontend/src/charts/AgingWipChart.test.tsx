import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgingWipChart } from "./AgingWipChart";
import type { components } from "../api-types";

type WipSnapshot = components["schemas"]["WipSnapshot"];
type CycleTimePercentiles = components["schemas"]["FlowMetrics"]["cycle_time_percentiles"];

const snapshots: WipSnapshot[] = [
  { key: "ENG-2", started_at: "2026-09-01", age_days: 36 },
  { key: "ENG-1", started_at: "2026-10-01", age_days: 6 },
];

const percentiles: CycleTimePercentiles = { "50": 3, "70": 3, "85": 12, "95": 20 };

describe("AgingWipChart", () => {
  it("renders a figure with a visible title and a caption explaining how to read it", () => {
    render(<AgingWipChart snapshots={snapshots} percentiles={percentiles} />);
    const figure = screen.getByRole("figure", { name: /aging work in progress/i });
    expect(figure).toBeInTheDocument();
    expect(screen.getByText(/how long.*in progress/i)).toBeInTheDocument();
  });

  it("includes a text alternative naming the oldest item and its age", () => {
    render(<AgingWipChart snapshots={snapshots} percentiles={percentiles} />);
    expect(screen.getByText(/ENG-2.*36 days/i)).toBeInTheDocument();
  });

  it("flags items older than the 85th-percentile threshold as at-risk", () => {
    render(<AgingWipChart snapshots={snapshots} percentiles={percentiles} />);
    // ENG-2 (36 days) exceeds the 12-day threshold; ENG-1 (6 days) does not.
    expect(screen.getByText(/85% threshold.*12 days/i)).toBeInTheDocument();
    expect(screen.getByText(/ENG-2.*exceeds/i)).toBeInTheDocument();
    expect(screen.queryByText(/ENG-1.*exceeds/i)).not.toBeInTheDocument();
  });

  it("shows no threshold line or at-risk flagging when there isn't enough history", () => {
    render(<AgingWipChart snapshots={snapshots} percentiles={null} />);
    expect(screen.queryByText(/threshold/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/exceeds/i)).not.toBeInTheDocument();
  });

  it("shows the plain 'nothing in progress' state when there are no snapshots", () => {
    render(<AgingWipChart snapshots={[]} percentiles={percentiles} />);
    expect(screen.getByText(/nothing currently in progress/i)).toBeInTheDocument();
    expect(screen.queryByRole("figure")).not.toBeInTheDocument();
  });
});
