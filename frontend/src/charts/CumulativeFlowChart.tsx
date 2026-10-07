import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { components } from "../api-types";

type FlowStateCount = components["schemas"]["FlowStateCount"];

interface CumulativeFlowChartProps {
  counts: FlowStateCount[];
}

/**
 * Simplified cumulative-flow diagram (spec 011 User Story 3): three bands
 * (not started, in progress, done) derived only from each item's start and
 * resolution signals - not a full multi-state workflow diagram (spec
 * Assumptions). Shows whether work-in-progress has been building up.
 */
export function CumulativeFlowChart({ counts }: Readonly<CumulativeFlowChartProps>) {
  if (counts.length === 0) {
    return <p className="text-sm text-slate-500">Not enough data to show cumulative flow yet.</p>;
  }

  const first = counts[0];
  const last = counts.at(-1) ?? first;

  return (
    <figure aria-label="Cumulative flow">
      <h3 className="text-base font-semibold text-slate-900">Cumulative flow</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <AreaChart data={counts} margin={{ top: 8, right: 8, bottom: 24, left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis dataKey="day" tick={{ fontSize: 11 }} />
            <YAxis
              label={{ value: "Items", angle: -90, position: "insideLeft" }}
              allowDecimals={false}
            />
            <Tooltip />
            <Area
              dataKey="not_started"
              stackId="flow"
              stroke="oklch(80.9% 0.105 251.813)"
              fill="oklch(80.9% 0.105 251.813)"
              name="Not started"
            />
            <Area
              dataKey="in_progress"
              stackId="flow"
              stroke="oklch(62.3% 0.214 259.815)"
              fill="oklch(62.3% 0.214 259.815)"
              name="In progress"
            />
            <Area
              dataKey="done"
              stackId="flow"
              stroke="oklch(37.9% 0.146 265.522)"
              fill="oklch(37.9% 0.146 265.522)"
              name="Done"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        Not started, in progress, and done counts, each day from {first.day} to {last.day}.
      </figcaption>
    </figure>
  );
}
