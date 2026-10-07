import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgingWipChart } from "./AgingWipChart";
import type { components } from "../api-types";

type WipSnapshot = components["schemas"]["WipSnapshot"];

const snapshots: WipSnapshot[] = [
  { key: "ENG-2", started_at: "2026-09-01", age_days: 36 },
  { key: "ENG-1", started_at: "2026-10-01", age_days: 6 },
];

describe("AgingWipChart", () => {
  it("renders a figure with a visible title and a caption explaining how to read it", () => {
    render(<AgingWipChart snapshots={snapshots} />);
    const figure = screen.getByRole("figure", { name: /aging work in progress/i });
    expect(figure).toBeInTheDocument();
    expect(screen.getByText(/how long.*in progress/i)).toBeInTheDocument();
  });

  it("includes a text alternative naming the oldest item and its age", () => {
    render(<AgingWipChart snapshots={snapshots} />);
    expect(screen.getByText(/ENG-2.*36 days/i)).toBeInTheDocument();
  });

  it("shows the plain 'nothing in progress' state when there are no snapshots", () => {
    render(<AgingWipChart snapshots={[]} />);
    expect(screen.getByText(/nothing currently in progress/i)).toBeInTheDocument();
    expect(screen.queryByRole("figure")).not.toBeInTheDocument();
  });
});
