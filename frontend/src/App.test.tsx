import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
  it("renders inputs for history, period length, backlog size, target date, seed, and submit", () => {
    render(<App />);

    expect(screen.getByLabelText(/history/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/period/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/backlog size/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/target date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/seed/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit|forecast/i })).toBeInTheDocument();
  });
});
