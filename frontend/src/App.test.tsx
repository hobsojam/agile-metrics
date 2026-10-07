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
      reference_date: "2026-10-01",
      history: [3, 5, 4, 6, 2, 5, 4, 3],
      done_statuses: [],
      distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
      projection: [
        { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
      ],
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
          period_days: 7,
          history: [3, 5, 4, 6, 2, 5, 4, 3],
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
      reference_date: "2026-10-01",
      history: [3, 5, 4, 6, 2, 5, 4, 3],
      done_statuses: [],
      distribution: [{ lower: 26, upper: 32, trials: 10000 }],
      projection: [
        { period: 1, period_end: "2026-10-08", cumulative: { "50": 32, "70": 30, "85": 28, "95": 26 } },
      ],
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
          period_days: 7,
          history: [3, 5, 4, 6, 2, 5, 4, 3],
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

describe("App - User Story 3 (errors and loading)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the server's error message on the page instead of crashing", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          error: "exactly one of backlog_size or target_date is required, not both or neither",
        }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    );

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/period/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    await waitFor(() => {
      expect(screen.getByText(/exactly one of backlog_size or target_date/)).toBeInTheDocument();
    });
  });

  it("shows an in-progress indicator while a request is pending", async () => {
    let resolveFetch!: (value: Response) => void;
    vi.mocked(fetch).mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      })
    );

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/period/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    expect(await screen.findByText(/loading|computing|forecasting/i)).toBeInTheDocument();

    resolveFetch(
      new Response(
        JSON.stringify({
          outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
          trials_run: 10000,
          periods_used: 8,
          reference_date: "2026-10-01",
          history: [3, 5, 4, 6, 2, 5, 4, 3],
          done_statuses: [],
          distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
          projection: [
            {
              period: 1,
              period_end: "2026-10-08",
              cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 },
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    await waitFor(() => {
      expect(screen.queryByText(/loading|computing|forecasting/i)).not.toBeInTheDocument();
    });
  });
});

describe("App - Linear data-source toggle (spec 006)", () => {
  it("shows the manual history field by default, and hides the Linear fields", () => {
    render(<App />);

    expect(screen.getByLabelText(/history/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/linear api key/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/linear team/i)).not.toBeInTheDocument();
  });

  it("switches to the Linear fields and hides history when Linear mode is selected", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /linear/i }));

    expect(screen.getByLabelText(/linear api key/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/linear team/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^history/i)).not.toBeInTheDocument();
  });

  it("switches back to the history field when manual paste is reselected", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /linear/i }));
    await user.click(screen.getByRole("radio", { name: /manual paste/i }));

    expect(screen.getByLabelText(/^history/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/linear api key/i)).not.toBeInTheDocument();
  });

  it("uses a password-style input for the Linear API key", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /linear/i }));

    expect(screen.getByLabelText(/linear api key/i)).toHaveAttribute("type", "password");
  });

  it("submits linear_api_key/linear_team_id instead of history, and renders results and charts", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const mockResult = {
      outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
      trials_run: 10000,
      periods_used: 8,
      reference_date: "2026-10-01",
      history: [3, 5, 4, 6, 2, 5, 4, 3],
      done_statuses: [],
      distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
      projection: [
        { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
      ],
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /linear/i }));
    await user.type(screen.getByLabelText(/period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.type(screen.getByLabelText(/linear api key/i), "lin_api_test");
    await user.type(screen.getByLabelText(/linear team/i), "team-123");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/forecast",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          period_days: 7,
          linear_api_key: "lin_api_test",
          linear_team_id: "team-123",
          backlog_size: 20,
        }),
      })
    );

    await waitFor(() => {
      expect(screen.getByText(/50% confidence: 2026-11-06/)).toBeInTheDocument();
      expect(screen.getByRole("region", { name: /forecast charts/i })).toBeInTheDocument();
      expect(screen.getByRole("figure", { name: /outcome distribution/i })).toBeInTheDocument();
    });

    vi.unstubAllGlobals();
  });
});

