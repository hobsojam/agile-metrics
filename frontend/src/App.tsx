import { useState } from "react";
import type { components } from "./api-types";
import { ForecastCharts, type SubmittedForecastInputs } from "./charts/ForecastCharts";

export type ForecastResult = components["schemas"]["ForecastResult"];
export type ForecastRequestBody = components["schemas"]["ForecastRequestBody"];
export type ErrorResponseBody = components["schemas"]["ErrorResponseBody"];

const CONFIDENCE_LEVELS = ["50", "70", "85", "95"] as const;

export function App() {
  const [history, setHistory] = useState("");
  const [periodDays, setPeriodDays] = useState("");
  const [backlogSize, setBacklogSize] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [seed, setSeed] = useState("");
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [submittedInputs, setSubmittedInputs] = useState<SubmittedForecastInputs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const historyValues = history.split(",").map((value) => Number(value.trim()));
    const body: ForecastRequestBody = {
      history: historyValues,
      period_days: Number(periodDays),
      ...(backlogSize ? { backlog_size: Number(backlogSize) } : {}),
      ...(targetDate ? { target_date: targetDate } : {}),
      ...(seed ? { seed: Number(seed) } : {}),
    };

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch("/api/forecast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (response.ok) {
        setResult((await response.json()) as ForecastResult);
        // Freeze the inputs alongside the result, so later edits to the form
        // don't change what the already-drawn charts show (FR-009).
        setSubmittedInputs({
          history: historyValues,
          periodDays: Number(periodDays),
          ...(backlogSize ? { backlogSize: Number(backlogSize) } : {}),
          ...(targetDate ? { targetDate } : {}),
        });
      } else {
        const data = (await response.json()) as ErrorResponseBody;
        setError(data.error);
      }
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const inputClassName =
    "rounded-md border border-slate-300 px-3 py-2 text-base text-slate-900 " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 " +
    "focus-visible:ring-offset-2";
  const labelClassName = "text-sm font-medium text-slate-900";

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      {/* The form column stays at 004's max-w-xl; only the results+charts
          area below widens, since a 60-bar histogram needs more room than a
          five-field form (research.md §7 decision 3, confirmed with the
          project owner before implementation). */}
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <h1 className="text-2xl font-semibold text-slate-900">Agile Metrics Forecast</h1>

        <form
          onSubmit={(event) => void handleSubmit(event)}
          className="flex max-w-xl flex-col gap-4 rounded-lg border border-slate-200 bg-white p-6"
        >
          <div className="flex flex-col gap-2">
            <label htmlFor="history" className={labelClassName}>
              History (comma-separated)
            </label>
            <input
              id="history"
              value={history}
              onChange={(event) => setHistory(event.target.value)}
              className={inputClassName}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="period-days" className={labelClassName}>
              Period length (days)
            </label>
            <input
              id="period-days"
              value={periodDays}
              onChange={(event) => setPeriodDays(event.target.value)}
              className={inputClassName}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="backlog-size" className={labelClassName}>
              Backlog size
            </label>
            <input
              id="backlog-size"
              value={backlogSize}
              onChange={(event) => setBacklogSize(event.target.value)}
              className={inputClassName}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="target-date" className={labelClassName}>
              Target date
            </label>
            <input
              id="target-date"
              value={targetDate}
              onChange={(event) => setTargetDate(event.target.value)}
              className={inputClassName}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="seed" className={labelClassName}>
              Seed (optional)
            </label>
            <input
              id="seed"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              className={inputClassName}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
              focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Get forecast
          </button>
        </form>

        {loading && (
          <output className="max-w-xl text-sm text-slate-500">Computing forecast…</output>
        )}

        {error && (
          <div
            role="alert"
            className="max-w-xl rounded-lg border border-red-200 bg-red-50 p-4 text-red-700"
          >
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && submittedInputs && (
          <section className="flex flex-col gap-6 rounded-lg border border-slate-200 bg-white p-6">
            <div className="flex flex-col gap-4">
              <p className="text-sm text-slate-500">
                Forecast ({result.trials_run} trials, {result.periods_used} historical periods):
              </p>
              <ul className="flex max-w-xl flex-col gap-2">
                {CONFIDENCE_LEVELS.map((level) => (
                  <li
                    key={level}
                    className="border-b border-slate-100 pb-2 text-base text-slate-900
                      last:border-0 last:pb-0"
                  >
                    {level}% confidence: {String(result.outcomes[level])}
                  </li>
                ))}
              </ul>
            </div>
            <ForecastCharts result={result} inputs={submittedInputs} />
          </section>
        )}
      </div>
    </main>
  );
}
