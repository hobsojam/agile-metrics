import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { components } from "../api-types";

type WipSnapshot = components["schemas"]["WipSnapshot"];

interface AgingWipChartProps {
  snapshots: WipSnapshot[];
}

/**
 * Every currently-in-progress item, oldest first (spec 011 User Story 2), so a
 * team can spot work that has been open longer than usual. The server already
 * sorts `snapshots` oldest-first; this component renders them as given.
 */
export function AgingWipChart({ snapshots }: Readonly<AgingWipChartProps>) {
  if (snapshots.length === 0) {
    return <p className="text-sm text-slate-500">Nothing currently in progress.</p>;
  }

  const data = snapshots.map((snapshot) => ({ label: snapshot.key, days: snapshot.age_days }));
  const oldest = snapshots[0];

  return (
    <figure aria-label="Aging work in progress">
      <h3 className="text-base font-semibold text-slate-900">Aging work in progress</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 24, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis
              label={{ value: "Days in progress", angle: -90, position: "insideLeft" }}
              allowDecimals={false}
            />
            <Tooltip formatter={(value) => [`${value} days`, ""]} />
            <Bar dataKey="days" fill="oklch(70.7% 0.165 254.624)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        How long each item currently in progress has been open, oldest first.
      </figcaption>
      <p className="sr-only">
        {snapshots.length} items in progress. Oldest: {oldest.key}, {oldest.age_days} days.
      </p>
    </figure>
  );
}