describe("App - CSV data-source toggle (spec 007)", () => {
  it("shows a file input and a paste textarea when CSV mode is selected, hiding other fields", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /csv/i }));

    expect(screen.getByLabelText(/csv file/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/paste csv text/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^history/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/linear api key/i)).not.toBeInTheDocument();
  });

  it("switches back to the history field when manual paste is reselected from CSV mode", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /csv/i }));
    await user.click(screen.getByRole("radio", { name: /manual paste/i }));

    expect(screen.getByLabelText(/^history/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/csv file/i)).not.toBeInTheDocument();
  });

  it("submits pasted CSV text as FormData to /api/forecast/csv instead of history", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const mockResult = {
      outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
      trials_run: 10000,
      periods_used: 8,
      reference_date: "2026-10-01",
      history: [3, 5, 4, 6, 2, 5, 4, 3],
      done_statuses: [],
      distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
      projection: [
        { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
      ],
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /csv/i }));
    await user.type(screen.getByLabelText(/period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.type(
      screen.getByLabelText(/paste csv text/i),
      "id,type,title,start_date,end_date\n1,story,Item,,2026-10-01"
    );
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    expect(fetch).toHaveBeenCalledWith("/api/forecast/csv", expect.objectContaining({ method: "POST" }));
    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = options?.body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("period_days")).toBe("7");
    expect(body.get("backlog_size")).toBe("20");
    expect(body.get("csv_text")).toContain("id,type,title,start_date,end_date");
    expect(body.has("csv_file")).toBe(false);

    await waitFor(() => {
      expect(screen.getByText(/50% confidence: 2026-11-06/)).toBeInTheDocument();
      expect(screen.getByRole("region", { name: /forecast charts/i })).toBeInTheDocument();
    });

    vi.unstubAllGlobals();
  });

  it("submits an uploaded CSV file as FormData instead of pasted text", async () => {
    vi.stubGlobal("fetch", vi.fn());
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
          trials_run: 10000,
          periods_used: 8,
          reference_date: "2026-10-01",
          history: [3, 5, 4, 6, 2, 5, 4, 3],
          done_statuses: [],
          distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
          projection: [
            {
              period: 1,
              period_end: "2026-10-08",
              cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 },
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: /csv/i }));
    await user.type(screen.getByLabelText(/period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    const file = new File(["id,type,title,start_date,end_date\n1,story,Item,,2026-10-01"], "items.csv", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText(/csv file/i), file);
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    const [, options] = vi.mocked(fetch).mock.calls[0];
    const body = options?.body as FormData;
    expect(body.get("csv_file")).toBeInstanceOf(File);
    expect(body.has("csv_text")).toBe(false);

    vi.unstubAllGlobals();
  });
});

describe("App - forecast charts (spec 005)", () => {
  const mockResult = {
    outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
    trials_run: 10000,
    periods_used: 8,
    reference_date: "2026-10-01",
    history: [3, 5, 4, 6, 2, 5, 4, 3],
    done_statuses: [],
    distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
    projection: [
      { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
    ],
  };

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function submitValidBacklogForecast(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/period/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));
  }

  it("renders a forecast charts region below the confidence-level list after a successful submission", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);
    await submitValidBacklogForecast(user);

    await waitFor(() => {
      expect(screen.getByText(/50% confidence: 2026-11-06/)).toBeInTheDocument();
      expect(screen.getByRole("region", { name: /forecast charts/i })).toBeInTheDocument();
      expect(screen.getByRole("figure", { name: /outcome distribution/i })).toBeInTheDocument();
    });
  });

  it("renders no charts region when the submission fails", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ error: "backlog_size must be a positive whole number" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);
    await submitValidBacklogForecast(user);

    await waitFor(() => {
      expect(screen.getByText(/backlog_size must be a positive whole number/)).toBeInTheDocument();
    });
    expect(screen.queryByRole("region", { name: /forecast charts/i })).not.toBeInTheDocument();
  });

  it("keeps the charts drawn from the submitted inputs even if the form is edited afterwards", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);
    await submitValidBacklogForecast(user);

    await waitFor(() => {
      expect(screen.getByRole("region", { name: /forecast charts/i })).toBeInTheDocument();
    });

    // Editing the form after a successful submission must not change what the
    // already-rendered charts show - they reflect what was submitted (FR-009).
    await user.clear(screen.getByLabelText(/backlog size/i));
    await user.type(screen.getByLabelText(/backlog size/i), "999");

    expect(screen.getByRole("region", { name: /forecast charts/i })).toBeInTheDocument();
    expect(screen.getByText(/50% confidence: 2026-11-06/)).toBeInTheDocument();
  });
});

