import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { CumulativeFlowChart } from "./CumulativeFlowChart";
import type { components } from "../api-types";

type FlowStateCount = components["schemas"]["FlowStateCount"];

const counts: FlowStateCount[] = [
  { day: "2026-09-01", not_started: 0, in_progress: 2, done: 0 },
  { day: "2026-09-05", not_started: 0, in_progress: 1, done: 1 },
];

describe("CumulativeFlowChart", () => {
  it("renders a figure with a visible title and a caption explaining how to read it", () => {
    render(<CumulativeFlowChart counts={counts} />);
    const figure = screen.getByRole("figure", { name: /cumulative flow/i });
    expect(figure).toBeInTheDocument();
    expect(screen.getByText(/not started.*in progress.*done/i)).toBeInTheDocument();
  });

  it("includes a text alternative naming the date range covered", () => {
    render(<CumulativeFlowChart counts={counts} />);
    expect(screen.getByText(/2026-09-01.*2026-09-05/)).toBeInTheDocument();
  });

  it("shows a plain not-enough-data state when there are no counts", () => {
    render(<CumulativeFlowChart counts={[]} />);
    expect(screen.getByText(/not enough data/i)).toBeInTheDocument();
    expect(screen.queryByRole("figure")).not.toBeInTheDocument();
  });
});
