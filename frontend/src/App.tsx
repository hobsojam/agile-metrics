import { useState } from "react";
import type { components } from "./api-types";

export type ForecastResult = components["schemas"]["ForecastResult"];

export function App() {
  const [history, setHistory] = useState("");
  const [periodDays, setPeriodDays] = useState("");
  const [backlogSize, setBacklogSize] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [seed, setSeed] = useState("");

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Submit wiring added in User Story 1/2 (fetch + rendering the result).
  }

  return (
    <main>
      <h1>Agile Metrics Forecast</h1>
      <form onSubmit={handleSubmit}>
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
        <button type="submit">Get forecast</button>
      </form>
    </main>
  );
}