describe("App - Jira flow-metrics charts (spec 011)", () => {
  const baseResult = {
    outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
    trials_run: 10000,
    periods_used: 8,
    reference_date: "2026-10-01",
    history: [3, 5, 4, 6, 2, 5, 4, 3],
    done_statuses: ["Done"],
    distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
    projection: [
      { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
    ],
  };

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function submitJiraForecast(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole("radio", { name: /jira/i }));
    await user.type(screen.getByLabelText(/jira site/i), "acme.atlassian.net");
    await user.type(screen.getByLabelText(/jira account email/i), "dev@example.com");
    await user.type(screen.getByLabelText(/jira api token/i), "tok-123");
    await user.type(screen.getByLabelText(/jira project/i), "ENG");
    await user.type(screen.getByLabelText(/^period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));
  }

  it("renders the three flow-metrics charts alongside the existing four when flow_metrics is present", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          ...baseResult,
          flow_metrics: {
            cycle_time: [
              { key: "ENG-1", started_at: "2026-09-01", resolved_at: "2026-09-05" },
            ],
            wip: [{ key: "ENG-2", started_at: "2026-09-20", age_days: 17 }],
            flow_state_counts: [
              { day: "2026-09-01", not_started: 0, in_progress: 1, done: 0 },
            ],
            excluded_count: 0,
            capped_count: 0,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const user = userEvent.setup();
    render(<App />);
    await submitJiraForecast(user);

    await waitFor(() => {
      expect(screen.getByRole("figure", { name: /outcome distribution/i })).toBeInTheDocument();
      expect(screen.getByRole("figure", { name: /cycle time/i })).toBeInTheDocument();
      expect(screen.getByRole("figure", { name: /aging work in progress/i })).toBeInTheDocument();
      expect(screen.getByRole("figure", { name: /cumulative flow/i })).toBeInTheDocument();
    });
  });

  it("renders no flow-metrics charts for a manual-paste result", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ ...baseResult, flow_metrics: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/^period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    await waitFor(() => {
      expect(screen.getByRole("figure", { name: /outcome distribution/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole("figure", { name: /cycle time/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("figure", { name: /aging work in progress/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("figure", { name: /cumulative flow/i })).not.toBeInTheDocument();
  });
});

describe("App - forecast precision warning (spec 009)", () => {
  const baseResult = {
    outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
    trials_run: 10000,
    periods_used: 8,
    reference_date: "2026-10-01",
    history: [3, 5, 4, 6, 2, 5, 4, 3],
    done_statuses: [],
    distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
    projection: [
      { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
    ],
  };

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function submitValidBacklogForecast(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/period/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));
  }

  it("renders a visible warning banner, distinct from the error banner, when precision_warning is present", async () => {
    const mockResult = {
      ...baseResult,
      precision_warning: { message: "This forecast's range is very wide." },
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);
    await submitValidBacklogForecast(user);

    await waitFor(() => {
      expect(screen.getByText(/50% confidence: 2026-11-06/)).toBeInTheDocument();
    });
    const warning = screen.getByText(/this forecast's range is very wide/i);
    expect(warning).toBeInTheDocument();
    // The error banner uses role="alert" with red styling; the warning banner
    // must not reuse it, so the two are visually and semantically distinct.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: /forecast charts/i })).toBeInTheDocument();
  });

  it("renders no warning banner when precision_warning is absent", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(baseResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const user = userEvent.setup();
    render(<App />);
    await submitValidBacklogForecast(user);

    await waitFor(() => {
      expect(screen.getByText(/50% confidence: 2026-11-06/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/this forecast's range is very wide/i)).not.toBeInTheDocument();
  });
});

describe("App - Jira data-source option (spec 010)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const jiraResult = {
    outcomes: { "50": "2026-11-06", "70": "2026-11-13", "85": "2026-11-13", "95": "2026-11-20" },
    trials_run: 10000,
    periods_used: 8,
    reference_date: "2026-10-01",
    history: [3, 5, 4, 6, 2, 5, 4, 3],
    done_statuses: ["Done", "Released"],
    distribution: [{ lower: "2026-11-06", upper: "2026-11-06", trials: 10000 }],
    projection: [
      { period: 1, period_end: "2026-10-08", cumulative: { "50": 4, "70": 4, "85": 3, "95": 2 } },
    ],
  };

  it("shows Jira fields and hides the manual history field when Jira is selected", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("radio", { name: /jira/i }));

    expect(screen.getByLabelText(/jira site/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/jira account email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/jira api token/i)).toHaveAttribute("type", "password");
    expect(screen.getByLabelText(/jira project/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^history/i)).not.toBeInTheDocument();
  });

  it("submits the Jira fields instead of history", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(jiraResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("radio", { name: /jira/i }));
    await user.type(screen.getByLabelText(/jira site/i), "acme.atlassian.net");
    await user.type(screen.getByLabelText(/jira account email/i), "dev@example.com");
    await user.type(screen.getByLabelText(/jira api token/i), "tok-123");
    await user.type(screen.getByLabelText(/jira project/i), "ENG");
    await user.type(screen.getByLabelText(/^period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/forecast",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          period_days: 7,
          jira_site: "acme.atlassian.net",
          jira_email: "dev@example.com",
          jira_api_token: "tok-123",
          jira_project_key: "ENG",
          backlog_size: 20,
        }),
      })
    );
  });

  it("renders a Done statuses line when the result names them", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(jiraResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("radio", { name: /jira/i }));
    await user.type(screen.getByLabelText(/jira site/i), "acme.atlassian.net");
    await user.type(screen.getByLabelText(/jira account email/i), "dev@example.com");
    await user.type(screen.getByLabelText(/jira api token/i), "tok-123");
    await user.type(screen.getByLabelText(/jira project/i), "ENG");
    await user.type(screen.getByLabelText(/^period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    await waitFor(() => {
      expect(screen.getByText("Done statuses: Done, Released")).toBeInTheDocument();
    });
  });

  it("renders no Done statuses line for a manual-paste result", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ ...jiraResult, done_statuses: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/history/i), "3,5,4,6,2,5,4,3");
    await user.type(screen.getByLabelText(/^period length/i), "7");
    await user.type(screen.getByLabelText(/backlog size/i), "20");
    await user.click(screen.getByRole("button", { name: /submit|forecast/i }));

    await waitFor(() => {
      expect(screen.getByText(/50% confidence/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Done statuses/)).not.toBeInTheDocument();
  });
});
