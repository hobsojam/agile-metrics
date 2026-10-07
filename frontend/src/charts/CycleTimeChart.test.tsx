import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { CycleTimeChart } from "./CycleTimeChart";
import type { components } from "../api-types";

type CycleTimeEntry = components["schemas"]["CycleTimeEntry"];

const entries: CycleTimeEntry[] = [
  { key: "ENG-1", started_at: "2026-09-01", resolved_at: "2026-09-05" },
  { key: "ENG-2", started_at: "2026-09-01", resolved_at: "2026-09-03" },
];

describe("CycleTimeChart", () => {
  it("renders a figure with a visible title and a caption explaining how to read it", () => {
    render(<CycleTimeChart entries={entries} />);
    const figure = screen.getByRole("figure", { name: /cycle time/i });
    expect(figure).toBeInTheDocument();
    expect(screen.getByText(/how long each.*took/i)).toBeInTheDocument();
  });

  it("includes a text alternative naming the item count and median duration", () => {
    render(<CycleTimeChart entries={entries} />);
    expect(screen.getByText(/2 items/i)).toBeInTheDocument();
    expect(screen.getByText(/median.*3\.0 days/i)).toBeInTheDocument();
  });

  it("shows a plain not-enough-data state when there are no entries", () => {
    render(<CycleTimeChart entries={[]} />);
    expect(screen.getByText(/no resolved issues with a known start/i)).toBeInTheDocument();
    expect(screen.queryByRole("figure")).not.toBeInTheDocument();
  });
});
