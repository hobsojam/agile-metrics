import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { components } from "../api-types";
import { agingWipThreshold } from "./chartData";

type WipSnapshot = components["schemas"]["WipSnapshot"];
type CycleTimePercentiles = components["schemas"]["FlowMetrics"]["cycle_time_percentiles"];

interface AgingWipChartProps {
  snapshots: WipSnapshot[];
  percentiles: CycleTimePercentiles;
}

// Tailwind's amber-600 oklch value (same sourcing convention as confidenceLevels.ts's
// blue shades), distinct from the blue confidence-level palette so an at-risk bar
// reads as a different signal, not just a darker shade of the same color.
const AT_RISK_COLOR = "oklch(66.6% 0.179 58.318)";
const NORMAL_COLOR = "oklch(70.7% 0.165 254.624)";

/**
 * Every currently-in-progress item, oldest first (spec 011 User Story 2), so a
 * team can spot work that has been open longer than usual. The server already
 * sorts `snapshots` oldest-first; this component renders them as given.
 *
 * When historical cycle-time percentiles are available, overlays the 85th-
 * percentile cycle time as a threshold line and visually flags any item whose
 * age already exceeds it (spec 012 FR-004/FR-005) - omitted entirely when
 * there isn't enough resolved history to trust a percentile (FR-006).
 */
export function AgingWipChart({ snapshots, percentiles }: Readonly<AgingWipChartProps>) {
  if (snapshots.length === 0) {
    return <p className="text-sm text-slate-500">Nothing currently in progress.</p>;
  }

  const data = snapshots.map((snapshot) => ({ label: snapshot.key, days: snapshot.age_days }));
  const oldest = snapshots[0];
  const threshold = agingWipThreshold(percentiles);
  const atRisk = threshold ? snapshots.filter((s) => s.age_days > threshold.days) : [];

  return (
    <figure aria-label="Aging work in progress">
      <h3 className="text-base font-semibold text-slate-900">Aging work in progress</h3>
      <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 24, right: 8, bottom: 24, left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92.9% 0.013 255.508)" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis
              label={{ value: "Days in progress", angle: -90, position: "insideLeft" }}
              allowDecimals={false}
            />
            <Tooltip formatter={(value) => [`${value} days`, ""]} />
            <Bar dataKey="days">
              {data.map((entry) => (
                <Cell
                  key={entry.label}
                  fill={threshold && entry.days > threshold.days ? AT_RISK_COLOR : NORMAL_COLOR}
                />
              ))}
            </Bar>
            {threshold && (
              <ReferenceLine
                y={threshold.days}
                stroke={threshold.color}
                strokeWidth={2}
                label={{
                  value: `${threshold.label} threshold`,
                  position: "right",
                  fill: threshold.color,
                  fontSize: 11,
                }}
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-sm text-slate-500">
        How long each item currently in progress has been open, oldest first.
        {threshold && " Differently-colored bars have passed the historical service level."}
      </figcaption>
      <p className="sr-only">
        {snapshots.length} items in progress. Oldest: {oldest.key}, {oldest.age_days} days.{" "}
        {threshold &&
          (atRisk.length > 0
            ? `${threshold.label} threshold: ${threshold.days} days. ` +
              atRisk.map((s) => `${s.key} (${s.age_days} days) exceeds it`).join(", ") +
              "."
            : `${threshold.label} threshold: ${threshold.days} days. No items exceed it.`)}
      </p>
    </figure>
  );
}
