import { useState } from "react";
import type { components } from "./api-types";

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
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const body: ForecastRequestBody = {
      history: history.split(",").map((value) => Number(value.trim())),
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

  return (
    <main>
      <h1>Agile Metrics Forecast</h1>
      <form onSubmit={(event) => void handleSubmit(event)}>
        <div>
          <label htmlFor="history">History (comma-separated)</label>
          <input
            id="history"
            value={history}
            onChange={(event) => setHistory(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="period-days">Period length (days)</label>
          <input
            id="period-days"
            value={periodDays}
            onChange={(event) => setPeriodDays(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="backlog-size">Backlog size</label>
          <input
            id="backlog-size"
            value={backlogSize}
            onChange={(event) => setBacklogSize(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="target-date">Target date</label>
          <input
            id="target-date"
            value={targetDate}
            onChange={(event) => setTargetDate(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="seed">Seed (optional)</label>
          <input id="seed" value={seed} onChange={(event) => setSeed(event.target.value)} />
        </div>
        <button type="submit" disabled={loading}>
          Get forecast
        </button>
      </form>

      {loading && <output>Computing forecast…</output>}

      {error && (
        <p role="alert">
          <strong>Error:</strong> {error}
        </p>
      )}

      {result && (
        <section>
          <p>
            Forecast ({result.trials_run} trials, {result.periods_used} historical periods):
          </p>
          <ul>
            {CONFIDENCE_LEVELS.map((level) => (
              <li key={level}>
                {level}% confidence: {String(result.outcomes[level])}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
