import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BurnUpChart } from "./BurnUpChart";
import { outcomeLabels, toBurnUpSeries } from "./chartData";
import type { components } from "../api-types";

type ForecastResult = components["schemas"]["ForecastResult"];

const backlogResult: ForecastResult = {
  outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
  trials_run: 10000,
  periods_used: 8,
  reference_date: "2026-10-01",
  distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
  projection: [
    { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
  ],
};

const history = [3, 5, 4, 6, 2, 5, 4, 3];

describe("BurnUpChart", () => {
  it("renders a figure with a title and caption", () => {
    const series = toBurnUpSeries(backlogResult, history, 7, {
      kind: "backlog",
      backlogSize: 20,
    });
    render(
      <BurnUpChart series={series} outcomes={outcomeLabels(backlogResult)} mode="backlog" />
    );
    expect(screen.getByRole("figure", { name: /history and forecast/i })).toBeInTheDocument();
    expect(screen.getByText(/project each confidence level/i)).toBeInTheDocument();
  });

  it("includes a text alternative stating the historical total, the target, and each level's outcome", () => {
    const series = toBurnUpSeries(backlogResult, history, 7, {
      kind: "backlog",
      backlogSize: 20,
    });
    render(
      <BurnUpChart series={series} outcomes={outcomeLabels(backlogResult)} mode="backlog" />
    );
    expect(screen.getByText(/32 items completed so far/i)).toBeInTheDocument();
    expect(screen.getByText(/52 items/i)).toBeInTheDocument(); // target = 32 + 20
    expect(screen.getByText(/50%.*2026-11-06/)).toBeInTheDocument();
  });

  it("states the target date in target-date mode", () => {
    const series = toBurnUpSeries(backlogResult, history, 7, {
      kind: "target-date",
      targetDate: "2026-11-14",
    });
    render(
      <BurnUpChart series={series} outcomes={outcomeLabels(backlogResult)} mode="target-date" />
    );
    expect(screen.getByText(/2026-11-14/)).toBeInTheDocument();
  });
});
