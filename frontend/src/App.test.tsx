import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

describe("App - User Story 1 (backlog size)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits the backlog-size request and renders the four returned dates", async () => {
    const mockResult = {
      outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
      trials_run: 10000,
      periods_used: 8,
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/period/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.type(screen.getByLabelText(/seed/i), "42");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/forecast",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          history: [3, 5, 4, 6, 2, 5, 4, 3],
          period_days: 7,
          backlog_size: 20,
          seed: 42,
        }),
      })
    );

    await waitFor(() => {
      expect(screen.getByText(/50% confidence: 2026-11-06/)).toBeInTheDocument();
      expect(screen.getByText(/70% confidence: 2026-11-13/)).toBeInTheDocument();
      expect(screen.getByText(/85% confidence: 2026-11-13/)).toBeInTheDocument();
      expect(screen.getByText(/95% confidence: 2026-11-20/)).toBeInTheDocument();
    });
  });
});

describe("App - User Story 2 (target date)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits the target-date request (backlog size left blank) and renders the four returned counts", async () => {
    const mockResult = {
      outcomes: { "50": 32, "70": 30, "85": 28, "95": 26 },
      trials_run: 10000,
      periods_used: 8,
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/period/i), "7");
    await user.type(screen.getByLabelText(/target date/i), "2026-12-01");
    await user.type(screen.getByLabelText(/seed/i), "42");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/forecast",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          history: [3, 5, 4, 6, 2, 5, 4, 3],
          period_days: 7,
          target_date: "2026-12-01",
          seed: 42,
        }),
      })
    );

    await waitFor(() => {
      expect(screen.getByText(/50% confidence: 32/)).toBeInTheDocument();
      expect(screen.getByText(/70% confidence: 30/)).toBeInTheDocument();
      expect(screen.getByText(/85% confidence: 28/)).toBeInTheDocument();
      expect(screen.getByText(/95% confidence: 26/)).toBeInTheDocument();
    });
  });
});
