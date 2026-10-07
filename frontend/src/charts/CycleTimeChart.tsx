import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { components } from "../api-types";

type CycleTimeEntry = components["schemas"]["CycleTimeEntry"];

interface CycleTimeChartProps {
  entries: CycleTimeEntry[];
}

function daysBetween(start: string, end: string): number {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

/**
 * How long each resolved item took from its first in-progress transition to
 * resolution (spec 011 User Story 1) - a diagnostic, retrospective view
 * alongside the existing forecast charts, not a replacement for them.
 */
export function CycleTimeChart({ entries }: Readonly<CycleTimeChartProps>) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No resolved issues with a known start - nothing to show yet.
      </p>
    );
  }

  const durations = entries.map((entry) => daysBetween(entry.started_at, entry.resolved_at));
  const data = entries.map((entry, index) => ({
    label: entry.key,
    days: durations[index],
  }));
  const medianDays = median(durations);

  return (
    <figure aria-label="Cycle time">
      <h3 className="text-base font-semibold text-slate-900">Cycle time</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 24, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis
              label={{ value: "Days from start to resolution", angle: -90, position: "insideLeft" }}
              allowDecimals={false}
            />
            <Tooltip formatter={(value) => [`${value} days`, ""]} />
            <Bar dataKey="days" fill="oklch(70.7% 0.165 254.624)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        How long each resolved item took, from when it first entered progress to resolution.
      </figcaption>
      <p className="sr-only">
        {entries.length} items with a known start; median cycle time {medianDays.toFixed(1)} days.
      </p>
    </figure>
  );
}
